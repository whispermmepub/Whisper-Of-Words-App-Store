const root=document.querySelector('#detailRoot');
if(!document.querySelector('link[data-premium-previews]')){const l=document.createElement('link');l.rel='stylesheet';l.href='premium-previews.css?v=16';l.dataset.premiumPreviews='1';document.head.append(l)}
if(!document.querySelector('link[data-designed-previews]')){const l=document.createElement('link');l.rel='stylesheet';l.href='designed-previews.css?v=16';l.dataset.designedPreviews='1';document.head.append(l)}
const slug=new URLSearchParams(location.search).get('app')||'wow-reader';
function setTheme(t){document.documentElement.dataset.theme=t;localStorage.setItem('wow-store-theme',t);document.querySelector('meta[name="theme-color"]')?.setAttribute('content',t==='dark'?'#11161d':'#f7f8fa')}
setTheme(localStorage.getItem('wow-store-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'));document.querySelector('#themeToggle')?.addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
const esc=(v='')=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

const previewCopy={
  'wow-reader':[
    ['Beautiful Library','Browse your books in a clean grid'],
    ['Library List','Track reading progress at a glance'],
    ['Comfort Reading','Smooth, focused reading for long books'],
    ['Reader Settings','Fonts, spacing, margins and themes']
  ],
  'wow-epub-maker':[
    ['Create EPUB','Convert DOCX into a clean offline EPUB'],
    ['Book Details','Set title, author, cover and output'],
    ['Building EPUB','Structure, chapters and fonts'],
    ['Preserve Layout','Keep pages, footnotes and Word layout'],
    ['Ready to Read','Open the EPUB as soon as it is built']
  ],
  'wow-ocr':[
    ['Scan · OCR · Export','စာရွက်ပုံထဲက စာသားတွေကို မြန်မြန်ဖတ်'],
    ['Fast Text Scanning','ပုံထဲက စာသားကို မြန်မြန်ဖတ်'],
    ['Editable Text','OCR ပြီးရင် စာသားကို ပြင်နိုင်'],
    ['Cloud & AI OCR','Online OCR နှင့် AI OCR settings']
  ],
  'wow-proof-reader':[
    ['Read · Edit · Perfect','ဖတ်မယ် · ပြင်မယ် · ပြီးစီး'],
    ['Inline Editing','စာဖတ်ရင်း တိုက်ရိုက်ပြင်'],
    ['Find & Replace','ရှာ၊ အစားထိုး၊ မြန်မြန်ပြင်'],
    ['Paragraph Tools','Align, justify, bold နှင့် page tools']
  ]
};
const designedSlugs=new Set(['wow-ocr','wow-proof-reader']);

Promise.all([
  fetch('data/apps.json?v=16',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error();return r.json()}),
  fetch('data/wow-note.json?v=16',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error();return r.json()})
]).then(([d,wowNote])=>{const a=[...(d.apps||[]),wowNote].find(x=>x.slug===slug);if(!a)throw new Error();document.title=`${a.name} · Whisper Of Words App Store`;render(a)}).catch(()=>root.innerHTML='<div class="loading-card">App not found.<br><br><a href="./">Back to Store</a></div>');

