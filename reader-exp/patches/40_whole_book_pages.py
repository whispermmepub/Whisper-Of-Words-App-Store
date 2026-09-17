#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve(); java=root/'app/src/main/java/com/whisper/wowreader'; reader=java/'BookReaderActivity.java'
if not reader.is_file(): raise SystemExit('BookReaderActivity.java missing')

def rep(old,new):
    s=reader.read_text(encoding='utf-8')
    if old not in s: raise SystemExit(f'Whole-page anchor missing: {old[:120]!r}')
    reader.write_text(s.replace(old,new,1),encoding='utf-8')

(java/'WholeBookPageModel.java').write_text(r'''package com.whisper.wowreader;

final class WholeBookPageModel {
    private int[] counts = new int[0];
    private int known = 0;
    void reset(int chapters){ counts=new int[Math.max(0,chapters)]; known=0; }
    int chapterCount(){ return counts.length; }
    void setChapterCount(int index,int count){
        if(index<0||index>=counts.length)return;int clean=Math.max(1,count);if(counts[index]<=0)known++;counts[index]=clean;
    }
    boolean isComplete(){ return counts.length>0&&known==counts.length; }
    int wholePageIfKnown(int chapter,int page){
        if(chapter<0||chapter>=counts.length)return -1;long prefix=0;for(int i=0;i<chapter;i++){if(counts[i]<=0)return -1;prefix+=counts[i];if(prefix>Integer.MAX_VALUE)return Integer.MAX_VALUE;}
        if(counts[chapter]<=0)return -1;long value=prefix+Math.max(1,Math.min(page,counts[chapter]));return value>Integer.MAX_VALUE?Integer.MAX_VALUE:(int)value;
    }
    int totalPagesIfComplete(){
        if(!isComplete())return -1;long total=0;for(int c:counts){total+=c;if(total>Integer.MAX_VALUE)return Integer.MAX_VALUE;}return (int)total;
    }
}
''',encoding='utf-8')

# Fields for the hidden paginator/model.
rep('''    private WebView webView;\n    private ReaderWebView preloadWebView;''','''    private WebView webView;\n    private ReaderWebView preloadWebView;\n    private ReaderWebView wholeBookCounterWebView;\n    private final WholeBookPageModel wholeBookPageModel = new WholeBookPageModel();\n    private int wholeBookCounterSpine = 0;\n    private int wholeBookCounterToken = 0;\n    private boolean wholeBookCounterRunning = false;\n    private String wholeBookLayoutFingerprint = "";''')

# Add hidden same-size WebView after normal preload WebView. INVISIBLE still participates in layout but cannot intercept touches.
rep('''            webView.bringToFront();\n        }\n\n        chapterTransitionOverlay = new ImageView(this);''','''            webView.bringToFront();\n        }\n\n        wholeBookCounterWebView = createPreloadWebView();\n        if (wholeBookCounterWebView != null) {\n            wholeBookCounterWebView.setEnabled(false);\n            wholeBookCounterWebView.setVisibility(View.INVISIBLE);\n            wholeBookCounterWebView.addJavascriptInterface(new WholeBookCounterBridge(), "WoWPageCounter");\n            wholeBookCounterWebView.setWebViewClient(new WebViewClient() {\n                @Override public void onPageFinished(WebView view, String url) {\n                    super.onPageFinished(view, url);\n                    if (view == wholeBookCounterWebView) measureWholeBookCounterChapter();\n                }\n            });\n            content.addView(wholeBookCounterWebView, new FrameLayout.LayoutParams(\n                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));\n            webView.bringToFront();\n        }\n\n        chapterTransitionOverlay = new ImageView(this);''')

# Initialize model whenever EPUB spine is replaced.
rep('''                    epubProgressModel = progressModel;\n                    tocSpineIndices.clear();''','''                    epubProgressModel = progressModel;\n                    wholeBookPageModel.reset(info.spine.size());\n                    wholeBookLayoutFingerprint = "";\n                    wholeBookCounterRunning = false;\n                    wholeBookCounterToken++;\n                    tocSpineIndices.clear();''')

