#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
java=root/'app/src/main/java/com/whisper/wowreader'
drive=java/'GoogleDriveSync.java'
main=java/'MainActivity.java'
if not drive.is_file() or not main.is_file():
    raise SystemExit('Bugfix source files missing')

def rep(path, old, new):
    s=path.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit(f'Bugfix anchor missing in {path.name}: {old[:140]!r}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')

(java/'DriveMetadataPolicy.java').write_text(r'''package com.whisper.wowreader;

import java.nio.charset.StandardCharsets;

final class DriveMetadataPolicy {
    private DriveMetadataPolicy() {}
    static final int MAX_PROPERTY_BYTES = 124;
    static boolean isSafe(String key,String value) {
        String k=key==null?"":key, v=value==null?"":value;
        return (k+v).getBytes(StandardCharsets.UTF_8).length <= MAX_PROPERTY_BYTES;
    }
    static String safeValue(String key,String value) {
        String k=key==null?"":key, v=value==null?"":value;
        if(isSafe(k,v)) return v;
        int budget=Math.max(0,MAX_PROPERTY_BYTES-k.getBytes(StandardCharsets.UTF_8).length);
        StringBuilder out=new StringBuilder();
        for(int i=0;i<v.length();) {
            int cp=v.codePointAt(i);
            String ch=new String(Character.toChars(cp));
            if(out.toString().getBytes(StandardCharsets.UTF_8).length + ch.getBytes(StandardCharsets.UTF_8).length > budget) break;
            out.append(ch); i+=Character.charCount(cp);
        }
        return out.toString();
    }
}
''',encoding='utf-8')

(java/'CoverSearchPolicy.java').write_text(r'''package com.whisper.wowreader;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

final class CoverSearchPolicy {
    private CoverSearchPolicy() {}
    static List<String> queries(String title,String author,String isbn) {
        String t=clean(title), a=clean(author), i=clean(isbn);
        LinkedHashSet<String> q=new LinkedHashSet<>();
        if(!i.isEmpty()) q.add(i);
        if(!t.isEmpty() && !a.isEmpty()) q.add(t+" "+a);
        if(!t.isEmpty()) q.add(t);
        if(!a.isEmpty() && t.isEmpty()) q.add(a);
        return new ArrayList<>(q);
    }
    static String webQuery(String title,String author,String isbn) {
        List<String> q=queries(title,author,isbn);
        return q.isEmpty()?"book cover":q.get(0)+" book cover";
    }
    private static String clean(String s){return s==null?"":s.trim().replaceAll("\\s+"," ");}
}
''',encoding='utf-8')

# Drive custom property bug: never put an arbitrary UTF-8 filename in appProperties.
rep(drive,
'''        JSONObject props=new JSONObject();props.put("originalName",file.getName());props.put("contentHash",hash);meta.put("appProperties",props);''',
'''        JSONObject props=new JSONObject();props.put("contentHash",DriveMetadataPolicy.safeValue("contentHash",hash));meta.put("appProperties",props);''')

