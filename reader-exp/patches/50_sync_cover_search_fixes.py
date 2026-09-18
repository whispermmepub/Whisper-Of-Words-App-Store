#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
java=root/'app/src/main/java/com/whisper/wowreader'
drive=java/'GoogleDriveSync.java'
cover=java/'GoogleBooksCoverSearch.java'
if not drive.is_file() or not cover.is_file():
    raise SystemExit('Phase F source files missing')

def rep(path,old,new):
    s=path.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit(f'Phase F anchor missing in {path.name}: {old[:160]!r}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')

# Google Drive custom-property values are capped at 124 UTF-8 bytes INCLUDING the key.
# Never put user-controlled filenames/titles/authors in appProperties. A fixed 64-char SHA-256 is safe.
rep(drive,
'''        JSONObject props=new JSONObject();props.put("originalName",file.getName());props.put("contentHash",hash);meta.put("appProperties",props);''',
'''        JSONObject props=new JSONObject();props.put("contentHash",hash);meta.put("appProperties",props);''')

# Pure Java helpers make query broadening/dedup behavior testable without Android.
(java/'CoverSearchPlanner.java').write_text(r'''package com.whisper.wowreader;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

final class CoverSearchPlanner {
    private CoverSearchPlanner() {}

    static List<String> googleQueries(String title,String author,String isbn) {
        String t=clean(title), a=clean(author), i=clean(isbn);
        LinkedHashSet<String> q=new LinkedHashSet<>();
        if(!i.isEmpty()) q.add("isbn:"+i);
        if(!t.isEmpty()&&!a.isEmpty()) q.add(t+" "+a);
        if(!t.isEmpty()) q.add(t);
        if(!t.isEmpty()) q.add("intitle:"+t);
        if(t.isEmpty()&&!a.isEmpty()) q.add(a);
        return new ArrayList<>(q);
    }

    static String openLibraryQuery(String title,String author,String isbn) {
        String t=clean(title), a=clean(author), i=clean(isbn);
        if(!i.isEmpty()) return "isbn:"+i;
        if(!t.isEmpty()&&!a.isEmpty()) return t+" "+a;
        if(!t.isEmpty()) return t;
        return a;
    }

    static String webImageQuery(String title,String author,String isbn) {
        String t=clean(title), a=clean(author), i=clean(isbn);
        if(!t.isEmpty()&&!a.isEmpty()) return t+" "+a+" book cover";
        if(!t.isEmpty()) return t+" book cover";
        if(!i.isEmpty()) return i+" book cover";
        if(!a.isEmpty()) return a+" book cover";
        return "book cover";
    }

    static String clean(String s){ return s==null?"":s.trim(); }
}
''',encoding='utf-8')

