const root=document.querySelector('#detailRoot');if(!document.querySelector('link[data-premium-previews]')){const l=document.createElement('link');l.rel='stylesheet';l.href='premium-previews.css?v=15';l.dataset.premiumPreviews='1';document.head.append(l)}const slug=new URLSearchParams(location.search).get('app')||'wow-reader';
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
    ['Fast OCR','Scan text from images quickly'],
    ['Scan & Read','Read and OCR page images'],
    ['Editable Text','Edit recognized text easily'],
    ['Cloud & AI OCR','Optional Cloud Vision and AI OCR']
  ],
  'wow-proof-reader':[
    ['Proof Library','Manage your DOCX books'],
    ['Inline Editing','Edit paragraphs while you read'],
    ['Find & Replace','Search and replace fast'],
    ['Paragraph Tools','Align, style, justify and format']
  ]
};

Promise.all([
  fetch('data/apps.json?v=15',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error();return r.json()}),
  fetch('data/wow-note.json?v=15',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error();return r.json()})
]).then(([d,wowNote])=>{const a=[...(d.apps||[]),wowNote].find(x=>x.slug===slug);if(!a)throw new Error();document.title=`${a.name} · Whisper Of Words App Store`;render(a)}).catch(()=>root.innerHTML='<div class="loading-card">App not found.<br><br><a href="./">Back to Store</a></div>');

function rawPreview(a,s,i){
  return `<img class="raw-preview-shot" src="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=" alt="${esc(a.name)} screenshot ${i+1}" data-preview-src="${esc(s)}">`
}
function premiumPreview(a,s,i){
  const copy=(previewCopy[a.slug]||[])[i]||[`Feature ${i+1}`,'Explore the app experience'];
  return `<article class="promo-preview">
    <div class="promo-grid-dots" aria-hidden="true"></div>
    <div class="promo-ring" aria-hidden="true"></div>
    <div class="promo-brand"><span class="promo-brand-icon"><img src="${esc(a.icon)}" alt=""></span><strong>${esc(a.name)}</strong></div>
    <div class="promo-flare" aria-hidden="true"><i></i></div>
    <h3>${esc(copy[0])}</h3><p>${esc(copy[1])}</p>
    <div class="promo-stage" aria-hidden="true"></div>
    <div class="promo-phone">
      <div class="promo-speaker" aria-hidden="true"></div>
      <img class="promo-shot" src="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=" alt="${esc(a.name)} screenshot ${i+1}" data-preview-src="${esc(s)}">
      <div class="promo-phone-fallback" aria-hidden="true"><img src="${esc(a.icon)}" alt=""><b>${esc(copy[0])}</b><span>${esc(copy[1])}</span></div>
    </div>
    <div class="promo-side-icon" aria-hidden="true">✦</div>
  </article>`
}
function previewMarkup(a,s,i){return a.slug==='wow-note'?rawPreview(a,s,i):premiumPreview(a,s,i)}

function render(a){const shots=a.screenshots||[],features=a.features||[],changes=a.whatsNew||[];const action=a.comingSoon?'<span class="install-main coming-soon" aria-disabled="true">COMING SOON</span>':`<a class="install-main" href="${esc(a.apk)}" download>GET</a>`;root.innerHTML=`
<section class="app-head"><img class="detail-icon" src="${esc(a.icon)}" alt="${esc(a.name)} icon"><div><h1>${esc(a.name)}</h1><div class="developer">${esc(a.developer)}</div><p>${esc(a.shortDescription)}</p><div class="head-actions">${action}<span class="version-note">v${esc(a.version)}${a.comingSoon?' · Preview':` · ${esc(a.size)}`}</span></div></div></section>
<section class="metrics">${[['Version',a.version],['Android',a.android],['Size',a.comingSoon?'Coming Soon':a.size],['Price',a.price]].map(([l,v])=>`<div class="metric"><strong>${esc(v)}</strong><span>${esc(l)}</span></div>`).join('')}</section>
${a.comingSoon?'<section class="coming-soon-banner"><strong>Coming Soon</strong><span>Download is temporarily disabled. The APK is not hosted here yet.</span></section>':''}
${shots.length?`<section class="detail-section"><h2>Preview</h2><div class="screenshot-strip ${a.slug==='wow-note'?'':'premium-preview-strip'}">${shots.map((s,i)=>previewMarkup(a,s,i)).join('')}</div></section>`:''}
<section class="detail-section"><h2>About</h2><p>${esc(a.description)}</p><div class="feature-list">${features.map(f=>`<div class="feature"><strong>${esc(f.title)}</strong><span>${esc(f.text)}</span></div>`).join('')}</div></section>
<section class="detail-section"><h2>What's New</h2><div class="release-card"><strong>Version ${esc(a.version)}</strong><ul>${changes.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div></section>
<section class="detail-section"><h2>Privacy</h2><div class="safety-card"><strong>${esc(a.safety?.title||'Local-first')}</strong><p>${esc(a.safety?.text||'')}</p></div></section>
<section class="detail-section"><h2>Information</h2><div class="info-list"><div class="info-row"><strong>Developer</strong><span>${esc(a.developer)}</span></div><div class="info-row"><strong>Category</strong><span>${esc(a.category)}</span></div><div class="info-row"><strong>Updated</strong><span>${esc(a.updated)}</span></div>${a.packageName?`<div class="info-row"><strong>Package</strong><span>${esc(a.packageName)}</span></div>`:''}${a.source?`<div class="info-row"><strong>Source</strong><span><a href="${esc(a.source)}" target="_blank" rel="noreferrer">View on GitHub</a></span></div>`:''}</div></section>`;hydratePreviews()}

async function hydratePreviews(){
  const imgs=[...root.querySelectorAll('[data-preview-src]')];
  await Promise.all(imgs.map(async img=>{
    const path=img.dataset.previewSrc;
    try{
      let src=path;
      if(path.endsWith('.b64')){
        const r=await fetch(`${path}?v=15`,{cache:'no-store'});
        if(!r.ok)throw new Error('preview fetch failed');
        const b64=(await r.text()).trim().replace(/\s+/g,'');
        const mime=b64.startsWith('/9j/')?'image/jpeg':b64.startsWith('iVBOR')?'image/png':b64.startsWith('UklGR')?'image/webp':null;
        if(!mime)throw new Error('unsupported preview image');
        src=`data:${mime};base64,${b64}`
      }
      img.src=src;
      await img.decode();
      img.classList.add('is-loaded');
      img.addEventListener('click',()=>openImage(src))
    }catch{
      const card=img.closest('.promo-preview');
      if(card){card.classList.add('preview-fallback');img.remove()}
      else img.remove()
    }
  }));
  const strip=root.querySelector('.screenshot-strip');
  if(strip&&!strip.querySelector('img')&&!strip.querySelector('.promo-preview'))strip.closest('.detail-section')?.remove()
}

const dlg=document.querySelector('#imageDialog'),dlgImg=document.querySelector('#dialogImage');
function openImage(src){if(!dlg||!dlgImg)return;dlgImg.src=src;dlg.showModal()}
document.querySelector('#closeImage')?.addEventListener('click',()=>dlg.close());
dlg?.addEventListener('click',e=>{if(e.target===dlg)dlg.close()});
