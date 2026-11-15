/* ---------- the live phone ---------- */
const W0 = 0.9, WD = 0.42, LOOP = 9;
// Smart caption rule: a caption page holds at most 3 words, breaks at a pause, shows just before its first word and stays until the next page.
function mkClip(title, text){ const words = text.split(' '), pages = []; let a = 0;
  words.forEach((w, i) => { if (i - a === 2 || /[,.!?]$/.test(w) || i === words.length - 1){ pages.push([a, i]); a = i + 1; } });
  return {title, words, pages, swear:words.findIndex(w => /^damn/i.test(w)), capY:null, vol:100, notes:'', ver:1}; }
const CLIPS = [mkClip('Why I quit my job at 30', 'I quit my job, and it was the best damn call I ever made.'),
  mkClip('The advice nobody gives you', 'Nobody tells you the first year is supposed to feel this hard.'),
  mkClip('Part 1: The week it all broke', 'We lost every client in one week, and I had no damn plan.'),
  mkClip('Part 2: How we got them back', 'We called every client back, one by one, and asked what broke.'),
  mkClip('The one habit that saved me', 'I write down one thing I learned before I go to bed.')];
const defAnchor = () => C.overlay === 'Banner' && C.ovs.Banner.pos === 'Bottom' ? 30 : 78;
const person = (x, y, s, mouthId) => `<g transform="translate(${x} ${y}) scale(${s})">
  <path d="M-30 80 C-30 36 -16 26 0 26 C16 26 30 36 30 80 Z" fill="#2f4a7a"/><rect x="-5" y="12" width="10" height="16" fill="#b9826a"/>
  <ellipse cx="0" cy="0" rx="13" ry="15.5" fill="#c99279"/><path d="M-13 -3 C-14 -18 -3 -19 0 -19 C9 -19 15 -13 13 -2 C9 -10 -6 -12 -13 -3Z" fill="#2a1d1d"/>
  <path d="M-15 0 C-16 -24 16 -24 15 0" fill="none" stroke="#141414" stroke-width="2.6"/><rect x="-18" y="-4" width="6" height="11" rx="2.5" fill="#141414"/><rect x="12" y="-4" width="6" height="11" rx="2.5" fill="#141414"/>
  <ellipse ${mouthId ? 'id="' + mouthId + '"' : ''} cx="0" cy="8" rx="3.4" ry="1.3" fill="#5a2a2a"/>
  <path d="M36 -16 L14 14" stroke="#222" stroke-width="2.4"/><rect x="5" y="9" width="10" height="17" rx="5" fill="#1b1b20" transform="rotate(-30 10 17)"/></g>`;
const SCENE = `<svg class="st" viewBox="0 0 90 160" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
  <defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a2a4f"/><stop offset="1" stop-color="#151226"/></linearGradient>
  <radialGradient id="lg"><stop offset="0" stop-color="#ffb36b" stop-opacity=".55"/><stop offset="1" stop-color="#ffb36b" stop-opacity="0"/></radialGradient>
  <radialGradient id="lb"><stop offset="0" stop-color="#6bc7ff" stop-opacity=".4"/><stop offset="1" stop-color="#6bc7ff" stop-opacity="0"/></radialGradient></defs>
  <rect width="90" height="160" fill="url(#sg)"/><circle cx="14" cy="40" r="22" fill="url(#lg)"/><circle cx="80" cy="56" r="26" fill="url(#lb)"/>
  <rect x="0" y="66" width="90" height="2" fill="#2b1f35"/><rect x="8" y="56" width="6" height="10" fill="#5b3f5f"/><rect x="16" y="52" width="4" height="14" fill="#7a5568"/><rect x="66" y="58" width="12" height="8" rx="1" fill="#3a3a5a"/>
  ${person(45, 92, 1, 'mouth')}</svg>
  <svg class="sw" viewBox="0 0 160 90" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
  <rect width="160" height="90" fill="url(#sg)"/><circle cx="80" cy="20" r="30" fill="url(#lg)"/><rect x="0" y="40" width="160" height="2" fill="#2b1f35"/>
  ${person(48, 52, .62, 'mouthw')}${person(114, 54, .6, '')}</svg>`;
