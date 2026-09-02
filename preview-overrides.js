(()=>{
  const slug=new URLSearchParams(location.search).get('app')||'wow-reader';
  const posters={
    'wow-ocr':[
      'apps/wow-ocr/screenshots/01-scan-ocr-export.svg?v=20',
      'apps/wow-ocr/screenshots/02-fast-text-scanning.svg?v=20',
      'apps/wow-ocr/screenshots/03-editable-text.svg?v=20',
      'apps/wow-ocr/screenshots/04-cloud-ai-ocr.svg?v=20'
    ],
    'wow-proof-reader':[
      'apps/wow-proof-reader/screenshots/01-read-edit-perfect.svg?v=20',
      'apps/wow-proof-reader/screenshots/02-inline-editing.svg?v=20',
      'apps/wow-proof-reader/screenshots/03-find-replace.svg?v=20',
      'apps/wow-proof-reader/screenshots/04-paragraph-tools.svg?v=20'
    ]
  };
  if(!posters[slug])return;
  const root=document.querySelector('#detailRoot');
  const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const apply=()=>{
    const strip=root?.querySelector('.screenshot-strip');
    if(!strip)return false;
    strip.className='screenshot-strip poster-asset-strip';
    strip.innerHTML=posters[slug].map((src,i)=>`<img src="${esc(src)}" alt="${slug==='wow-ocr'?'WoW OCR':'WoW Proof Reader'} premium preview ${i+1}" loading="eager">`).join('');
    const dlg=document.querySelector('#imageDialog'),dlgImg=document.querySelector('#dialogImage');
    strip.querySelectorAll('img').forEach(img=>img.addEventListener('click',()=>{if(dlg&&dlgImg){dlgImg.src=img.src;dlg.showModal()}}));
    return true;
  };
  if(apply())return;
  const obs=new MutationObserver(()=>{if(apply())obs.disconnect()});
  if(root)obs.observe(root,{childList:true,subtree:true});
  setTimeout(()=>obs.disconnect(),10000);
})();
