const $ = s => document.querySelector(s);
const grid = $('#appGrid');
const search = $('#search');
const count = $('#appCount');
const featured = $('#featuredApp');
let apps = [];

function setTheme(theme){document.documentElement.dataset.theme=theme;localStorage.setItem('wow-store-theme',theme)}
function initTheme(){const saved=localStorage.getItem('wow-store-theme');if(saved)setTheme(saved);else setTheme(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark')}
initTheme();
$('#themeToggle')?.addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));

function esc(v=''){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}

function renderFeatured(app){
  if(!featured||!app)return;
  featured.innerHTML=`
    <article class="showcase-card">
      <div class="showcase-top"><span class="featured-label">FEATURED APP</span><span class="showcase-version">v${esc(app.version)}</span></div>
      <div class="showcase-app">
        <img class="showcase-icon" src="${esc(app.icon)}" alt="${esc(app.name)} icon">
        <div><h2>${esc(app.name)}</h2><div class="developer">${esc(app.developer)}</div></div>
      </div>
      <p>${esc(app.shortDescription)}</p>
      <div class="showcase-meta">
        <div class="showcase-stat"><strong>${esc(app.size)}</strong><span>Size</span></div>
        <div class="showcase-stat"><strong>${esc(app.android)}</strong><span>Android</span></div>
        <div class="showcase-stat"><strong>${esc(app.price)}</strong><span>Price</span></div>
      </div>
      <div class="showcase-actions">
        <a class="card-btn secondary" href="app.html?app=${encodeURIComponent(app.slug)}">View details</a>
        <a class="card-btn primary" href="${esc(app.apk)}" download>Download APK</a>
      </div>
    </article>`;
}

function render(list){
  count.textContent=String(list.length);
  grid.innerHTML=list.map(app=>`
    <article class="app-card">
      <div class="app-card-top">
        <img class="app-icon" src="${esc(app.icon)}" alt="${esc(app.name)} icon" loading="lazy">
        <div><h3>${esc(app.name)}</h3><div class="developer">${esc(app.developer)}</div>
          <div class="meta-pills"><span class="pill">v${esc(app.version)}</span><span class="pill">${esc(app.platform)}</span><span class="pill">${esc(app.category)}</span></div>
        </div>
      </div>
      <p class="app-summary">${esc(app.shortDescription)}</p>
      <div class="app-card-actions">
        <a class="card-btn secondary" href="app.html?app=${encodeURIComponent(app.slug)}">Details</a>
        <a class="card-btn primary" href="${esc(app.apk)}" download>Download</a>
      </div>
    </article>`).join('') || '<div class="loading-card">No apps found.</div>';
}

fetch('data/apps.json').then(r=>{if(!r.ok)throw new Error('catalog');return r.json()}).then(data=>{apps=data.apps||[];renderFeatured(apps[0]);render(apps)}).catch(()=>{grid.innerHTML='<div class="loading-card">Unable to load the app catalog.</div>';if(featured)featured.innerHTML='<div class="loading-card">Featured app unavailable.</div>'});

search?.addEventListener('input',e=>{const q=e.target.value.trim().toLowerCase();render(!q?apps:apps.filter(a=>[a.name,a.developer,a.category,a.shortDescription,(a.tags||[]).join(' ')].join(' ').toLowerCase().includes(q)))});
if('serviceWorker' in navigator) window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));
