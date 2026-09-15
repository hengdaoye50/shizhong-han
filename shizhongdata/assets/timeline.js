/* 侍中时间轴 — 折线刻度拉宽三国；只画可考年代，仅朝代者聚合 */
(function () {
  "use strict";

  const canvas = document.getElementById("tl-canvas");
  const listEl = document.getElementById("tl-list");
  const aggEl = document.getElementById("tl-agg");
  if (!canvas) return;

  const COLORS = {
    西漢: "#7e0c6e",
    新: "#9a1a6e",
    更始: "#b04a9a",
    東漢: "#a33d90",
    漢魏之際: "#8a5aaa",
    魏: "#6b3fc4",
    蜀漢: "#b03a6a",
    吳: "#3d6fb5",
    晉: "#5a4a9a",
  };

  const PREC_LABEL = {
    exact: "生卒",
    era: "年号",
    reign: "帝号",
    dynasty: "朝代",
  };

  // 折线刻度：压缩两汉前段空疏期，拉宽 180–285（汉末+三国）
  // [year, visualPos] visualPos ∈ [0,1] 单调
  const SCALE_PTS = [
    [-205, 0],
    [8, 0.22],
    [25, 0.24],
    [180, 0.52],
    [220, 0.68],
    [285, 1.0],
  ];

  function yearToPos(year) {
    if (year <= SCALE_PTS[0][0]) return 0;
    if (year >= SCALE_PTS[SCALE_PTS.length - 1][0]) return 1;
    for (let i = 0; i < SCALE_PTS.length - 1; i++) {
      const [y0, p0] = SCALE_PTS[i];
      const [y1, p1] = SCALE_PTS[i + 1];
      if (year >= y0 && year <= y1) {
        if (y1 === y0) return p0;
        return p0 + ((year - y0) / (y1 - y0)) * (p1 - p0);
      }
    }
    return 1;
  }

  function posToYear(pos) {
    if (pos <= 0) return SCALE_PTS[0][0];
    if (pos >= 1) return SCALE_PTS[SCALE_PTS.length - 1][0];
    for (let i = 0; i < SCALE_PTS.length - 1; i++) {
      const [y0, p0] = SCALE_PTS[i];
      const [y1, p1] = SCALE_PTS[i + 1];
      if (pos >= p0 && pos <= p1) {
        if (p1 === p0) return y0;
        return y0 + ((pos - p0) / (p1 - p0)) * (y1 - y0);
      }
    }
    return SCALE_PTS[SCALE_PTS.length - 1][0];
  }

  // 视图存 visual position，便于非线性缩放/平移
  let data = null;
  let view = { p0: 0, p1: 1 };
  let filter = "all";
  let hover = null;
  let selected = null;
  let drag = null;
  let showLives = true;

  function colorOf(dyn) {
    if (!dyn) return "#a33d90";
    if (dyn.includes("西漢")) return COLORS["西漢"];
    if (dyn.includes("東漢") && !dyn.includes("漢魏")) return COLORS["東漢"];
    if (dyn === "魏" || dyn.startsWith("魏_") || dyn.endsWith("_魏")) return COLORS["魏"];
    if (dyn.includes("蜀")) return COLORS["蜀漢"];
    if (dyn.includes("吳") || dyn.includes("吴")) return COLORS["吳"];
    if (dyn.includes("漢魏")) return COLORS["漢魏之際"];
    return COLORS[dyn] || "#8a5aaa";
  }

  function inFilter(it) {
    if (filter === "all") return true;
    const d = it.dynasty || "";
    const isHan =
      d.includes("西漢") || d.includes("東漢") || d === "兩漢" || d === "更始" || d === "新";
    return filter === "han" ? isHan : !isHan;
  }

  function fmtYear(y) {
    if (y == null) return "?";
    return y < 0 ? "前" + -y : String(y);
  }

  function fmtSpan(a, b) {
    if (a == null && b == null) return "—";
    if (b == null || a === b) return fmtYear(a);
    return fmtYear(a) + "–" + fmtYear(b);
  }

  /** year → px（含 padL） */
  function xOf(year, contentW, padL) {
    const span = view.p1 - view.p0 || 1;
    const p = yearToPos(year);
    return ((p - view.p0) / span) * contentW + padL;
  }

  /** px → year（content 坐标系，不含 pad） */
  function yearAt(mx, contentW, padL) {
    const span = view.p1 - view.p0 || 1;
    const p = view.p0 + ((mx - padL) / contentW) * span;
    return posToYear(p);
  }

  function yearRangeInView() {
    return [posToYear(view.p0), posToYear(view.p1)];
  }

  function visible(it) {
    if (!inFilter(it)) return false;
    const [x0, x1] = yearRangeInView();
    const anchors = [];
    if (it.term) anchors.push(it.term[0], it.term[1]);
    if (it.life) anchors.push(it.life[0], it.life[1]);
    if (!anchors.length) return false;
    return Math.max.apply(null, anchors) >= x0 && Math.min.apply(null, anchors) <= x1;
  }

  function setViewYears(y0, y1) {
    view.p0 = yearToPos(y0);
    view.p1 = yearToPos(y1);
    if (view.p1 - view.p0 < 0.02) view.p1 = view.p0 + 0.02;
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    canvas.getContext("2d").setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  }

  function layout(items, padT, axisY, bandH) {
    const top = padT + bandH + 22;
    const bottom = axisY - 12;
    const rowH = 13.5;
    const rows = Math.max(1, Math.floor((bottom - top) / rowH));
    const slots = new Array(rows).fill(null);
    const placed = [];

    const sorted = items.slice().sort((a, b) => {
      const ay = a.term ? a.term[0] : a.life ? a.life[0] : 0;
      const by = b.term ? b.term[0] : b.life ? b.life[0] : 0;
      return ay - by;
    });

    const rect = canvas.getBoundingClientRect();
    const w = rect.width;
    const padL = 20;
    const padR = 20;
    const contentW = w - padL - padR;

    for (const it of sorted) {
      if (!visible(it)) continue;
      const box = it.term || it.life;
      if (!box) continue;
      const [vx0, vx1] = yearRangeInView();
      const y0 = Math.max(vx0, box[0]);
      const y1 = Math.min(vx1, box[1] != null ? box[1] : box[0]);
      const x0 = xOf(y0, contentW, padL);
      const x1 = xOf(y1, contentW, padL);
      let row = -1;
      for (let r = 0; r < rows; r++) {
        const last = slots[r];
        if (last == null || x0 > last + 8) {
          row = r;
          break;
        }
      }
      if (row < 0) row = placed.length % rows;
      slots[row] = Math.max(slots[row] || 0, x1);
      placed.push({ it, x0, x1, row });
    }

    // 垂直居中：按实际用到的行数留白
    let maxRow = -1;
    for (const p of placed) maxRow = Math.max(maxRow, p.row);
    const used = maxRow + 1;
    const offsetY = Math.max(0, ((rows - used) * rowH) / 2);
    for (const p of placed) {
      p.y = top + p.row * rowH + rowH / 2 + offsetY;
    }
    return placed;
  }

  function drawPerson(ctx, p, contentW, padL) {
    const it = p.it;
    const isOn = (hover && hover.id === it.id) || (selected && selected.id === it.id);
    const col = colorOf(it.dynasty);
    const y = p.y;

    if (showLives && it.life) {
      const [vx0, vx1] = yearRangeInView();
      const a = Math.max(vx0, it.life[0]);
      const b = Math.min(vx1, it.life[1] != null ? it.life[1] : it.life[0]);
      const xa = xOf(a, contentW, padL);
      const xb = xOf(b, contentW, padL);
      ctx.globalAlpha = isOn ? 0.3 : 0.15;
      ctx.fillStyle = col;
      const h = isOn ? 9 : 7;
      const r = h / 2;
      const x0 = Math.min(xa, xb);
      const ww = Math.max(4, Math.abs(xb - xa));
      ctx.beginPath();
      ctx.moveTo(x0 + r, y - h / 2);
      ctx.arcTo(x0 + ww, y - h / 2, x0 + ww, y + h / 2, r);
      ctx.arcTo(x0 + ww, y + h / 2, x0, y + h / 2, r);
      ctx.arcTo(x0, y + h / 2, x0, y - h / 2, r);
      ctx.arcTo(x0, y - h / 2, x0 + ww, y - h / 2, r);
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = 1;
    }

    if (it.term) {
      const [vx0, vx1] = yearRangeInView();
      const a = Math.max(vx0, it.term[0]);
      const b = Math.min(vx1, it.term[1] != null ? it.term[1] : it.term[0]);
      const xa = xOf(a, contentW, padL);
      const xb = xOf(b, contentW, padL);
      const span = Math.abs(xb - xa);

      if (it.precision === "era") {
        ctx.strokeStyle = col;
        ctx.fillStyle = col;
        ctx.globalAlpha = isOn ? 1 : 0.8;
        ctx.lineWidth = isOn ? 2.5 : 1.5;
        if (span > 3) {
          ctx.beginPath();
          ctx.moveTo(xa, y);
          ctx.lineTo(xb, y);
          ctx.stroke();
        }
        ctx.beginPath();
        ctx.arc((xa + xb) / 2, y, isOn ? 5.2 : 3.4, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      } else if (it.precision === "reign") {
        ctx.globalAlpha = isOn ? 0.4 : 0.2;
        ctx.fillStyle = col;
        const h = isOn ? 11 : 8;
        ctx.fillRect(xa, y - h / 2, Math.max(3, xb - xa), h);
        ctx.globalAlpha = isOn ? 1 : 0.6;
        ctx.strokeStyle = col;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(xa, y);
        ctx.lineTo(xb, y);
        ctx.stroke();
        ctx.globalAlpha = 1;
      } else {
        ctx.strokeStyle = col;
        ctx.globalAlpha = isOn ? 1 : 0.85;
        ctx.lineWidth = isOn ? 2.5 : 1.8;
        ctx.beginPath();
        ctx.moveTo((xa + xb) / 2, y - 5.5);
        ctx.lineTo((xa + xb) / 2, y + 5.5);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
    } else if (it.life) {
      const pts = [it.life[0]];
      if (it.life[1] != null && it.life[1] !== it.life[0]) pts.push(it.life[1]);
      ctx.fillStyle = col;
      ctx.globalAlpha = isOn ? 1 : 0.75;
      for (const yy of pts) {
        const [vx0, vx1] = yearRangeInView();
        if (yy < vx0 || yy > vx1) continue;
        ctx.beginPath();
        ctx.arc(xOf(yy, contentW, padL), y, isOn ? 4.4 : 3, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }

    if (isOn) {
      const label =
        it.name + " · " + (it.term_label || fmtSpan(it.life && it.life[0], it.life && it.life[1]));
      ctx.font = "12px sans-serif";
      const tw = ctx.measureText(label).width;
      const lx = Math.min(contentW + padL - tw - 12, Math.max(8, p.x0 + 10));
      ctx.fillStyle = "rgba(255,250,253,0.95)";
      ctx.fillRect(lx - 4, y - 22, tw + 8, 18);
      ctx.strokeStyle = "rgba(126,12,110,0.22)";
      ctx.strokeRect(lx - 4, y - 22, tw + 8, 18);
      ctx.fillStyle = "#1a0a18";
      ctx.fillText(label, lx, y - 9);
    }
  }

  /** 在当前折线刻度下取合适年刻度步长 */
  function tickYears() {
    const [y0, y1] = yearRangeInView();
    const span = y1 - y0;
    // 三国段已拉宽，可用更密的年号级刻度
    if (span > 400) return { major: 50, minor: null };
    if (span > 220) return { major: 25, minor: null };
    if (span > 120) return { major: 20, minor: 10 };
    if (span > 60) return { major: 10, minor: 5 };
    if (span > 30) return { major: 5, minor: 1 };
    return { major: 2, minor: 1 };
  }

  function draw() {
    if (!data) return;
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    const padL = 20;
    const padR = 20;
    const contentW = w - padL - padR;
    const padT = 24;
    const axisY = h - 44;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#fffafd";
    ctx.fillRect(0, 0, w, h);

    const [vx0, vx1] = yearRangeInView();

    // 朝代色带（三国并行细带，避免同时代叠色）
    const threeKs = [
      { name: "魏", start: 220, end: 265 },
      { name: "蜀漢", start: 221, end: 263 },
      { name: "吳", start: 222, end: 280 },
    ];
    const mainBands = (data.bands || []).filter(
      (b) => b.name !== "魏" && b.name !== "蜀漢" && b.name !== "吳"
    );

    function drawBandRect(b, y, h, opts) {
      if (b.end < vx0 || b.start > vx1) return;
      const x0 = Math.max(padL, xOf(b.start, contentW, padL));
      const x1 = Math.min(w - padR, xOf(b.end, contentW, padL));
      if (x1 - x0 < 1) return;
      const col = colorOf(b.name);
      const strong = opts && opts.strong;
      ctx.fillStyle = col;
      ctx.globalAlpha = strong ? 0.24 : 0.1;
      ctx.fillRect(x0, y, x1 - x0, h);
      ctx.globalAlpha = 1;
      ctx.fillStyle = col;
      ctx.fillRect(x0, y, strong ? 3 : 2, h);
      if (strong) {
        ctx.globalAlpha = 0.5;
        ctx.fillRect(x0, y, x1 - x0, 1.5);
        ctx.globalAlpha = 1;
      }
      ctx.font = strong ? "bold 11px sans-serif" : "12px sans-serif";
      const label = b.name;
      const tw = ctx.measureText(label).width;
      let lx = x0 + 7;
      if (x1 - x0 < tw + 12) lx = Math.max(padL, Math.min(x0 + 2, w - padR - tw - 2));
      ctx.fillStyle = strong ? col : "#5c4558";
      ctx.fillText(label, lx, y + h / 2 + 3.5);

      if (!strong) {
        const agg = (data.aggregates || []).find((a) => a.dynasty === b.name);
        if (agg && agg.count && x1 - x0 > 56) {
          ctx.font = "10px sans-serif";
          ctx.fillStyle = "#8a6d84";
          ctx.fillText("仅朝代 " + agg.count, x0 + 7, y + h - 5);
        }
      }
    }

    // 主朝代：单条（含计数）
    const mainH = 30;
    for (const b of mainBands) {
      drawBandRect(b, padT, mainH, { strong: false });
    }

    // 魏蜀吴：三条并行
    const subH = 12;
    const subTop = padT + mainH + 2;
    threeKs.forEach((b, i) => {
      drawBandRect(b, subTop + i * subH, subH - 1, { strong: true });
    });
    const bandH = mainH + 2 + threeKs.length * subH;

    // 汉末/三国分界提示线
    const sep = xOf(220, contentW, padL);
    if (sep > padL && sep < w - padR) {
      ctx.strokeStyle = "rgba(107,63,196,0.25)";
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(sep, padT);
      ctx.lineTo(sep, axisY);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = "10px sans-serif";
      ctx.fillStyle = "#8a5aaa";
      ctx.fillText("魏黄初", Math.min(sep + 4, w - 48), padT + bandH + 12);
    }

    // 帝号细刻度
    ctx.strokeStyle = "rgba(126,12,110,0.14)";
    ctx.fillStyle = "#b9a3b5";
    ctx.font = "10px sans-serif";
    for (const e of data.emperors || []) {
      if (e.end < vx0 || e.start > vx1) continue;
      const xa = xOf(e.start, contentW, padL);
      const xb = xOf(e.end, contentW, padL);
      if (xb - xa < 16) continue;
      ctx.beginPath();
      ctx.moveTo(xa, padT + bandH + 6);
      ctx.lineTo(xb, padT + bandH + 6);
      ctx.stroke();
      ctx.fillText(e.name, xa + 2, padT + bandH + 17);
    }

    // 年网格（折线刻度下按年取整，避免点距不均）
    const ticks = tickYears();
    ctx.strokeStyle = "rgba(126,12,110,0.07)";
    ctx.fillStyle = "#8a6d84";
    ctx.font = "11px sans-serif";
    const t0 = Math.ceil(vx0 / ticks.major) * ticks.major;
    for (let y = t0; y <= vx1; y += ticks.major) {
      const x = xOf(y, contentW, padL);
      if (x < padL - 2 || x > w - padR + 2) continue;
      ctx.beginPath();
      ctx.moveTo(x, padT);
      ctx.lineTo(x, axisY);
      ctx.stroke();
      const lab = y < 0 ? "前" + -y : String(y);
      ctx.fillText(lab, x - ctx.measureText(lab).width / 2, axisY + 20);
    }
    if (ticks.minor) {
      ctx.strokeStyle = "rgba(126,12,110,0.04)";
      const m0 = Math.ceil(vx0 / ticks.minor) * ticks.minor;
      for (let y = m0; y <= vx1; y += ticks.minor) {
        if (y % ticks.major === 0) continue;
        const x = xOf(y, contentW, padL);
        if (x < padL || x > w - padR) continue;
        ctx.beginPath();
        ctx.moveTo(x, padT + 20);
        ctx.lineTo(x, axisY);
        ctx.stroke();
      }
    }

    // 主轴
    ctx.strokeStyle = "rgba(126,12,110,0.35)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL, axisY);
    ctx.lineTo(w - padR, axisY);
    ctx.stroke();

    // 人物
    const items = data.items.filter(inFilter);
    const placed = layout(items, padT, axisY, bandH);
    for (const p of placed) {
      drawPerson(ctx, p, contentW, padL);
    }
    draw._boxes = placed;
    draw._geo = { padL, padR, contentW, padT, axisY, bandH };
  }

  function hitTest(mx, my) {
    const boxes = draw._boxes || [];
    let best = null;
    let bestD = 12;
    for (const p of boxes) {
      const x0 = Math.min(p.x0, p.x1) - 6;
      const x1 = Math.max(p.x0, p.x1) + 6;
      if (mx >= x0 && mx <= x1 && Math.abs(my - p.y) < 8) {
        const d = Math.abs(my - p.y);
        if (d < bestD) {
          bestD = d;
          best = p.it;
        }
      }
    }
    return best;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(
      /[&<>"]/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])
    );
  }

  function yearText(it) {
    if (it.term) return fmtSpan(it.term[0], it.term[1]);
    if (it.life) return fmtSpan(it.life[0], it.life[1]);
    return "—";
  }

  function renderList() {
    if (!data) return;
    const items = data.items.filter(inFilter).slice();
    document.getElementById("tl-count").textContent = items.length;
    document.getElementById("tl-agg-count").textContent = (data.aggregates || [])
      .filter((a) => {
        if (filter === "all") return true;
        const d = a.dynasty || "";
        const isHan =
          d.includes("西漢") || d.includes("東漢") || d === "兩漢" || d === "更始" || d === "新";
        return filter === "han" ? isHan : !isHan;
      })
      .reduce((s, a) => s + (a.count || 0), 0);

    listEl.innerHTML = items
      .map((it) => {
        const on = selected && selected.id === it.id ? " on" : "";
        const prec = PREC_LABEL[it.precision] || it.precision;
        const style = it.style && it.style !== "阙" ? "字" + it.style : "";
        const detail = it.term_label || (it.nature || "").slice(0, 24);
        return `<div class="tl-row${on}" data-id="${esc(it.id)}">
          <span class="tl-prec p-${esc(it.precision)}">${esc(prec)}</span>
          <span class="tl-year">${esc(yearText(it))}</span>
          <span class="tl-name">${esc(it.name)}${style ? ' <span class="tl-style">' + esc(style) + "</span>" : ""}</span>
          <span class="tl-dyn">${esc(it.dynasty || "")}</span>
          <span class="tl-nat">${esc(detail)}</span>
        </div>`;
      })
      .join("");

    listEl.querySelectorAll(".tl-row").forEach((row) => {
      row.addEventListener("click", () => {
        selected = data.items.find((x) => x.id === row.getAttribute("data-id"));
        renderList();
        draw();
      });
    });

    renderAgg();
  }

  function renderAgg() {
    if (!aggEl || !data) return;
    const aggs = (data.aggregates || []).filter((a) => {
      if (filter === "all") return true;
      const d = a.dynasty || "";
      const isHan =
        d.includes("西漢") || d.includes("東漢") || d === "兩漢" || d === "更始" || d === "新";
      return filter === "han" ? isHan : !isHan;
    });
    aggEl.innerHTML = aggs
      .map((a) => {
        const col = colorOf(a.dynasty);
        const names = (a.names || []).slice(0, 12).join("、");
        const more = (a.count || 0) > 12 ? " 等" : "";
        return `<div class="agg-card" style="--c:${col}">
          <div class="agg-head">
            <strong>${esc(a.dynasty)}</strong>
            <span>${a.count} 人 · 仅知朝代</span>
          </div>
          <div class="agg-names">${esc(names)}${more}</div>
        </div>`;
      })
      .join("");
  }

  canvas.addEventListener("mousemove", (e) => {
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left;
    const my = e.clientY - r.top;
    if (drag) {
      const geo = draw._geo || { contentW: r.width - 40, padL: 20 };
      const dPos = ((mx - drag.x) / geo.contentW) * (view.p1 - view.p0);
      view.p0 -= dPos;
      view.p1 -= dPos;
      // 钳制
      if (view.p0 < -0.05) {
        view.p1 += -0.05 - view.p0;
        view.p0 = -0.05;
      }
      if (view.p1 > 1.05) {
        view.p0 -= view.p1 - 1.05;
        view.p1 = 1.05;
      }
      drag.x = mx;
      draw();
      return;
    }
    hover = hitTest(mx, my);
    canvas.style.cursor = hover ? "pointer" : "grab";
    draw();
  });
  canvas.addEventListener("mousedown", (e) => {
    const r = canvas.getBoundingClientRect();
    drag = { x: e.clientX - r.left };
  });
  window.addEventListener("mouseup", () => (drag = null));
  canvas.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      const geo = draw._geo || { contentW: canvas.getBoundingClientRect().width - 40, padL: 20 };
      const r = canvas.getBoundingClientRect();
      const mx = e.clientX - r.left;
      const f = Math.max(0, Math.min(1, (mx - geo.padL) / geo.contentW));
      const tPos = view.p0 + f * (view.p1 - view.p0);
      const k = e.deltaY > 0 ? 1.12 : 0.89;
      const span = (view.p1 - view.p0) * k;
      if (span < 0.03 || span > 1.2) return;
      view.p0 = tPos - span * f;
      view.p1 = view.p0 + span;
      if (view.p0 < -0.05) {
        view.p1 += -0.05 - view.p0;
        view.p0 = -0.05;
      }
      if (view.p1 > 1.05) {
        view.p0 -= view.p1 - 1.05;
        view.p1 = 1.05;
      }
      draw();
    },
    { passive: false }
  );

  document.querySelectorAll("[data-range]").forEach((btn) => {
    btn.addEventListener("click", () => {
      filter = btn.getAttribute("data-range");
      document.querySelectorAll("[data-range]").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      if (filter === "han") {
        setViewYears(-205, 230);
      } else if (filter === "wei") {
        setViewYears(175, 285);
      } else {
        setViewYears(-205, 285);
      }
      selected = null;
      renderList();
      draw();
    });
  });

  const lifeBtn = document.getElementById("tl-toggle-life");
  if (lifeBtn) {
    lifeBtn.addEventListener("click", () => {
      showLives = !showLives;
      lifeBtn.classList.toggle("active", showLives);
      lifeBtn.textContent = showLives ? "寿命条：开" : "寿命条：关";
      draw();
    });
  }

  fetch("data/timeline.json")
    .then((r) => r.json())
    .then((d) => {
      data = d;
      setViewYears(-205, 285);
      const m = d.meta || {};
      const nExact = (m.stats && m.stats.exact) || 0;
      const nEra = (m.stats && m.stats.era) || 0;
      const nReign = (m.stats && m.stats.reign) || 0;
      const el = document.getElementById("tl-meta-note");
      if (el) {
        el.textContent =
          "可定位 " +
          (m.plotted || 0) +
          " 人（生卒 " +
          nExact +
          " · 年号 " +
          nEra +
          " · 帝号 " +
          nReign +
          "）；仅知朝代 " +
          (m.aggregated || 0) +
          " 人不画个人横条，见下方聚合。横轴为折线刻度：汉末—三国段已拉宽。";
      }
      resize();
      renderList();
      window.addEventListener("resize", resize);
    })
    .catch((err) => {
      listEl.innerHTML = "<p style=padding:12px>加载失败 " + esc(err) + "</p>";
    });
})();
