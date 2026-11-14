
/* ---------- the real pieces behind the setup steps ---------- */
// A file the owner adds is stored with the page, so every device and every Claude Code session can reach it.
function upload(kind, label, hint, accept, okType, onHint){
  const id = 'u-' + kind, box = h('div', {class:'field'}), err = h('p', {class:'err', role:'status'});
  const draw = () => { const f = C.media[kind];
    box.replaceChildren(h('span', {class:'fl'}, label), h('p', {class:'fh'}, hint),
      h('div', {class:'up'},
        h('label', {class:'btn ghost sm', for:id}, f ? 'Replace file' : 'Upload file'),
        h('input', {type:'file', id, accept, class:'vh', onchange:async e => { const file = e.target.files[0]; e.target.value = ''; if (!file) return;
          if (!okType.test(file.type)){ err.textContent = 'That file type does not work here. ' + (kind === 'banner' ? 'Use a PNG or JPG image.' : 'Use an MP4 or MOV video.'); return; }
          if (file.size > 20 * 1048576){ err.textContent = 'That file is ' + Math.round(file.size / 1048576) + ' MB. The limit is 20 MB.'; return; }
          err.textContent = 'Uploading ' + file.name + '…';
          try { let rec; if (assets){ const r = await assets.upload(file); rec = {id:r.id, url:'/_blob/' + r.id, name:file.name}; } else rec = {url:URL.createObjectURL(file), name:file.name, temp:true};
            const old = C.media[kind]; C.media[kind] = rec; if (old && old.id && assets) assets.delete(old.id).catch(() => {});
            err.textContent = assets ? '' : 'This view cannot store files. The file stays in this tab only.'; S.hint = onHint; restart(); draw(); refresh(); }
          catch (x) { err.textContent = 'The upload did not go through. Try again.'; } }}),
        h('span', {class:'fname'}, f ? f.name : 'No file yet'),
        f ? h('button', {class:'btn ghost sm', type:'button', onclick:() => { if (f.id && assets) assets.delete(f.id).catch(() => {}); C.media[kind] = null; S.hint = label + ' removed.'; restart(); draw(); refresh(); }}, 'Remove') : null),
      err); };
  draw(); return box;
}
function channelsDemo(){
  return h('div', {class:'panel'}, h('span', {class:'lab'}, 'How your clips travel'),
    h('div', {class:'flow'},
      h('div', {class:'node on'}, h('span', null, 'Studio4Free'), h('span', {class:'st'}, 'Cuts the clips')),
      h('div', {class:'arrow'}, '↓ sends each clip with its post time'),
      h('div', {class:'node on'}, h('span', null, 'Buffer'), h('span', {class:'st'}, C.buffer ? 'Login: ' + C.buffer : 'Default login')),
      h('div', {class:'arrow'}, '↓ posts at that time'),
      h('div', {class:'chan'}, ['YouTube','TikTok','Instagram'].map(s => { const on = C.services.includes(s);
        return h('div', {class:'node ' + (on ? 'on' : 'off')}, h('span', null, s), h('span', {class:'st'}, on ? 'On' : 'Off')); }))));
}
// Buffer cannot be signed in to from this page. The owner names the saved Buffer login and each channel instead.
Object.assign(STEPS[0], {
  hint:() => C.services.length ? 'Clips go to ' + andList(C.services) + ' through Buffer.' : 'Pick at least one channel.',
  body:() => [
    group('1 · Buffer account', C.buffer ? 'Named' : 'Default',
      field('f-buffer', 'Buffer login', 'The name of the saved Buffer login this studio posts with, such as main. It is only a name. Never put a key or a password here.',
        h('input', {type:'text', id:'f-buffer', maxlength:24, autocapitalize:'none', autocomplete:'off', spellcheck:'false', value:C.buffer, placeholder:'Leave empty for the default login',
          oninput:e => { const v = e.target.value.replace(/[^A-Za-z0-9_-]/g, '').slice(0, 24); e.target.value = v; C.buffer = v; S.hint = ''; refresh(); }}))),
    group('2 · Channels', 'Pick one or more', opts('services', ['YouTube','TikTok','Instagram'], CHD, true),
      liveEl(() => h('div', {style:'display:flex;flex-direction:column;gap:12px'}, ['YouTube','TikTok','Instagram'].filter(o => C.services.includes(o)).map(o => { const k = o.toLowerCase(), id = 'f-ch-' + k;
        return field(id, o + ' channel name in Buffer', 'Type the name the way Buffer shows it.', h('input', {type:'text', id, maxlength:80, value:C.channels[k] || '', onchange:e => { C.channels[k] = e.target.value.trim(); dirty(); }})); })))),
    h('p', {class:'mut small'}, 'Claude Code hands each clip to Buffer. Clips wait in your queue until then.')] });
SUM[0] = () => 'Buffer ' + (C.buffer ? 'login ' + C.buffer : 'default login') + ' · ' + (andList(C.services) || 'no channels');