const MUTE_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M17 9l5 6M22 9l-5 6"/></svg>';
const phones = [];
function makePhone(big, clip, edit){
  clip = clip || CLIPS[0];
  const p = h('div', {class:'phone' + (big ? ' big' : ''), role:edit ? 'group' : 'img', 'aria-label':edit ? 'Clip preview. Drag up or down to move the captions. Arrow keys work too.' : 'Live preview of a finished clip'});
  p.innerHTML = '<div class="scene">' + SCENE + '</div><div class="frm"></div><div class="tb"><div class="tt">Why I quit my job at 30</div><div class="br"><i class="mk"></i><span class="bt"></span></div></div>'
    + '<img class="cban" alt="" hidden><div class="caps"></div><div class="br bu"><i class="mk"></i><span class="bt"></span></div><div class="mute">' + MUTE_SVG + 'Muted</div>'
    + '<div class="end"><div class="edf"><i class="mk"></i><b class="bt"></b><span class="ed"></span></div><video class="fv" muted playsinline loop hidden></video></div>'
    + '<div class="endv"><video muted playsinline loop></video></div><div class="pbar"><i></i></div><span class="plabel">Preview</span>';
  const q = s => p.querySelector(s);
  const o = {el:p, scene:q('.scene'), tb:q('.tb'), caps:q('.caps'), bu:q('.bu'), mute:q('.mute'), end:q('.end'), edf:q('.edf'), fv:q('.fv'), endv:q('.endv'), ev:q('.endv video'), ban:q('.cban'),
    bar:q('.pbar i'), page:-1, seg:'', clip, edit:!!edit, mouths:p.querySelectorAll('#mouth,#mouthw')};
  if (edit){
    p.classList.add('edit'); p.tabIndex = 0;
    const fz = h('div', {class:'fz'}, h('span', null, 'Face')), vm = h('div', {class:'vm', 'aria-hidden':'true'}, [0, 1, 2, 3].map(() => h('i')));
    p.append(fz, vm); o.fz = fz; o.vm = [...vm.children];
    const yOf = e => { const r = p.getBoundingClientRect(); return Math.min(90, Math.max(10, (e.clientY - r.top) / r.height * 100)); };
    const up = () => { if (!o.dragging) return; o.dragging = false; p.classList.remove('dragging'); if (o.onDrop) o.onDrop(); };
    p.addEventListener('pointerdown', e => { if (C.captions !== 'Yes') return; o.dragging = true; p.classList.add('dragging'); try { p.setPointerCapture(e.pointerId); } catch (x) {} clip.capY = yOf(e); e.preventDefault(); });
    p.addEventListener('pointermove', e => { if (o.dragging) clip.capY = yOf(e); });
    p.addEventListener('pointerup', up); p.addEventListener('pointercancel', up);
    p.addEventListener('keydown', e => { if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown' || C.captions !== 'Yes') return; e.preventDefault();
      const cur = clip.capY != null ? clip.capY : C.capY != null ? C.capY : defAnchor(); clip.capY = Math.min(90, Math.max(10, cur + (e.key === 'ArrowUp' ? -3 : 3))); if (o.onDrop) o.onDrop(); });
  }
  phones.push(o); paint(o); return p;
}
function paint(o){
  const ov = OV[C.overlay], s = C.ovs[C.overlay], st = o.el.style, set = (k, v) => st.setProperty(k, v);
  o.el.querySelector('.tt').textContent = o.clip.title;
  o.el.dataset.ov = ov; o.el.dataset.pos = String(s.pos || 'Top').toLowerCase();
  set('--hl', C.capColor);
  if (ov === 'banner'){ set('--ovbg', s.bg); set('--ovfg', s.fg); }
  if (ov === 'glass'){ set('--tint', s.tint); set('--gb', s.blur === 'Strong' ? '14px' : '5px'); set('--gr', s.round === 'Round' ? '5cqw' : '1.2cqw'); }
  if (ov === 'poster'){ set('--pc', s.color); set('--ps', {Small:'9cqw', Medium:'10.5cqw', Large:'12cqw'}[s.size]); }
  if (ov === 'sticker'){ set('--ovbg', s.bg); set('--ovfg', ink(s.bg)); set('--tilt', {Left:'-4deg', None:'0deg', Right:'4deg'}[s.tilt]); }
  if (ov === 'frame'){ set('--ovbg', s.color); set('--ovfg', ink(s.color)); set('--fw', s.width === 'Thick' ? '5cqw' : '2.2cqw'); }
  o.el.querySelectorAll('.bt').forEach(b => { b.textContent = C.brand.trim(); });
  o.el.querySelectorAll('.br').forEach(b => { b.style.visibility = C.brand.trim() ? '' : 'hidden'; });
  o.end.querySelector('b').textContent = C.brand.trim() || 'Noxi';
  o.end.querySelector('.ed').textContent = 'Noxi flash · ' + shortDays(C.flashDays) + ' posts';
  const m = C.media;
  o.ban.hidden = !m.banner; if (m.banner && o.ban.getAttribute('src') !== m.banner.url) o.ban.src = m.banner.url;
  o.tb.classList.toggle('gone', !!m.banner);
  o.fv.hidden = !m.flash; o.edf.hidden = !!m.flash; if (m.flash && o.fv.getAttribute('src') !== m.flash.url) o.fv.src = m.flash.url;
  if (m.ending && o.ev.getAttribute('src') !== m.ending.url) o.ev.src = m.ending.url;
  o.page = -1; o.seg = '';
}
const ease = x => x < 0 ? 0 : x > 1 ? 1 : x * x * (3 - 2 * x);
function zoomAt(t){
  if (C.zoom === 'Smooth') return 1 + .14 * (ease((t - 3.6) / .5) - ease((t - 5.7) / .6));
  if (C.zoom === 'Slow creep') return 1 + .09 * Math.min(t, 7.2) / 7.2;
  return 1;
}
function frame(o, t){
  o.scene.style.transform = 'scale(' + zoomAt(t).toFixed(4) + ')';
  const ovn = C.overlay, hold = parseFloat(C.ovs.Poster.hold);
  o.tb.style.opacity = ovn === 'Poster' && t > hold ? 0 : 1;
  const under = ovn === 'Poster' ? t > hold + .3 : (ovn === 'Sticker' || ovn === 'Frame');
  o.bu.style.opacity = under && t < 7.2 && C.brand.trim() ? 1 : 0;
  const cl = o.clip, n = cl.words.length;
  const wi = t >= W0 && t < W0 + n * WD ? Math.floor((t - W0) / WD) : -1;
  let pg = -1;
  cl.pages.forEach((p, k) => { const s = W0 + p[0] * WD - .1, e = k + 1 < cl.pages.length ? W0 + cl.pages[k + 1][0] * WD - .1 : W0 + n * WD + .35; if (t >= s && t < e) pg = k; });
  if (o.dragging && pg < 0) pg = 0;
  if (C.captions !== 'Yes'){ if (o.page !== -2){ o.caps.replaceChildren(); o.page = -2; } }
  else {
    if (pg !== o.page){ o.page = pg; o.caps.replaceChildren(...(pg < 0 ? [] : cl.words.slice(cl.pages[pg][0], cl.pages[pg][1] + 1).map((w, k) => {
      const i = cl.pages[pg][0] + k, bleep = i === cl.swear && C.language === 'Mute it';
      return h('span', {class:'w' + (bleep ? ' bleep' : ''), 'data-i':i}, (bleep ? '****' : w) + ' '); }))); }
    o.caps.querySelectorAll('.w').forEach(s => s.classList.toggle('on', +s.dataset.i === wi));
  }
  // Smart caption rule: the captions keep to their spot, and step aside while that spot would cover the face.
  const z = zoomAt(t), anchor = cl.capY != null ? cl.capY : C.capY != null ? C.capY : defAnchor();
  const fT = 45 - z, fB = 45 + 24 * z, hh = Math.max(3, o.caps.offsetHeight / (o.el.offsetHeight || 1) * 50);
  const hits = anchor + hh > fT && anchor - hh < fB; let pos = anchor;
  if (hits && !o.dragging){ const c = [fB + hh + 1.5, fT - hh - 1.5].filter(x => x >= 7 && x <= 93).sort((a, b) => Math.abs(a - anchor) - Math.abs(b - anchor)); if (c.length) pos = c[0]; }
  o.caps.style.top = pos.toFixed(1) + '%';
  if (o.fz){ o.fz.style.top = fT + '%'; o.fz.style.height = (fB - fT) + '%'; o.fz.classList.toggle('hit', hits); }
  o.mute.style.opacity = wi === cl.swear && C.language === 'Mute it' ? 1 : 0;
  const talking = wi >= 0 && !(wi === cl.swear && C.language === 'Mute it');
  if (o.vm) o.vm.forEach((b, k) => { const lv = talking ? (.3 + .7 * Math.abs(Math.sin(t * (8 + k * 3) + k))) * cl.vol / 100 : .06; b.style.transform = 'scaleY(' + Math.min(1.4, Math.max(.06, lv)).toFixed(2) + ')'; });
  o.mouths.forEach(m => m.setAttribute('ry', talking ? (1.2 + 2.4 * Math.abs(Math.sin(t * 17))).toFixed(2) : 1.3));
  const segs = endSegs(), si = t >= 7.25 ? Math.floor((t - 7.25) / 1.75) : -1, sg = segs[si] || '';
  o.end.style.opacity = sg === 'flash' ? 1 : 0; o.endv.style.opacity = sg === 'ending' ? 1 : 0;
  if (sg !== o.seg){ o.seg = sg; const v = sg === 'flash' && C.media.flash ? o.fv : sg === 'ending' && C.media.ending ? o.ev : null;
    [o.fv, o.ev].forEach(x => { if (x !== v) x.pause(); });
    if (v && v.getAttribute('src')){ try { v.currentTime = 0; } catch (e) {} v.play().catch(() => {}); } }
  o.bar.style.width = (t / loopLen() * 100).toFixed(2) + '%';
}
function endSegs(){ const s = []; if (S.pday !== 'other' && C.flashDays.length) s.push('flash'); if (C.media.ending) s.push('ending'); return s; }
const loopLen = () => Math.max(LOOP, 7.25 + endSegs().length * 1.75);
const still = matchMedia('(prefers-reduced-motion: reduce)');
let t0 = performance.now();
function tick(now){
  for (let i = phones.length - 1; i >= 0; i--) if (!phones[i].el.isConnected) phones.splice(i, 1);
  const t = still.matches ? 4.1 : ((now - t0) / 1000) % loopLen();
  phones.forEach(o => frame(o, t));
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
const restart = () => { t0 = performance.now(); };

