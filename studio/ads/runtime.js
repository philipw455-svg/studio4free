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
      --display:${display};--body:${body};--W:${W}px;--H:${H}px;--wscale:1;--wcolor:${look.text}}
    html,body{margin:0;width:${W}px;height:${H}px;overflow:hidden;background:var(--ground);color:var(--text);font-family:var(--body)}
    .safe{position:absolute;left:${SAFE.left}px;top:${SAFE.top}px;width:${SAFE.right - SAFE.left}px;height:${SAFE.bottom - SAFE.top}px}
    .words{text-wrap:balance;color:var(--wcolor)}`;
  document.head.appendChild(style);

  const frames = (SB.frames || []).slice().sort((a, b) => a.start - b.start);
  const frameAt = (t) => { let f = null; for (const x of frames) if (t >= x.start && t < x.end) f = x; return f || frames[frames.length - 1]; };
  const file = (p) => (BRAND.files && BRAND.files[p]) || (BRAND.base ? BRAND.base + p : p);

  // ---- Per-scene settings. Every scene can override the ad's choices; a missing field keeps the ad's choice. ----
  // look, mode ("dark" | "light"), textSize ("S" | "M" | "L" | "XL"), textSpot ("top" | "middle" | "bottom"),
  // textColor ("text" | "accent" | "#hex"), motion ("pop" | "slide" | "fade" | "type" | "none"), speed ("Calm" | "Normal" | "Hyped").
  const SIZES = { S: 0.8, M: 1, L: 1.22, XL: 1.45 };
  const colorsOf = (f) => {
    const L = BRAND.looks[(f && f.look) || SB.look] || BRAND.looks[Object.keys(BRAND.looks)[0]] || {};
    return L[(f && f.mode) || SB.mode || "dark"] || look;
  };
  let lastScene = null;
  function applyScene(f) {
    if (f === lastScene) return;
    lastScene = f;
    const c = colorsOf(f), r = document.documentElement.style;
    r.setProperty("--ground", c.ground); r.setProperty("--text", c.text); r.setProperty("--quiet", c.quiet);
    r.setProperty("--line", c.line); r.setProperty("--accent", c.accent);
    r.setProperty("--wscale", SIZES[(f && f.textSize) || SB.textSize] || 1);
    const col = (f && f.textColor) || SB.textColor || "text";
    r.setProperty("--wcolor", col === "accent" ? c.accent : col === "text" ? c.text : col);
  }
  const paceOf = (f) => ({ Calm: 1.5, Normal: 1, Hyped: 0.65 }[(f && f.speed) || SB.pace] || 1);
  // spot: a template gives its own y for each spot; the scene picks one.
  const spot = (f, ys, fallback) => ys[(f && f.textSpot) || SB.textSpot || fallback] ?? ys[fallback];
  // enter: how a scene's words come in, from the scene's start time.
  function enter(el, t, start, f, text) {
    const kind = (f && f.motion) || SB.motion || "slide", p = paceOf(f), a = tw(t, start, start + 0.45 * p, kind === "pop" ? back : out);
    if (text != null) el.textContent = kind === "type" ? text.slice(0, Math.round(text.length * tw(t, start, start + 0.7 * p, (x) => x))) || "\u00a0" : text;
    if (kind === "none") { el.style.opacity = 1; el.style.transform = ""; return; }
    el.style.opacity = kind === "type" ? (t >= start ? 1 : 0) : Math.min(1, a * 1.4);
    el.style.transform = kind === "pop" ? `scale(${0.6 + 0.4 * a})` : kind === "slide" ? `translateY(${(1 - a) * 40}px)` : "";
  }

  let draw = () => {};
  const S4F = { SB, BRAND, W, H, SAFE, look, pace, clamp, ease, out, back, tw, lerp, seeded, frames, frameAt, file,
    paceOf, spot, enter, colorsOf,
    setup(fn) { draw = (t) => { applyScene(frameAt(t)); fn(t); }; } };
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