cover.write_text(r'''package com.whisper.wowreader;

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
import java.util.Map;

final class GoogleBooksCoverSearch {
    static final class Result {
        String title="";
        String author="";
        String imageUrl="";
        String source="";
    }

    static List<Result> search(String title,String author,String isbn)throws Exception {
        if(CoverSearchPlanner.clean(title).isEmpty() &&
                CoverSearchPlanner.clean(author).isEmpty() &&
                CoverSearchPlanner.clean(isbn).isEmpty())
            throw new Exception("Enter a title, author or ISBN");

        LinkedHashMap<String,Result> merged=new LinkedHashMap<>();
        Exception googleError=null, openLibraryError=null;

        // Google Books: do not require strict intitle/inauthor matching.
        // Broad free-text queries are much better for translated titles and Myanmar metadata.
        try {
            List<String> queries=CoverSearchPlanner.googleQueries(title,author,isbn);
            int calls=0;
            for(String q:queries) {
                if(calls>=3 || merged.size()>=50) break;
                addGoogle(merged,q);
                calls++;
            }
        } catch(Exception e) { googleError=e; }

        // Open Library broadens coverage and supplies covers by stable Cover ID/ISBN.
        try {
            addOpenLibrary(merged,CoverSearchPlanner.openLibraryQuery(title,author,isbn));
        } catch(Exception e) { openLibraryError=e; }

        if(merged.isEmpty()) {
            if(googleError!=null && openLibraryError!=null)
                throw new Exception("Cover search failed. Check internet and try a different/original title.");
            return new ArrayList<>();
        }
        return new ArrayList<>(merged.values());
    }

    private static void addGoogle(Map<String,Result> out,String query)throws Exception {
        if(query==null||query.trim().isEmpty()) return;
        String u="https://www.googleapis.com/books/v1/volumes?q="+
                URLEncoder.encode(query,"UTF-8")+"&maxResults=40&printType=books";
        JSONObject root=getJson(u,"WoWReader/2.19");
        JSONArray items=root.optJSONArray("items");
        if(items==null) return;
        for(int i=0;i<items.length() && out.size()<70;i++) {
            JSONObject item=items.optJSONObject(i); if(item==null) continue;
            JSONObject v=item.optJSONObject("volumeInfo"); if(v==null) continue;
            JSONObject imgs=v.optJSONObject("imageLinks"); if(imgs==null) continue;
            String image=first(imgs,"extraLarge","large","medium","small","thumbnail","smallThumbnail");
            if(image.isEmpty()) continue;
            if(image.startsWith("http://")) image="https://"+image.substring(7);
            Result r=new Result();
            r.title=v.optString("title","");
            JSONArray aa=v.optJSONArray("authors");
            if(aa!=null&&aa.length()>0) r.author=aa.optString(0,"");
            r.imageUrl=image;
            r.source="Google Books";
            out.putIfAbsent(normalizeImageKey(image),r);
        }
    }

    private static void addOpenLibrary(Map<String,Result> out,String query)throws Exception {
        if(query==null||query.trim().isEmpty()) return;
        String u="https://openlibrary.org/search.json?q="+URLEncoder.encode(query,"UTF-8")+
                "&fields=title,author_name,cover_i,isbn,key&limit=40";
        JSONObject root=getJson(u,"WoWReader/2.19 (book cover search)");
        JSONArray docs=root.optJSONArray("docs");
        if(docs==null) return;
        for(int i=0;i<docs.length() && out.size()<90;i++) {
            JSONObject d=docs.optJSONObject(i); if(d==null) continue;
            String image="";
            long coverId=d.optLong("cover_i",0L);
            if(coverId>0) {
                image="https://covers.openlibrary.org/b/id/"+coverId+"-L.jpg?default=false";
            } else {
                JSONArray isbns=d.optJSONArray("isbn");
                if(isbns!=null&&isbns.length()>0) {
                    String iv=isbns.optString(0,"").trim();
                    if(!iv.isEmpty()) image="https://covers.openlibrary.org/b/isbn/"+
                            URLEncoder.encode(iv,"UTF-8")+"-L.jpg?default=false";
                }
            }
            if(image.isEmpty()) continue;
            Result r=new Result();
            r.title=d.optString("title","");
            JSONArray authors=d.optJSONArray("author_name");
            if(authors!=null&&authors.length()>0) r.author=authors.optString(0,"");
            r.imageUrl=image;
            r.source="Open Library";
            out.putIfAbsent(normalizeImageKey(image),r);
        }
    }

    private static JSONObject getJson(String url,String userAgent)throws Exception {
        HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();
        c.setConnectTimeout(15000);
        c.setReadTimeout(25000);
        c.setRequestProperty("Accept","application/json");
        c.setRequestProperty("User-Agent",userAgent);
        int code=c.getResponseCode();
        if(code<200||code>=300) {
            InputStream err=c.getErrorStream();
            if(err!=null) try{while(err.read()!=-1){} }finally{err.close();}
            c.disconnect();
            throw new Exception("Book cover search failed ("+code+")");
        }
        byte[] data;
        try(InputStream in=c.getInputStream();ByteArrayOutputStream b=new ByteArrayOutputStream()){
            byte[] buf=new byte[16384]; int n;
            while((n=in.read(buf))>0) {
                if(b.size()+n>4*1024*1024) throw new Exception("Cover search response is too large");
                b.write(buf,0,n);
            }
            data=b.toByteArray();
        } finally { c.disconnect(); }
        return new JSONObject(new String(data,StandardCharsets.UTF_8));
    }

    private static String first(JSONObject o,String...keys){
        for(String k:keys){
            String v=o.optString(k,"");
            if(v!=null&&!v.trim().isEmpty()) return v.trim();
        }
        return "";
    }

    private static String normalizeImageKey(String s) {
        if(s==null) return "";
        return s.replace("http://","https://").replace("&zoom=1","").trim();
    }
}
''',encoding='utf-8')

# Make the UI accurately describe the broader providers and show where a result came from.
main=java/'MainActivity.java'
rep(main,
'''LinearLayout sheet=premiumSheet("Find cover online","Google Books · edit Title / Author / ISBN and search",d);''',
'''LinearLayout sheet=premiumSheet("Find cover online","Google Books + Open Library · edit Title / Author / ISBN and search",d);''')
rep(main,
'''sheet.addView(search,sp);ScrollView scroll=new ScrollView(this);''',
'''sheet.addView(search,sp);TextView webImages=filterChoice("Search Google Images",false);webImages.setGravity(Gravity.CENTER);LinearLayout.LayoutParams wip=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(40));wip.topMargin=dp(5);sheet.addView(webImages,wip);webImages.setOnClickListener(v->{try{String q=CoverSearchPlanner.webImageQuery(title.getText().toString(),author.getText().toString(),isbn.getText().toString());startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse("https://www.google.com/search?tbm=isch&q="+Uri.encode(q))));}catch(Exception e){Toast.makeText(this,"Unable to open Google Images",Toast.LENGTH_SHORT).show();}});ScrollView scroll=new ScrollView(this);''')
rep(main,
'''TextView none=new TextView(this);none.setText("No cover results");grid.addView(none);return;''',
'''TextView none=new TextView(this);none.setText("No catalog cover results. Try a simpler/original title or Search Google Images.");grid.addView(none);return;''')
rep(main,
'''TextView text=new TextView(this);text.setText(r.title);text.setTextSize(9f);text.setMaxLines(2);''',
'''TextView text=new TextView(this);text.setText(r.title+(r.source.isEmpty()?"":" · "+r.source));text.setTextSize(9f);text.setMaxLines(3);''')

print('Applied Phase F: Drive 124-byte property fix + broad multi-provider cover search + Google Images fallback')
