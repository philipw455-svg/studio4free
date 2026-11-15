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

/* ---------- settings: what a missing field of a settings document means ---------- */
const OVDEF = { Poster:{color:'#ffffff', size:'Large', hold:'2'}, Banner:{bg:'#000000', fg:'#ffffff', pos:'Top'}, 'Glass card':{tint:'#ffffff', blur:'Soft', round:'Round'},
  Sticker:{bg:'#f8ff7a', tilt:'Left'}, Frame:{color:'#ff6ad5', width:'Thin'} };
const DEF = { times:['12:15','17:00'], tz:'America/Chicago', services:['YouTube','TikTok'], brand:'', descTail:'', count:'10', len:'20 to 40 seconds',
  kinds:['Strong opinions','Funny moments','Emotional moments'], fit:'Black banner with title and brand', zoom:'Smooth', captions:'Yes', language:'Mute it',
  parts:'Split long stories into parts', overlay:'Poster', capColor:'#ffe300', flashDays:['Tuesday','Friday'], comment:'', buffer:'' };
// The first (legacy) account keeps DEF. A new account starts cleaner.
const defaults = legacy => Object.assign({}, DEF, legacy ? null : {services:['YouTube','Instagram'], flashDays:[]});
const ESTYLES = ['Quick-cut talking clip','Raw funny moments','Heavy-edit comedy'];
const EDITS = ['Cut filler words','Cut silences','Add captions','Mute strong language','Add a title at the top','Make it vertical'];
const STATUS = { sent:['Waiting for Claude Code','wait'], working:['Claude Code is working','info'], shortlist:['Pick your clips','hot'], cutting:['Cutting clips','info'], checking:['Checking the rules','info'],
  review:['Check the clips','hot'], scheduling:['Sending to Buffer','info'], scheduled:['Scheduled','ok'], done:['Done','ok'], blocked:['Blocked','wait'] };

// screen: signin, admin, step (the five setup steps), recap (the studio home), start (new clips), edit (new edit job), jobs, job, queue, schedule, setup.
// key and acct are the open account. gate is the state of the sign-in form. ALL holds every job; S.jobs holds the open account's.
const S = { screen:'signin', step:0, id:null, jobs:new Map(), set:{}, store:'wait', note:'', key:null, acct:null, busy:true, old:null,
  gate:{mode:'in', key:'', msg:'', remember:true, wait:false, newKey:''}, pday:'flash', hint:'', err:'', back:false, welcome:true,
  showPast:false, open:new Set(), q:'next', form:null, preset:'', presetMsg:'', link:'', job:'', show:'', want:'' };
let db = null, col = null, setDoc = null, acctDoc = null, comments = null, downloads = null, assets = null, owner = false;
let ALL = new Map(), setLS = 's4f.set', watches = [], saveT = 0, lastSaved = '';
const ovName = () => OV[S.set.overlay] ? S.set.overlay : 'Poster';
// The setup screens read and write their choices through C. It is the open account's settings.
const C = new Proxy({}, { get:(_, k) => k === 'overlay' ? ovName() : S.set[k], set:(_, k, v) => { S.set[k] = v; return true; } });
