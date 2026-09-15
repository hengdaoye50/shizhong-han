/* 两汉侍中 Web UI */
(function () {
  "use strict";

  const state = {
    data: null,
    query: "",
    dynasty: "全部",
    sort: "dynasty",
  };

  const $ = (sel) => document.querySelector(sel);
  const grid = $("#person-grid");
  const detail = $("#detail");
  const backdrop = $("#detail-backdrop");
  const empty = $("#empty-state");

  async function load() {
    const res = await fetch("data/shizhong.json");
    state.data = await res.json();
    const m = state.data.meta;
    $("#stat-persons").textContent = m.person_count;
    $("#stat-relations").textContent = m.relation_count;
    $("#stat-sources").textContent = m.source_count;
    $("#updated").textContent = "更新 " + m.updated;
    renderFilters();
    render();
    await initGraph();
  }

  async function initGraph() {
    const canvas = $("#graph-canvas");
    if (!canvas || !window.ShizhongGraph) return;
    try {
      const gres = await fetch("data/graph.json");
      const gdata = await gres.json();
      const meta = document.querySelector(".graph-overlay .eyebrow");
      if (meta) {
        meta.textContent =
          "Knowledge Graph · " +
          gdata.meta.node_count +
          " nodes · " +
          gdata.meta.link_count +
          " edges";
      }
      const ctrl = window.ShizhongGraph.init(canvas, gdata, {
        autoRotate: true,
        onNodeClick(n) {
          openDetail(n.id);
        },
        onHover(n) {
          const hint = $("#graph-hint");
          if (!hint) return;
          hint.textContent = n
            ? n.name + " · " + n.dynasty + " · 关系 " + (n.degree || 0)
            : "悬停或点击节点 · 滚轮缩放 · 拖拽改变视角";
        },
      });
      const btnRotate = $("#btn-rotate");
      let rotating = true;
      btnRotate.addEventListener("click", () => {
        rotating = !rotating;
        ctrl.setAutoRotate(rotating);
        btnRotate.classList.toggle("active", rotating);
        btnRotate.textContent = rotating ? "自转" : "暂停";
      });
      $("#btn-reset").addEventListener("click", () => {
        // soft reload of scale via dummy — re-init not needed; just nudge hint
        const hint = $("#graph-hint");
        if (hint) hint.textContent = "拖拽旋转 · 滚轮缩放 · 点击打开卡片";
      });
    } catch (err) {
      console.warn("graph load failed", err);
    }
  }

  function renderChips() {
    const el = $("#dynasty-chips");
    const counts = state.data.dynasty_counts;
    const order = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    el.innerHTML = order
      .map(
        ([k, v]) =>
          `<span class="dyn-chip"><strong>${v}</strong> ${escapeHtml(k)}</span>`
      )
      .join("");
  }

  function renderFilters() {
    const el = $("#dynasty-filters");
    const keys = ["全部", ...Object.keys(state.data.dynasty_counts).sort()];
    el.innerHTML = keys
      .map(
        (k) =>
          `<button type="button" class="chip${k === state.dynasty ? " active" : ""}" data-dyn="${escapeAttr(k)}">${escapeHtml(k)}</button>`
      )
      .join("");
    el.querySelectorAll("[data-dyn]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.dynasty = btn.getAttribute("data-dyn");
        el.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        btn.classList.add("active");
        render();
      });
    });
  }

  function filtered() {
    let list = state.data.persons.slice();
    if (state.dynasty !== "全部") {
      list = list.filter((p) => p.dynasty === state.dynasty);
    }
    const q = state.query.trim().toLowerCase();
    if (q) {
      list = list.filter((p) => {
        const blob = [p.name, p.style_name, p.origin, p.category, p.dynasty, (p.tags || []).join(" ")]
          .join(" ")
          .toLowerCase();
        return blob.includes(q);
      });
    }
    if (state.sort === "name") {
      list.sort((a, b) => a.name.localeCompare(b.name, "zh"));
    } else if (state.sort === "terms") {
      list.sort((a, b) => (b.n_terms || 0) - (a.n_terms || 0) || a.name.localeCompare(b.name, "zh"));
    } else {
      list.sort(
        (a, b) =>
          (a.dynasty || "").localeCompare(b.dynasty || "", "zh") ||
          a.name.localeCompare(b.name, "zh")
      );
    }
    return list;
  }

  function render() {
    const list = filtered();
    $("#result-count").textContent = `显示 ${list.length} / ${state.data.persons.length} 人`;
    if (!list.length) {
      grid.innerHTML = "";
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    const frag = document.createDocumentFragment();
    list.forEach((p) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "person-card";
      btn.dataset.id = p.id;
      btn.innerHTML = `
        <div class="pc-top">
          <div>
            <h3 class="pc-name">${escapeHtml(p.name)}</h3>
            ${p.style_name && p.style_name !== "阙" ? `<p class="pc-style">字 ${escapeHtml(p.style_name)}</p>` : ""}
          </div>
          <span class="pc-dyn">${escapeHtml(p.dynasty || "—")}</span>
        </div>
        <div class="pc-meta">
          ${p.origin && p.origin !== "阙" ? `<span>${escapeHtml(p.origin)}</span>` : ""}
          ${(p.tags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}
        </div>
        <div class="pc-foot">任职记录 ${p.n_terms} · 史料 ${p.n_sources}</div>
      `;
      btn.addEventListener("click", () => openDetail(p.id));
      frag.appendChild(btn);
    });
    grid.innerHTML = "";
    grid.appendChild(frag);
  }

  function openDetail(id) {
    const p = state.data.persons.find((x) => x.id === id);
    if (!p) return;
    const body = $("#detail-body");
    const relOut = (p.relations_out || []).filter((r) => r.to_name);
    const relIn = (p.relations_in || []).filter((r) => r.to_name);

    body.innerHTML = `
      <p class="sub" style="margin-top:8px">${escapeHtml(p.dynasty)}${p.category ? " · " + escapeHtml(p.category) : ""}</p>
      <h2>${escapeHtml(p.name)}${p.style_name && p.style_name !== "阙" ? ` <span style="font-size:0.7em;font-weight:400;color:var(--ink-3)">字 ${escapeHtml(p.style_name)}</span>` : ""}</h2>
      <p class="sub">${[p.origin, p.birth, p.death].filter((x) => x && x !== "阙").map(escapeHtml).join(" · ") || "籍贯生卒待考"}</p>

      <section>
        <h3>任职</h3>
        ${(p.terms || [])
          .map(
            (t) =>
              `<p class="quote-block">${escapeHtml(t.nature || t.nature_primary || "侍中")}<span class="src">${escapeHtml([t.start_ym, t.end_ym].filter(Boolean).join(" — ") || "起讫待考")} · ${escapeHtml(t.evidence || "")}</span></p>`
          )
          .join("") || `<p style="color:var(--ink-soft);font-size:0.9rem">暂无任职结构化记录</p>`}
      </section>

      <section>
        <h3>原典</h3>
        ${(p.sources || [])
          .map(
            (s) =>
              `<blockquote class="quote-block">${escapeHtml(s.quote || "")}<span class="src">${escapeHtml(s.book)} ${escapeHtml(s.juan || "")}</span></blockquote>`
          )
          .join("") || `<p style="color:var(--ink-soft);font-size:0.9rem">暂无引文</p>`}
      </section>

      <section>
        <h3>关系</h3>
        <ul class="rel-list">
          ${relOut
            .map(
              (r) =>
                `<li><span class="type">${escapeHtml(r.rel_primary || "关系")}</span>${escapeHtml(r.to_name)}${r.note ? ` <span style="color:var(--ink-soft);font-size:0.85em">— ${escapeHtml(r.note)}</span>` : ""}</li>`
            )
            .join("")}
          ${relIn
            .map(
              (r) =>
                `<li><span class="type">← ${escapeHtml(r.rel_primary || "关系")}</span>${escapeHtml(r.to_name)}</li>`
            )
            .join("")}
        </ul>
        ${!relOut.length && !relIn.length ? `<p style="color:var(--ink-soft);font-size:0.9rem">暂无关系边</p>` : ""}
      </section>
    `;
    detail.hidden = false;
    backdrop.hidden = false;
    document.body.style.overflow = "hidden";
    $("#detail-close").focus();
  }

  function closeDetail() {
    detail.hidden = true;
    backdrop.hidden = true;
    document.body.style.overflow = "";
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  function bind() {
    $("#search").addEventListener("input", (e) => {
      state.query = e.target.value;
      render();
    });
    document.querySelectorAll("[data-sort]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.sort = btn.getAttribute("data-sort");
        document.querySelectorAll("[data-sort]").forEach((c) => c.classList.remove("active"));
        btn.classList.add("active");
        render();
      });
    });
    $("#detail-close").addEventListener("click", closeDetail);
    backdrop.addEventListener("click", closeDetail);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !detail.hidden) closeDetail();
    });
  }

  bind();
  load().catch((err) => {
    $("#result-count").textContent = "数据加载失败：" + err.message;
  });
})();
