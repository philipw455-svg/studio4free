(() => {
'use strict';
function h(tag, attrs, ...kids){
  const e = document.createElement(tag);
  if (attrs) for (const k in attrs){ const v = attrs[k]; if (v == null || v === false) continue;
    if (k === 'class') e.className = v; else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'value') e.value = v; else if (k === 'html') e.innerHTML = v; else e.setAttribute(k, v === true ? '' : v); }
  for (const kid of kids.flat(3)){ if (kid == null || kid === false) continue; e.append(kid.nodeType ? kid : document.createTextNode(String(kid))); }
  return e;
}

/* ---------- choices (example answers, so the preview starts full) ---------- */
const C = { buffer:false, services:['YouTube','TikTok'], overlay:'Poster', capColor:'#f8ff7a', media:{banner:null, flash:null, ending:null},
  ovs:{ Poster:{color:'#ffffff', size:'Large', hold:'1.5'}, Banner:{bg:'#000000', fg:'#ffffff', pos:'Top'}, 'Glass card':{tint:'#ffffff', blur:'Soft', round:'Round'},
    Sticker:{bg:'#f8ff7a', tilt:'Left'}, Frame:{color:'#ff6ad5', width:'Thin'} }, captions:'Yes', zoom:'Smooth', language:'Mute it',
  brand:'appnoxi.com', descTail:'Try Noxi free at appnoxi.com', comment:'Full episode on our channel.', flashDays:['Tuesday','Friday'],
  tz:'America/Chicago', slots:[{time:'12:15', show:''},{time:'17:00', show:''}],
  count:'10', len:'20 to 40 seconds', parts:'Split long stories into parts', kinds:['Strong opinions','Funny moments','Emotional moments'] };
const TEST = { buffer:true, services:['YouTube','TikTok','Instagram'], overlay:'Glass card', captions:'Yes', zoom:'Slow creep', language:'Mute it',
  brand:'appnoxi.com', descTail:'Plan your week with Noxi: appnoxi.com', comment:'Which take do you agree with?', flashDays:['Monday','Thursday'],
  tz:'America/New_York', slots:[{time:'09:30', show:'Morning Show'},{time:'13:00', show:''},{time:'19:45', show:''}],
  count:'5', len:'40 to 60 seconds', parts:'Short clips only', kinds:['Stories','Advice and tips','Quotable one-liners'] };
const S = { pday:'flash', screen:'signin', step:0, path:null, number:'', back:false, hint:'', err:'', welcome:false };

const OV = {Poster:'poster',Banner:'banner','Glass card':'glass',Sticker:'sticker',Frame:'frame'};
const OVD = {
  Poster:'A big title shows first. Then your brand moves under the captions.',
  Banner:'A solid bar holds the title and your brand. You pick its color and place.',
  'Glass card':'A frosted card floats at the top. The video shows through it.',
  Sticker:'The title sits on a tilted color sticker. Your brand stays under the captions.',
  Frame:'A color frame wraps the clip. The title sits in the top edge, your brand in the bottom.' };
const SW = [['Black','#000000'],['White','#ffffff'],['Lime','#f8ff7a'],['Pink','#ff6ad5'],['Sky','#6bc7ff'],['Orange','#ff8a3d']];
const SWT = [['White','#ffffff'],['Black','#111111'],['Lime','#f8ff7a']];
const OVSET = {
  Poster:[['color','Title color','color',SW.slice(1)],['size','Title size','seg',['Small','Medium','Large']],['hold','Title stays for','seg',['1','1.5','2','3'],v => v + ' s']],
  Banner:[['bg','Bar color','color',SW],['fg','Text color','color',SWT],['pos','Bar position','seg',['Top','Bottom']]],
  'Glass card':[['tint','Glass tint','color',SW.slice(1)],['blur','Blur','seg',['Soft','Strong']],['round','Corners','seg',['Round','Square']]],
  Sticker:[['bg','Sticker color','color',SW],['tilt','Tilt','seg',['Left','None','Right']]],
  Frame:[['color','Frame color','color',SW],['width','Side edges','seg',['Thin','Thick']]] };
const SETHINT = {
  hold:v => 'The title stays for ' + v + (v === '1' ? ' second' : ' seconds') + '. Then it fades.',
  size:v => 'The title now shows at ' + v.toLowerCase() + ' size.',
  pos:v => 'The bar now sits at the ' + v.toLowerCase() + ' of the clip.',
  blur:v => v === 'Strong' ? 'The glass now hides more of the video behind it.' : 'The glass now shows more of the video behind it.',
  round:v => v === 'Round' ? 'The card now has round corners.' : 'The card now has square corners.',
  tilt:v => v === 'None' ? 'The sticker now sits straight.' : 'The sticker now tilts to the ' + v.toLowerCase() + '.',
  width:v => v === 'Thick' ? 'The frame now has thick side edges.' : 'The frame now has thin side edges.' };
const ink = hex => { const n = parseInt(hex.slice(1), 16), r = n >> 16 & 255, g = n >> 8 & 255, b = n & 255; return (.299 * r + .587 * g + .114 * b) / 255 > .6 ? '#111111' : '#ffffff'; };
const CAPD = {Yes:'Words appear as the speaker says them. They never cover the speaker’s face.', No:'The clip shows no words. Viewers have to listen.'};
const ZD = {Smooth:'The picture pushes in on the key line, then eases back out.', 'Slow creep':'The picture moves closer very slowly for the whole clip.', None:'The picture stays still for the whole clip.'};
const LD = {'Mute it':'Claude mutes each swear word and hides it in the captions.', 'Leave it in':'Claude keeps every word the way the speaker said it.'};
const CHD = {YouTube:'Each clip posts as a YouTube Short.', TikTok:'Each clip posts to your TikTok account.', Instagram:'Each clip posts as a Reel. Buffer adds your first comment there.'};
const DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
const COUNTS = ['3','5','10','20','As many as are good'];
const LENS = ['Under 20 seconds','20 to 40 seconds','40 to 60 seconds','Whatever the moment needs'];
const KINDS = ['Strong opinions','Funny moments','Stories','Advice and tips','Emotional moments','Surprising facts','Disagreements','Quotable one-liners'];
const TZS = [['America/New_York','Eastern time'],['America/Chicago','Central time'],['America/Denver','Mountain time'],['America/Los_Angeles','Pacific time'],['Europe/London','UK time']];

const fmt12 = t => { const [H, M] = t.split(':').map(Number); return ((H % 12) || 12) + ':' + String(M).padStart(2, '0') + (H < 12 ? ' AM' : ' PM'); };
const andList = a => a.length < 2 ? (a[0] || '') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1];
const shortDays = a => andList(a.map(d => d.slice(0, 3)));
const tzName = () => (TZS.find(x => x[0] === C.tz) || [0, C.tz])[1];
const goodSlots = () => C.slots.filter(s => /^\d\d:\d\d$/.test(s.time)).sort((a, b) => a.time.localeCompare(b.time));

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

