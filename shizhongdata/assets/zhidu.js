/* 制度沿革页 */
(function () {
  const phaseRail = document.getElementById("phase-rail");
  const phaseHost = document.getElementById("phase-host");
  const gapBody = document.getElementById("gap-body");
  const noteList = document.getElementById("roster-notes");
  const sourceList = document.getElementById("source-list");
  const el = (id) => document.getElementById(id);

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderStats(data) {
    const st = data.stats || {};
    const rc = data.roster_check || {};
    el("stat-phases").textContent = (data.phases || []).length;
    el("stat-quotes").textContent = st.institution_page_quotes || 0;
    el("stat-corpus").textContent = st.corpus_sentences_scanned || st.sentences_total || "—";
    el("stat-gaps").textContent = (rc.gaps || []).length;
    el("stat-roster").textContent = rc.roster_size || 258;
  }

  function renderRail(phases) {
    phaseRail.innerHTML = "";
    phases.forEach((p, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = p.title.replace(/^.*：/, "");
      b.dataset.phase = p.id;
      if (i === 0) b.classList.add("active");
      b.addEventListener("click", () => {
        const sec = document.getElementById("phase-" + p.id);
        if (sec) sec.scrollIntoView({ behavior: "smooth", block: "start" });
        phaseRail.querySelectorAll("button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
      });
      phaseRail.appendChild(b);
    });
  }

  function renderPhases(phases) {
    phaseHost.innerHTML = phases
      .map((p) => {
        const themes = (p.themes || [])
          .map((t) => `<span>${esc(t)}</span>`)
          .join("");
        const curated = (p.curated_points || [])
          .map((t) => `<p>${esc(t)}</p>`)
          .join("");
        const quotes = (p.quotes || [])
          .map(
            (q) => `
        <article class="quote-card">
          <div class="quote-meta">
            <span class="book">${esc(q.book)}</span>
            <span class="juan">${esc(q.juan)}</span>
            <span class="kind">${esc(q.kind || "史料")}</span>
          </div>
          <p class="quote-text">${esc(q.sentence)}</p>
        </article>`
          )
          .join("");
        return `
      <section class="phase-section" id="phase-${esc(p.id)}">
        <h3>${esc(p.title)}</h3>
        <div><span class="phase-range">${esc(p.range)}</span></div>
        <div class="theme-chips">${themes}</div>
        <p class="phase-summary">${esc(p.summary)}</p>
        ${curated ? `<div class="curated-box">${curated}</div>` : ""}
        <div class="quote-list">${quotes || '<p class="phase-summary">本阶段史料句较少，详见语料库。</p>'}</div>
      </section>`;
      })
      .join("");
  }

  function renderGaps(rc) {
    const gaps = rc.gaps || [];
    gapBody.innerHTML = gaps
      .map((g) => {
        const conf = g.confidence === "高" ? "high" : "mid";
        return `<tr>
          <td class="name">${esc(g.name)}</td>
          <td>${esc(g.dynasty_guess || "")}</td>
          <td><span class="badge ${conf}">${esc(g.confidence || "")}</span></td>
          <td>${esc(g.status || "")}</td>
          <td>${esc(g.evidence || "")}<br/><span style="color:#8a6d84;font-size:0.8em">${esc(g.source || "")}</span></td>
          <td>${esc(g.note || "")}</td>
        </tr>`;
      })
      .join("");
    noteList.innerHTML = (rc.notes || []).map((n) => `<li>${esc(n)}</li>`).join("");
    sourceList.innerHTML = (dataSources() || [])
      .map((s) => `<li>${esc(s)}</li>`)
      .join("");
  }

  let _data = null;
  function dataSources() {
    return (_data && _data.sources_note) || [];
  }

  function onScrollSpy() {
    const secs = [...document.querySelectorAll(".phase-section")];
    let cur = secs[0];
    const y = window.scrollY + 160;
    for (const s of secs) {
      if (s.offsetTop <= y) cur = s;
    }
    if (!cur) return;
    const id = cur.id.replace("phase-", "");
    phaseRail.querySelectorAll("button").forEach((b) => {
      b.classList.toggle("active", b.dataset.phase === id);
    });
  }

  fetch("data/institution.json")
    .then((r) => r.json())
    .then((data) => {
      _data = data;
      renderStats(data);
      renderRail(data.phases || []);
      renderPhases(data.phases || []);
      renderGaps(data.roster_check || {});
      el("zhidu-updated").textContent = data.updated || "";
      window.addEventListener("scroll", onScrollSpy, { passive: true });
    })
    .catch((err) => {
      phaseHost.innerHTML = `<p class="phase-summary">制度数据加载失败：${esc(err)}</p>`;
    });
})();
