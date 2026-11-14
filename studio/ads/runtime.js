// Shared runtime for the ad templates. The filmer (studio/film.py) injects window.SB (the storyboard) and
// window.BRAND (looks, fonts and files from the brand brain), then calls window.seek(t) once per frame and takes a screenshot.
// Every picture must be a pure function of t: no CSS transitions, no timers, no Math.random without a seed.
(function () {
  const SB = window.SB || { frames: [], look: "Graphite", mode: "dark", length: 2 };
  const BRAND = window.BRAND || { looks: {}, fonts: [], files: {} };
  const W = window.innerWidth, H = window.innerHeight;
  // Words stay inside the Reels safe area: not in the top 240 px, the bottom 440 px or the right 190 px (of 1080 x 1920).
  // Scaled for other shapes. The left margin matches the right one, so centred words look centred.
  const k = H / 1920;
  const SAFE = SB.shape === "9:16" || !SB.shape
    ? { top: 260, bottom: H - 460, left: 190, right: W - 190 }
    : { top: Math.round(60 * k), bottom: H - Math.round(80 * k), left: Math.round(W * 0.08), right: W - Math.round(W * 0.08) };

  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2); // in and out
  const out = (x) => 1 - Math.pow(1 - x, 3);
  const back = (x) => { const c = 1.70158, d = c + 1; return 1 + d * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
  const tw = (t, a, b, f = ease) => f(clamp((t - a) / Math.max(1e-6, b - a)));
  const lerp = (a, b, x) => a + (b - a) * x;
  function seeded(seed) { return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

  const look = (BRAND.looks[SB.look] || BRAND.looks[Object.keys(BRAND.looks)[0]] || {})[SB.mode || "dark"] ||
    { ground: "#131517", text: "#E6E8EA", quiet: "#9EA5AC", line: "#33383D", accent: "#7C4DFF" };
  // Pace: Calm stretches every entrance, Hyped shortens it.
  const pace = { Calm: 1.5, Normal: 1, Hyped: 0.65 }[SB.pace] || 1;

  // Fonts from the brain. The first is the display font, the second the body font.
  const fonts = BRAND.fonts || [];
  const css = fonts.map((f) => `@font-face{font-family:"${f.family}";src:url("${f.url}");font-weight:100 900;font-display:block}`).join("\n");
  const display = fonts[0] ? `"${fonts[0].family}", serif` : "Georgia, serif";
  const body = fonts[1] ? `"${fonts[1].family}", system-ui, sans-serif` : "system-ui, sans-serif";
  const style = document.createElement("style");
  style.textContent = css + `
    :root{--ground:${look.ground};--text:${look.text};--quiet:${look.quiet};--line:${look.line};--accent:${look.accent};
      --display:${display};--body:${body};--W:${W}px;--H:${H}px}
    html,body{margin:0;width:${W}px;height:${H}px;overflow:hidden;background:var(--ground);color:var(--text);font-family:var(--body)}
    .safe{position:absolute;left:${SAFE.left}px;top:${SAFE.top}px;width:${SAFE.right - SAFE.left}px;height:${SAFE.bottom - SAFE.top}px}
    .words{text-wrap:balance}`;
  document.head.appendChild(style);

  const frames = (SB.frames || []).slice().sort((a, b) => a.start - b.start);
  const frameAt = (t) => { let f = null; for (const x of frames) if (t >= x.start && t < x.end) f = x; return f || frames[frames.length - 1]; };
  const file = (p) => (BRAND.files && BRAND.files[p]) || (BRAND.base ? BRAND.base + p : p);

  let draw = () => {};
  const S4F = { SB, BRAND, W, H, SAFE, look, pace, clamp, ease, out, back, tw, lerp, seeded, frames, frameAt, file,
    setup(fn) { draw = fn; } };
  window.S4F = S4F;
  window.seek = (t) => { draw(t); return true; };

  // Ready when the fonts and every picture have loaded.
  window.ready = (async () => {
    await new Promise((r) => (document.readyState === "complete" ? r() : addEventListener("load", r)));
    for (const f of fonts) { try { await document.fonts.load(`700 40px "${f.family}"`); } catch (e) {} }
    await document.fonts.ready;
    await Promise.all([...document.images].map((im) => (im.complete ? 0 : new Promise((r) => { im.onload = im.onerror = r; }))));
    draw(0);
    return true;
  })();
})();