/* ---------- live bits that redraw on every change ---------- */
let live = [];
function refresh(){ phones.forEach(paint); live.forEach(f => f()); const hEl = document.getElementById('hint'); if (hEl) hEl.textContent = S.hint || STEPS[S.step].hint(); navState(); }
function liveEl(build){ const box = h('div', {style:'display:contents'}); const f = () => box.replaceChildren(build()); live.push(f); f(); return box; }

/* ---------- small widgets ---------- */
function opts(key, list, descs, multi, extra){
  const box = h('div', {class:'opts' + (extra && extra.two ? ' two' : ''), role:'group'});
  for (const v of list){
    const on = () => multi ? C[key].includes(v) : C[key] === v;
    const b = h('button', {class:'opt' + (multi ? ' multi' : ''), type:'button', 'aria-pressed':String(on()), onclick:() => {
      if (multi){ const s = new Set(C[key]); s.has(v) ? s.delete(v) : s.add(v); C[key] = list.filter(x => s.has(x)); }
      else C[key] = v;
      box.querySelectorAll('.opt').forEach((x, i) => x.setAttribute('aria-pressed', String(multi ? C[key].includes(list[i]) : C[key] === list[i])));
      S.hint = descs && descs[v] ? (multi && !C[key].includes(v) ? v + ' is off.' : descs[v]) : '';
      if (extra && extra.restart) restart();
      refresh(); }},
      extra && extra.mini ? h('span', {class:'mini', 'data-ov':OV[v], 'aria-hidden':'true'}, h('i'), h('u')) : null,
      h('span', {class:'tx'}, h('b', null, v), descs && descs[v] ? h('small', null, descs[v]) : null), h('span', {class:'ck', 'aria-hidden':'true'}));
    box.append(b);
  }
  return box;
}
function chips(key, list, multi, onSet){
  const g = h('div', {class:'chips', role:'group'});
  list.forEach(v => g.append(h('button', {class:'chip', type:'button', 'aria-pressed':String(multi ? C[key].includes(v) : C[key] === v), onclick:() => {
    if (multi){ const s = new Set(C[key]); s.has(v) ? s.delete(v) : s.add(v); C[key] = list.filter(x => s.has(x)); } else C[key] = v;
    g.querySelectorAll('.chip').forEach((x, i) => x.setAttribute('aria-pressed', String(multi ? C[key].includes(list[i]) : C[key] === list[i])));
    S.hint = onSet ? onSet(v) : ''; refresh(); }}, multi && list === DAYS ? v.slice(0, 3) : v)));
  return g;
}
function colorPick(obj, key, label, list, id){
  const g = h('div', {class:'sw', role:'group', 'aria-label':label});
  const mark = () => g.querySelectorAll('.swb').forEach((b, i) => b.setAttribute('aria-pressed', String(obj[key].toLowerCase() === list[i][1])));
  const input = h('input', {type:'color', id, value:obj[key], 'aria-label':'Custom ' + label.toLowerCase(),
    oninput:e => { obj[key] = e.target.value; mark(); S.hint = label + ' changed to your own color.'; refresh(); }});
  list.forEach(([n, c]) => g.append(h('button', {class:'swb', type:'button', style:'background:' + c, 'aria-label':n, title:n, 'aria-pressed':String(obj[key].toLowerCase() === c),
    onclick:() => { obj[key] = c; input.value = c; mark(); S.hint = label + ' changed to ' + n.toLowerCase() + '.'; refresh(); }})));
  g.append(h('label', {class:'swc'}, input, 'Custom'));
  return h('div', {class:'field'}, h('span', {class:'fl'}, label), g);
}
function upload(kind, label, hint, accept, okType, onHint){
  const id = 'u-' + kind, box = h('div', {class:'field'}), err = h('p', {class:'err', role:'status'});
  const draw = () => { const f = C.media[kind];
    box.replaceChildren(h('span', {class:'fl'}, label), h('p', {class:'fh'}, hint),
      h('div', {class:'up'},
        h('label', {class:'btn ghost sm', for:id}, f ? 'Replace file' : 'Upload file'),
        h('input', {type:'file', id, accept, class:'vh', onchange:e => { const file = e.target.files[0]; e.target.value = ''; if (!file) return;
          if (!okType.test(file.type)){ err.textContent = 'That file type does not work here. ' + (kind === 'banner' ? 'Use a PNG or JPG image.' : 'Use an MP4 or MOV video.'); return; }
          err.textContent = ''; if (C.media[kind]) URL.revokeObjectURL(C.media[kind].url);
          C.media[kind] = {url:URL.createObjectURL(file), name:file.name}; S.hint = onHint; restart(); draw(); refresh(); }}),
        h('span', {class:'fname'}, f ? f.name : 'No file yet'),
        f ? h('button', {class:'btn ghost sm', type:'button', onclick:() => { URL.revokeObjectURL(f.url); C.media[kind] = null; S.hint = label + ' removed.'; restart(); draw(); refresh(); }}, 'Remove') : null),
      err); };
  draw(); return box;
}
function seg(obj, key, label, list, fmt, hintFn){
  const g = h('div', {class:'chips', role:'group', 'aria-label':label});
  list.forEach(v => g.append(h('button', {class:'chip', type:'button', 'aria-pressed':String(obj[key] === v), onclick:() => {
    obj[key] = v; g.querySelectorAll('.chip').forEach((b, i) => b.setAttribute('aria-pressed', String(list[i] === v)));
    S.hint = hintFn ? hintFn(v) : label + ': ' + (fmt ? fmt(v) : v) + '.'; restart(); refresh(); }}, fmt ? fmt(v) : v)));
  return h('div', {class:'field'}, h('span', {class:'fl'}, label), g);
}
const group = (label, right, ...kids) => h('div', {class:'group'}, h('div', {class:'gh'}, h('span', {class:'lab'}, label), right ? h('span', {class:'lab', style:'color:var(--iron)'}, right) : null), ...kids);
const field = (id, label, hint, ctl) => h('div', {class:'field'}, h('label', {for:id}, label), hint ? h('p', {class:'fh'}, hint) : null, ctl);
const text = (id, key, area, ph) => h(area ? 'textarea' : 'input', {id, type:area ? null : 'text', value:C[key], placeholder:ph || '', oninput:e => { C[key] = e.target.value; S.hint = ''; refresh(); }});