# Whole-page label in current progress display: exact prefix when known; exact total only after background scan completes.
rep('''        String base = "page".equals(readingMode)\n                ? "Page " + currentPageInChapter + " / " + pageCountInChapter + " · " + percent + "%"\n                : chapter + " · " + percent + "%";''','''        String pageLabel = null;\n        if ("page".equals(readingMode)) {\n            wholeBookPageModel.setChapterCount(currentSpine, pageCountInChapter);\n            int wholePage = wholeBookPageModel.wholePageIfKnown(currentSpine, currentPageInChapter);\n            int wholeTotal = wholeBookPageModel.totalPagesIfComplete();\n            if (wholePage > 0) pageLabel = "Page " + wholePage + " / " + (wholeTotal > 0 ? String.valueOf(wholeTotal) : "…");\n            else pageLabel = "Page " + currentPageInChapter + " / …";\n        }\n        String base = "page".equals(readingMode)\n                ? pageLabel + " · " + percent + "%"\n                : chapter + " · " + percent + "%";''')

# Every actual chapter report overrides scanner count and ensures scan is running for current geometry/settings.
rep('''        pageCountInChapter = Math.max(1, count);\n        int effectiveProgress = p;''','''        pageCountInChapter = Math.max(1, count);\n        wholeBookPageModel.setChapterCount(currentSpine, pageCountInChapter);\n        ensureWholeBookPageScan();\n        int effectiveProgress = p;''')