function rawPreview(a,s,i){return `<img class="raw-preview-shot" src="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=" alt="${esc(a.name)} screenshot ${i+1}" data-preview-src="${esc(s)}">`}
function premiumPreview(a,s,i){
  const copy=(previewCopy[a.slug]||[])[i]||[`Feature ${i+1}`,'Explore the app experience'];
  return `<article class="promo-preview"><div class="promo-grid-dots"></div><div class="promo-ring"></div><div class="promo-brand"><span class="promo-brand-icon"><img src="${esc(a.icon)}" alt=""></span><strong>${esc(a.name)}</strong></div><div class="promo-flare"><i></i></div><h3>${esc(copy[0])}</h3><p>${esc(copy[1])}</p><div class="promo-stage"></div><div class="promo-phone"><div class="promo-speaker"></div><img class="promo-shot" src="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=" alt="${esc(a.name)} screenshot ${i+1}" data-preview-src="${esc(s)}"><div class="promo-phone-fallback"><img src="${esc(a.icon)}" alt=""><b>${esc(copy[0])}</b><span>${esc(copy[1])}</span></div></div><div class="promo-side-icon">✦</div></article>`
}
function posterLogo(slug){
  return slug==='wow-ocr'
    ? `<span class="poster-logo poster-logo-ocr"><i></i><b>W</b></span>`
    : `<span class="poster-logo poster-logo-proof"><i class="book-left"></i><i class="book-right"></i><i class="bookmark"></i><i class="feather"></i></span>`;
}
const lines=(n=8)=>Array.from({length:n},(_,i)=>`<i style="--w:${72+((i*17)%25)}%"></i>`).join('');
function posterMock(slug,i){
  if(slug==='wow-ocr'){
    if(i===0)return `<div class="mock-status">1:30 <span>◌⌁ Wi‑Fi ▮▮</span></div><div class="ocr-splash"><span class="ocr-splash-logo">W</span></div><div class="mock-nav">≡　□　◁　♟</div>`;
    if(i===1)return `<div class="mock-status">1:32 <span>◌⌁ Wi‑Fi ▮▮</span></div><div class="mock-top dark">‹ <b>1 / 1</b><span>⚙</span></div><div class="mock-tabs dark"><b>▣ Image</b><span>Tᵀ Text</span></div><div class="scan-doc">${lines(17)}</div><div class="tool-row dark"><span>✂<small>Crop</small></span><span>↻<small>Rotate</small></span><span>◩<small>B&amp;W</small></span><span>✧<small>Enhance</small></span><span>▣<small>Lens</small></span></div><div class="tool-row dark bottom"><span>Tᵀ<small>OCR</small></span><span>✦<small>AI OCR</small></span><span>⌯<small>Share</small></span><span>⌫<small>Delete</small></span></div>`;
    if(i===2)return `<div class="mock-status">1:32 <span>◌⌁ Wi‑Fi ▮▮</span></div><div class="mock-top dark">‹ <b>1 / 1</b><span>⚙</span></div><div class="mock-tabs dark"><span>▣ Image</span><b>Tᵀ Text</b></div><div class="edit-tools dark"><span>▣<small>Paste</small></span><span>▢<small>Copy</small></span><span>⌫<small>Clear</small></span><span>Tᵀ<small>OCR</small></span><span>✦<small>AI</small></span></div><div class="align-row dark"><b>Normal</b><span>≡</span><span>≡</span><span>≡</span><span>≡</span></div><div class="ocr-text-block">${lines(19)}</div>`;
    return `<div class="mock-status settings-status">1:32 <span>◌⌁ Wi‑Fi ▮▮</span></div><div class="settings-panel"><h4>Settings</h4><h5>Appearance</h5><div class="setting-chips"><span>White</span><span>Black</span><b>Midnight</b></div><hr><h5>Fast online OCR</h5><p>Add a Google Cloud Vision API key for fast DOCUMENT_TEXT_DETECTION.</p><div class="fake-input">Cloud Vision API key</div><button>Save OCR key</button><small>Online OCR not configured</small><hr><h5>AI OCR</h5><p>Choose an AI provider and paste your own API key.</p><div class="setting-actions">Clear Gemini　 Close</div></div>`;
  }
  if(i===0)return `<div class="mock-status light">1:40 <span>◌⌁ Wi‑Fi ▮▮</span></div><div class="proof-library"><header><span class="tiny-book">⌑</span><b>WoW Proof Reader</b><small>Read · Edit · Perfect</small></header><div class="search-box">Search books</div><div class="library-tabs"><b>Active</b><span>Favorites</span><span>Archive</span><span>Trash</span></div><label>YOUR LIBRARY <em>1 book</em></label><div class="doc-card"><strong>DOCX</strong><div><b>သန်းမိုး_ပုလဲကကြိုး</b><small>8% read　·　7 edits</small><i></i></div></div><button class="add-docx">＋　Add DOCX</button></div><div class="mock-nav light">≡　□　◁　♟</div>`;
  if(i===1)return `<div class="mock-status light">1:42 <span>◌⌁ Wi‑Fi ▮▮</span></div><div class="proof-reader"><div class="reader-head">‹ <b>သန်းမိုး_ပုလဲကကြိုး</b><button>Save</button><span>•••</span></div><small>22%　·　8 edits　·　0 marks</small><div class="reader-lines">${lines(7)}<div class="highlight-lines">${lines(4)}</div>${lines(6)}</div><div class="reader-menu"><span>Find</span><b>Edit</b><span>Fix</span><span>Mark</span><span>Chapters</span><span>Aa</span></div></div>`;
  if(i===2)return `<div class="mock-status light">1:42 <span>◌⌁ Wi‑Fi ▮▮</span></div><div class="proof-find"><div class="reader-head">‹ <b>သန်းမိုး_ပုလဲကကြိုး</b><button>Save</button><span>•••</span></div><small>22%　·　8 edits　·　0 marks</small><div class="find-panel"><div class="find-row"><div>Find in document</div><small>0/0</small><button>↑</button><button>↓</button><button>×</button></div><div class="find-row"><div>Replace with</div><button>Replace</button><button class="all">All</button></div><label>□ Match case　　　 □ Whole word</label></div><div class="reader-lines short">${lines(5)}</div><div class="reader-menu"><span>Find</span><b>Edit</b><span>Fix</span><span>Mark</span><span>Chapters</span><span>Aa</span></div><div class="keyboard">${Array.from({length:30},(_,j)=>`<i>${['က','ခ','ဂ','ဃ','င','စ','ဆ','ဇ','ည','တ'][j%10]}</i>`).join('')}<b>မြန်မာ</b></div></div>`;
  return `<div class="mock-status light">1:42 <span>◌⌁ Wi‑Fi ▮▮</span></div><div class="proof-paragraph"><div class="reader-head">‹ <b>သန်းမိုး_ပုလဲကကြိုး</b><button>Save</button><span>•••</span></div><small>8%　·　7 edits　·　0 marks</small><div class="paragraph-modal"><h4>Edit paragraph</h4><p>Text and paragraph layout</p><h5>ALIGNMENT</h5><div class="align-buttons"><span>Left</span><span>Center</span><span>Right</span><b>Justify</b></div><div class="style-row"><span>Normal　⌄</span><span>New page</span></div><h5>TEXT <b>B</b></h5><div class="paragraph-text">“ပုလဲကကြိုး” ဟု မှတ်မိနေတာကို လက်သည်းဖြင့် မိမိစိတ်ထဲက စာသားများ ပြန်ပြင်လိုက်၏။<br><br>ဒီကာလအတွင်း ပြင်ဆင်မှုများကို သိမ်းထားနိုင်သည်။</div><small>Select text → B for bold · Save writes it to the DOCX</small><footer><span>RESTORE</span><span>CANCEL</span><b>APPLY</b></footer></div></div>`;
}
function designedPoster(a,i){
  const copy=(previewCopy[a.slug]||[])[i]||[`Feature ${i+1}`,''];
  const sideIcon=a.slug==='wow-ocr'?(i===3?'⚙':i===2?'T':i===1?'⌕':'▤'):(i===2?'⌕':i===1?'✎':'▤');
  return `<article class="designed-poster ${a.slug==='wow-ocr'?'poster-ocr':'poster-proof'}"><div class="poster-dots"></div><div class="poster-orbit"></div><div class="poster-brand">${posterLogo(a.slug)}<strong>${esc(a.name)}</strong></div><div class="poster-flare"><i></i></div><h3>${esc(copy[0])}</h3><p>${esc(copy[1])}</p><div class="poster-phone"><div class="phone-shell"><div class="phone-camera"></div><div class="phone-screen ${a.slug==='wow-ocr'?'ocr-screen':'proof-screen'}">${posterMock(a.slug,i)}</div></div></div><div class="poster-side-icon">${sideIcon}</div><div class="poster-stage"></div></article>`;
}
function previewMarkup(a,s,i){if(a.slug==='wow-note')return rawPreview(a,s,i);if(designedSlugs.has(a.slug))return designedPoster(a,i);return premiumPreview(a,s,i)}