/* ---------- small pieces for the working screens ---------- */
const fld = (label, hint, ctl, id) => h('div', {class:'field'}, id ? h('label', {for:id}, label) : h('span', {class:'fl'}, label), hint ? h('p', {class:'fh'}, hint) : null, ctl);
function pickChips(list, cur, multi, onPick){
  const g = h('div', {class:'chips', role:'group'});
  list.forEach(o => g.append(h('button', {class:'chip', type:'button', 'aria-pressed':String(multi ? (cur || []).includes(o) : cur === o), onclick:e => { const b = e.currentTarget, now = b.getAttribute('aria-pressed') !== 'true';
    if (!multi) for (const x of g.children) x.setAttribute('aria-pressed', 'false'); b.setAttribute('aria-pressed', String(now)); onPick(o, now); }}, o)));
  return g;
}
const pagehead = (lab, title, sub) => h('div', {class:'pagehead'}, h('span', {class:'lab'}, lab), h('h2', null, title), sub ? h('p', null, sub) : null);
const pillFor = st => { const t = String(st || '').toLowerCase(); return /publish|posted|sent/.test(t) ? 'ok' : /schedul/.test(t) ? 'info' : /draft|plan/.test(t) ? 'wait' : /refus|fail|block/.test(t) ? 'bad' : ''; };
const hasVid = c => /^[0-9a-f]{32}$/.test((c && c.asset) || '');
const io = 'IntersectionObserver' in window ? new IntersectionObserver(es => { for (const e of es) if (e.isIntersecting){ const v = e.target; if (!v.getAttribute('src')) v.src = v.dataset.src; io.unobserve(v); } }, {rootMargin:'300px'}) : null;
function lazyVid(asset, controls, cls){ const v = h('video', {class:cls || null, controls:controls || null, playsinline:true, muted:controls ? null : true, preload:'metadata', 'data-src':'/_blob/' + asset + '#t=0.1'}); if (!controls) v.muted = true; if (io) io.observe(v); else v.src = v.dataset.src; return v; }
function allClips(){ const out = []; for (const [id, j] of S.jobs) for (const c of (j.clips || [])) if (c.publishAt) out.push({id, j, c}); return out.sort((a, b) => new Date(a.c.publishAt) - new Date(b.c.publishAt)); }
const slots = () => goodSlots().map(x => ({time:x.time, show:String(x.show || '').trim()}));
const same = (a, b) => String(a || '').trim().toLowerCase() === String(b || '').trim().toLowerCase();
// A job's clips go into the post times of its own podcast. With no match, they use the times that have no podcast.
function slotTimes(show){ const all = slots(); let m = String(show || '').trim() ? all.filter(x => same(x.show, show)) : []; if (!m.length) m = all.filter(x => !x.show); if (!m.length) m = all; return [...new Set(m.map(x => x.time))]; }
const shows = () => [...new Set([...slots().map(x => x.show), ...[...S.jobs.values()].map(j => String(j.show || '').trim())].filter(Boolean))];
function qState(c){ const t = String(c.status || '').toLowerCase(); return /publish|posted/.test(t) ? ['Posted', 'ok'] : /schedul/.test(t) ? ['Scheduled', 'info'] : /draft/.test(t) ? ['Draft in Buffer', 'wait'] : ['Not in Buffer yet', '']; }
function liveLinks(c){
  const out = [], seen = new Set(), add = (name, url) => { if (url && /^https:\/\//.test(url) && !seen.has(url)){ seen.add(url); out.push([name, url]); } };
  for (const k in (c.live || {})) add(k === 'youtube' ? 'YouTube' : k[0].toUpperCase() + k.slice(1), String(c.live[k] || ''));
  const m = /((?:www\.)?youtube\.com\/shorts\/[\w-]+)/.exec(String(c.status || '')); if (m) add('YouTube', 'https://' + m[1].replace(/^(?!www\.)/, 'www.'));
  return out;
}
const when12 = iso => dayShort(iso) + ' ' + fmt12(hm(iso));

/* ---------- screens ---------- */
const app = document.getElementById('app'), nav = document.getElementById('nav'), bk = document.getElementById('bk'), nx = document.getElementById('nx'), why = document.getElementById('why');
const tabs = document.getElementById('tabs'), badge = document.getElementById('badge');
const TABS = [['recap','Studio','studio'],['jobs','Jobs','jobs'],['queue','Queue','queue'],['schedule','Schedule','schedule'],['setup','Setup','setup']];
function go(screen, arg){
  S.screen = screen; if (screen === 'step' && arg != null) S.step = arg; if (screen === 'job') S.id = arg; S.hint = ''; S.err = '';
  const t = TABS.find(x => x[0] === screen); try { if (t) location.hash = t[2]; else if (screen === 'job') location.hash = 'job-' + arg; } catch (e) {}
  render(); scrollTo(0, 0);
}
function render(){
  live = []; dirty();
  if (S.screen !== 'admin' && admStop){ admStop(); admStop = null; admRows = null; admErr = ''; }
  const wait = S.store === 'wait' || S.busy, inApp = !wait && !!S.key && !['signin','admin','step'].includes(S.screen);
  badge.hidden = wait || !S.key || S.screen === 'signin'; badge.textContent = S.acct ? S.acct.name || 'My studio' : '';
  tabs.hidden = !inApp || S.screen === 'start' || S.screen === 'edit';
  const cur = S.screen === 'job' ? 'jobs' : S.screen;
  tabs.replaceChildren(...TABS.map(t => h('button', {type:'button', class:t[0] === cur ? 'now' : 'done', 'aria-current':t[0] === cur ? 'page' : null, onclick:() => go(t[0])}, h('i'), h('span', null, t[1]))));
  nav.hidden = wait || !['step','recap','start'].includes(S.screen);
  if (wait){ app.replaceChildren(...[S.note ? h('p', {class:'note', style:'margin-top:18px'}, S.note) : null, h('p', {class:'mut', style:'padding-top:28px'}, 'Loading your studio…')].filter(Boolean)); return; }
  const top = [S.note ? h('p', {class:'note', style:'margin-top:18px'}, S.note) : null,
    S.store === 'local' ? h('p', {class:'note', style:'margin-top:18px'}, 'This view saves on this device only. Open the page inside Claude to keep your work everywhere.') : null];
  const v = ({signin:vSignin, admin:vAdmin, step:vStep, recap:vRecap, start:vStart, edit:vEdit, jobs:vJobs, job:vJob, queue:vQueue, schedule:vSchedule, setup:vSetup}[S.screen] || vRecap)();
  app.replaceChildren(...top.filter(Boolean), ...v.flat(3).filter(Boolean));
  navState();
}
function navState(){
  bk.hidden = false;
  if (S.screen === 'step'){
    const st = STEPS[S.step], bad = st.ok();
    bk.textContent = S.step ? 'Back' : S.back ? 'Recap' : 'Sign out'; bk.onclick = () => S.step ? go('step', S.step - 1) : S.back ? (S.back = false, go('recap')) : signOut('', true);
    nx.textContent = S.back ? 'Back to recap' : S.step === STEPS.length - 1 ? 'See my recap' : 'Next: ' + STEPS[S.step + 1].name;
    nx.disabled = !!bad; why.textContent = bad;
    nx.onclick = () => { if (bad) return; if (S.back || S.step === STEPS.length - 1){ S.back = false; if (!S.acct.setupDone) saveAcct({setupDone:true}); go('recap'); } else go('step', S.step + 1); };
  } else if (S.screen === 'recap'){
    bk.hidden = S.welcome; bk.textContent = 'Back'; bk.onclick = () => go('step', STEPS.length - 1); why.textContent = '';
    nx.disabled = false; nx.textContent = S.welcome ? 'Make new clips' : 'Start my first job'; nx.onclick = () => go('start');
  } else if (S.screen === 'start'){
    bk.textContent = 'Recap'; bk.onclick = () => go('recap'); why.textContent = '';
    nx.disabled = false; nx.textContent = 'Send to Claude Code'; nx.onclick = sendJob;
  }
}

function vSignin(){
  const G = S.gate, msg = h('p', {class:'err', role:'status', id:'f-gate-msg'}, G.msg || '');
  const done = () => { S.gate.msg = ''; if (S.acct.setupDone){ S.welcome = true; route(); } else { S.welcome = false; S.back = false; go('step', 0); } scrollTo(0, 0); };
  const signIn = async () => { if (G.wait) return; const k = normKey(G.key);
    if (!k){ msg.textContent = 'That is not a studio number. A studio number looks like S4F-ABCD-EFGH.'; return; }
    G.wait = true; msg.textContent = 'Opening your studio…'; const r = await openAcct(k); G.wait = false;
    if (r){ msg.textContent = r !== 'none' ? r : db ? 'No studio has that number. Check it, or tap "Get my number".' : NOLOCAL; return; }
    localSet('s4f.key', G.remember ? k : ''); done(); };
  const make = async (b, name, legacy) => { if (G.wait) return; G.wait = true; b.disabled = true; let r; try { r = await makeAcct(name, legacy, G.remember); } finally { G.wait = false; } if (r) G.msg = r; render(); };
  const pathHave = h('div', {class:'path'}, h('span', {class:'lab'}, 'Path A'), h('h3', null, 'I have a studio number'),
    h('p', {class:'mut small'}, 'Type the number you saved when you started.'),
    h('input', {type:'text', id:'f-num', autocomplete:'off', autocapitalize:'characters', spellcheck:'false', placeholder:'S4F-ABCD-EFGH', value:G.key || '', 'aria-label':'Studio number', 'aria-describedby':'f-gate-msg',
      oninput:e => { G.key = e.target.value; }, onkeydown:e => { if (e.key === 'Enter') signIn(); }}),
    h('button', {class:'btn pri wide', type:'button', id:'f-signin', onclick:signIn}, 'Sign in'), msg,
    pickChips(['Remember on this device'], G.remember ? ['Remember on this device'] : [], true, (o, on) => { G.remember = on; }));
  let newBox;
  if (G.mode === 'show' && S.key){
    const num = h('p', {class:'num', id:'acct-key', style:'font-size:clamp(22px,6.6vw,34px)'}, G.newKey || S.key);
    newBox = h('div', {class:'path', style:'border-color:var(--ink)'}, h('span', {class:'lab'}, S.acct.legacy ? 'Your studio · your number' : 'Path B · your number'), num,
      h('p', {class:'small'}, 'Save this number. You sign in with it on any phone or computer. There is no password.'),
      h('div', {style:'display:flex;gap:10px;align-items:center;flex-wrap:wrap'}, copyBtn(G.newKey || S.key, num, 'f-key-copy')),
      S.acct.setupDone ? null : h('div', {class:'note'}, 'Next come five short steps: Channels, Style, Motion, Brand and Times. Each step shows what it changes. It takes about two minutes.'),
      h('button', {class:'btn pri wide', type:'button', id:'f-key-saved', onclick:() => { G.mode = 'in'; done(); }}, S.acct.setupDone ? 'I saved it, open my studio' : 'Start step 1 of 5'));
  } else newBox = h('div', {class:'path'}, h('span', {class:'lab'}, 'Path B'), h('h3', null, 'I’m new'),
    h('p', {class:'mut small'}, 'Get a studio number. Then set up your studio in five short steps.'),
    h('button', {class:'btn wide', type:'button', id:'f-new', onclick:e => make(e.currentTarget, 'My studio', false)}, 'Get my number'));
  const n = oldJobs();
  const old = offerOld() && G.mode !== 'show' ? h('div', {class:'path', style:'border-color:var(--ink);margin-top:26px'}, h('span', {class:'lab'}, 'Your existing studio'),
    h('p', null, (n ? n + (n === 1 ? ' job is' : ' jobs are') + ' waiting in your existing studio.' : 'Your existing studio has saved settings.') + ' Give it a studio number to open it. Nothing in it changes.'),
    h('button', {class:'btn pri wide', type:'button', id:'f-old-move', onclick:e => make(e.currentTarget, 'My studio', true)}, 'Get the number for my existing studio')) : null;
  return [h('section', {class:'hero'}, h('span', {class:'lab'}, 'Automate your channels, hands free'), h('h1', null, 'One video in.', h('br'), 'A week of clips out.'),
      h('p', null, 'Paste a YouTube link. Claude finds the best moments, cuts the clips and fills your posting schedule.')),
    old, h('div', {class:'paths'}, pathHave, newBox),
    owner ? h('div', {style:'padding-top:26px'}, h('button', {class:'btn ghost sm', type:'button', id:'f-admin', onclick:() => go('admin')}, 'Admin: see all studio numbers')) : null];
}

// The admin view lists every studio and its number. Only the owner of this page, signed in to Claude, can open it.
// One watch on the accounts runs while the admin view is open. render() stops it on every other screen.
let admStop = null, admRows = null, admErr = '';
function vAdmin(){
  if (owner && !admStop){
    if (db) admStop = db.collection('accounts').onSnapshot(snap => { admRows = snap.docs.map(d => [d.id, d.data()]); admErr = ''; if (S.screen === 'admin') render(); },
      () => { admErr = 'The studios could not be loaded. Check your connection and open this view again.'; if (S.screen === 'admin') render(); });
    else { admStop = () => {}; admRows = Object.entries(localGet('s4f.accounts', {})); } }
  const rows = (admRows || []).slice().sort((a, b) => (a[1].createdAt || 0) - (b[1].createdAt || 0));
  const box = h('div', {class:'rec'}, !owner ? h('p', {class:'note'}, 'Only the owner of this page can open the admin view.')
    : admErr ? h('p', {class:'note'}, admErr) : !admRows ? h('p', {class:'mut', style:'padding-block:14px'}, 'Loading the studios…')
    : !rows.length ? h('p', {class:'mut', style:'padding-block:14px'}, 'No studio exists yet.')
    : rows.map(([key, a]) => { const jobs = [...ALL.values()].filter(j => mine(j, key, a.legacy)).length, code = h('span', {class:'code'}, key), msg = h('span', {class:'fine', role:'status'});
      return h('div', {class:'acctrow'}, h('div', {style:'display:flex;flex-direction:column;gap:5px;min-width:0'}, h('b', {style:'font-weight:500'}, String(a.name || 'Unnamed studio')), code,
          h('span', {class:'fine'}, (a.createdAt ? 'Made ' + new Date(a.createdAt).toLocaleDateString() + ' · ' : '') + jobs + (jobs === 1 ? ' job' : ' jobs') + (a.legacy ? ' · first studio' : '') + (a.setupDone ? '' : ' · setup not finished')), msg),
        h('div', {style:'display:flex;flex-direction:column;gap:6px'}, copyBtn(key, code, null, 'Copy'),
          h('button', {class:'btn sm', type:'button', onclick:async e => { e.currentTarget.disabled = true; const r = await openAcct(key); if (r){ msg.textContent = r === 'none' ? 'That studio is gone.' : r; return; } S.welcome = true; S.gate.mode = 'in'; go('recap'); }}, 'Open'))); }));
  return [pagehead('Admin', 'Every studio number.', 'Each number opens one studio. Share a number only with the person who runs that studio. This list shows only for the owner of this page.'),
    h('div', {class:'stack'}, box, h('div', null, h('button', {class:'btn ghost', type:'button', onclick:() => S.key ? go('setup') : go('signin')}, S.key ? 'Back to Setup' : 'Back to sign-in')))];
}

/*__VSTEP__*/

/* ---------- the studio home ---------- */
function clipRows(){
  const now = Date.now(), all = []; for (const [id, j] of S.jobs) for (const c of (j.clips || [])) all.push({id, j, c});
  const t = x => x.c.publishAt ? new Date(x.c.publishAt).getTime() : 0;
  const up = all.filter(x => t(x) >= now).sort((a, b) => t(a) - t(b)), rest = all.filter(x => t(x) < now).sort((a, b) => t(b) - t(a));
  return up.concat(rest);
}
function realPhone(c, cls){ return h('div', {class:'phone' + (cls ? ' ' + cls : '')}, hasVid(c) ? lazyVid(c.asset, false, 'real') : h('div', {class:'ph0'}, String(c.onScreen || c.title || 'Clip ' + c.n))); }
function clipTag(c){ const st = qState(c); if (c.redo) return ['Changes sent · v' + (c.ver || 2), ' sent'];
  return [st[0] === 'Posted' ? 'Posted' + (c.publishAt ? ' · ' + dayShort(c.publishAt) : '') : c.publishAt ? when12(c.publishAt) : st[0], st[0] === 'Posted' ? ' sent' : '']; }
function vRecap(){
  const rows = clipRows(), real = rows.length > 0;
  const cards = real ? rows.slice(0, 12).map((x, i) => { const tg = clipTag(x.c);
      return h('button', {class:'cc', type:'button', role:'listitem', 'aria-label':'Open clip: ' + (x.c.title || 'clip ' + x.c.n), onclick:e => { if (carousel.dataset.moved === '1'){ e.preventDefault(); return; } openEditor(x); }},
        realPhone(x.c), h('span', {class:'tag' + tg[1]}, tg[0]), h('b', null, String(x.c.title || 'Clip ' + x.c.n))); })
    : CLIPS.map((c, i) => h('div', {class:'cc', role:'listitem'}, makePhone(false, c), h('span', {class:'tag'}, 'Example ' + (i + 1)), h('b', null, c.title)));
  const carousel = h('div', {class:'car', role:'list', 'aria-label':'Your clips'}, cards);
  carousel.addEventListener('pointerdown', e => { if (e.pointerType !== 'mouse') return; carDrag = {el:carousel, sx:e.clientX, sl:carousel.scrollLeft}; carousel.dataset.moved = '0'; });
  const step = d => carousel.scrollBy({left:d * (carousel.firstElementChild.offsetWidth + 12), behavior:'smooth'});
  const stage = h('div', {class:'group'}, h('div', {class:'carhead'}, h('span', {class:'lab'}, real ? 'Your clips · drag or tap one to open' : 'Example clips · yours show here after your first job'),
      h('div', {class:'arrows'}, h('button', {class:'btn ghost sm', type:'button', 'aria-label':'Earlier clips', onclick:() => step(-1)}, '←'), h('button', {class:'btn ghost sm', type:'button', 'aria-label':'Later clips', onclick:() => step(1)}, '→'))),
    carousel, real && rows.length > 12 ? h('div', null, h('button', {class:'btn ghost sm', type:'button', onclick:() => go('queue')}, 'See all ' + rows.length + ' clips in the queue')) : null);
  return vRecapRest(stage);
}
function recRows(){ return h('div', {class:'rec'}, STEPS.map((st, i) => h('div', {class:'recrow'}, h('span', {class:'lab'}, st.name), h('span', {class:'v'}, SUM[i]()),
    h('button', {class:'btn ghost sm', type:'button', 'aria-label':'Edit ' + st.name, onclick:() => { S.back = true; go('step', i); }}, 'Edit')))); }
function vRecapRest(stage){
  return [h('div', {class:'main', style:'grid-template-columns:minmax(0,1fr)'}, h('div', {class:'content', style:'max-width:760px'},
    h('div', {class:'head'}, h('span', {class:'lab'}, S.welcome ? 'Signed in' : 'Recap · all five steps done'), h('h2', null, S.welcome ? 'Welcome back.' : 'Here is your studio.'),
      h('p', null, 'Every new job starts from these answers. Tap Edit to change one. You can also change them later in Setup.')),
    stage, recRows(), presetPanel(() => render()),
    h('div', {class:'group'}, h('span', {class:'lab'}, 'What happens after you start a job'),
      h('div', {class:'pipe'}, h('div', null, 'You paste a YouTube link.'), h('div', null, 'Claude finds the best moments and lists them.'),
        h('div', null, 'You keep or skip each moment.'), h('div', null, 'Claude cuts the clips and checks the platform rules.'), h('div', null, 'Buffer posts each clip at its time.')))))];
}
/*__CARDRAG__*/
// One clip, opened: the real video, the caption spot, the volume, and notes for Claude.
function openEditor(x){
  const cl = x.c, j = x.j, id = x.id, total = (j.clips || []).length;
  const spotText = c => c.capY == null ? (S.set.capY == null ? 'Default spot, low on the screen' : 'Your spot for all clips') : (c.capY < 40 ? 'Near the top' : c.capY < 62 ? 'In the middle' : 'Near the bottom') + ' · ' + Math.round(c.capY) + '% down';
  const volOf = () => cl.vol == null ? 100 : cl.vol, volText = v => v === 0 ? 'Clip volume · muted' : 'Clip volume · ' + v + '%';
  const note = h('p', {class:'hint', 'aria-live':'polite'}, 'Drag up or down on the clip to mark where its captions should sit.');
  const spot = h('span', {class:'small'}, spotText(cl));
  const vid = hasVid(cl) ? h('video', {class:'real', playsinline:true, loop:true, preload:'metadata', src:'/_blob/' + cl.asset + '#t=0.1'}) : null;
  const mark = h('div', {class:'caps capmark', 'aria-hidden':'true'}, 'Captions');
  const big = h('div', {class:'phone big edit', tabindex:'0', role:'group', 'aria-label':'Clip. Drag up or down to mark the caption spot. Arrow keys work too.'}, vid || h('div', {class:'ph0'}, String(cl.title || 'Clip ' + cl.n)), mark);
  const place = () => { mark.style.top = (cl.capY != null ? cl.capY : S.set.capY != null ? S.set.capY : 78) + '%'; spot.textContent = spotText(cl); };
  const drop = () => { const a = cl.capY; note.textContent = a > 41 && a < 72 ? 'That spot is where a face often sits. Claude keeps the captions off the face.' : 'Marked. Save to keep this spot.'; };
  const yOf = e => { const r = big.getBoundingClientRect(); return Math.min(90, Math.max(10, (e.clientY - r.top) / r.height * 100)); };
  let drag = false; const up = () => { if (!drag) return; drag = false; big.classList.remove('dragging'); drop(); };
  big.addEventListener('pointerdown', e => { drag = true; big.classList.add('dragging'); try { big.setPointerCapture(e.pointerId); } catch (err) {} cl.capY = yOf(e); place(); e.preventDefault(); });
  big.addEventListener('pointermove', e => { if (drag){ cl.capY = yOf(e); place(); } });
  big.addEventListener('pointerup', up); big.addEventListener('pointercancel', up);
  big.addEventListener('keydown', e => { if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return; e.preventDefault();
    const cur = cl.capY != null ? cl.capY : S.set.capY != null ? S.set.capY : 78; cl.capY = Math.min(90, Math.max(10, cur + (e.key === 'ArrowUp' ? -3 : 3))); place(); drop(); });
  place();
  const play = vid ? h('button', {class:'btn ghost sm', type:'button', onclick:e => { if (vid.paused){ vid.volume = Math.min(1, volOf() / 100); vid.play().catch(() => {}); e.currentTarget.textContent = 'Pause'; } else { vid.pause(); e.currentTarget.textContent = 'Play'; } }}, 'Play') : null;
  const vl = h('label', {class:'lab', for:'f-vol'}, volText(volOf()));
  const vol = h('input', {type:'range', id:'f-vol', min:0, max:150, step:5, value:volOf(), oninput:e => { cl.vol = +e.target.value; vl.textContent = volText(cl.vol); if (vid) vid.volume = Math.min(1, cl.vol / 100);
    note.textContent = cl.vol > 100 ? 'This clip will play louder than the source video.' : cl.vol === 0 ? 'This clip will play with no sound.' : 'This clip will play at ' + cl.vol + '% of the source volume.'; }});
  const ctl = h('div', {class:'ctl'}, h('span', {class:'lab'}, 'Caption spot'), spot,
    h('div', {style:'display:flex;gap:8px;flex-wrap:wrap'},
      h('button', {class:'btn ghost sm', type:'button', onclick:() => { if (cl.capY == null){ note.textContent = 'Drag the caption mark first. Then you can use that spot for all clips.'; return; }
        S.set.capY = Math.round(cl.capY); dirty(); note.textContent = 'New clips now use this caption spot.'; }}, 'Use for all clips'),
      h('button', {class:'btn ghost sm', type:'button', onclick:() => { cl.capY = null; place(); note.textContent = 'This clip uses the shared caption spot again.'; }}, 'Reset')),
    vl, vol, h('p', {class:'fine'}, vid ? 'Press Play to hear the clip. The volume changes when Claude cuts the next version.' : 'This clip has no video on the page yet.'));
  const notes = h('textarea', {id:'f-notes', value:cl.notes || '', placeholder:'For example: start one second later, or use a shorter title.', oninput:e => { cl.notes = e.target.value; }});
  const sent = h('p', {class:'small', role:'status'}, cl.redo ? 'Version ' + (cl.ver || 2) + ' was asked for. It replaces the earlier version.' : '');
  const st = qState(cl);
  const close = () => { if (vid) vid.pause(); ov.remove(); document.body.style.overflow = ''; removeEventListener('keydown', esc); render(); };
  const esc = e => { if (e.key === 'Escape') close(); };
  const xb = h('button', {class:'btn ghost sm', type:'button', onclick:close}, 'Close');
  const ov = h('div', {class:'ov', role:'dialog', 'aria-modal':'true', 'aria-label':'Edit clip ' + cl.n, onclick:e => { if (e.target === ov) close(); }},
    h('div', {class:'ovin'},
      h('div', {class:'ovhead'}, h('div', {style:'display:flex;flex-direction:column;gap:6px;min-width:0'}, h('span', {class:'lab'}, 'Clip ' + cl.n + ' of ' + total + ' · version ' + (cl.ver || 1) + ' · ' + (j.name || 'job')), h('h3', null, String(cl.title || 'Clip ' + cl.n))), xb),
      h('div', {style:'display:flex;flex-direction:column;gap:10px;min-width:0'}, big, play ? h('div', null, play) : null, note),
      h('div', {style:'display:flex;flex-direction:column;gap:14px;min-width:0'},
        h('div', {class:'row'}, h('span', {class:'pill ' + st[1]}, st[0]), cl.publishAt ? h('span', {class:'pill'}, when12(cl.publishAt)) : null, rulesPill(cl),
          liveLinks(cl).map(l => h('a', {class:'btn ghost sm', href:l[1], target:'_blank', rel:'noopener'}, 'Open on ' + l[0]))),
        ctl,
        h('div', {class:'field'}, h('label', {for:'f-notes'}, 'Notes for Claude'), h('p', {class:'fh'}, 'Say what else to change. Claude reads this with your edits.'), notes),
        h('p', {class:'note'}, 'Claude always replaces this clip. It never makes a second copy.'),
        h('div', {style:'display:flex;gap:10px;flex-wrap:wrap'},
          h('button', {class:'btn ghost', type:'button', onclick:async () => { await saveJob(id, {clips:j.clips}); sent.textContent = 'Saved. Nothing was sent yet.'; }}, 'Save'),
          h('button', {class:'btn pri', type:'button', style:'flex:1 1 200px', disabled:st[0] === 'Posted' ? true : null, onclick:async e => { const b = e.currentTarget; b.disabled = true; cl.ver = (cl.ver || 1) + 1; cl.redo = {at:Date.now(), from:(cl.redo && cl.redo.from) || j.status || 'review'};
            const r = await tell(b, 'Studio4Free: change clip ' + cl.n + ' of job "' + (j.name || 'untitled') + '" (job id ' + id + '). Follow CLAUDE.md in the studio4free repository.');
            await saveJob(id, {clips:j.clips, status:'cutting'}); b.disabled = false;
            sent.textContent = (r === 'sent' ? 'Sent. ' : 'Saved. No Claude Code session is listening, so say "run the studio jobs" there. ') + 'Claude will replace clip ' + cl.n + ' with version ' + cl.ver + '.'; }}, 'Save and send for changes')),
        sent, st[0] === 'Posted' ? h('p', {class:'fine'}, 'This clip is already posted. Claude cannot change a posted clip.') : null,
        h('div', null, h('button', {class:'btn ghost sm', type:'button', onclick:() => { close(); S.open.add(id + '-' + cl.n); go('job', id); }}, 'Open the whole job')))));
  document.body.append(ov); document.body.style.overflow = 'hidden'; addEventListener('keydown', esc); xb.focus();
}

/*__PRESETS__*/

/* ---------- new clips ---------- */
function vStart(){
  const msg = h('p', {class:'err', id:'startmsg', role:'status'});
  const keep = () => { const g = id => (document.getElementById(id) || {}).value || ''; S.link = g('f-link'); S.job = g('f-job'); S.show = g('f-show'); S.want = g('f-want'); };
  return [h('div', {class:'main'}, h('aside', {class:'stage', style:'flex-direction:column;align-items:stretch;gap:14px'}, liveEl(clipsDemo), makePhone(true),
      liveEl(() => h('p', {class:'fine'}, 'Style: ' + SUM[1]() + '. Ad: ' + SUM[3]() + '.'))),
    h('div', {class:'content'}, h('div', {class:'head'}, h('span', {class:'lab'}, S.jobs.size ? 'New clips' : 'First job'), h('h2', null, CLIPSTEP.q),
        h('p', null, 'Start with what Claude should look for. Then paste the video. You check the moments before anything gets cut.')),
      presetPanel(() => { keep(); render(); }), CLIPSTEP.body(),
      h('div', {class:'group'}, h('span', {class:'lab'}, 'The video'),
        field('f-link', 'YouTube link', 'It starts with https://youtu.be/ or https://www.youtube.com/.', h('input', {type:'url', id:'f-link', inputmode:'url', placeholder:'https://youtu.be/…', value:S.link || '', oninput:keep})),
        field('f-job', 'Job name', 'A short name, such as the guest.', h('input', {type:'text', id:'f-job', placeholder:'Episode 42 with Sam', value:S.job || '', oninput:keep})),
        field('f-show', 'Podcast', 'The show this video comes from. Its clips fill the post times of that show.', h('div', {class:'field'}, h('input', {type:'text', id:'f-show', value:S.show || '', oninput:keep}),
          shows().length ? pickChips(shows(), S.show, false, (o, on) => { S.show = on ? o : ''; document.getElementById('f-show').value = S.show; }) : null)),
        field('f-want', 'Moments you already want', 'Optional. Timestamps help.', h('textarea', {id:'f-want', value:S.want || '', oninput:keep})), msg)))];
}
async function sendJob(){
  const g = id => ((document.getElementById(id) || {}).value || '').trim(), v = g('f-link'), msg = document.getElementById('startmsg');
  const bad = CLIPSTEP.ok(); if (bad){ msg.style.color = 'var(--warn)'; msg.textContent = bad; return; }
  if (!/^https:\/\/((www\.|m\.)?youtube\.com\/(watch\?|shorts\/|live\/)|youtu\.be\/)\S+$/i.test(v)){ msg.style.color = 'var(--warn)'; msg.textContent = 'Paste a full YouTube link first.'; return; }
  nx.disabled = true; const s = S.set, look = ovName();
  const doc = {kind:'clips', name:g('f-job') || 'Untitled', show:g('f-show'), link:v, status:'sent', statusNote:'', shortlist:[], clips:[],
    ask:{count:s.count, len:s.len, parts:s.parts, kinds:s.kinds, want:g('f-want')},
    look:{overlay:look, ovs:clone(s.ovs[look]), capColor:s.capColor, capY:s.capY == null ? null : s.capY, media:clone(s.media), fit:s.fit, zoom:s.zoom, captions:s.captions, language:s.language, brand:s.brand, descTail:s.descTail}};
  const id = await addJob(doc); if (!id){ nx.disabled = false; msg.style.color = 'var(--warn)'; msg.textContent = 'The job could not be saved. Check your connection.'; return; }
  const r = await tell(nx, 'Studio4Free: run the new clipping job "' + doc.name + '" (job id ' + id + '). Follow CLAUDE.md in the studio4free repository.');
  S.jobs.get(id).sentNote = told(r); S.link = S.job = S.show = S.want = ''; go('job', id);
}
function vEdit(){
  const f = S.form || (S.form = {link:'', name:'', what:'', estyle:'', edits:['Add captions'], target:''}), msg = h('p', {class:'err', role:'status'});
  const inp = (id, k, area, ph) => h(area ? 'textarea' : 'input', {id, type:area ? null : 'text', value:f[k] || '', placeholder:ph || '', oninput:e => { f[k] = e.target.value; }});
  return [pagehead('New edit job', 'What should the edit do?', 'Give one video and say what to change. Claude shows you the plan before it renders.'),
    h('div', {class:'stack', style:'max-width:760px'},
      group('The video', null, field('f-elink', 'YouTube link', 'It starts with https://youtu.be/ or https://www.youtube.com/.', inp('f-elink', 'link', false, 'https://youtu.be/…')), field('f-ename', 'Job name', null, inp('f-ename', 'name'))),
      group('The edit', null, field('f-ewhat', 'What should the edit do?', 'Say it the way you would tell a friend.', inp('f-ewhat', 'what', true)),
        fld('Editing style', null, pickChips(ESTYLES, f.estyle, false, (o, on) => { f.estyle = on ? o : ''; })),
        fld('The edit should also', null, pickChips(EDITS, f.edits, true, (o, on) => { const s = new Set(f.edits); on ? s.add(o) : s.delete(o); f.edits = [...s]; })),
        field('f-etarget', 'Length of the finished video', 'Optional.', inp('f-etarget', 'target'))),
      msg, h('div', {class:'row'}, h('button', {class:'btn ghost', type:'button', onclick:() => { S.form = null; go('jobs'); }}, 'Back'),
        h('button', {class:'btn pri grow', type:'button', onclick:async e => { const b = e.currentTarget, v = (f.link || '').trim();
          if (!/^https:\/\/((www\.|m\.)?youtube\.com\/(watch\?|shorts\/|live\/)|youtu\.be\/)\S+$/i.test(v)){ msg.textContent = 'Paste a full YouTube link first.'; return; }
          b.disabled = true; const s = S.set, doc = {kind:'edit', name:(f.name || '').trim() || 'Untitled', show:'', link:v, status:'sent', statusNote:'', shortlist:[], clips:[],
            ask:{what:f.what || '', style:f.estyle, edits:f.edits, target:f.target || ''}, look:{overlay:ovName(), zoom:s.zoom, captions:s.captions, language:s.language, brand:s.brand, descTail:s.descTail}};
          const id = await addJob(doc); if (!id){ b.disabled = false; msg.textContent = 'The job could not be saved. Check your connection.'; return; }
          const r = await tell(b, 'Studio4Free: run the new edit job "' + doc.name + '" (job id ' + id + '). Follow CLAUDE.md in the studio4free repository.');
          S.jobs.get(id).sentNote = told(r); S.form = null; go('job', id); }}, 'Send to Claude Code')))];
}

/* ---------- jobs ---------- */
function vJobs(){
  const list = [...S.jobs].sort((a, b) => (b[1].updatedAt || 0) - (a[1].updatedAt || 0));
  return [pagehead('Jobs', 'Every video you sent.', 'One job is one video. Open a job to keep or skip its moments and to check its clips.'),
    h('div', {class:'stack'}, h('div', {class:'row'}, h('button', {class:'btn pri grow', type:'button', onclick:() => go('start')}, 'Make new clips'), h('button', {class:'btn grow', type:'button', onclick:() => { S.form = null; go('edit'); }}, 'New edit job')),
      list.length ? h('div', {class:'sect'}, list.map(([id, j]) => { const st = STATUS[j.status] || [j.status || 'Draft', '']; const n = (j.clips || []).length, sl = (j.shortlist || []).length;
        return h('button', {class:'card', type:'button', onclick:() => go('job', id)}, h('div', {class:'row'}, h('span', {class:'pill'}, j.kind === 'edit' ? 'Edit' : 'Clips'), h('span', {class:'pill ' + st[1]}, st[0])),
          h('h3', null, j.name || 'Untitled'), h('p', {class:'mut small'}, (j.show ? j.show + ' · ' : '') + (n ? n + (n === 1 ? ' clip' : ' clips') : sl ? sl + ' moments found' : 'No clips yet') + ' · edited ' + new Date(j.updatedAt || j.createdAt || Date.now()).toLocaleDateString())); }))
      : h('div', {class:'empty'}, h('b', null, 'No jobs yet. '), 'Tap "Make new clips" and paste a YouTube link. The job appears here with its status and its clips.'))];
}
function vJob(){
  const id = S.id, j = S.jobs.get(id); if (!j) return [pagehead('Job', 'This job is not here.', 'It may have been deleted.')];
  const st = STATUS[j.status] || [j.status || 'Draft', ''], out = [];
  const act = (label, status, text, pri) => h('button', {class:'btn wide' + (pri ? ' pri' : ''), type:'button', onclick:async e => { const b = e.currentTarget; b.disabled = true; const r = await tell(b, text); await saveJob(id, {status}); j.sentNote = told(r); render(); }}, label);
  out.push(h('div', {class:'pagehead'}, h('div', {class:'row'}, h('button', {class:'btn ghost sm', type:'button', onclick:() => go('jobs')}, '← Jobs'), h('span', {class:'pill'}, j.kind === 'edit' ? 'Edit' : 'Clips'), h('span', {class:'pill ' + st[1]}, st[0])),
    h('h2', null, j.name || 'Untitled'), h('p', {style:'overflow-wrap:anywhere'}, j.link ? h('a', {href:j.link, target:'_blank', rel:'noopener'}, j.link) : 'No link')));
  const body = h('div', {class:'stack', style:'max-width:760px'}); out.push(body);
  body.append(...[fld('Podcast', 'Clips from this job fill the post times of this show: ' + slotTimes(j.show).map(fmt12).join(', ') + '.', h('input', {type:'text', id:'f-jshow', value:j.show || '', onchange:e => { saveJob(id, {show:e.target.value.trim()}).then(render); }}), 'f-jshow'),
    j.statusNote ? h('p', {class:'note'}, String(j.statusNote)) : null, j.sentNote ? h('p', {class:'note', role:'status'}, j.sentNote) : null,
    j.status === 'sent' ? act('Send to Claude Code again', 'sent', 'Studio4Free: run the job "' + j.name + '" (job id ' + id + '). Follow CLAUDE.md in the studio4free repository.') : null].filter(Boolean));
  const sl = j.shortlist || [], clips = (j.clips || []).slice().sort((a, b) => (a.publishAt ? new Date(a.publishAt) : 9e15) - (b.publishAt ? new Date(b.publishAt) : 9e15) || a.n - b.n);
  if (sl.length && !clips.length){ const kept = () => sl.filter(x => x.keep !== false).length; const cnt = h('span', null, kept());
    body.append(h('div', {class:'group'}, h('div', {class:'gh'}, h('span', {class:'lab'}, 'Moments found'), h('span', {class:'lab', style:'color:var(--iron)'}, sl.length + ' found')),
      h('p', {class:'mut small'}, 'Switch off the moments you do not want. Then cut the rest. The parts of one story switch together.'),
      h('div', null, sl.map(x => h('div', {class:'pick'}, h('div', null, x.parts > 1 ? h('span', {class:'pill info', style:'margin-right:8px'}, 'Part ' + x.part + ' of ' + x.parts) : null, h('b', null, String(x.title || 'Moment ' + x.n)), x.line ? h('p', {class:'small'}, '"' + x.line + '"') : null, x.why ? h('p', {class:'small mut'}, String(x.why)) : null),
        h('button', {class:'chip', type:'button', 'aria-pressed':String(x.keep !== false), onclick:e => { x.keep = x.keep === false; if (x.series){ for (const y of sl) if (y.series === x.series) y.keep = x.keep; saveJob(id, {shortlist:sl}); render(); return; } e.currentTarget.setAttribute('aria-pressed', String(x.keep)); e.currentTarget.textContent = x.keep ? 'Keep' : 'Skip'; cnt.textContent = kept(); saveJob(id, {shortlist:sl}); }}, x.keep !== false ? 'Keep' : 'Skip'),
        h('span', {class:'tcode'}, tcode(x.start) + ' → ' + tcode(x.end) + ' · ' + Math.round(x.end - x.start) + 's')))),
      j.status === 'shortlist' ? h('button', {class:'btn pri wide', type:'button', onclick:async e => { const b = e.currentTarget; b.disabled = true; const r = await tell(b, 'Studio4Free: cut the kept moments for job "' + j.name + '" (job id ' + id + '). Follow CLAUDE.md in the studio4free repository.'); await saveJob(id, {status:'cutting', shortlist:sl}); j.sentNote = told(r); render(); }}, 'Cut the kept moments (', cnt, ')') : null)); }
  if (clips.length){
    const open = clips.filter(c => !c.publishAt).length, held = clips.filter(c => c.check && c.check.level === 'risk' && !c.check.override).length;
    body.append(h('div', {class:'group'}, h('div', {class:'gh'}, h('span', {class:'lab'}, 'Clips'), h('span', {class:'lab', style:'color:var(--iron)'}, clips.length + (clips.length === 1 ? ' clip' : ' clips'))),
      open ? h('button', {class:'btn wide', type:'button', onclick:() => { fillSlots(j); saveJob(id, {clips:j.clips}); render(); }}, 'Fill the next open times (' + open + (open === 1 ? ' clip)' : ' clips)')) : null,
      h('div', {class:'sect'}, clips.map(c => clipCard(id, j, c))),
      partIssues(clips).map(t => h('p', {class:'note'}, t)),
      flashIssues(clips).length ? h('p', {class:'note'}, flashIssues(clips).join(' ')) : null,
      flashIssues(clips).length ? act('Fix the Noxi card on these clips', 'cutting', 'Studio4Free: cut the clips of job "' + j.name + '" (job id ' + id + ') again where the Noxi flash does not match the post day. Follow CLAUDE.md in the studio4free repository.') : null,
      held ? h('p', {class:'note'}, held + (held === 1 ? ' clip has' : ' clips have') + ' a rules risk. Claude Code will not schedule ' + (held === 1 ? 'it' : 'them') + ' unless you choose "Post anyway".') : null,
      act('Check these clips against the platform rules', 'checking', 'Studio4Free: check the clips of job "' + j.name + '" (job id ' + id + ') against the platform rules. Follow CLAUDE.md in the studio4free repository.'),
      j.status === 'review' ? act('Schedule these in Buffer', 'scheduling', 'Studio4Free: schedule the clips of job "' + j.name + '" (job id ' + id + ') in Buffer. Follow CLAUDE.md in the studio4free repository.', true) : null)); }
  if (!sl.length && !clips.length) body.append(h('div', {class:'empty'}, h('b', null, 'Nothing to show yet. '), j.kind === 'edit' ? 'The edited video appears here when Claude Code finishes it.' : 'The moments Claude Code finds appear here. You pick the ones to cut.'));
  let sure = false; body.append(h('div', null, h('button', {class:'btn sm warn', type:'button', onclick:e => { if (sure) dropJob(id); else { sure = true; e.currentTarget.textContent = 'Delete this job for good?'; } }}, 'Delete job')));
  return out;
}
// A job can hold a dozen clips, so each clip starts as a short row. A tap opens its editor.
function clipCard(id, j, c){
  const k = id + '-' + c.n; if (S.open.has(k)) return clipFull(id, j, c);
  const note = c.check && c.check.level !== 'clear' && (c.check.notes || [])[0];
  return h('button', {class:'card cliprow', type:'button', 'aria-label':'Open clip ' + c.n, onclick:() => { S.open.add(k); render(); }},
    h('div', {class:'row'}, h('span', {class:'pill'}, 'Clip ' + c.n), c.parts > 1 ? h('span', {class:'pill info'}, 'Part ' + c.part + ' of ' + c.parts) : null, c.flash ? h('span', {class:'pill hot'}, 'Noxi card') : null, rulesPill(c), c.redo ? h('span', {class:'pill ok'}, 'Changes sent · v' + (c.ver || 2)) : null),
    h('h3', null, String(c.title || 'Clip ' + c.n)),
    h('p', {class:'small mut'}, (c.publishAt ? when12(c.publishAt) + ' · ' + wall(c.publishAt).slice(5, 10).replace('-', '/') : 'No post time') + (c.seconds ? ' · ' + Math.round(c.seconds) + 's' : '') + ' · tap to open'),
    note ? h('p', {class:'small', style:'overflow-wrap:anywhere'}, String(note)) : null);
}
function clipFull(id, j, c){
  const save = () => saveJob(id, {clips:j.clips}); const k = id + '-' + c.n;
  const vid = hasVid(c) ? lazyVid(c.asset, true) : h('div', {class:'ph'}, 'Clip ' + c.n, h('br'), c.seconds ? Math.round(c.seconds) + 's' : '');
  const dl = downloads && hasVid(c) ? h('button', {class:'btn ghost sm', type:'button', onclick:async e => { const b = e.currentTarget; b.disabled = true; b.textContent = 'Preparing…';
    try { const blob = await (await fetch('/_blob/' + c.asset)).blob(); await downloads.save({filename:(j.name || 'clip').replace(/[^\w -]+/g, '').trim().replace(/\s+/g, '-') + '-' + c.n + '.mp4', data:blob}); b.textContent = 'Saved'; } catch (err) { b.textContent = 'Download'; } b.disabled = false; }}, 'Download') : null;
  return h('div', {class:'card'}, h('div', {class:'row'}, h('button', {class:'btn ghost sm', type:'button', onclick:() => { S.open.delete(k); render(); }}, 'Close clip ' + c.n),
      h('button', {class:'btn ghost sm', type:'button', onclick:() => openEditor({id, j, c})}, 'Caption spot, volume, notes')),
    h('div', {class:'clip'}, vid, h('div', {class:'side'},
      h('div', {class:'row'}, h('span', {class:'pill'}, 'Clip ' + c.n), c.parts > 1 ? h('span', {class:'pill info'}, 'Part ' + c.part + ' of ' + c.parts) : null, c.flash ? h('span', {class:'pill hot'}, 'Noxi card') : null, rulesPill(c), h('span', {class:'pill ' + qState(c)[1]}, qState(c)[0])),
      c.status ? h('p', {class:'small mut', style:'overflow-wrap:anywhere'}, String(c.status)) : null,
      fld('Publish time', null, h('input', {type:'datetime-local', id:'f-at-' + k, value:c.publishAt ? wall(c.publishAt) : '', onchange:e => { c.publishAt = e.target.value ? wallToISO(e.target.value) : ''; save(); }}), 'f-at-' + k), dl)),
    rulesBox(c, save),
    fld('Title', null, h('input', {type:'text', id:'f-t-' + k, value:c.title || '', onchange:e => { c.title = e.target.value; save(); }}), 'f-t-' + k),
    fld('Description', null, h('textarea', {id:'f-d-' + k, value:c.description || '', onchange:e => { c.description = e.target.value; save(); }}), 'f-d-' + k));
}
function rulesPill(c){ const k = c.check && c.check.level; return h('span', {class:'pill ' + ({clear:'ok', look:'wait', risk:'bad'}[k] || '')}, k === 'clear' ? 'Rules: clear' : k === 'look' ? 'Rules: look' : k === 'risk' ? 'Rules: risk' : 'Rules: not checked'); }
function rulesBox(c, save){
  const ck = c.check; if (!ck || !((ck.notes || []).length || ck.level === 'risk')) return null;
  const src = (ck.sources || []).filter(s => /^https:\/\//.test(s.url || ''));
  return h('div', {class:'note rules'}, h('b', {style:'font-weight:500;color:var(--ink)'}, 'Rules check' + (ck.at ? ', ' + new Date(ck.at).toLocaleDateString() : '')),
    (ck.notes || []).length ? h('ul', null, ck.notes.map(n => h('li', null, String(n)))) : null,
    src.length ? h('p', {class:'small mut'}, 'Read: ', src.flatMap((s, i) => [i ? ', ' : '', h('a', {href:s.url, target:'_blank', rel:'noopener'}, String(s.title || s.url))])) : null,
    ck.level === 'risk' ? h('div', {class:'row', style:'margin-top:8px'}, h('button', {class:'chip', type:'button', 'aria-pressed':String(!!ck.override), onclick:e => { ck.override = !ck.override; e.currentTarget.setAttribute('aria-pressed', String(ck.override)); save(); }}, 'Post anyway')) : null);
}
function flashIssues(clips){
  const days = S.set.flashDays || [], out = [];
  if (!(S.acct && S.acct.legacy)) return out;   // the Noxi card belongs to the first studio only
  for (const c of clips){ if (!c.publishAt || /publish/i.test(c.status || '')) continue; const want = days.includes(weekday(c.publishAt));
    if (want && !c.flash) out.push('Clip ' + c.n + ' posts on a ' + weekday(c.publishAt) + ' and has no Noxi card yet.');
    if (!want && c.flash) out.push('Clip ' + c.n + ' has the Noxi card, and it posts on a ' + weekday(c.publishAt) + '.'); }
  return out;
}
function partIssues(clips){
  const out = [], by = {}; for (const c of clips) if (c.series && c.parts > 1) (by[c.series] || (by[c.series] = [])).push(c);
  for (const s in by){ const ps = by[s].slice().sort((a, b) => a.part - b.part);
    for (let i = 1; i < ps.length; i++){ const a = ps[i - 1], b = ps[i]; if (b.publishAt && (!a.publishAt || new Date(a.publishAt) >= new Date(b.publishAt))) out.push('Part ' + b.part + ' of "' + (b.title || s) + '" posts before part ' + a.part + '. Give part ' + a.part + ' the earlier time.'); } }
  return out;
}
function fillSlots(j){
  const taken = new Set(allClips().map(x => wall(x.c.publishAt))), times = slotTimes(j.show).sort();
  if (!times.length) return;   // with no post times the search below would never end
  let day = new Date(todayKey() + 'T12:00:00Z'); const next = () => { for (;;){ day = new Date(day.getTime() + 864e5); const key = day.toISOString().slice(0, 10); for (const t of times){ const w = key + 'T' + t; if (!taken.has(w)){ taken.add(w); day = new Date(day.getTime() - 864e5); return w; } } } };
  for (const c of (j.clips || []).slice().sort((a, b) => a.n - b.n)) if (!c.publishAt) c.publishAt = wallToISO(next());
}

/* ---------- the queue and the schedule ---------- */
function qRow(x){
  const c = x.c, j = x.j, st = qState(c), posted = st[0] === 'Posted', ids = c.bufferIds || {};
  const where = (S.set.services || []).map(svc => { const k = svc.toLowerCase(), on = !!ids[k] || (posted && new RegExp(svc, 'i').test(c.status || '')) || !!(c.live || {})[k];
    return h('span', {class:'pill ' + (on ? (posted ? 'ok' : 'info') : '')}, svc + (on ? '' : ' · not yet')); });
  return h('div', {class:'slot'}, h('span', {class:'t'}, c.publishAt ? fmt12(hm(c.publishAt)).replace(' ', ' ') : '--:--'),
    h('div', {class:'b'}, h('b', null, String(c.title || 'Clip ' + c.n) + (c.parts > 1 ? ' · Part ' + c.part + ' of ' + c.parts : '')),
      h('span', {class:'from'}, 'From ' + (j.show || 'an unnamed show') + (j.name ? ' · ' + j.name : ''), j.link ? [' · ', h('a', {href:j.link, target:'_blank', rel:'noopener'}, 'source video')] : null),
      h('div', {class:'row'}, h('span', {class:'pill ' + st[1]}, st[0]), st[0] === 'Not in Buffer yet' ? null : where),
      h('div', {class:'row'}, h('button', {class:'btn ghost sm', type:'button', onclick:() => openEditor(x)}, hasVid(c) ? 'Watch and edit' : 'Edit'),
        liveLinks(c).map(l => h('a', {class:'btn ghost sm', href:l[1], target:'_blank', rel:'noopener'}, 'Open on ' + l[0])))));
}
function vQueue(){
  const rows = []; for (const [id, j] of S.jobs) for (const c of (j.clips || [])) rows.push({id, j, c});
  const when = x => x.c.publishAt ? new Date(x.c.publishAt).getTime() : 9e15;
  const posted = rows.filter(x => qState(x.c)[0] === 'Posted').sort((a, b) => when(b) - when(a));
  const next = rows.filter(x => qState(x.c)[0] !== 'Posted').sort((a, b) => when(a) - when(b));
  const waiting = next.filter(x => qState(x.c)[0] === 'Not in Buffer yet').length, list = S.q === 'posted' ? posted : next;
  const seg = h('div', {class:'chips', role:'group', 'aria-label':'Which clips to show'}, [['next', 'Up next · ' + next.length], ['posted', 'Posted · ' + posted.length]].map(o =>
    h('button', {class:'chip', type:'button', 'aria-pressed':String(S.q === o[0]), onclick:() => { S.q = o[0]; render(); }}, o[1])));
  const days = []; let cur = null;
  for (const x of list){ const k = x.c.publishAt ? dayKey(x.c.publishAt) : ''; if (!cur || cur.k !== k){ cur = {k, items:[]}; days.push(cur); } cur.items.push(x); }
  return [pagehead('Queue', 'What posts, and where it is from.', 'Every clip that is posted or waiting to post, with its show. Times are in ' + tzName() + '.'),
    h('div', {class:'stack', style:'max-width:760px;gap:8px'}, seg,
      S.q !== 'posted' && waiting ? h('p', {class:'note', style:'margin-top:10px'}, waiting + (waiting === 1 ? ' clip has' : ' clips have') + ' a post time and ' + (waiting === 1 ? 'is' : 'are') + ' not in Buffer yet. ' + (waiting === 1 ? 'It' : 'They') + ' will not post until a Claude Code session schedules ' + (waiting === 1 ? 'it' : 'them') + '.') : null,
      list.length ? days.map(d => h('div', {class:'day'}, h('h3', null, d.k ? dayName(d.k) + (d.k === todayKey() ? ' · today' : '') : 'No post time yet'), d.items.map(qRow)))
        : h('div', {class:'empty', style:'margin-top:14px'}, h('b', null, S.q === 'posted' ? 'Nothing is posted yet. ' : 'Nothing is waiting. '), S.q === 'posted' ? 'A clip moves here when Buffer publishes it.' : 'Clips appear here when a job gives them a post time.'))];
}
function coverage(){
  const all = allClips(), today = todayKey();
  return h('div', {class:'panel'}, h('span', {class:'lab'}, 'Post times · ' + slots().length + ' a day'), h('div', null, slots().map(sl => {
    const mine2 = all.filter(x => hm(x.c.publishAt) === sl.time && dayKey(x.c.publishAt) >= today && !/publish/i.test(x.c.status || ''));
    const days = new Set(mine2.map(x => dayKey(x.c.publishAt))); let d = new Date(today + 'T12:00:00Z'), last = '';
    while (days.has(d.toISOString().slice(0, 10))){ last = d.toISOString().slice(0, 10); d = new Date(d.getTime() + 864e5); }
    const drafts = mine2.filter(x => qState(x.c)[0] !== 'Scheduled').length;
    return h('div', {class:'pick'}, h('div', null, h('b', null, fmt12(sl.time) + ' · ' + (sl.show || 'Any podcast')),
        h('p', {class:'small mut'}, !mine2.length ? 'No clips waiting.' : (last ? 'Filled every day through ' + dayName(last) + '.' : 'Nothing for today. ' + mine2.length + ' clips wait on later days.') + (drafts ? ' ' + drafts + ' of ' + mine2.length + ' are not scheduled in Buffer yet.' : ''))),
      h('span', {class:'pill ' + (!mine2.length ? 'bad' : drafts ? 'wait' : 'ok')}, mine2.length + (mine2.length === 1 ? ' clip' : ' clips'))); })));
}
function vSchedule(){
  const all = allClips(), today = todayKey(), byDay = new Map();
  for (const x of all){ const k = dayKey(x.c.publishAt); if (!S.showPast && k < today) continue; (byDay.get(k) || byDay.set(k, []).get(k)).push(x); }
  const past = all.filter(x => dayKey(x.c.publishAt) < today).length, times = slots();
  const keys = new Set(byDay.keys()); for (let i = 0; i < 7; i++) keys.add(new Date(new Date(today + 'T12:00:00Z').getTime() + i * 864e5).toISOString().slice(0, 10));
  const days = [...keys].sort().map(k => { const rows = (byDay.get(k) || []).map(x => ({t:hm(x.c.publishAt), x})); if (k >= today) for (const sl of times) if (!rows.some(r => r.t === sl.time)) rows.push({t:sl.time, x:null, show:sl.show});
    rows.sort((a, b) => a.t.localeCompare(b.t));
    return h('div', {class:'day'}, h('h3', null, dayName(k), k === today ? ' · today' : ''), rows.map(r => r.x ? h('div', {class:'slot'}, h('span', {class:'t'}, fmt12(r.t).replace(' ', ' ')),
        h('div', {class:'b'}, h('b', null, String(r.x.c.title || 'Clip ' + r.x.c.n) + (r.x.c.parts > 1 ? ' · Part ' + r.x.c.part + ' of ' + r.x.c.parts : '')),
          h('div', {class:'row'}, h('span', {class:'pill ' + qState(r.x.c)[1]}, qState(r.x.c)[0]), h('button', {class:'btn ghost sm', type:'button', onclick:() => go('job', r.x.id)}, r.x.j.name || 'Job'),
            h('button', {class:'btn ghost sm', type:'button', onclick:() => openEditor(r.x)}, hasVid(r.x.c) ? 'Watch' : 'Edit'))))
      : h('div', {class:'slot open'}, h('span', {class:'t'}, fmt12(r.t).replace(' ', ' ')), h('div', {class:'b'}, 'Open' + (r.show ? ' · ' + r.show : ''))))); });
  return [pagehead('Schedule', 'Each day, slot by slot.', 'Every clip with a post time, in ' + tzName() + '. Open rows are post times with no clip yet.'),
    h('div', {class:'stack', style:'max-width:760px;gap:8px'}, coverage(),
      past ? h('div', {style:'padding-top:10px'}, h('button', {class:'btn ghost sm', type:'button', onclick:() => { S.showPast = !S.showPast; render(); }}, S.showPast ? 'Hide past days' : 'Show ' + past + ' past clips')) : null, days)];
}

/* ---------- setup ---------- */
function vSetup(){
  const num = h('span', {class:'num', id:'acct-key', style:'font-size:clamp(20px,6vw,28px);-webkit-user-select:all;user-select:all'}, S.key); let sure = false;
  return [pagehead('Setup', 'Your studio.', 'Your studio number, your answers and your clip choices. Every new job starts from these.'),
    h('div', {class:'stack', style:'max-width:760px'},
      group('Studio', S.acct.legacy ? 'First studio' : null,
        field('f-acct-name', 'Studio name', null, h('input', {type:'text', id:'f-acct-name', maxlength:60, value:S.acct.name || '', onchange:e => { const v = e.target.value.trim(); if (v) saveAcct({name:v}).then(render); else e.target.value = S.acct.name || ''; }})),
        h('div', {class:'field'}, h('span', {class:'fl'}, 'Studio number'), h('p', {class:'fh'}, 'This number is the only way into this studio. There is no password. Keep it somewhere safe.'), num, h('div', null, copyBtn(S.key, num, 'f-acct-copy')))),
      group('Your answers', '5 steps', recRows(), h('div', null, h('button', {class:'btn ghost', type:'button', id:'f-acct-wiz', onclick:() => { S.back = false; S.welcome = false; go('step', 0); }}, 'Run the five steps again'))),
      group('Clip choices', 'For new jobs', CLIPSTEP.body()),
      group('Leave', null, h('div', {class:'row'},
        h('button', {class:'btn warn', type:'button', id:'f-acct-out', onclick:e => { if (sure) signOut('', true); else { sure = true; e.currentTarget.textContent = 'Sign out? You need the studio number to get back in.'; } }}, 'Sign out'),
        owner ? h('button', {class:'btn ghost', type:'button', id:'f-admin', onclick:() => go('admin')}, 'Admin: see all studio numbers') : null)))];
}

/* ---------- start ---------- */
function route(){
  if (!S.key){ if (S.screen !== 'admin') S.screen = 'signin'; return render(); }
  if (['step','start','edit','admin'].includes(S.screen)) return render();
  const m = /^#job-(.+)$/.exec(location.hash), v = location.hash.slice(1), t = TABS.find(x => x[2] === v);
  if (m && S.jobs.has(m[1])){ S.screen = 'job'; S.id = m[1]; } else if (t) S.screen = t[0]; else if (S.screen === 'signin' || !TABS.some(x => x[0] === S.screen)) S.screen = 'recap';
  render();
}
addEventListener('hashchange', () => { if (S.key && !['step','start','edit'].includes(S.screen)) route(); });
// Is there a studio from before accounts that no account holds yet? The sign-in screen offers to give it a number.
function checkOld(n){
  (db ? Promise.all([db.doc('meta/legacy').get(), db.doc('settings/main').get()]).then(([m, s]) => ({claimed:m.exists, main:s.exists}))
    : Promise.resolve({claimed:!!localGet('s4f.legacyClaimed', false), main:localGet('s4f.set', null) !== null})).then(o => { S.old = o;
      if (S.screen !== 'signin' || S.gate.wait || S.busy || S.store === 'wait' || !offerOld() || typing()) return; render(); },
    e => { if (again(e)) setTimeout(checkOld, Math.min(30000, 3000 * (n || 1)), (n || 1) + 1); });
}
// Runs once, when the store is known. A number remembered on this device opens its studio without asking.
async function boot(){
  checkOld(); const k = normKey(localGet('s4f.key', ''));
  if (k){ const r = await openAcct(k, 3);
    if (r) Object.assign(S.gate, {key:k, msg:r !== 'none' ? r : db ? 'The studio remembered on this device no longer exists. Enter another number, or get a new one.' : NOLOCAL});
    else if (S.acct.setupDone){ S.screen = 'recap'; S.welcome = true; } else { S.screen = 'step'; S.step = 0; S.welcome = false; } }
  S.busy = false; if (S.store !== 'wait') route();
}
function useLocal(){ db = null; S.store = 'local'; ALL = new Map(Object.entries(localGet('s4f.jobs', {}))); boot(); }
render();
const cl = window.claude && typeof window.claude.use === 'function' ? window.claude : null;
if (cl){
  cl.use('db').then(d => { if (!d) return useLocal(); db = d; col = d.collection('jobs');
    const t = setTimeout(() => { if (S.store === 'wait'){ S.store = 'db'; S.note = 'Your saved jobs cannot be reached yet. The page keeps trying.'; render(); } }, 10000);
    // One watch on all jobs for the life of the page. Signing in or out only changes which of them S.jobs holds.
    col.onSnapshot(snap => { clearTimeout(t); S.note = ''; const first = S.store === 'wait'; S.store = 'db'; const m = new Map(); for (const x of snap.docs){ const old = ALL.get(x.id); m.set(x.id, Object.assign({}, x.data(), old && old.sentNote ? {sentNote:old.sentNote} : {})); } ALL = m; scope();
      if (first){ if (!S.busy) route(); return; } soft(); },
      () => { clearTimeout(t); S.store = 'db'; S.note = 'Your saved jobs could not be loaded. Close and reopen this page.'; render(); });
    boot();
  }).catch(useLocal);
  cl.use('comments').then(x => { comments = x || null; }).catch(() => {});
  cl.use('downloads').then(x => { downloads = x || null; }).catch(() => {});
  cl.use('assets').then(x => { assets = x || null; }).catch(() => {});
  cl.use('user').then(u => u ? u.isOwner() : false).then(v => { owner = !!v; if (owner && !S.busy && S.store !== 'wait' && (S.screen === 'signin' || S.screen === 'setup') && !typing() && !S.gate.wait) render(); }).catch(() => {});
} else useLocal();
})();
