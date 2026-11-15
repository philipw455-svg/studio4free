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