function render(a){const shots=a.screenshots||[],features=a.features||[],changes=a.whatsNew||[];const action=a.comingSoon?'<span class="install-main coming-soon" aria-disabled="true">COMING SOON</span>':`<a class="install-main" href="${esc(a.apk)}" download>GET</a>`;root.innerHTML=`
<section class="app-head"><img class="detail-icon" src="${esc(a.icon)}" alt="${esc(a.name)} icon"><div><h1>${esc(a.name)}</h1><div class="developer">${esc(a.developer)}</div><p>${esc(a.shortDescription)}</p><div class="head-actions">${action}<span class="version-note">v${esc(a.version)}${a.comingSoon?' · Preview':` · ${esc(a.size)}`}</span></div></div></section>
<section class="metrics">${[['Version',a.version],['Android',a.android],['Size',a.comingSoon?'Coming Soon':a.size],['Price',a.price]].map(([l,v])=>`<div class="metric"><strong>${esc(v)}</strong><span>${esc(l)}</span></div>`).join('')}</section>
${a.comingSoon?'<section class="coming-soon-banner"><strong>Coming Soon</strong><span>Download is temporarily disabled. The APK is not hosted here yet.</span></section>':''}
${shots.length?`<section class="detail-section"><h2>Preview</h2><div class="screenshot-strip ${a.slug==='wow-note'?'':'premium-preview-strip'} ${designedSlugs.has(a.slug)?'designed-preview-strip':''}">${shots.map((s,i)=>previewMarkup(a,s,i)).join('')}</div></section>`:''}
<section class="detail-section"><h2>About</h2><p>${esc(a.description)}</p><div class="feature-list">${features.map(f=>`<div class="feature"><strong>${esc(f.title)}</strong><span>${esc(f.text)}</span></div>`).join('')}</div></section>
<section class="detail-section"><h2>What's New</h2><div class="release-card"><strong>Version ${esc(a.version)}</strong><ul>${changes.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div></section>
<section class="detail-section"><h2>Privacy</h2><div class="safety-card"><strong>${esc(a.safety?.title||'Local-first')}</strong><p>${esc(a.safety?.text||'')}</p></div></section>
<section class="detail-section"><h2>Information</h2><div class="info-list"><div class="info-row"><strong>Developer</strong><span>${esc(a.developer)}</span></div><div class="info-row"><strong>Category</strong><span>${esc(a.category)}</span></div><div class="info-row"><strong>Updated</strong><span>${esc(a.updated)}</span></div>${a.packageName?`<div class="info-row"><strong>Package</strong><span>${esc(a.packageName)}</span></div>`:''}${a.source?`<div class="info-row"><strong>Source</strong><span><a href="${esc(a.source)}" target="_blank" rel="noreferrer">View on GitHub</a></span></div>`:''}</div></section>`;hydratePreviews()}

