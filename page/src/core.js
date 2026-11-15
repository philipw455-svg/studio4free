
/* ---------- settings shape ---------- */
function norm(s){
  for (const k of ['services','flashDays','kinds','presets']) s[k] = Array.isArray(s[k]) ? s[k] : [];
  for (const k of ['brand','descTail','comment','buffer']) s[k] = String(s[k] == null ? '' : s[k]);
  s.channels = Object.assign({youtube:'', instagram:'', tiktok:''}, s.channels);
  s.media = Object.assign({banner:null, flash:null, ending:null}, s.media);
  for (const k in s.media) if (s.media[k] && (s.media[k].temp || !s.media[k].url)) s.media[k] = null;   // a file that lived in one browser tab only
  const o = s.ovs || {}; s.ovs = {}; for (const k in OVDEF) s.ovs[k] = Object.assign({}, OVDEF[k], o[k]);
  if (!/^#[0-9a-f]{6}$/i.test(s.capColor || '')) s.capColor = DEF.capColor;
  s.slots = (Array.isArray(s.slots) && s.slots.length ? s.slots : (s.times || DEF.times).map(t => ({time:t, show:''}))).map(x => ({time:String(x.time || ''), show:String(x.show || '')}));
  if (!s.tz) s.tz = DEF.tz;
  if (!TZS.some(z => z[0] === s.tz)) TZS.push([s.tz, s.tz.replace(/_/g, ' ')]);
  return s;
}

/* ---------- time ---------- */
function tzOff(d, tz){ const p = {}; for (const x of new Intl.DateTimeFormat('en-US', {timeZone:tz, hourCycle:'h23', year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit'}).formatToParts(d)) p[x.type] = +x.value;
  return (Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - Math.floor(d.getTime() / 1000) * 1000) / 60000; }
function wallToISO(wall){ const m = /^(\d+)-(\d+)-(\d+)T(\d+):(\d+)/.exec(wall); if (!m) return ''; const g = Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5]);
  let t = g - tzOff(new Date(g), S.set.tz) * 60000; t = g - tzOff(new Date(t), S.set.tz) * 60000; return new Date(t).toISOString(); }
function wall(iso){ const d = new Date(iso); if (isNaN(d)) return ''; return new Date(d.getTime() + tzOff(d, S.set.tz) * 60000).toISOString().slice(0, 16); }
const dayKey = iso => wall(iso).slice(0, 10), hm = iso => wall(iso).slice(11, 16);
function dayName(key){ const d = new Date(key + 'T12:00:00Z'); return d.toLocaleDateString(undefined, {weekday:'long', month:'short', day:'numeric', timeZone:'UTC'}); }
const todayKey = () => dayKey(new Date().toISOString());
const dayShort = iso => new Date(dayKey(iso) + 'T12:00:00Z').toLocaleDateString(undefined, {weekday:'short', timeZone:'UTC'});
const weekday = iso => new Date(dayKey(iso) + 'T12:00:00Z').toLocaleDateString('en-US', {weekday:'long', timeZone:'UTC'});
function tcode(s){ s = Math.max(0, +s || 0); const hh = Math.floor(s / 3600), mm = Math.floor(s % 3600 / 60), ss = Math.floor(s % 60); return (hh ? hh + ':' : '') + String(mm).padStart(2, '0') + ':' + String(ss).padStart(2, '0'); }

/* ---------- storage ---------- */
const saveEl = document.getElementById('save');
const say = t => { saveEl.textContent = t; };
function localGet(k, d){ try { return JSON.parse(localStorage.getItem(k)) || d; } catch (e) { return d; } }
function localSet(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
async function saveJob(id, patch){
  const j = S.jobs.get(id); if (!j) return; Object.assign(j, patch, {updatedAt:Date.now()}); say('Saving…');
  try { if (S.store === 'db') await col.doc(id).update(Object.assign({}, patch, {updatedAt:j.updatedAt})); else localSet('s4f.jobs', Object.fromEntries(ALL)); say(S.store === 'db' ? 'Saved' : 'Saved on this device only'); }
  catch (e) { say('Not saved. Check your connection.'); }
}
async function addJob(doc){
  const now = Date.now(); Object.assign(doc, {account:S.key, createdAt:now, updatedAt:now}); let id;
  try { if (S.store === 'db'){ const ref = col.doc(); id = ref.id; await ref.set(doc); } else { id = 'l' + now.toString(36); }
    S.jobs.set(id, doc); ALL.set(id, doc); if (S.store !== 'db') localSet('s4f.jobs', Object.fromEntries(ALL)); return id; }
  catch (e) { say('The job could not be saved.'); return null; }
}
async function dropJob(id){ S.jobs.delete(id); ALL.delete(id); try { if (S.store === 'db') await col.doc(id).delete(); else localSet('s4f.jobs', Object.fromEntries(ALL)); } catch (e) { say('The job could not be deleted.'); } go('jobs'); }
async function saveSet(){
  if (!S.key) return; S.set.times = [...new Set(goodSlots().map(x => x.time))]; const body = JSON.stringify(S.set); say('Saving…');
  try { if (S.store === 'db') await setDoc.set(JSON.parse(body)); else localSet(setLS, S.set); lastSaved = body; say(S.store === 'db' ? 'Saved' : 'Saved on this device only'); } catch (e) { say('Settings were not saved.'); }
}
// Every choice saves by itself, a moment after the last change.
function dirty(){ if (!S.key) return; clearTimeout(saveT); saveT = setTimeout(() => { saveT = 0; if (S.key && JSON.stringify(S.set) !== lastSaved) saveSet(); }, 600); }

/* ---------- accounts ---------- */
// The studio number is the only credential. The page reads and watches accounts/<the entered number>. Only the admin view lists the collection.
const KEYCH = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
function newKey(){ let s = ''; const lim = 256 - 256 % KEYCH.length;   // bytes at or over lim are dropped, so every character is equally likely
  while (s.length < 8) for (const b of crypto.getRandomValues(new Uint8Array(16))) if (b < lim && s.length < 8) s += KEYCH[b % KEYCH.length];
  return 'S4F-' + s.slice(0, 4) + '-' + s.slice(4); }
function normKey(v){ let s = String(v == null ? '' : v).toUpperCase().replace(/[\s-]/g, ''); if (s.length === 11 && s.startsWith('S4F')) s = s.slice(3);
  return s.length === 8 && [...s].every(c => KEYCH.includes(c)) ? 'S4F-' + s.slice(0, 4) + '-' + s.slice(4) : ''; }
// A job with no account field is from before accounts. It belongs to the legacy account. Old jobs are never rewritten.
const mine = (j, key, legacy) => !!key && (j.account === key || (!!legacy && !j.account));
function scope(){ S.jobs = new Map([...ALL].filter(([, j]) => mine(j, S.key, S.acct && S.acct.legacy))); }
const typing = () => { const a = document.activeElement; return !!a && /INPUT|TEXTAREA|SELECT/.test(a.tagName); };
// Draw again after a change from the database, unless that would take a field, a setup step or an open clip away from the owner.
function soft(){ if (S.store === 'wait' || S.busy || typing() || S.gate.wait || ['signin','step','start','edit','montage'].includes(S.screen) || document.querySelector('.ov')) return; render(); }
// db.d.ts: "unavailable", and any code it does not list, is worth another try. The codes below cannot succeed on this page load.
const again = e => !/^(invalid_argument|quota_exceeded|revoked|not_granted|capability_disabled|capability_removed|transform_error)$/.test((e && e.code) || '');
// Local mode reads the stored accounts on every use, so a second tab never writes back an old copy.
const putAcct = (k, a) => localSet('s4f.accounts', Object.assign(localGet('s4f.accounts', {}), {[k]:a}));
const NOLOCAL = 'This view only sees studios made on this device. None of them has that number. Open the page inside Claude to reach your studio.';
const oldJobs = () => [...ALL.values()].filter(j => !j.account).length;
const offerOld = () => !!S.old && !S.old.claimed && (S.old.main || oldJobs() > 0);
const unwatch = () => { for (const u of watches) u(); watches = []; };
function enter(key, a, set){
  unwatch(); clearTimeout(saveT); saveT = 0; S.key = key; S.acct = Object.assign({}, a); S.set = norm(Object.assign(defaults(a.legacy), set)); lastSaved = JSON.stringify(S.set);
  PRESETS = S.set.presets; S.preset = ''; setLS = a.legacy ? 's4f.set' : 's4f.set.' + key;
  if (db){ acctDoc = db.doc('accounts/' + key); setDoc = db.doc(a.legacy ? 'settings/main' : 'settings/' + key);
    watches = [acctDoc.onSnapshot(x => { if (S.key !== key) return; if (!x.exists){ if (!x.metadata.fromCache) signOut('That studio no longer exists.'); return; } S.acct = Object.assign({}, x.data()); soft(); }, () => {}),
      // A settings change from elsewhere is taken only while the owner is not in the middle of changing settings here.
      setDoc.onSnapshot(x => { if (S.key !== key || !x.exists || saveT || ['step','start'].includes(S.screen)) return;
        const nx = norm(Object.assign(defaults(a.legacy), x.data())), body = JSON.stringify(nx); if (body === JSON.stringify(S.set)) return;
        S.set = nx; lastSaved = body; PRESETS = S.set.presets; soft(); }, () => {})]; }
  scope();
}
// Returns '' when the account is open, 'none' when no account has that number, or a sentence to show.
async function openAcct(key, tries){
  try { let a, set;
    if (db){ const x = await db.doc('accounts/' + key).get(); if (!x.exists) return 'none'; a = x.data();
      const sx = await db.doc(a.legacy ? 'settings/main' : 'settings/' + key).get(); set = sx.exists ? sx.data() : {}; }
    else { a = localGet('s4f.accounts', {})[key]; if (!a) return 'none'; set = localGet(a.legacy ? 's4f.set' : 's4f.set.' + key, {}); }
    enter(key, a, set); return ''; }
  catch (e) { if (tries > 0 && again(e)){ await new Promise(ok => setTimeout(ok, 3000)); return openAcct(key, tries - 1); }
    return 'Your studio cannot be reached. Check your connection and try again.'; }
}
// Everything is read before anything is written. When a write fails, the half-made account is removed.
async function makeAcct(name, legacy, remember){
  const key = newKey(), a = Object.assign({name, createdAt:Date.now()}, legacy ? {legacy:true, setupDone:true} : null); let set = defaults(false);
  const taken = 'Your existing studio is already in an account. Sign in with its number.';
  try {
    if (db){
      if (legacy){ const [m, sx] = await Promise.all([db.doc('meta/legacy').get(), db.doc('settings/main').get()]); if (m.exists){ S.old = {claimed:true, main:sx.exists}; return taken; } set = sx.exists ? sx.data() : {}; }
      await db.doc('accounts/' + key).set(a);
      if (legacy) await db.doc('meta/legacy').set({claimed:true, at:Date.now()}); else await db.doc('settings/' + key).set(set);
    } else {
      if (legacy && localGet('s4f.legacyClaimed', false)){ S.old = {claimed:true, main:true}; return taken; }
      putAcct(key, a); if (legacy){ localSet('s4f.legacyClaimed', true); set = localGet('s4f.set', {}); } else localSet('s4f.set.' + key, set); }
  } catch (e) {
    if (db) db.doc('accounts/' + key).delete().catch(() => {});
    return 'The studio could not be created. Check your connection and try again.'; }
  if (legacy) S.old = {claimed:true, main:true};
  enter(key, a, set); localSet('s4f.key', remember ? key : ''); S.gate.mode = 'show'; S.gate.newKey = key; return '';
}
async function saveAcct(patch){ Object.assign(S.acct, patch); say('Saving…');
  try { if (db) await acctDoc.update(patch); else putAcct(S.key, S.acct); say(db ? 'Saved' : 'Saved on this device only'); } catch (e) { say('The studio was not saved.'); } }
function signOut(msg, forget){ unwatch(); clearTimeout(saveT); saveT = 0; if (forget) localSet('s4f.key', ''); S.key = null; S.acct = null; S.jobs = new Map(); S.set = {}; PRESETS = [];
  S.gate = {mode:'in', key:'', msg:msg || '', remember:true, wait:false, newKey:''}; try { location.hash = ''; } catch (e) {} go('signin'); }
function copyBtn(key, el, id, label){
  return h('button', {class:'btn ghost sm', type:'button', id, onclick:e => { const b = e.currentTarget;
    const pick = () => { try { const r = document.createRange(); r.selectNodeContents(el); const s = getSelection(); s.removeAllRanges(); s.addRange(r); } catch (err) {} b.textContent = 'Selected. Copy it now.'; };
    try { navigator.clipboard.writeText(key).then(() => { b.textContent = 'Copied'; }, pick); } catch (err) { pick(); } }}, label || 'Copy number');
}
async function tell(el, text){
  if (!comments) return 'none';
  try { const can = await comments.canSendToClaude(); if (can !== 'available') return can; const anchor = await comments.anchorFor(el); await comments.sendToClaude({anchor, text}); return 'sent'; }
  catch (e) { return (e && e.code) || 'error'; }
}
const told = r => r === 'sent' ? 'Sent to Claude Code. It starts without you asking.' : 'Saved. No Claude Code session is listening. Open Claude Code in the studio4free repository and say "run the studio jobs".';
