(()=>{
  const NOTE_PACKAGE='com.whispermmepub.wowcolornote';
  const NOTE_SCHEME='wownote';

  function noteIntent(){
    const fallback=encodeURIComponent(location.href);
    return `intent://open#Intent;scheme=${NOTE_SCHEME};package=${NOTE_PACKAGE};S.browser_fallback_url=${fallback};end`;
  }

  function isNoteOpenLink(a){
    if(!(a instanceof HTMLAnchorElement)) return false;
    if(a.dataset.openApp==='wow-note') return true;
    if(document.body.dataset.app==='wow-note' && a.classList.contains('install-action') && a.textContent.trim()==='Open') return true;
    return false;
  }

  document.addEventListener('click',e=>{
    const a=e.target.closest('a');
    if(!isNoteOpenLink(a)) return;
    e.preventDefault();
    location.href=noteIntent();
  },true);
})();