/* ---------- demos ---------- */
function channelsDemo(){
  return h('div', {class:'panel'}, h('span', {class:'lab'}, 'How your clips travel'),
    h('div', {class:'flow'},
      h('div', {class:'node on'}, h('span', null, 'Studio4Free'), h('span', {class:'st'}, 'Cuts the clips')),
      h('div', {class:'arrow'}, '↓ sends each clip with its post time'),
      h('div', {class:'node ' + (C.buffer ? 'on' : 'off')}, h('span', null, 'Buffer'), h('span', {class:'st'}, C.buffer ? 'Signed in' : 'Not signed in')),
      h('div', {class:'arrow'}, '↓ posts at that time'),
      h('div', {class:'chan'}, ['YouTube','TikTok','Instagram'].map(s => { const on = C.services.includes(s);
        return h('div', {class:'node ' + (on ? 'on' : 'off')}, h('span', null, s), h('span', {class:'st'}, on ? 'On' : 'Off')); }))));
}
function postDemo(){
  const desc = 'He left a safe job to start over at 30. Here is why.';
  const tail = C.descTail.trim();
  return h('div', {class:'panel post'}, h('span', {class:'lab'}, 'How each post reads'),
    h('p', {class:'pt'}, 'Why I quit my job at 30'),
    h('p', {class:'pd'}, desc, tail ? ['\n\n', h('mark', null, tail)] : null),
    C.comment.trim() ? h('div', {class:'cm'}, h('span', {class:'av'}), h('div', null, h('p', {class:'lab', style:'text-transform:none;letter-spacing:0'}, 'First comment'), h('p', null, C.comment.trim()))) : null,
    h('p', {class:'fine'}, 'Green line: the text you added. ' + (C.services.includes('Instagram') ? 'Buffer adds the comment on Instagram. On YouTube, you pin it yourself.' : 'On YouTube, you add and pin the comment yourself.')));
}
function timesDemo(){
  const sl = goodSlots(), today = new Date(); today.setHours(12, 0, 0, 0);
  const days = [1, 2, 3].map(n => new Date(today.getTime() + n * 864e5));
  const pct = t => { const [H, M] = t.split(':').map(Number); return (H * 60 + M) / 1440 * 100; };
  return h('div', {class:'panel'}, h('span', {class:'lab'}, 'A sample day · ' + tzName()),
    h('div', {class:'track', 'aria-hidden':'true'}, [0, 6, 12, 18, 24].map(x => [h('span', {class:'tk', style:'left:' + (x / 24 * 100) + '%'}), h('span', {class:'tl', style:'left:' + Math.min(96, Math.max(4, x / 24 * 100)) + '%'}, x === 0 || x === 24 ? '12a' : x === 12 ? '12p' : x < 12 ? x + 'a' : (x - 12) + 'p')]),
      sl.map(s => h('span', {class:'dot', style:'left:' + pct(s.time) + '%', title:fmt12(s.time)}))),
    h('div', {class:'days'}, days.map(d => { const name = d.toLocaleDateString('en-US', {weekday:'long'}), end = C.flashDays.includes(name);
      return h('div', {class:'dayrow'}, h('b', null, d.toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric'})),
        h('div', {class:'sl'}, sl.length ? sl.map(s => h('span', {class:'tag'}, fmt12(s.time) + ' · ' + (s.show || 'any podcast'))) : h('span', {class:'mut small'}, 'No post times'), end ? h('span', {class:'tag end'}, 'Ends with Noxi card') : null)); })),
    h('p', {class:'fine'}, sl.length + (sl.length === 1 ? ' clip a day. ' : ' clips a day. ') + '10 clips fill about ' + Math.ceil(10 / Math.max(1, sl.length)) + ' days.'));
}
function briefText(){
  const n = C.count === 'As many as are good' ? 'every clip worth posting' : C.count + ' clips';
  const len = C.len === 'Whatever the moment needs' ? 'Let each moment set its own length.' : 'Keep each clip ' + C.len.toLowerCase() + ' long.';
  const kinds = C.kinds.length ? 'Look for ' + andList(C.kinds.map(k => k.toLowerCase())) + '.' : 'Look for any strong moment.';
  const parts = C.parts === 'Split long stories into parts' ? 'Split a long story into Part 1, Part 2 and more. Post Part 1 first.' : 'Skip stories that need more time.';
  return [['Find ', h('em', null, n), ' in each video.'], ' ', len, ' ', kinds, ' ', parts];
}
const clipsDemo = () => h('div', {class:'panel'}, h('span', {class:'lab'}, 'The sentence Claude works from'), h('p', {class:'brief'}, briefText()),
  h('p', {class:'fine'}, 'You still pick the moments. Claude shows a list first, and cuts only the ones you keep.'));

/* ---------- the five setup steps ---------- */
const STEPS = [
 { name:'Channels', q:'Where should your clips go?', intro:'Studio4Free hands each clip to Buffer. Buffer posts it to the channels you pick.', phone:false,
   hint:() => C.buffer ? 'Buffer is ready. ' + (C.services.length ? 'Clips go to ' + andList(C.services) + '.' : 'Pick at least one channel.') : 'Sign in to Buffer, then pick your channels.',
   ok:() => C.services.length ? '' : 'Pick at least one channel.',
   demo:channelsDemo,
   body:() => [
     group('1 · Buffer account', C.buffer ? 'Signed in' : null, h('div', {class:'row', style:'display:flex;gap:10px;flex-wrap:wrap;align-items:center'},
       h('button', {class:C.buffer ? 'btn ghost' : 'btn pri', type:'button', onclick:() => { C.buffer = !C.buffer; S.hint = C.buffer ? 'Buffer is signed in. Now pick the channels it posts to.' : 'Buffer is signed out.'; render(); }}, C.buffer ? 'Sign out of Buffer' : 'Sign in to Buffer'),
       h('span', {class:'fh mut small'}, C.buffer ? 'In the real app, your Buffer name shows here.' : 'In the real app, this opens Buffer’s own sign-in page.'))),
     group('2 · Channels', 'Pick one or more', opts('services', ['YouTube','TikTok','Instagram'], CHD, true)),
     h('p', {class:'mut small'}, 'You can sign in to Buffer later from Setup. Clips wait in your queue until then.')] },
 { name:'Style', q:'How should each clip look?', intro:'Tap a look. The preview redraws right away.', phone:true,
   hint:() => OVD[C.overlay], ok:() => '',
   body:() => {
     const desc = h('p', {class:'fh'}), tune = h('div', {class:'tune'});
     const fill = () => { desc.textContent = OVD[C.overlay]; const s = C.ovs[C.overlay];
       tune.replaceChildren(h('span', {class:'lab'}, 'Adjust ' + C.overlay), ...OVSET[C.overlay].map(([k, label, kind, list, fmt]) =>
         kind === 'color' ? colorPick(s, k, label, list, 'c-' + OV[C.overlay] + '-' + k) : seg(s, k, label, list, fmt, SETHINT[k]))); };
     const sel = h('select', {id:'f-ov', onchange:e => { C.overlay = e.target.value; S.hint = OVD[C.overlay]; restart(); fill(); refresh(); }},
       Object.keys(OV).map(k => h('option', {value:k, selected:k === C.overlay ? true : null}, k === 'Poster' ? 'Poster (your current look)' : k)));
     fill();
     return [ group('Overlay', '5 looks', field('f-ov', 'Pick a look', null, sel), desc, tune),
       group('Captions', null, opts('captions', ['Yes','No'], CAPD, false), colorPick(C, 'capColor', 'Highlight color', SW.slice(1), 'c-cap'),
         h('div', {class:'note'}, h('b', {style:'font-weight:500;color:var(--ink)'}, 'Smart captions are always on. '),
           'Each word shows right as it is said. Lines break at natural pauses. Captions step aside on their own so they never cover a face.')) ]; } },
 { name:'Motion', q:'How should the picture move?', intro:'Watch the speaker in the preview as you tap.', phone:true,
   hint:() => ZD[C.zoom] + ' ' + LD[C.language], ok:() => '',
   body:() => [ group('Zoom', null, opts('zoom', ['Smooth','Slow creep','None'], ZD, false, {restart:true})),
     group('Strong language', null, opts('language', ['Mute it','Leave it in'], LD, false, {restart:true})),
     h('p', {class:'mut small'}, 'The preview line has one swear word. Watch the captions around the 4-second mark.') ] },
 { name:'Brand', q:'How should people find you?', intro:'Your brand shows on each clip and in each post.', phone:true,
   hint:() => (C.brand.trim() ? '“' + C.brand.trim() + '” sits beside your mark on every clip. ' : 'No brand text shows on the clips. ') + (C.flashDays.length ? 'Clips on ' + shortDays(C.flashDays) + ' end with the Noxi card.' : 'No clip ends with the Noxi card.'),
   ok:() => '',
   body:() => [ group('On the clip', null,
       field('f-brand', 'Brand text', 'It sits beside your mark. Leave it empty for none.', text('f-brand', 'brand', false, 'appnoxi.com')),
       h('div', {class:'field'}, h('span', {class:'fl'}, 'Noxi card days'), h('p', {class:'fh'}, 'Clips that post on these days end with a 2-second Noxi card.'),
         chips('flashDays', DAYS, true, () => { restart(); return ''; })),
       seg(S, 'pday', 'Preview a clip that posts on', ['flash','other'], v => v === 'flash' ? 'A Noxi card day' : 'Another day',
         v => v === 'flash' ? 'The preview now shows a Noxi card day.' : 'The preview now shows a day without the Noxi card.')),
     group('Your own files', 'Optional',
       upload('banner', 'Banner image', 'It replaces the title area on every clip. Best at 1080 × 360 pixels.', 'image/png,image/jpeg,image/webp', /^image\//, 'Your banner now replaces the title area on every clip.'),
       upload('flash', 'Flash clip', 'It plays on Noxi card days in place of the default card. Keep it near 2 seconds.', 'video/*', /^video\//, 'Your flash clip now plays on Noxi card days.'),
       upload('ending', 'Ending video', 'It plays at the end of every clip, after any flash. Keep it under 3 seconds.', 'video/*', /^video\//, 'Your ending video now plays at the end of every clip.'),
       h('p', {class:'fine'}, 'Design preview: your files stay in this browser tab. The real app saves them to your studio.')),
     group('In the post', null,
       field('f-tail', 'Line added to every description', 'For example, a link to your app.', text('f-tail', 'descTail', true)),
       field('f-com', 'First comment on each post', null, text('f-com', 'comment', true))),
     liveEl(postDemo),
     h('p', {class:'fine'}, 'Example text is filled in. Change it to yours.') ] },
 { name:'Times', q:'When should clips post?', intro:'Each post time gets one clip a day. A time can belong to one podcast.', phone:false,
   hint:() => { const s = goodSlots(); return s.length ? 'Clips post at ' + andList(s.map(x => fmt12(x.time))) + ', ' + tzName() + '.' : 'Add at least one post time.'; },
   ok:() => goodSlots().length ? '' : 'Add at least one post time.',
   demo:timesDemo,
   body:() => [ group('Time zone', null, h('select', {id:'f-tz', 'aria-label':'Time zone', onchange:e => { C.tz = e.target.value; S.hint = ''; refresh(); }},
       TZS.map(z => h('option', {value:z[0], selected:z[0] === C.tz ? true : null}, z[1])))),
     group('Post times', C.slots.length + ' a day',
       C.slots.map((s, i) => h('div', {class:'slotrow'},
         h('input', {type:'time', id:'f-t' + i, 'aria-label':'Post time ' + (i + 1), value:s.time, onchange:e => { s.time = e.target.value; S.hint = ''; refresh(); }}),
         h('input', {type:'text', id:'f-s' + i, 'aria-label':'Podcast for post time ' + (i + 1), placeholder:'Any podcast', value:s.show, oninput:e => { s.show = e.target.value.trim(); refresh(); }}),
         h('button', {class:'x', type:'button', 'aria-label':'Remove ' + fmt12(s.time || '00:00'), onclick:() => { C.slots.splice(i, 1); S.hint = ''; render(); }}, '×'))),
       h('div', null, h('button', {class:'btn ghost sm', type:'button', disabled:C.slots.length >= 6 ? true : null, onclick:() => {
         let H = 9; while (C.slots.some(x => x.time === String(H).padStart(2, '0') + ':00') && H < 22) H++;
         C.slots.push({time:String(H).padStart(2, '0') + ':00', show:''}); S.hint = 'Added ' + fmt12(String(H).padStart(2, '0') + ':00') + '. Change it to the time you want.'; render(); }}, '+ Add a post time'))),
     h('p', {class:'mut small'}, 'Leave the podcast empty to let any clip take that time.') ] }
];
// The clip choices open every new job, so they live on the New clips screen, not in setup.
const CLIPSTEP = { name:'Clips', q:'What should Claude look for?', intro:'These answers tell Claude which moments to cut from each video.', phone:false,
   hint:() => 'Each new job starts from these answers. You can change them per job.',
   ok:() => C.kinds.length ? '' : 'Pick at least one kind of moment.',
   demo:clipsDemo,
   body:() => [ group('How many clips?', null, chips('count', COUNTS, false)),
     group('How long is each clip?', null, chips('len', LENS, false)),
     group('Long stories', null, opts('parts', ['Split long stories into parts','Short clips only'], {'Split long stories into parts':'A long story becomes Part 1, Part 2 and more.','Short clips only':'Claude skips stories that need more time.'}, false)),
     group('Good moments', 'Pick any', chips('kinds', KINDS, true)) ] };
const SUM = [
  () => (C.buffer ? 'Buffer' : 'Buffer not signed in') + ' · ' + (andList(C.services) || 'no channels'),
  () => { const s = C.ovs[C.overlay], d = {Poster:s.size + ' title, ' + s.hold + ' s', Banner:s.pos + ' bar', 'Glass card':s.blur + ' blur, ' + s.round + ' corners',
      Sticker:s.tilt === 'None' ? 'no tilt' : 'tilted ' + s.tilt, Frame:s.width + ' edges'}[C.overlay];
    return C.overlay + ' (' + String(d).toLowerCase() + ') · captions ' + (C.captions === 'Yes' ? 'on' : 'off'); },
  () => C.zoom + ' zoom · swear words ' + (C.language === 'Mute it' ? 'muted' : 'left in'),
  () => { const own = [C.media.banner && 'own banner', C.media.flash && 'own flash clip', C.media.ending && 'ending video'].filter(Boolean);
    return (C.brand.trim() || 'No brand text') + ' · Noxi card on ' + (C.flashDays.length ? shortDays(C.flashDays) : 'no days') + (own.length ? ' · ' + andList(own) : ''); },
  () => andList(goodSlots().map(x => fmt12(x.time))) + ' · ' + tzName()
];

/* ---------- screens ---------- */
const app = document.getElementById('app'), nav = document.getElementById('nav'), bk = document.getElementById('bk'), nx = document.getElementById('nx'), why = document.getElementById('why');
function go(screen, step){ S.screen = screen; if (step != null) S.step = step; S.hint = ''; S.err = ''; render(); scrollTo(0, 0); }
function render(){
  live = [];
  nav.hidden = !(S.screen === 'step' || S.screen === 'recap' || S.screen === 'start');
  const v = {signin:vSignin, step:vStep, recap:vRecap, start:vStart}[S.screen]();
  app.replaceChildren(...v);
  navState();
}
function navState(){
  if (S.screen === 'step'){
    const st = STEPS[S.step], bad = st.ok();
    bk.textContent = S.step ? 'Back' : 'Sign-in'; bk.onclick = () => S.step ? go('step', S.step - 1) : go('signin');
    nx.textContent = S.back ? 'Back to recap' : S.step === STEPS.length - 1 ? 'See my recap' : 'Next: ' + STEPS[S.step + 1].name;
    nx.disabled = !!bad; why.textContent = bad;
    nx.onclick = () => { if (bad) return; if (S.back || S.step === STEPS.length - 1){ S.back = false; go('recap'); } else go('step', S.step + 1); };
  } else if (S.screen === 'recap'){
    bk.textContent = S.welcome ? 'Sign-in' : 'Back'; bk.onclick = () => S.welcome ? go('signin') : go('step', STEPS.length - 1); why.textContent = '';
    nx.disabled = false; nx.textContent = S.welcome ? 'Make new clips' : 'Start my first job'; nx.onclick = () => go('start');
  } else if (S.screen === 'start'){
    bk.textContent = 'Recap'; bk.onclick = () => go('recap'); why.textContent = '';
    nx.disabled = false; nx.textContent = 'Send to Claude Code'; nx.onclick = sendJob;
  }
}

function vSignin(){
  const msg = h('p', {class:'err', role:'status'}, S.err);
  const pathHave = h('div', {class:'path'}, h('span', {class:'lab'}, 'Path A'), h('h3', null, 'I have a studio number'),
    h('p', {class:'mut small'}, 'Type the 8 digits you saved when you started.'),
    h('input', {type:'text', id:'f-num', inputmode:'numeric', autocomplete:'off', placeholder:'0000 0000', value:S.number, 'aria-label':'Studio number',
      oninput:e => { const d = e.target.value.replace(/\D/g, '').slice(0, 8); S.number = d; e.target.value = d.length > 4 ? d.slice(0, 4) + ' ' + d.slice(4) : d; },
      onkeydown:e => { if (e.key === 'Enter') signIn(); }}),
    h('button', {class:'btn pri wide', type:'button', onclick:signIn}, 'Sign in'), msg,
    h('p', {class:'fine'}, 'Test studio: 4004 2026'));
  function signIn(){
    if (S.number.length !== 8){ msg.textContent = 'Type all 8 digits of your studio number.'; return; }
    if (S.number === '40042026'){ if (!PRESETS.some(x => x.name === 'Morning Show')){ PRESETS.push({name:'Morning Show', parts:['clips','style','ad'], data:{count:'3', len:'Under 20 seconds', parts:'Short clips only', kinds:['Funny moments','Quotable one-liners'],
      overlay:'Sticker', ovs:clone(C.ovs), captions:'Yes', capColor:'#6bc7ff', zoom:'Smooth', language:'Mute it', brand:'appnoxi.com', descTail:'Morning Show, new every weekday.', comment:'What would you do?', flashDays:['Wednesday'], media:{banner:null, flash:null, ending:null}}}); }
      Object.assign(C, TEST); C.slots = TEST.slots.map(x => Object.assign({}, x)); S.welcome = true; go('recap'); return; }
    if (S.newNum && S.number === S.newNum){ S.welcome = true; go('recap'); return; }
    msg.textContent = 'No studio has that number. Check the digits, or tap "Get my number".';
  }
  let newBox;
  if (S.path === 'new'){
    const n = S.newNum || (S.newNum = String(Math.floor(1e7 + Math.random() * 9e7)));
    const pretty = n.slice(0, 4) + ' ' + n.slice(4);
    const copied = h('span', {class:'fine', role:'status'});
    newBox = h('div', {class:'path', style:'border-color:var(--ink)'}, h('span', {class:'lab'}, 'Path B · your number'),
      h('p', {class:'num'}, pretty),
      h('p', {class:'small'}, 'Save this number. You sign in with it on any phone or computer.'),
      h('div', {style:'display:flex;gap:10px;align-items:center;flex-wrap:wrap'}, h('button', {class:'btn ghost sm', type:'button', onclick:() => {
        Promise.resolve().then(() => navigator.clipboard.writeText(pretty)).then(() => { copied.textContent = 'Copied.'; }, () => { copied.textContent = 'Copy did not work. Write it down instead.'; }); }}, 'Copy number'), copied),
      h('div', {class:'note'}, 'Next come five short steps: Channels, Style, Motion, Brand and Times. Each step shows what it changes. It takes about two minutes.'),
      h('button', {class:'btn pri wide', type:'button', onclick:() => { S.welcome = false; go('step', 0); }}, 'Start step 1 of 5'));
  } else newBox = h('div', {class:'path'}, h('span', {class:'lab'}, 'Path B'), h('h3', null, 'I’m new'),
    h('p', {class:'mut small'}, 'Get a studio number. Then set up your studio in five short steps.'),
    h('button', {class:'btn wide', type:'button', onclick:() => { S.path = 'new'; render(); }}, 'Get my number'));
  return [h('section', {class:'hero'}, h('span', {class:'lab'}, 'Automate your channels, hands free'), h('h1', null, 'One video in.', h('br'), 'A week of clips out.'),
      h('p', null, 'Paste a YouTube link. Claude finds the best moments, cuts the clips and fills your posting schedule.')),
    h('div', {class:'paths'}, pathHave, newBox)];
}

function vStep(){
  const st = STEPS[S.step];
  const bar = h('nav', {class:'steps', 'aria-label':'Setup steps'}, STEPS.map((x, i) =>
    h('button', {type:'button', class:i < S.step ? 'done' : i === S.step ? 'now' : '', 'aria-current':i === S.step ? 'step' : null, disabled:i > S.step ? true : null,
      onclick:() => { if (i < S.step) go('step', i); }}, h('i'), h('span', null, (i < S.step ? '✓ ' : '') + x.name))));
  const hint = h('p', {class:'hint', id:'hint', 'aria-live':'polite'}, S.hint || st.hint());
  const stage = st.phone
    ? h('aside', {class:'stage sticky'}, makePhone(), h('div', {class:'side'}, h('span', {class:'lab'}, 'What this changes'), hint, h('p', {class:'fine'}, 'Drawn preview. It is not your real footage.')))
    : h('aside', {class:'stage', style:'flex-direction:column;align-items:stretch'}, liveEl(st.demo), h('div', {class:'side'}, h('span', {class:'lab'}, 'What this changes'), hint));
  const content = h('div', {class:'content'}, h('div', {class:'head'}, h('span', {class:'lab'}, 'Step ' + (S.step + 1) + ' of ' + STEPS.length + ' · ' + st.name), h('h2', null, st.q), h('p', null, st.intro)), st.body());
  return [bar, h('div', {class:'main'}, stage, content)];
}

function vRecap(){
  const carousel = h('div', {class:'car', role:'list', 'aria-label':'Your clips'}, CLIPS.map((c, i) => h('button', {class:'cc', type:'button', role:'listitem', 'aria-label':'Open clip ' + (i + 1) + ': ' + c.title,
      onclick:e => { if (carousel.dataset.moved === '1'){ e.preventDefault(); return; } openEditor(i); }},
    makePhone(false, c), h('span', {class:'tag' + (c.ver > 1 ? ' sent' : '')}, c.ver > 1 ? 'Changes sent · v' + c.ver : 'Clip ' + (i + 1) + ' · v1'), h('b', null, c.title))));
  carousel.addEventListener('pointerdown', e => { if (e.pointerType !== 'mouse') return; carDrag = {el:carousel, sx:e.clientX, sl:carousel.scrollLeft}; carousel.dataset.moved = '0'; });
  const step = d => carousel.scrollBy({left:d * (carousel.firstElementChild.offsetWidth + 12), behavior:'smooth'});
  const stage = h('div', {class:'group'}, h('div', {class:'carhead'}, h('span', {class:'lab'}, 'Your clips · drag or tap one to open'),
      h('div', {class:'arrows'}, h('button', {class:'btn ghost sm', type:'button', 'aria-label':'Earlier clips', onclick:() => step(-1)}, '←'), h('button', {class:'btn ghost sm', type:'button', 'aria-label':'Later clips', onclick:() => step(1)}, '→'))),
    carousel);
  return vRecapRest(stage);
}
// Mouse users drag the clip row sideways. Touch users swipe it natively.
let carDrag = null;
addEventListener('pointermove', e => { const d = carDrag; if (!d) return; const dx = e.clientX - d.sx;
  if (Math.abs(dx) > 6){ d.el.dataset.moved = '1'; d.el.classList.add('drag'); } if (d.el.dataset.moved === '1') d.el.scrollLeft = d.sl - dx; });
addEventListener('pointerup', () => { const d = carDrag; if (!d) return; carDrag = null; d.el.classList.remove('drag'); setTimeout(() => { d.el.dataset.moved = '0'; }, 0); });
function openEditor(i){
  const cl = CLIPS[i];
  const spotText = c => c.capY == null ? (C.capY == null ? 'Default spot, low on the screen' : 'Your spot for all clips') : (c.capY < 40 ? 'Near the top' : c.capY < 62 ? 'In the middle' : 'Near the bottom') + ' · ' + Math.round(c.capY) + '% down';
  const volText = v => v === 0 ? 'Clip volume · muted' : 'Clip volume · ' + v + '%';
  const note = h('p', {class:'hint', 'aria-live':'polite'}, C.captions === 'Yes' ? 'Drag up or down on the clip to move its captions.' : 'Captions are off. Turn them on in Style to move them.');
  const spot = h('span', {class:'small'}, spotText(cl));
  const big = makePhone(true, cl, true), po = phones[phones.length - 1];
  po.onDrop = () => { spot.textContent = spotText(cl);
    const a = cl.capY, covers = a > 41 && a < 72;
    note.textContent = covers ? 'That spot covers the face. The captions will step aside while the face is there.' : 'Saved. This clip’s captions now sit here.'; };
  const vl = h('label', {class:'lab', for:'f-vol'}, volText(cl.vol));
  const vol = h('input', {type:'range', id:'f-vol', min:0, max:150, step:5, value:cl.vol, oninput:e => { cl.vol = +e.target.value; vl.textContent = volText(cl.vol); note.textContent = cl.vol > 100 ? 'This clip plays louder than the source video.' : cl.vol === 0 ? 'This clip plays with no sound.' : 'This clip plays at ' + cl.vol + '% of the source volume.'; }});
  const ctl = h('div', {class:'ctl'}, h('span', {class:'lab'}, 'Caption spot'), spot,
    h('div', {style:'display:flex;gap:8px;flex-wrap:wrap'},
      h('button', {class:'btn ghost sm', type:'button', onclick:() => { if (cl.capY == null){ note.textContent = 'Drag the captions first. Then you can use that spot for all clips.'; return; }
        C.capY = cl.capY; CLIPS.forEach(c => { c.capY = null; }); spot.textContent = spotText(cl); note.textContent = 'All clips now use this caption spot.'; }}, 'Use for all clips'),
      h('button', {class:'btn ghost sm', type:'button', onclick:() => { cl.capY = null; spot.textContent = spotText(cl); note.textContent = 'This clip uses the shared caption spot again.'; }}, 'Reset')),
    vl, vol, h('p', {class:'fine'}, 'The drawn preview has no sound. The level bars show the change.'));
  const notes = h('textarea', {id:'f-notes', value:cl.notes || '', placeholder:'For example: start one second later, or use a shorter title.', oninput:e => { cl.notes = e.target.value; }});
  const sent = h('p', {class:'small', role:'status'}, cl.ver > 1 ? 'Version ' + cl.ver + ' was sent. It replaces the earlier version.' : '');
  const close = () => { ov.remove(); document.body.style.overflow = ''; removeEventListener('keydown', esc); render(); };
  const esc = e => { if (e.key === 'Escape') close(); };
  const x = h('button', {class:'btn ghost sm', type:'button', onclick:close}, 'Close');
  const ov = h('div', {class:'ov', role:'dialog', 'aria-modal':'true', 'aria-label':'Edit clip ' + (i + 1), onclick:e => { if (e.target === ov) close(); }},
    h('div', {class:'ovin'},
      h('div', {class:'ovhead'}, h('div', {style:'display:flex;flex-direction:column;gap:6px;min-width:0'}, h('span', {class:'lab'}, 'Clip ' + (i + 1) + ' of ' + CLIPS.length + ' · version ' + cl.ver), h('h3', null, cl.title)), x),
      h('div', {style:'display:flex;flex-direction:column;gap:10px;min-width:0'}, big, note),
      h('div', {style:'display:flex;flex-direction:column;gap:14px;min-width:0'}, ctl,
        h('div', {class:'field'}, h('label', {for:'f-notes'}, 'Notes for Claude'), h('p', {class:'fh'}, 'Say what else to change. Claude reads this with your edits.'), notes),
        h('p', {class:'note'}, 'Claude always replaces this clip. It never makes a second copy.'),
        h('div', {style:'display:flex;gap:10px;flex-wrap:wrap'},
          h('button', {class:'btn ghost', type:'button', onclick:() => { sent.textContent = 'Saved. Nothing was sent yet.'; }}, 'Save'),
          h('button', {class:'btn pri', type:'button', style:'flex:1 1 200px', onclick:() => { cl.ver += 1;
            sent.textContent = 'Sent. Claude will replace clip ' + (i + 1) + ' with version ' + cl.ver + '. The old version goes away.'; }}, 'Save and send for changes')),
        sent, h('p', {class:'fine'}, 'Design preview: the real app sends this to Claude Code.'))));
  document.body.append(ov); document.body.style.overflow = 'hidden'; addEventListener('keydown', esc); x.focus();
}
function vRecapRest(stage){
  const rows = STEPS.map((st, i) => h('div', {class:'recrow'}, h('span', {class:'lab'}, st.name), h('span', {class:'v'}, SUM[i]()),
    h('button', {class:'btn ghost sm', type:'button', 'aria-label':'Edit ' + st.name, onclick:() => { S.back = true; go('step', i); }}, 'Edit')));
  return [h('div', {class:'main', style:'grid-template-columns:minmax(0,1fr)'}, h('div', {class:'content', style:'max-width:760px'},
    h('div', {class:'head'}, h('span', {class:'lab'}, S.welcome ? 'Signed in' : 'Recap · all five steps done'), h('h2', null, S.welcome ? 'Welcome back.' : 'Here is your studio.'),
      h('p', null, 'Every new job starts from these answers. Tap Edit to change one. You can also change them later in Setup.')),
    stage, h('div', {class:'rec'}, rows), presetPanel(() => render()),
    h('div', {class:'group'}, h('span', {class:'lab'}, 'What happens after you start a job'),
      h('div', {class:'pipe'}, h('div', null, 'You paste a YouTube link.'), h('div', null, 'Claude finds the best moments and lists them.'),
        h('div', null, 'You keep or skip each moment.'), h('div', null, 'Claude cuts the clips and checks the platform rules.'), h('div', null, 'Buffer posts each clip at its time.')))))];
}

/* ---------- saved setups: named sets of clip, style and ad choices (never caption spots) ---------- */
const PARTS = {
  clips:{name:'Clips', keys:['count','len','parts','kinds']},
  style:{name:'Style', keys:['overlay','ovs','captions','capColor','zoom','language']},
  ad:{name:'Ad', keys:['brand','descTail','comment','flashDays','media']} };
const clone = v => v && typeof v === 'object' ? JSON.parse(JSON.stringify(v)) : v;
let PRESETS = (() => { try { return JSON.parse(localStorage.getItem('s4f.presets')) || []; } catch (e) { return []; } })();
const keepPresets = () => { try { localStorage.setItem('s4f.presets', JSON.stringify(PRESETS.map(x => Object.assign({}, x, {data:Object.assign({}, x.data, x.data.media ? {media:{banner:null, flash:null, ending:null}} : {})})))); } catch (e) {} };
function snapshot(parts){ const d = {}; parts.forEach(pt => PARTS[pt].keys.forEach(k => { d[k] = k === 'media' ? Object.assign({}, C.media) : clone(C[k]); })); return d; }
function applyPreset(pr){ for (const k in pr.data) C[k] = k === 'media' ? Object.assign({}, pr.data.media) : clone(pr.data[k]); restart(); }
const partList = pr => andList(pr.parts.map(x => PARTS[x].name.toLowerCase()));
function presetPanel(onApply){
  const msg = h('p', {class:'small', role:'status'});
  const sel = h('select', {id:'f-preset', 'aria-label':'Saved setup', onchange:e => { const pr = PRESETS.find(x => x.name === e.target.value); if (!pr) return;
      applyPreset(pr); S.preset = pr.name; msg.textContent = 'Applied ' + pr.name + '. Its ' + partList(pr) + ' choices are in place.'; if (onApply) onApply(); }},
    h('option', {value:''}, PRESETS.length ? 'Pick a saved setup' : 'No saved setups yet'),
    PRESETS.map(pr => h('option', {value:pr.name, selected:S.preset === pr.name ? true : null}, pr.name + ' · ' + partList(pr))));
  const name = h('input', {type:'text', id:'f-pname', placeholder:'Name it, such as Morning Show', value:S.preset || ''});
  const pick = new Set(['clips','style','ad']);
  const tog = h('div', {class:'chips', role:'group', 'aria-label':'What to save'}, Object.keys(PARTS).map(pt => h('button', {class:'chip', type:'button', 'aria-pressed':'true',
    onclick:e => { pick.has(pt) ? pick.delete(pt) : pick.add(pt); e.currentTarget.setAttribute('aria-pressed', String(pick.has(pt))); }}, PARTS[pt].name)));
  const save = h('button', {class:'btn pri sm', type:'button', onclick:() => {
    const n = name.value.trim(); if (!n){ msg.textContent = 'Type a name for this setup first.'; return; }
    if (!pick.size){ msg.textContent = 'Pick at least one part to save.'; return; }
    const parts = Object.keys(PARTS).filter(x => pick.has(x)), old = PRESETS.findIndex(x => x.name.toLowerCase() === n.toLowerCase()), pr = {name:n, parts, data:snapshot(parts)};
    if (old >= 0) PRESETS[old] = pr; else PRESETS.push(pr); keepPresets(); S.preset = n;
    S.presetMsg = (old >= 0 ? 'Updated ' : 'Saved ') + n + '. It holds your ' + partList(pr) + ' choices.'; render(); }}, 'Save setup');
  const del = S.preset && PRESETS.some(x => x.name === S.preset) ? h('button', {class:'btn ghost sm', type:'button', onclick:() => {
    PRESETS = PRESETS.filter(x => x.name !== S.preset); keepPresets(); S.presetMsg = 'Deleted ' + S.preset + '.'; S.preset = ''; render(); }}, 'Delete ' + S.preset) : null;
  if (S.presetMsg){ msg.textContent = S.presetMsg; S.presetMsg = ''; }
  return h('div', {class:'group'}, h('div', {class:'gh'}, h('span', {class:'lab'}, 'Saved setups'), h('span', {class:'lab', style:'color:var(--iron)'}, PRESETS.length + ' saved')),
    field('f-preset', 'Use a saved setup', 'It sets your clip, style or ad choices in one tap.', sel),
    h('div', {class:'tune'}, h('span', {class:'lab'}, 'Save what you have now'), field('f-pname', 'Setup name', null, name),
      h('div', {class:'field'}, h('span', {class:'fl'}, 'What to save'), tog), h('div', {style:'display:flex;gap:8px;flex-wrap:wrap'}, save, del),
      h('p', {class:'fine'}, 'Caption spots are not saved. Smart captions place them on their own.')),
    msg);
}
function vStart(){
  const msg = h('p', {class:'err', id:'startmsg', role:'status'});
  return [h('div', {class:'main'}, h('aside', {class:'stage', style:'flex-direction:column;align-items:stretch;gap:14px'}, liveEl(clipsDemo), makePhone(true),
      liveEl(() => h('p', {class:'fine'}, 'Style: ' + SUM[1]() + '. Ad: ' + SUM[3]() + '.'))),
    h('div', {class:'content'}, h('div', {class:'head'}, h('span', {class:'lab'}, S.welcome ? 'New clips' : 'First job'), h('h2', null, CLIPSTEP.q),
        h('p', null, 'Start with what Claude should look for. Then paste the video. You check the moments before anything gets cut.')),
      presetPanel(() => { const g = id => (document.getElementById(id) || {}).value || ''; S.link = g('f-link'); S.job = g('f-job'); render(); }), CLIPSTEP.body(),
      h('div', {class:'group'}, h('span', {class:'lab'}, 'The video'),
        field('f-link', 'YouTube link', 'It starts with https://youtu.be/ or https://www.youtube.com/.', h('input', {type:'url', id:'f-link', inputmode:'url', placeholder:'https://youtu.be/…', value:S.link || ''})),
        field('f-job', 'Job name', 'A short name, such as the guest.', h('input', {type:'text', id:'f-job', placeholder:'Episode 42 with Sam', value:S.job || ''})), msg)))];
}
function sendJob(){
  const v = (document.getElementById('f-link') || {}).value || '', msg = document.getElementById('startmsg');
  const bad = CLIPSTEP.ok(); if (bad){ msg.style.color = 'var(--warn)'; msg.textContent = bad; return; }
  if (!/^https:\/\/((www\.|m\.)?youtube\.com\/(watch\?|shorts\/|live\/)|youtu\.be\/)\S+$/i.test(v.trim())){ msg.style.color = 'var(--warn)'; msg.textContent = 'Paste a full YouTube link first.'; return; }
  msg.style.color = 'var(--live)'; msg.textContent = 'Design preview: the real app sends this job to Claude Code here.';
}

render();
})();
