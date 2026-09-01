const root=document.querySelector('#detailRoot');
const params=new URLSearchParams(location.search);const slug=params.get('app')||'wow-reader';
function setTheme(theme){document.documentElement.dataset.theme=theme;localStorage.setItem('wow-store-theme',theme)}
const saved=localStorage.getItem('wow-store-theme');if(saved)setTheme(saved);else setTheme(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark');
document.querySelector('#themeToggle')?.addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
const esc=(v='')=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

fetch('data/apps.json').then(r=>{if(!r.ok)throw new Error('catalog');return r.json()}).then(data=>{const a=(data.apps||[]).find(x=>x.slug===slug);if(!a)throw new Error('not-found');document.title=`${a.name} · Whisper Of Words App Store`;render(a)}).catch(()=>root.innerHTML='<div class="loading-card"><h2>App not found</h2><p><a href="./">Return to the store</a></p></div>');

function render(a){
  const shots=(a.screenshots||[]);
  const features=(a.features||[]);
  const changes=(a.whatsNew||[]);
  root.innerHTML=`
  <section class="detail-hero">
    <div class="detail-main">
      <img class="detail-icon" src="${esc(a.icon)}" alt="${esc(a.name)} icon">
      <div class="detail-title">
        <span class="eyebrow">${esc(a.category)}</span>
        <h1>${esc(a.name)}</h1>
        <div class="developer">${esc(a.developer)}</div>
        <p>${esc(a.shortDescription)}</p>
      </div>
      <aside class="install-panel">
        <strong>${esc(a.price)}</strong>
        <span>${esc(a.size)} · Direct APK</span>
        <a class="install-btn" href="${esc(a.apk)}" download>Download APK</a>
      </aside>
    </div>
    <div class="stats">
      ${[['Version',a.version],['Size',a.size],['Android',a.android],['Updated',a.updated],['Price',a.price]].map(([l,v])=>`<div class="stat"><strong>${esc(v)}</strong><span>${esc(l)}</span></div>`).join('')}
    </div>
  </section>

  ${shots.length?`<section class="content-section"><span class="eyebrow">PREVIEW</span><h2>Screenshots</h2><div class="screenshot-strip">${shots.map((s,i)=>`<img src="${esc(s)}" alt="${esc(a.name)} screenshot ${i+1}" loading="lazy" data-full="${esc(s)}">`).join('')}</div></section>`:''}

  <section class="content-section">
    <span class="eyebrow">ABOUT</span><h2>About this app</h2><p>${esc(a.description)}</p>
    <div class="feature-grid">${features.map(f=>`<div class="feature"><strong>${esc(f.title)}</strong><span>${esc(f.text)}</span></div>`).join('')}</div>
  </section>

  <section class="content-section">
    <span class="eyebrow">RELEASE NOTES</span><h2>What's new</h2>
    <div class="whats-new"><strong>Version ${esc(a.version)}</strong><ul>${changes.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>
  </section>

  <section class="content-section">
    <span class="eyebrow">PRIVACY</span><h2>Data safety</h2>
    <div class="safety-card"><div class="safety-icon">✓</div><div><strong>${esc(a.safety?.title||'Local-first')}</strong><p>${esc(a.safety?.text||'')}</p></div></div>
  </section>

  <section class="content-section">
    <span class="eyebrow">DETAILS</span><h2>App info</h2>
    <div class="feature-grid">
      <div class="feature"><strong>Updated</strong><span>${esc(a.updated)}</span></div>
      <div class="feature"><strong>Category</strong><span>${esc(a.category)}</span></div>
      <div class="feature"><strong>Developer</strong><span>${esc(a.developer)}</span></div>
      <div class="feature"><strong>Package</strong><span>${esc(a.packageName)}</span></div>
    </div>
    <div class="hero-actions" style="margin-top:16px"><a class="secondary-btn" href="${esc(a.source)}" target="_blank" rel="noreferrer">View source</a><a class="install-btn" style="width:auto" href="${esc(a.apk)}" download>Download APK</a></div>
  </section>`;
  root.querySelectorAll('[data-full]').forEach(img=>img.addEventListener('click',()=>openImage(img.dataset.full)));
}

const dlg=document.querySelector('#imageDialog'),dlgImg=document.querySelector('#dialogImage');
function openImage(src){if(!dlg||!dlgImg)return;dlgImg.src=src;dlg.showModal()}
document.querySelector('#closeImage')?.addEventListener('click',()=>dlg.close());
dlg?.addEventListener('click',e=>{if(e.target===dlg)dlg.close()});
