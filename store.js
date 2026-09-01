const $ = s => document.querySelector(s);
const grid = $('#appGrid');
const search = $('#search');
const count = $('#appCount');
let apps = [];

function setTheme(theme){document.documentElement.dataset.theme=theme;localStorage.setItem('wow-store-theme',theme)}
function initTheme(){const saved=localStorage.getItem('wow-store-theme');if(saved)setTheme(saved);else if(matchMedia('(prefers-color-scheme: dark)').matches)setTheme('dark')}
initTheme();
$('#themeToggle')?.addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));

function esc(v=''){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function render(list){count.textContent=`${list.length} ${list.length===1?'app':'apps'}`;grid.innerHTML=list.map(app=>`
  <a class="app-card" href="app.html?app=${encodeURIComponent(app.slug)}">
    <img class="app-icon" src="${esc(app.icon)}" alt="${esc(app.name)} icon" loading="lazy">
    <div><h3>${esc(app.name)}</h3><div class="developer">${esc(app.developer)}</div><p class="app-summary">${esc(app.shortDescription)}</p>
    <div class="meta-pills"><span class="pill">${esc(app.version)}</span><span class="pill">${esc(app.platform)}</span><span class="pill">${esc(app.price)}</span></div></div>
  </a>`).join('') || '<div class="loading-card">No apps found.</div>'}

fetch('data/apps.json').then(r=>r.json()).then(data=>{apps=data.apps||[];render(apps)}).catch(()=>grid.innerHTML='<div class="loading-card">Unable to load the app catalog.</div>');
search?.addEventListener('input',e=>{const q=e.target.value.trim().toLowerCase();render(!q?apps:apps.filter(a=>[a.name,a.developer,a.shortDescription,(a.tags||[]).join(' ')].join(' ').toLowerCase().includes(q)))});
if('serviceWorker' in navigator) window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));