# Replace strict single-provider search with relaxed Google Books + Open Library.
(java/'GoogleBooksCoverSearch.java').write_text(r'''package com.whisper.wowreader;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;

final class GoogleBooksCoverSearch {
    static final class Result { String title="",author="",imageUrl="",source=""; }

    static List<Result> search(String title,String author,String isbn)throws Exception{
        List<String> queries=CoverSearchPolicy.queries(title,author,isbn);
        if(queries.isEmpty()) throw new Exception("Enter a title, author or ISBN");
        LinkedHashMap<String,Result> all=new LinkedHashMap<>();
        Exception last=null;
        for(String q:queries){
            try{google(q,all);}catch(Exception e){last=e;}
            if(all.size()>=50)break;
        }
        for(String q:queries){
            try{openLibrary(q,all);}catch(Exception e){last=e;}
            if(all.size()>=80)break;
        }
        if(all.isEmpty()&&last!=null) throw last;
        return new ArrayList<>(all.values());
    }

    private static void google(String query,LinkedHashMap<String,Result> out)throws Exception{
        String u="https://www.googleapis.com/books/v1/volumes?q="+URLEncoder.encode(query,"UTF-8")+
                "&maxResults=40&printType=books&projection=lite";
        JSONObject root=getJson(u,"WoWReader/2.19.3");
        JSONArray items=root.optJSONArray("items"); if(items==null)return;
        for(int i=0;i<items.length()&&out.size()<80;i++){
            JSONObject item=items.optJSONObject(i); if(item==null)continue;
            JSONObject v=item.optJSONObject("volumeInfo"); if(v==null)continue;
            JSONObject imgs=v.optJSONObject("imageLinks"); if(imgs==null)continue;
            String image=first(imgs,"extraLarge","large","medium","small","thumbnail","smallThumbnail");
            if(image.isEmpty())continue;
            image=https(image);
            Result r=new Result(); r.title=v.optString("title","");
            JSONArray aa=v.optJSONArray("authors"); if(aa!=null&&aa.length()>0)r.author=aa.optString(0,"");
            r.imageUrl=image; r.source="Google Books";
            out.putIfAbsent(image,r);
        }
    }

    private static void openLibrary(String query,LinkedHashMap<String,Result> out)throws Exception{
        String u="https://openlibrary.org/search.json?q="+URLEncoder.encode(query,"UTF-8")+
                "&fields=key,title,author_name,cover_i&limit=40";
        JSONObject root=getJson(u,"WoWReader/2.19.3 (book cover lookup)");
        JSONArray docs=root.optJSONArray("docs"); if(docs==null)return;
        for(int i=0;i<docs.length()&&out.size()<80;i++){
            JSONObject d=docs.optJSONObject(i); if(d==null)continue;
            long cover=d.optLong("cover_i",0L); if(cover<=0)continue;
            String image="https://covers.openlibrary.org/b/id/"+cover+"-L.jpg?default=false";
            Result r=new Result();r.title=d.optString("title","");
            JSONArray aa=d.optJSONArray("author_name");if(aa!=null&&aa.length()>0)r.author=aa.optString(0,"");
            r.imageUrl=image;r.source="Open Library";
            out.putIfAbsent(image,r);
        }
    }

    private static JSONObject getJson(String url,String userAgent)throws Exception{
        HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();
        c.setConnectTimeout(15000);c.setReadTimeout(25000);
        c.setRequestProperty("Accept","application/json");
        c.setRequestProperty("User-Agent",userAgent);
        int code=c.getResponseCode();
        if(code<200||code>=300){c.disconnect();throw new Exception("Cover search failed ("+code+")");}
        byte[] data;
        try(InputStream in=c.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){
            byte[] b=new byte[16384];int n;while((n=in.read(b))>0)out.write(b,0,n);data=out.toByteArray();
        }finally{c.disconnect();}
        return new JSONObject(new String(data,StandardCharsets.UTF_8));
    }

    private static String first(JSONObject o,String...keys){
        for(String k:keys){String v=o.optString(k,"");if(v!=null&&!v.trim().isEmpty())return v.trim();}
        return "";
    }
    private static String https(String v){return v.startsWith("http://")?"https://"+v.substring(7):v;}
}
''',encoding='utf-8')

# Search UI: explain multi-provider results and add a standards-compliant browser fallback to Google Images.
rep(main,
'''premiumSheet("Find cover online","Google Books · edit Title / Author / ISBN and search",d)''',
'''premiumSheet("Find cover online","Google Books + Open Library · edit Title / Author / ISBN",d)''')

rep(main,
'''sheet.addView(search,sp);ScrollView scroll=new ScrollView(this);''',
'''sheet.addView(search,sp);TextView webImages=filterChoice("Search Google Images",false);webImages.setGravity(Gravity.CENTER);LinearLayout.LayoutParams wip=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(40));wip.topMargin=dp(5);sheet.addView(webImages,wip);webImages.setOnClickListener(v->{try{String q=CoverSearchPolicy.webQuery(title.getText().toString(),author.getText().toString(),isbn.getText().toString());Intent browser=new Intent(Intent.ACTION_VIEW,Uri.parse("https://www.google.com/search?tbm=isch&q="+Uri.encode(q)));startActivity(browser);}catch(Exception e){Toast.makeText(this,"Unable to open web image search",Toast.LENGTH_SHORT).show();}});ScrollView scroll=new ScrollView(this);''')

rep(main,
'''TextView none=new TextView(this);none.setText("No cover results");grid.addView(none);return;''',
'''TextView none=new TextView(this);none.setText("No catalog cover results. Try a simpler title, the original English title, or Search Google Images.");grid.addView(none);return;''')

rep(main,
'''text.setText(r.title);text.setTextSize(9f);''',
'''text.setText(r.title+(r.source.isEmpty()?"":" · "+r.source));text.setTextSize(9f);''')

print('Applied Phase F: Drive 124-byte metadata fix + relaxed multi-provider cover search')
