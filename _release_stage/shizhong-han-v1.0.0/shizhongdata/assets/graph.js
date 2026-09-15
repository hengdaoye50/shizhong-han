/* 3D force graph · canvas · auto-rotate · #7E0C6E */
(function () {
  "use strict";

  const PRIMARY = [126, 12, 110];
  const ACCENT = [196, 122, 224];

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function mixRGB(c1, c2, t) {
    return `rgb(${Math.round(lerp(c1[0], c2[0], t))},${Math.round(lerp(c1[1], c2[1], t))},${Math.round(lerp(c1[2], c2[2], t))})`;
  }

  window.ShizhongGraph = {
    init(canvas, graphData, opts) {
      const o = Object.assign(
        {
          autoRotate: true,
          rotateSpeed: 0.0004,
          onNodeClick: null,
          onHover: null,
        },
        opts || {}
      );

      const nodes = graphData.nodes.map((n, i) => ({
        ...n,
        x: Math.cos((i / graphData.nodes.length) * Math.PI * 2) * (180 + (i % 7) * 18),
        y: Math.sin((i / graphData.nodes.length) * Math.PI * 2 * 1.3) * (120 + (i % 5) * 22),
        z: Math.sin((i / graphData.nodes.length) * Math.PI * 2) * (100 + (i % 3) * 40),
        vx: 0,
        vy: 0,
        vz: 0,
      }));
      const idMap = {};
      nodes.forEach((n) => (idMap[n.id] = n));
      const links = graphData.links
        .map((l) => ({
          source: idMap[l.source],
          target: idMap[l.target],
          type: l.type,
        }))
        .filter((l) => l.source && l.target);

      const maxDeg = Math.max(1, ...nodes.map((n) => n.degree || 1));

      const ctx = canvas.getContext("2d");
      let W = 0;
      let H = 0;
      let dpr = 1;
      let rotY = 0.35;
      let rotX = 0.42;
      let scale = 1;
      let targetScale = 1;
      let running = true;
      let hover = null;
      let drag = null;
      let lastT = 0;

      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      function resize() {
        const rect = canvas.getBoundingClientRect();
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        W = rect.width;
        H = rect.height;
        canvas.width = Math.floor(W * dpr);
        canvas.height = Math.floor(H * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        scale = targetScale = Math.min(W, H) / 720;
      }

      function project(n) {
        const cosY = Math.cos(rotY);
        const sinY = Math.sin(rotY);
        const cosX = Math.cos(rotX);
        const sinX = Math.sin(rotX);
        let x = n.x;
        let y = n.y;
        let z = n.z;
        // Y then X
        let x1 = x * cosY - z * sinY;
        let z1 = x * sinY + z * cosY;
        let y1 = y * cosX - z1 * sinX;
        let z2 = y * sinX + z1 * cosX;
        const persp = 520 / (520 + z2);
        return {
          sx: W / 2 + x1 * persp * scale,
          sy: H / 2 + y1 * persp * scale,
          z: z2,
          s: persp,
        };
      }

      function tick(dt) {
        // repulsion
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const a = nodes[i];
            const b = nodes[j];
            let dx = a.x - b.x;
            let dy = a.y - b.y;
            let dz = a.z - b.z;
            let d2 = dx * dx + dy * dy + dz * dz + 0.01;
            let f = 900 / d2;
            let d = Math.sqrt(d2);
            dx /= d;
            dy /= d;
            dz /= d;
            a.vx += dx * f;
            a.vy += dy * f;
            a.vz += dz * f;
            b.vx -= dx * f;
            b.vy -= dy * f;
            b.vz -= dz * f;
          }
        }
        // springs
        for (const l of links) {
          const a = l.source;
          const b = l.target;
          let dx = b.x - a.x;
          let dy = b.y - a.y;
          let dz = b.z - a.z;
          let d = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01;
          const rest = 95;
          const k = 0.012 * (d - rest);
          dx = (dx / d) * k;
          dy = (dy / d) * k;
          dz = (dz / d) * k;
          a.vx += dx;
          a.vy += dy;
          a.vz += dz;
          b.vx -= dx;
          b.vy -= dy;
          b.vz -= dz;
        }
        // center gravity + integrate
        for (const n of nodes) {
          n.vx -= n.x * 0.0022;
          n.vy -= n.y * 0.0022;
          n.vz -= n.z * 0.0022;
          n.vx *= 0.86;
          n.vy *= 0.86;
          n.vz *= 0.86;
          n.x += n.vx * dt;
          n.y += n.vy * dt;
          n.z += n.vz * dt;
        }
      }

      function nodeRadius(n) {
        const t = (n.degree || 1) / maxDeg;
        return (3.5 + t * 11) * scale;
      }

      function draw() {
        ctx.clearRect(0, 0, W, H);

        // 浅色纸本底 + 柔和紫晕
        ctx.fillStyle = "#fffafd";
        ctx.fillRect(0, 0, W, H);
        const g0 = ctx.createRadialGradient(W / 2, H / 2, 40, W / 2, H / 2, Math.max(W, H) * 0.55);
        g0.addColorStop(0, "rgba(126,12,110,0.1)");
        g0.addColorStop(1, "rgba(126,12,110,0)");
        ctx.fillStyle = g0;
        ctx.fillRect(0, 0, W, H);

        const projected = nodes.map((n) => ({ n, p: project(n) }));
        projected.sort((a, b) => a.p.z - b.p.z);

        // edges
        ctx.lineWidth = 1;
        for (const l of links) {
          const a = project(l.source);
          const b = project(l.target);
          const depth = (a.s + b.s) * 0.5;
          const alpha = 0.18 + depth * 0.28;
          ctx.strokeStyle = `rgba(126,12,110,${alpha})`;
          ctx.beginPath();
          ctx.moveTo(a.sx, a.sy);
          ctx.lineTo(b.sx, b.sy);
          ctx.stroke();
        }

        // nodes
        for (const { n, p } of projected) {
          const r = nodeRadius(n);
          const t = (n.degree || 1) / maxDeg;
          const col = mixRGB(PRIMARY, ACCENT, t * 0.65);
          const isHover = hover && hover.id === n.id;

          // glow
          const glow = ctx.createRadialGradient(p.sx, p.sy, r * 0.2, p.sx, p.sy, r * 2.8);
          glow.addColorStop(0, `rgba(163,61,144,${0.2 * p.s})`);
          glow.addColorStop(1, "rgba(163,61,144,0)");
          ctx.fillStyle = glow;
          ctx.beginPath();
          ctx.arc(p.sx, p.sy, r * 2.8, 0, Math.PI * 2);
          ctx.fill();

          // body
          const grad = ctx.createRadialGradient(
            p.sx - r * 0.35,
            p.sy - r * 0.35,
            r * 0.1,
            p.sx,
            p.sy,
            r
          );
          grad.addColorStop(0, isHover ? "rgba(255,255,255,0.9)" : "rgba(200,120,180,0.95)");
          grad.addColorStop(1, col);
          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(p.sx, p.sy, r, 0, Math.PI * 2);
          ctx.fill();

          // rim
          ctx.strokeStyle = isHover ? "rgba(126,12,110,0.55)" : "rgba(126,12,110,0.25)";
          ctx.lineWidth = isHover ? 1.6 : 0.8;
          ctx.stroke();
        }
      }

      function hit(mx, my) {
        let best = null;
        let bestD = 18;
        for (const n of nodes) {
          const p = project(n);
          const dx = p.sx - mx;
          const dy = p.sy - my;
          const d = Math.sqrt(dx * dx + dy * dy);
          const r = nodeRadius(n) + 6;
          if (d < r && d < bestD + r * 0.5) {
            if (!best || p.z > best.p.z) best = { n, p, d };
          }
        }
        return best ? best.n : null;
      }

      function frame(t) {
        if (!running) return;
        const dt = Math.min(32, t - lastT || 16) / 16;
        lastT = t;
        if (!reduceMotion && o.autoRotate && !drag) {
          rotY += o.rotateSpeed * dt * 16;
        }
        scale += (targetScale - scale) * 0.08;
        // warmup physics stronger, then settle
        tick(dt * (t < 4000 ? 1.1 : 0.55));
        draw();
        requestAnimationFrame(frame);
      }

      function onMove(e) {
        const rect = canvas.getBoundingClientRect();
        const mx = (e.clientX ?? e.touches?.[0]?.clientX) - rect.left;
        const my = (e.clientY ?? e.touches?.[0]?.clientY) - rect.top;
        if (drag) {
          rotY += (mx - drag.x) * 0.008;
          rotX += (my - drag.y) * 0.006;
          rotX = Math.max(-1.2, Math.min(1.2, rotX));
          drag.x = mx;
          drag.y = my;
          return;
        }
        const n = hit(mx, my);
        hover = n;
        canvas.style.cursor = n ? "pointer" : "grab";
        if (o.onHover) o.onHover(n);
      }

      function onDown(e) {
        const rect = canvas.getBoundingClientRect();
        const mx = (e.clientX ?? e.touches?.[0]?.clientX) - rect.left;
        const my = (e.clientY ?? e.touches?.[0]?.clientY) - rect.top;
        drag = { x: mx, y: my, t: Date.now(), moved: false };
      }

      function onUp(e) {
        if (!drag) return;
        const rect = canvas.getBoundingClientRect();
        const mx = (e.clientX ?? e.changedTouches?.[0]?.clientX) - rect.left;
        const my = (e.clientY ?? e.changedTouches?.[0]?.clientY) - rect.top;
        const n = hit(mx, my);
        if (!drag.moved && n && o.onNodeClick) o.onNodeClick(n);
        drag = null;
      }

      function onWheel(e) {
        e.preventDefault();
        targetScale *= e.deltaY > 0 ? 0.94 : 1.06;
        targetScale = Math.max(0.35, Math.min(2.2, targetScale));
      }

      canvas.addEventListener("mousemove", onMove);
      canvas.addEventListener("mousedown", onDown);
      window.addEventListener("mouseup", onUp);
      canvas.addEventListener("touchstart", onDown, { passive: true });
      canvas.addEventListener("touchmove", onMove, { passive: true });
      canvas.addEventListener("touchend", onUp);
      canvas.addEventListener("wheel", onWheel, { passive: false });
      window.addEventListener("resize", resize);

      resize();
      requestAnimationFrame(frame);

      return {
        destroy() {
          running = false;
          window.removeEventListener("resize", resize);
        },
        setAutoRotate(v) {
          o.autoRotate = v;
        },
      };
    },
  };
})();