async function hydratePreviews(){const imgs=[...root.querySelectorAll('[data-preview-src]')];await Promise.all(imgs.map(async img=>{const path=img.dataset.previewSrc;try{let src=path;if(path.endsWith('.b64')){const r=await fetch(`${path}?v=16`,{cache:'no-store'});if(!r.ok)throw new Error('preview fetch failed');const b64=(await r.text()).trim().replace(/\s+/g,'');const mime=b64.startsWith('/9j/')?'image/jpeg':b64.startsWith('iVBOR')?'image/png':b64.startsWith('UklGR')?'image/webp':null;if(!mime)throw new Error('unsupported preview image');src=`data:${mime};base64,${b64}`}img.src=src;await img.decode();img.classList.add('is-loaded');img.addEventListener('click',()=>openImage(src))}catch{const card=img.closest('.promo-preview');if(card){card.classList.add('preview-fallback');img.remove()}else img.remove()}}));const strip=root.querySelector('.screenshot-strip');if(strip&&!strip.querySelector('img')&&!strip.querySelector('.promo-preview')&&!strip.querySelector('.designed-poster'))strip.closest('.detail-section')?.remove()}

const dlg=document.querySelector('#imageDialog'),dlgImg=document.querySelector('#dialogImage');function openImage(src){if(!dlg||!dlgImg)return;dlgImg.src=src;dlg.showModal()}document.querySelector('#closeImage')?.addEventListener('click',()=>dlg.close());dlg?.addEventListener('click',e=>{if(e.target===dlg)dlg.close()});