# Add scanner implementation before page progress method.
anchor='''    private void updateEpubPageProgress(int page, int count, int p) {'''
scanner=r'''    private String wholeBookPageFingerprint() {
        int w = webView == null ? 0 : webView.getWidth();
        int h = webView == null ? 0 : webView.getHeight();
        return w + "x" + h + "|" + fontPercent + "|" + fontWeight + "|" +
                String.valueOf(fontChoice) + "|" + lineSpacing + "|" + marginPercent + "|" +
                String.valueOf(textAlignment) + "|" + autoSpacingAdjustment;
    }

    private void ensureWholeBookPageScan() {
        if (isPdf || !"page".equals(readingMode) || spine.isEmpty() || wholeBookCounterWebView == null || isFinishing()) return;
        String fingerprint = wholeBookPageFingerprint();
        if (!fingerprint.equals(wholeBookLayoutFingerprint) || wholeBookPageModel.chapterCount() != spine.size()) {
            wholeBookLayoutFingerprint = fingerprint;
            wholeBookPageModel.reset(spine.size());
            wholeBookPageModel.setChapterCount(currentSpine, pageCountInChapter);
            wholeBookCounterToken++;
            wholeBookCounterSpine = 0;
            wholeBookCounterRunning = false;
            try { wholeBookCounterWebView.stopLoading(); } catch (Exception ignored) {}
        }
        if (wholeBookPageModel.isComplete() || wholeBookCounterRunning) return;
        wholeBookCounterRunning = true;
        loadNextWholeBookCounterChapter(wholeBookCounterToken);
    }

    private void loadNextWholeBookCounterChapter(int token) {
        if (token != wholeBookCounterToken || wholeBookCounterWebView == null || isFinishing()) { wholeBookCounterRunning=false; return; }
        if (wholeBookPageModel.isComplete() || wholeBookCounterSpine >= spine.size()) { wholeBookCounterRunning=false; updateEpubProgress(currentProgressPermille); return; }
        final int target = wholeBookCounterSpine;
        // Skip the current chapter when its live rendered count is already known.
        if (target == currentSpine && pageCountInChapter > 0) {
            wholeBookPageModel.setChapterCount(target,pageCountInChapter); wholeBookCounterSpine++; loadNextWholeBookCounterChapter(token); return;
        }
        try {
            wholeBookCounterWebView.getSettings().setTextZoom(Math.max(80,Math.min(300,fontPercent)));
            wholeBookCounterWebView.loadUrl(Uri.fromFile(spine.get(target)).toString());
        } catch (Exception e) {
            wholeBookPageModel.setChapterCount(target,1); wholeBookCounterSpine++; loadNextWholeBookCounterChapter(token);
        }
    }

    private String wholeBookCounterFamilyCss() {
        if (fontChoice == null || "publisher".equals(fontChoice)) return "";
        File file = null;
        if (fontChoice.startsWith("custom:")) file = ReaderFontStore.fileForChoice(this,fontChoice);
        if (file != null) {
            String u=Uri.fromFile(file).toString().replace("'","%27");
            return "@font-face{font-family:'WoWCountFont';src:url('"+u+"');font-display:block;}body,body *{font-family:'WoWCountFont',sans-serif !important;}";
        }
        String asset="";
        if("pyidaungsu".equals(fontChoice))asset="pyidaungsu.woff2";else if("yoeshin".equals(fontChoice))asset="yoeshin.woff2";else if("burma2".equals(fontChoice))asset="burma2.woff2";else if("burma001".equals(fontChoice))asset="burma001.ttf";else if("pupu".equals(fontChoice))asset="m01_pupu_bold.ttf";else if("ayar".equals(fontChoice))asset="myanmar_ayar_typewriter.ttf";else if("phantee".equals(fontChoice))asset="phantee_hand_written.ttf";
        if(asset.isEmpty())return "";
        return "@font-face{font-family:'WoWCountFont';src:url('file:///android_asset/fonts/"+asset+"');font-display:block;}body,body *{font-family:'WoWCountFont',sans-serif !important;}";
    }

    private void measureWholeBookCounterChapter() {
        if (!wholeBookCounterRunning || wholeBookCounterWebView == null || wholeBookCounterSpine < 0 || wholeBookCounterSpine >= spine.size()) return;
        final int token=wholeBookCounterToken, index=wholeBookCounterSpine;
        int safeMargin=Math.max(1,Math.min(14,marginPercent)); int adaptiveMargin=adaptiveReaderMarginCssPx(safeMargin);
        double line=lineSpacing/100.0; String family=wholeBookCounterFamilyCss();
        String align="right".equals(textAlignment)?"right":("left".equals(textAlignment)?"left":"justify");
        String css="html,body{height:100% !important;width:100% !important;margin:0 !important;padding:0 !important;overflow:hidden !important;}"+
                "body{font-size:100% !important;font-weight:"+fontWeight+" !important;line-height:"+line+" !important;max-width:none !important;}"+
                "#wow-count-vp{position:absolute !important;left:0 !important;top:0 !important;width:100vw !important;height:100vh !important;overflow:hidden !important;}"+
                "#wow-count-flow{position:absolute !important;left:0 !important;top:0 !important;height:100vh !important;margin:0 !important;padding:4.2vh 0 5.2vh 0 !important;box-sizing:border-box !important;overflow:visible !important;column-fill:auto !important;}"+
                "#wow-count-flow p,#wow-count-flow li,#wow-count-flow blockquote,#wow-count-flow dd,#wow-count-flow dt{text-align:"+align+" !important;box-sizing:border-box !important;max-width:100% !important;}"+
                "#wow-count-flow img,#wow-count-flow svg,#wow-count-flow video,#wow-count-flow table{max-width:100% !important;height:auto !important;}"+family;
        String js="(function(){try{"+
                "var s=document.getElementById('wow-count-style');if(!s){s=document.createElement('style');s.id='wow-count-style';document.head.appendChild(s);}s.innerHTML="+jsQuote(css)+";"+
                "var vp=document.getElementById('wow-count-vp'),flow=document.getElementById('wow-count-flow');if(!vp){vp=document.createElement('div');vp.id='wow-count-vp';if(!flow){flow=document.createElement('div');flow.id='wow-count-flow';while(document.body.firstChild)flow.appendChild(document.body.firstChild);}vp.appendChild(flow);document.body.appendChild(vp);}"+
                "var w=Math.max(1,vp.clientWidth||window.innerWidth),m=Math.max(0,Math.min(Math.round(w*"+(safeMargin/100.0)+"),"+adaptiveMargin+")),pw=Math.max(1,w-2*m),gap=Math.max(0,w-pw);flow.style.width=pw+'px';flow.style.minWidth=pw+'px';flow.style.columnWidth=pw+'px';flow.style.columnGap=gap+'px';flow.style.webkitColumnWidth=pw+'px';flow.style.webkitColumnGap=gap+'px';flow.style.transform='translate3d('+m+'px,0,0)';"+
                "var baseW=pw,wraps=flow.querySelectorAll('div,section,article,main,p,blockquote,dd,dt');for(var x=0;x<wraps.length;x++){var n=wraps[x],t=(n.textContent||'').replace(/\\s+/g,' ').trim();if(t.length<120)continue;var r=n.getBoundingClientRect();if(r.width>0&&r.width<baseW*.90){n.style.setProperty('width','auto','important');n.style.setProperty('max-width','none','important');n.style.setProperty('margin-left','0','important');n.style.setProperty('margin-right','0','important');}}"+
                "var used={},walker=document.createTreeWalker(flow,NodeFilter.SHOW_TEXT,null,false),node,range=document.createRange(),seen=0;var mark=function(r){if(!r||r.width<.35||r.height<.35)return;var a=Math.max(0,Math.floor((r.left-m+1)/w)),b=Math.max(a,Math.floor((r.right-m-1)/w));for(var k=a;k<=b;k++)used[k]=1;};"+
                "requestAnimationFrame(function(){requestAnimationFrame(function(){while((node=walker.nextNode())&&seen<24000){var tx=(node.nodeValue||'').replace(/\\s+/g,'');if(!tx)continue;seen++;try{range.selectNodeContents(node);var rr=range.getClientRects();for(var j=0;j<rr.length;j++)mark(rr[j]);}catch(e){}}var media=flow.querySelectorAll('img,svg,video,audio,object,embed,table,math,canvas,hr');for(var i=0;i<media.length;i++)mark(media[i].getBoundingClientRect());var count=Math.max(1,Object.keys(used).length);WoWPageCounter.onCount("+token+","+index+",count);});});return true;}catch(e){WoWPageCounter.onCount("+token+","+index+",1);return false;}})()";
        try { wholeBookCounterWebView.evaluateJavascript(js,null); }
        catch(Exception e){ onWholeBookCounterCount(token,index,1); }
    }

    private final class WholeBookCounterBridge {
        @JavascriptInterface public void onCount(int token,int index,int count){ runOnUiThread(() -> onWholeBookCounterCount(token,index,count)); }
    }
    private void onWholeBookCounterCount(int token,int index,int count){
        if(token!=wholeBookCounterToken||index!=wholeBookCounterSpine)return;
        wholeBookPageModel.setChapterCount(index,Math.max(1,count)); wholeBookCounterSpine++;
        if(wholeBookPageModel.isComplete()) { wholeBookCounterRunning=false; updateEpubProgress(currentProgressPermille); }
        else if(wholeBookCounterWebView!=null) wholeBookCounterWebView.postDelayed(() -> loadNextWholeBookCounterChapter(token),20L);
    }

'''
s=reader.read_text(encoding='utf-8')
if anchor not in s: raise SystemExit('updateEpubPageProgress anchor missing')
s=s.replace(anchor,scanner+anchor,1);reader.write_text(s,encoding='utf-8')

