const root=document.querySelector('#detailRoot');
const params=new URLSearchParams(location.search);const slug=params.get('app')||'wow-reader';
function setTheme(theme){document.documentElement.dataset.theme=theme;localStorage.setItem('wow-store-theme',theme)}
const saved=localStorage.getItem('wow-store-theme');if(saved)setTheme(saved);else if(matchMedia('(prefers-color-scheme: dark)').matches)setTheme('dark');
document.querySelector('#themeToggle')?.addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
const esc=(v='')=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

fetch('data/apps.json').then(r=>r.json()).then(data=>{const a=(data.apps||[]).find(x=>x.slug===slug);if(!a)throw new Error('not-found');document.title=`${a.name} · Whisper Of Words App Store`;render(a)}).catch(()=>root.innerHTML='<div class="loading-card"><h2>App not found</h2><p><a href="./">Return to the store</a></p></div>');

function render(a){root.innerHTML=`
<section class="app-hero">
  <img class="app-icon" src="${esc(a.icon)}" alt="${esc(a.name)} icon">
  <div class="app-title"><span class="eyebrow">${esc(a.category)}</span><h1>${esc(a.name)}</h1><div class="developer">${esc(a.developer)}</div><p class="app-tagline">${esc(a.shortDescription)}</p>
  <div class="install-row"><a class="install-btn" href="${esc(a.apk)}" download>Download APK</a><a class="secondary-btn" href="${esc(a.source)}">Source</a></div></div>
</section>
<section class="stats">${[['Version',a.version],['Size',a.size],['Android',a.android],['Price',a.price]].map(([l,v])=>`<div class="stat"><strong>${esc(v)}</strong><span>${esc(l)}</span></div>`).join('')}</section>
<section class="content-section"><h2>Preview</h2><div class="screenshot-strip">${a.screenshots.map((s,i)=>`<img src="${esc(s)}" alt="${esc(a.name)} screenshot ${i+1}" loading="lazy" data-full="${esc(s)}">`).join('')}</div></section>
<section class="content-section"><h2>About this app</h2><p>${esc(a.description)}</p><div class="feature-grid">${a.features.map(f=>`<div class="feature"><strong>${esc(f.title)}</strong><span>${esc(f.text)}</span></div>`).join('')}</div></section>
<section class="content-section"><h2>What's new</h2><div class="whats-new"><strong>Version ${esc(a.version)}</strong><ul>${a.whatsNew.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div></section>
<section class="content-section"><h2>Data safety</h2><div class="safety-card"><div class="safety-icon">⌾</div><div><strong>${esc(a.safety.title)}</strong><p>${esc(a.safety.text)}</p></div></div></section>
<section class="content-section"><h2>App info</h2><div class="feature-grid"><div class="feature"><strong>Updated</strong><span>${esc(a.updated)}</span></div><div class="feature"><strong>Category</strong><span>${esc(a.category)}</span></div><div class="feature"><strong>Developer</strong><span>${esc(a.developer)}</span></div><div class="feature"><strong>Package</strong><span>${esc(a.packageName)}</span></div></div></section>`;
root.querySelectorAll('[data-full]').forEach(img=>img.addEventListener('click',()=>openImage(img.dataset.full)));
}
const dlg=document.querySelector('#imageDialog'),dlgImg=document.querySelector('#dialogImage');function openImage(src){dlgImg.src=src;dlg.showModal()}document.querySelector('#closeImage')?.addEventListener('click',()=>dlg.close());dlg?.addEventListener('click',e=>{if(e.target===dlg)dlg.close()});