# Destroy hidden paginator with other WebViews.
rep('''        if (preloadWebView != null) {\n            try { preloadWebView.removeJavascriptInterface("WoW"); } catch (Exception ignored) {}\n            try { preloadWebView.stopLoading(); } catch (Exception ignored) {}\n            try { preloadWebView.destroy(); } catch (Exception ignored) {}\n            preloadWebView = null;\n        }''','''        if (preloadWebView != null) {\n            try { preloadWebView.removeJavascriptInterface("WoW"); } catch (Exception ignored) {}\n            try { preloadWebView.stopLoading(); } catch (Exception ignored) {}\n            try { preloadWebView.destroy(); } catch (Exception ignored) {}\n            preloadWebView = null;\n        }\n        if (wholeBookCounterWebView != null) {\n            try { wholeBookCounterWebView.removeJavascriptInterface("WoWPageCounter"); } catch (Exception ignored) {}\n            try { wholeBookCounterWebView.removeJavascriptInterface("WoW"); } catch (Exception ignored) {}\n            try { wholeBookCounterWebView.stopLoading(); } catch (Exception ignored) {}\n            try { wholeBookCounterWebView.destroy(); } catch (Exception ignored) {}\n            wholeBookCounterWebView = null;\n        }''')

print('Applied Phase E: whole-book EPUB page numbering with background rendered page-count scan')
