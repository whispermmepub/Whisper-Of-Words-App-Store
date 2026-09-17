#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve(); java=root/'app/src/main/java/com/whisper/wowreader'
db=java/'ReaderStateDb.java'; main=java/'MainActivity.java'; drive=java/'GoogleDriveSync.java'; visual=java/'BookVisualUtil.java'; gradle=root/'app/build.gradle'

def rep(path,old,new):
    s=path.read_text(encoding='utf-8')
    if old not in s: raise SystemExit(f'Custom-cover anchor missing in {path.name}: {old[:120]!r}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')

# EXIF orientation support down to minSdk 23.
rep(gradle,"    implementation 'androidx.core:core:1.15.0'","    implementation 'androidx.core:core:1.15.0'\n    implementation 'androidx.exifinterface:exifinterface:1.3.7'")

(java/'CustomCoverStore.java').write_text(r'''package com.whisper.wowreader;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Matrix;
import android.net.Uri;
import androidx.exifinterface.media.ExifInterface;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.Locale;

final class CustomCoverStore {
    private CustomCoverStore() {}
    static File importUri(Context context, Uri uri, String stableKey) throws Exception {
        if(context==null||uri==null)throw new Exception("Cover image is unavailable");
        File scratch=File.createTempFile("wow-cover-",".img",context.getCacheDir());
        try(InputStream in=context.getContentResolver().openInputStream(uri);FileOutputStream out=new FileOutputStream(scratch)){
            if(in==null)throw new Exception("Unable to open cover image");copy(in,out);out.getFD().sync();
        }
        try{return normalize(context,scratch,stableKey);}finally{scratch.delete();}
    }
    static File importUrl(Context context,String url,String stableKey)throws Exception{
        HttpURLConnection c=openUrl(url);File scratch=File.createTempFile("wow-cover-web-",".img",context.getCacheDir());
        try(InputStream in=c.getInputStream();FileOutputStream out=new FileOutputStream(scratch)){copy(in,out);out.getFD().sync();}
        finally{c.disconnect();}
        try{return normalize(context,scratch,stableKey);}finally{scratch.delete();}
    }
    static Bitmap downloadBitmap(String url,int targetW,int targetH)throws Exception{
        HttpURLConnection c=openUrl(url);File tmp=File.createTempFile("wow-cover-preview-",".img");
        try(InputStream in=c.getInputStream();FileOutputStream out=new FileOutputStream(tmp)){copy(in,out);}
        finally{c.disconnect();}
        try{return decodeSampled(tmp,targetW,targetH);}finally{tmp.delete();}
    }
    private static HttpURLConnection openUrl(String value)throws Exception{
        if(value==null||value.trim().isEmpty())throw new Exception("Cover URL is unavailable");String u=value.startsWith("http://")?"https://"+value.substring(7):value;
        HttpURLConnection c=(HttpURLConnection)new URL(u).openConnection();c.setConnectTimeout(15000);c.setReadTimeout(30000);c.setInstanceFollowRedirects(true);c.setRequestProperty("User-Agent","WoWReader/experimental");
        int code=c.getResponseCode();if(code<200||code>=300){c.disconnect();throw new Exception("Cover download failed ("+code+")");}return c;
    }
    private static File normalize(Context context,File source,String stableKey)throws Exception{
        BitmapFactory.Options b=new BitmapFactory.Options();b.inJustDecodeBounds=true;BitmapFactory.decodeFile(source.getAbsolutePath(),b);if(b.outWidth<=0||b.outHeight<=0)throw new Exception("Unsupported or corrupt image");
        int sample=1;while(b.outWidth/sample>1800||b.outHeight/sample>1800)sample*=2;BitmapFactory.Options o=new BitmapFactory.Options();o.inSampleSize=sample;o.inPreferredConfig=Bitmap.Config.RGB_565;
        Bitmap bitmap=BitmapFactory.decodeFile(source.getAbsolutePath(),o);if(bitmap==null)throw new Exception("Unable to decode image");Bitmap oriented=orient(source,bitmap);if(oriented!=bitmap)bitmap.recycle();
        int w=oriented.getWidth(),h=oriented.getHeight();float scale=Math.min(1f,1000f/Math.max(w,h));Bitmap finalBitmap=oriented;
        if(scale<.999f){finalBitmap=Bitmap.createScaledBitmap(oriented,Math.max(1,Math.round(w*scale)),Math.max(1,Math.round(h*scale)),true);if(finalBitmap!=oriented)oriented.recycle();}
        File dir=new File(context.getFilesDir(),"custom_covers");if(!dir.exists()&&!dir.mkdirs()){finalBitmap.recycle();throw new Exception("Unable to create cover folder");}
        File dest=new File(dir,key(stableKey)+".jpg"),tmp=new File(dir,dest.getName()+".tmp");
        try(FileOutputStream out=new FileOutputStream(tmp)){if(!finalBitmap.compress(Bitmap.CompressFormat.JPEG,86,out))throw new Exception("Unable to save cover");out.getFD().sync();}finally{finalBitmap.recycle();}
        if(dest.exists()&&!dest.delete()){tmp.delete();throw new Exception("Unable to replace cover");}if(!tmp.renameTo(dest)){tmp.delete();throw new Exception("Unable to finalize cover");}return dest;
    }
    private static Bitmap orient(File source,Bitmap bitmap){try{ExifInterface e=new ExifInterface(source.getAbsolutePath());int x=e.getAttributeInt(ExifInterface.TAG_ORIENTATION,ExifInterface.ORIENTATION_NORMAL);Matrix m=new Matrix();
        if(x==ExifInterface.ORIENTATION_ROTATE_90)m.postRotate(90);else if(x==ExifInterface.ORIENTATION_ROTATE_180)m.postRotate(180);else if(x==ExifInterface.ORIENTATION_ROTATE_270)m.postRotate(270);else if(x==ExifInterface.ORIENTATION_FLIP_HORIZONTAL)m.preScale(-1,1);else if(x==ExifInterface.ORIENTATION_FLIP_VERTICAL)m.preScale(1,-1);
        if(!m.isIdentity())return Bitmap.createBitmap(bitmap,0,0,bitmap.getWidth(),bitmap.getHeight(),m,true);}catch(Exception ignored){}return bitmap;}
    static Bitmap decodeSampled(File file,int tw,int th){if(file==null||!file.isFile())return null;BitmapFactory.Options b=new BitmapFactory.Options();b.inJustDecodeBounds=true;BitmapFactory.decodeFile(file.getAbsolutePath(),b);int s=1;tw=Math.max(80,tw);th=Math.max(120,th);while(b.outWidth/s>tw*2||b.outHeight/s>th*2)s*=2;BitmapFactory.Options o=new BitmapFactory.Options();o.inSampleSize=s;o.inPreferredConfig=Bitmap.Config.RGB_565;return BitmapFactory.decodeFile(file.getAbsolutePath(),o);}
    static void delete(File f){if(f!=null&&f.isFile())f.delete();}
    private static String key(String v)throws Exception{MessageDigest md=MessageDigest.getInstance("SHA-256");byte[] d=md.digest((v==null?"book":v).getBytes("UTF-8"));StringBuilder b=new StringBuilder();for(int i=0;i<12;i++)b.append(String.format(Locale.US,"%02x",d[i]));return b.toString();}
    private static void copy(InputStream in,FileOutputStream out)throws Exception{byte[] b=new byte[64*1024];int n;long total=0;while((n=in.read(b))>0){total+=n;if(total>50L*1024L*1024L)throw new Exception("Cover image is too large");out.write(b,0,n);}}
}
''',encoding='utf-8')

(java/'GoogleBooksCoverSearch.java').write_text(r'''package com.whisper.wowreader;
import org.json.JSONArray;import org.json.JSONObject;import java.io.ByteArrayOutputStream;import java.io.InputStream;import java.net.HttpURLConnection;import java.net.URL;import java.net.URLEncoder;import java.nio.charset.StandardCharsets;import java.util.ArrayList;import java.util.List;
final class GoogleBooksCoverSearch{
 static final class Result{String title="",author="",imageUrl="";}
 static List<Result> search(String title,String author,String isbn)throws Exception{StringBuilder q=new StringBuilder();if(title!=null&&!title.trim().isEmpty())q.append("intitle:").append(title.trim());if(author!=null&&!author.trim().isEmpty()){if(q.length()>0)q.append(' ');q.append("inauthor:").append(author.trim());}if(isbn!=null&&!isbn.trim().isEmpty()){if(q.length()>0)q.append(' ');q.append("isbn:").append(isbn.trim());}if(q.length()==0)throw new Exception("Enter a title, author or ISBN");
  String u="https://www.googleapis.com/books/v1/volumes?q="+URLEncoder.encode(q.toString(),"UTF-8")+"&maxResults=20&printType=books";HttpURLConnection c=(HttpURLConnection)new URL(u).openConnection();c.setConnectTimeout(15000);c.setReadTimeout(25000);c.setRequestProperty("Accept","application/json");int code=c.getResponseCode();if(code<200||code>=300){c.disconnect();throw new Exception("Book cover search failed ("+code+")");}byte[] data;try(InputStream in=c.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){byte[] b=new byte[16384];int n;while((n=in.read(b))>0)out.write(b,0,n);data=out.toByteArray();}finally{c.disconnect();}
  JSONObject root=new JSONObject(new String(data,StandardCharsets.UTF_8));JSONArray items=root.optJSONArray("items");List<Result> out=new ArrayList<>();if(items==null)return out;for(int i=0;i<items.length();i++){JSONObject item=items.optJSONObject(i);if(item==null)continue;JSONObject v=item.optJSONObject("volumeInfo");if(v==null)continue;JSONObject imgs=v.optJSONObject("imageLinks");if(imgs==null)continue;String image=first(imgs,"extraLarge","large","medium","small","thumbnail","smallThumbnail");if(image.isEmpty())continue;Result r=new Result();r.title=v.optString("title","");JSONArray aa=v.optJSONArray("authors");if(aa!=null&&aa.length()>0)r.author=aa.optString(0,"");r.imageUrl=image.startsWith("http://")?"https://"+image.substring(7):image;out.add(r);}return out;}
 private static String first(JSONObject o,String...k){for(String x:k){String v=o.optString(x,"");if(v!=null&&!v.trim().isEmpty())return v.trim();}return "";}
}
''',encoding='utf-8')

# DB v5 cover override and independent cover sync state.
rep(db,'private static final int DB_VERSION = 4;','private static final int DB_VERSION = 5;')
rep(db,
'''                "title TEXT NOT NULL DEFAULT '', author TEXT NOT NULL DEFAULT '', annotation_count INTEGER NOT NULL DEFAULT 0," +''',
'''                "title TEXT NOT NULL DEFAULT '', author TEXT NOT NULL DEFAULT '', annotation_count INTEGER NOT NULL DEFAULT 0," +\n                "custom_cover_path TEXT NOT NULL DEFAULT '', cover_scope TEXT NOT NULL DEFAULT 'library_only', cover_updated_at INTEGER NOT NULL DEFAULT 0," +\n                "remote_cover_file_id TEXT NOT NULL DEFAULT '', cover_sync_dirty INTEGER NOT NULL DEFAULT 0, cover_upload_session_url TEXT NOT NULL DEFAULT '', cover_upload_offset INTEGER NOT NULL DEFAULT 0," +''')
rep(db,
'''        if (oldVersion < 4) {\n            try { db.execSQL("ALTER TABLE books ADD COLUMN annotation_count INTEGER NOT NULL DEFAULT 0"); } catch (Exception ignored) {}\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_annotations ON books(annotation_count,last_opened_at DESC)");\n        }\n    }''',
'''        if (oldVersion < 4) {\n            try { db.execSQL("ALTER TABLE books ADD COLUMN annotation_count INTEGER NOT NULL DEFAULT 0"); } catch (Exception ignored) {}\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_annotations ON books(annotation_count,last_opened_at DESC)");\n        }\n        if (oldVersion < 5) {\n            try { db.execSQL("ALTER TABLE books ADD COLUMN custom_cover_path TEXT NOT NULL DEFAULT ''"); } catch (Exception ignored) {}\n            try { db.execSQL("ALTER TABLE books ADD COLUMN cover_scope TEXT NOT NULL DEFAULT 'library_only'"); } catch (Exception ignored) {}\n            try { db.execSQL("ALTER TABLE books ADD COLUMN cover_updated_at INTEGER NOT NULL DEFAULT 0"); } catch (Exception ignored) {}\n            try { db.execSQL("ALTER TABLE books ADD COLUMN remote_cover_file_id TEXT NOT NULL DEFAULT ''"); } catch (Exception ignored) {}\n            try { db.execSQL("ALTER TABLE books ADD COLUMN cover_sync_dirty INTEGER NOT NULL DEFAULT 0"); } catch (Exception ignored) {}\n            try { db.execSQL("ALTER TABLE books ADD COLUMN cover_upload_session_url TEXT NOT NULL DEFAULT ''"); } catch (Exception ignored) {}\n            try { db.execSQL("ALTER TABLE books ADD COLUMN cover_upload_offset INTEGER NOT NULL DEFAULT 0"); } catch (Exception ignored) {}\n        }\n    }''')

anchor='''    private void updateBookHash(File file, String hash) {'''
api=r'''    String contentHash(String fileName){return scalarString("SELECT content_hash FROM books WHERE file_name=?",new String[]{fileName});}
    String customCoverPath(String fileName){return scalarString("SELECT custom_cover_path FROM books WHERE file_name=?",new String[]{fileName});}
    String coverScope(String fileName){String s=scalarString("SELECT cover_scope FROM books WHERE file_name=?",new String[]{fileName});return "everywhere".equals(s)?"everywhere":"library_only";}
    void updateBookMetadata(String fileName,String title,String author){if(fileName==null)return;ContentValues v=new ContentValues();v.put("title",title==null||title.trim().isEmpty()?stripExtension(fileName):title.trim());v.put("author",author==null?"":author.trim());v.put("updated_at",System.currentTimeMillis());getWritableDatabase().update("books",v,"file_name=?",new String[]{fileName});}
    void updateCustomCover(String fileName,String path,String scope){if(fileName==null)return;ContentValues v=new ContentValues();v.put("custom_cover_path",path==null?"":path);v.put("cover_scope","everywhere".equals(scope)?"everywhere":"library_only");v.put("cover_updated_at",System.currentTimeMillis());v.put("cover_sync_dirty",1);v.put("cover_upload_session_url","");v.put("cover_upload_offset",0L);getWritableDatabase().update("books",v,"file_name=?",new String[]{fileName});}
    void setCoverScope(String fileName,String scope){if(fileName==null)return;ContentValues v=new ContentValues();v.put("cover_scope","everywhere".equals(scope)?"everywhere":"library_only");v.put("cover_updated_at",System.currentTimeMillis());if(!customCoverPath(fileName).isEmpty())v.put("cover_sync_dirty",1);getWritableDatabase().update("books",v,"file_name=?",new String[]{fileName});}
    void clearCustomCover(String fileName){updateCustomCover(fileName,"","library_only");}
    static final class PendingCoverRow{final String fileName,filePath,hash,coverPath,remoteId,session;final long offset;PendingCoverRow(Cursor c){fileName=c.getString(0);filePath=c.getString(1);hash=c.getString(2);coverPath=c.getString(3);remoteId=c.getString(4);session=c.getString(5);offset=c.getLong(6);}}
    List<PendingCoverRow> pendingCoverUploads(int limit){int n=Math.max(1,Math.min(100,limit));List<PendingCoverRow> out=new ArrayList<>();Cursor c=null;try{c=getReadableDatabase().rawQuery("SELECT file_name,file_path,content_hash,custom_cover_path,remote_cover_file_id,cover_upload_session_url,cover_upload_offset FROM books WHERE cover_sync_dirty=1 ORDER BY cover_updated_at ASC LIMIT "+n,null);while(c.moveToNext())out.add(new PendingCoverRow(c));}catch(Exception ignored){}finally{if(c!=null)c.close();}return out;}
    int pendingCoverUploadCount(){return (int)Math.min(Integer.MAX_VALUE,scalarLong("SELECT COUNT(*) FROM books WHERE cover_sync_dirty=1",null));}
    void saveCoverUploadCheckpoint(String fileName,String session,long offset){ContentValues v=new ContentValues();v.put("cover_upload_session_url",session==null?"":session);v.put("cover_upload_offset",Math.max(0L,offset));getWritableDatabase().update("books",v,"file_name=?",new String[]{fileName});}
    void markCoverSynced(String fileName,String remoteId){ContentValues v=new ContentValues();v.put("remote_cover_file_id",remoteId==null?"":remoteId);v.put("cover_sync_dirty",0);v.put("cover_upload_session_url","");v.put("cover_upload_offset",0L);getWritableDatabase().update("books",v,"file_name=?",new String[]{fileName});}

'''
rep(db,anchor,api+anchor)

# Extend sync policy to cover assets.
policy=java/'SyncBatchPolicy.java';s=policy.read_text(encoding='utf-8');s=s.replace('static final int DELETE_BATCH = 25;','static final int DELETE_BATCH = 25;\n    static final int COVER_BATCH = 25;').replace('static boolean hasMore(int pendingBooks, int pendingDeletes) { return pendingBooks + pendingDeletes > 0; }','static boolean hasMore(int pendingBooks, int pendingDeletes, int pendingCovers) { return pendingBooks + pendingDeletes + pendingCovers > 0; }');policy.write_text(s,encoding='utf-8')

# Drive cover uploads/deletes are a separate queue; changing a cover never re-uploads the EPUB/PDF.
s=drive.read_text(encoding='utf-8')
s=s.replace('''                int remainingBooks=db.pendingBookUploadCount();\n                int remainingDeletes=db.pendingTombstoneCount();\n                boolean more=SyncBatchPolicy.hasMore(remainingBooks,remainingDeletes);''','''                int coverSynced=0;\n                for (ReaderStateDb.PendingCoverRow row : db.pendingCoverUploads(SyncBatchPolicy.COVER_BATCH)) { syncOneCover(token,db,prefs,row); coverSynced++; }\n                int remainingBooks=db.pendingBookUploadCount();\n                int remainingDeletes=db.pendingTombstoneCount();\n                int remainingCovers=db.pendingCoverUploadCount();\n                boolean more=SyncBatchPolicy.hasMore(remainingBooks,remainingDeletes,remainingCovers);''',1)
s=s.replace('''                final int u=uploaded,d=deleted,r=remainingBooks+remainingDeletes;''','''                final int u=uploaded,d=deleted,c=coverSynced,r=remainingBooks+remainingDeletes+remainingCovers;''',1)
s=s.replace('''"Synced "+u+" books · "+r+" queued"''','''"Synced "+u+" books · "+c+" covers · "+r+" queued"''',1)
# MIME detection for resumable books and JPEG cover assets.
s=s.replace('''c.setRequestProperty("X-Upload-Content-Type", file.getName().toLowerCase(java.util.Locale.ROOT).endsWith(".pdf")?"application/pdf":"application/epub+zip");''','''c.setRequestProperty("X-Upload-Content-Type", mimeFor(file));''',1)
s=s.replace('''c.setRequestProperty("Content-Type",file.getName().toLowerCase(java.util.Locale.ROOT).endsWith(".pdf")?"application/pdf":"application/epub+zip");''','''c.setRequestProperty("Content-Type",mimeFor(file));''',1)
anchor='''    private static void deleteOneBook(String token, ReaderStateDb db, ReaderStateDb.TombstoneRow row) throws Exception {'''
cover_sync=r'''    private static void syncOneCover(String token,ReaderStateDb db,SharedPreferences prefs,ReaderStateDb.PendingCoverRow row)throws Exception{
        String hash=row.hash;File book=new File(row.filePath);if((hash==null||hash.isEmpty())&&book.isFile())hash=db.ensureHash(book,prefs);if(hash==null||hash.isEmpty())throw new Exception("Unable to identify cover book");
        if(row.coverPath==null||row.coverPath.isEmpty()){String id=row.remoteId;if((id==null||id.isEmpty())){BackupInfo i=findFileInfo(token,DriveObjectNamer.coverName(hash));if(i!=null)id=i.id;}if(id!=null&&!id.isEmpty())deleteRemoteFile(token,id);db.markCoverSynced(row.fileName,"");return;}
        File cover=new File(row.coverPath);if(!cover.isFile())throw new Exception("Custom cover file is unavailable");String name=DriveObjectNamer.coverName(hash);BackupInfo remote=null;if(row.remoteId!=null&&!row.remoteId.isEmpty()){remote=new BackupInfo();remote.id=row.remoteId;}else remote=findFileInfo(token,name);
        String session=row.session;long offset=Math.max(0,row.offset);if(session==null||session.isEmpty()){session=startResumable(token,name,cover,hash,remote==null?"":remote.id);offset=0;db.saveCoverUploadCheckpoint(row.fileName,session,0);}
        BackupInfo done;try{done=uploadResumableCover(token,cover,session,offset,db,row.fileName);}catch(ResumableExpiredException x){session=startResumable(token,name,cover,hash,remote==null?"":remote.id);db.saveCoverUploadCheckpoint(row.fileName,session,0);done=uploadResumableCover(token,cover,session,0,db,row.fileName);}String id=done.id;if((id==null||id.isEmpty())&&remote!=null)id=remote.id;db.markCoverSynced(row.fileName,id);
    }
    private static BackupInfo uploadResumableCover(String token,File file,String session,long start,ReaderStateDb db,String fileName)throws Exception{
        long total=file.length(),offset=Math.max(0,Math.min(start,total));try(RandomAccessFile raf=new RandomAccessFile(file,"r")){while(offset<total){int len=(int)Math.min((long)SyncBatchPolicy.CHUNK_BYTES,total-offset);long end=offset+len-1;HttpURLConnection c=open(session,"PUT",token);c.setDoOutput(true);c.setRequestProperty("Content-Type","image/jpeg");c.setRequestProperty("Content-Range","bytes "+offset+"-"+end+"/"+total);c.setFixedLengthStreamingMode(len);raf.seek(offset);byte[] b=new byte[64*1024];int remain=len;try(OutputStream out=new BufferedOutputStream(c.getOutputStream())){while(remain>0){int n=raf.read(b,0,Math.min(b.length,remain));if(n<0)throw new Exception("Unexpected end of cover file");out.write(b,0,n);remain-=n;}}int code=c.getResponseCode();if(code==404||code==410){c.disconnect();throw new ResumableExpiredException();}if(code==308){String range=c.getHeaderField("Range");c.disconnect();offset=parseNextOffset(range,end+1);db.saveCoverUploadCheckpoint(fileName,session,offset);continue;}if(code>=200&&code<300){byte[] data;try(InputStream in=c.getInputStream()){data=readAll(in);}finally{c.disconnect();}BackupInfo info=new BackupInfo();if(data.length>0){JSONObject o=new JSONObject(new String(data,StandardCharsets.UTF_8));info.id=o.optString("id","");info.modifiedTime=o.optString("modifiedTime","");}return info;}c.disconnect();throw new Exception("Google Drive cover upload error "+code);}}return new BackupInfo();
    }
    private static void deleteRemoteFile(String token,String id)throws Exception{HttpURLConnection c=open("https://www.googleapis.com/drive/v3/files/"+id,"DELETE",token);int code=c.getResponseCode();c.disconnect();if(code!=404&&code!=204&&!(code>=200&&code<300))throw new Exception("Google Drive delete error "+code);}
    private static String mimeFor(File file){String n=file==null?"":file.getName().toLowerCase(java.util.Locale.ROOT);if(n.endsWith(".pdf"))return "application/pdf";if(n.endsWith(".jpg")||n.endsWith(".jpeg"))return "image/jpeg";if(n.endsWith(".png"))return "image/png";return "application/epub+zip";}

'''
if anchor not in s:raise SystemExit('Drive cover sync anchor missing')
s=s.replace(anchor,cover_sync+anchor,1);drive.write_text(s,encoding='utf-8')

# BookVisualUtil: non-library surfaces use custom cover only for `everywhere` scope.
s=visual.read_text(encoding='utf-8')
needle='''        EXECUTOR.execute(() -> {\n            Bitmap bitmap = null;\n            try {'''
replace='''        EXECUTOR.execute(() -> {\n            Bitmap bitmap = null;\n            try {\n                ReaderStateDb stateDb = ReaderStateDb.peek();\n                if (stateDb != null && "everywhere".equals(stateDb.coverScope(file.getName()))) {\n                    String custom = stateDb.customCoverPath(file.getName());\n                    if (custom != null && !custom.isEmpty()) bitmap = CustomCoverStore.decodeSampled(new File(custom), widthPx, heightPx);\n                }\n                if (bitmap != null) { final Bitmap ready=bitmap; activity.runOnUiThread(() -> { Object current=target.getTag(); if(!activity.isFinishing()&&current instanceof Integer&&((Integer)current)==tag)target.setImageBitmap(ready); }); return; }'''
if needle not in s:raise SystemExit('BookVisualUtil anchor missing')
s=s.replace(needle,replace,1);visual.write_text(s,encoding='utf-8')

# MainActivity fields/request code.
rep(main,'private static final int REQ_RESTORE = 1003;','private static final int REQ_RESTORE = 1003;\n    private static final int REQ_COVER_IMAGE = 1004;\n    private File pendingCoverBook;\n    private String pendingCoverScope = "library_only";')
rep(main,'"✐", "Edit title & author"','"✐", "Edit book details"')

# Replace edit dialog with cover + metadata UI.
s=main.read_text(encoding='utf-8');a=s.index('    private void showEditBookMetadata(File file) {');b=s.index('    private void resetBookMetadataFromSource(File file) {',a)
edit=r'''    private void showEditBookMetadata(File file) {
        if(file==null)return;android.app.Dialog dialog=new android.app.Dialog(this);dialog.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE);dialog.setCanceledOnTouchOutside(true);
        LinearLayout sheet=premiumSheet("Edit Book Details","Personal library appearance · original EPUB/PDF stays unchanged",dialog);
        ImageView preview=new ImageView(this);preview.setScaleType(ImageView.ScaleType.CENTER_CROP);preview.setBackground(roundRect(themeControlSurface(),dp(14),dp(1),themeStroke()));preview.setClipToOutline(true);loadCustomCoverPreview(file,preview);LinearLayout.LayoutParams pp=new LinearLayout.LayoutParams(dp(132),dp(194));pp.gravity=Gravity.CENTER_HORIZONTAL;sheet.addView(preview,pp);
        LinearLayout coverButtons=new LinearLayout(this);coverButtons.setOrientation(LinearLayout.HORIZONTAL);TextView choose=filterChoice("Choose from device",false);TextView online=filterChoice("Find cover online",false);coverButtons.addView(choose,new LinearLayout.LayoutParams(0,dp(42),1f));LinearLayout.LayoutParams op=new LinearLayout.LayoutParams(0,dp(42),1f);op.leftMargin=dp(7);coverButtons.addView(online,op);LinearLayout.LayoutParams cbp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(48));cbp.topMargin=dp(8);sheet.addView(coverButtons,cbp);
        EditText titleInput=editField(cachedLibraryTitle(file),"Book title");EditText authorInput=editField(cachedLibraryAuthor(file),"Author name (optional)");LinearLayout.LayoutParams fp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(50));fp.topMargin=dp(7);sheet.addView(titleInput,fp);sheet.addView(authorInput,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(50)));
        TextView scopeLabel=new TextView(this);scopeLabel.setText("Cover display");scopeLabel.setTextSize(12.5f);scopeLabel.setTypeface(Typeface.DEFAULT,Typeface.BOLD);scopeLabel.setTextColor(themeSecondaryText());scopeLabel.setPadding(dp(2),dp(10),0,dp(3));sheet.addView(scopeLabel);
        android.widget.RadioGroup scopes=new android.widget.RadioGroup(this);scopes.setOrientation(android.widget.RadioGroup.VERTICAL);android.widget.RadioButton libraryOnly=new android.widget.RadioButton(this);libraryOnly.setText("Library Card Only — Recommended");android.widget.RadioButton everywhere=new android.widget.RadioButton(this);everywhere.setText("Everywhere in WoW Reader");scopes.addView(libraryOnly);scopes.addView(everywhere);String currentScope=stateDb==null?"library_only":stateDb.coverScope(file.getName());("everywhere".equals(currentScope)?everywhere:libraryOnly).setChecked(true);sheet.addView(scopes);
        choose.setOnClickListener(v->{pendingCoverBook=file;pendingCoverScope=everywhere.isChecked()?"everywhere":"library_only";Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("image/*");i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivityForResult(i,REQ_COVER_IMAGE);});
        online.setOnClickListener(v->showOnlineCoverSearch(file,everywhere.isChecked()?"everywhere":"library_only"));
        TextView restore=filterChoice("Restore Original Cover",false);restore.setGravity(Gravity.CENTER);restore.setOnClickListener(v->{String old=stateDb==null?"":stateDb.customCoverPath(file.getName());if(stateDb!=null)stateDb.clearCustomCover(file.getName());if(old!=null&&!old.isEmpty())CustomCoverStore.delete(new File(old));prefs.edit().putLong("sync_updated_ms",System.currentTimeMillis()).apply();dialog.dismiss();refreshAfterBookEdit();maybeAutoGoogleSync();});LinearLayout.LayoutParams rp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(40));rp.topMargin=dp(5);sheet.addView(restore,rp);
        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);actions.setGravity(Gravity.END|Gravity.CENTER_VERTICAL);TextView cancel=filterChoice("Cancel",false);cancel.setOnClickListener(v->dialog.dismiss());TextView save=filterChoice("Save",true);save.setTextColor(Color.WHITE);save.setBackground(roundRect(themeAccent(),dp(17),0,0));save.setOnClickListener(v->{String title=titleInput.getText()==null?"":titleInput.getText().toString().trim();String author=authorInput.getText()==null?"":authorInput.getText().toString().trim();if(title.isEmpty()){titleInput.setError("Book title is required");return;}if(stateDb!=null){stateDb.updateBookMetadata(file.getName(),title,author);stateDb.setCoverScope(file.getName(),everywhere.isChecked()?"everywhere":"library_only");}prefs.edit().putString("library_title_"+file.getName(),title).putString("library_author_"+file.getName(),author).putBoolean(customMetadataFlag(file),true).putLong("sync_updated_ms",System.currentTimeMillis()).apply();dialog.dismiss();refreshAfterBookEdit();maybeAutoGoogleSync();Toast.makeText(this,"Book details saved",Toast.LENGTH_SHORT).show();});LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(dp(96),dp(40));cp.rightMargin=dp(8);actions.addView(cancel,cp);actions.addView(save,new LinearLayout.LayoutParams(dp(96),dp(40)));LinearLayout.LayoutParams ap=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(52));ap.topMargin=dp(6);sheet.addView(actions,ap);
        presentBottomSheet(dialog,sheet,.88f);
    }

    private EditText editField(String value,String hint){EditText e=new EditText(this);e.setSingleLine(true);e.setText(value);e.setTextSize(15f);e.setTextColor(themePrimaryText());e.setHintTextColor(themeSecondaryText());e.setHint(hint);e.setPadding(dp(14),0,dp(14),0);e.setBackground(roundRect(themeControlSurface(),dp(16),dp(1),themeStroke()));if(pyidaungsuTypeface!=null)e.setTypeface(pyidaungsuTypeface);return e;}
    private void refreshAfterBookEdit(){if(homeMode)buildUi();else refreshLibrary();}
    private void loadCustomCoverPreview(File file,ImageView target){String path=stateDb==null?"":stateDb.customCoverPath(file.getName());if(path!=null&&!path.isEmpty()){Bitmap b=CustomCoverStore.decodeSampled(new File(path),300,440);if(b!=null){target.setImageBitmap(b);return;}}TextView t=new TextView(this),m=new TextView(this);loadBookVisual(file,target,t,m,true);}

    private void showOnlineCoverSearch(File file,String scope){android.app.Dialog d=new android.app.Dialog(this);d.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE);LinearLayout sheet=premiumSheet("Find cover online","Google Books · edit Title / Author / ISBN and search",d);EditText title=editField(cachedLibraryTitle(file),"Title");EditText author=editField(cachedLibraryAuthor(file),"Author");EditText isbn=editField("","ISBN (optional)");sheet.addView(title,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(48)));sheet.addView(author,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(48)));sheet.addView(isbn,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(48)));TextView search=filterChoice("Search covers",true);search.setTextColor(Color.WHITE);search.setBackground(roundRect(themeAccent(),dp(16),0,0));LinearLayout.LayoutParams sp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(42));sp.topMargin=dp(7);sheet.addView(search,sp);ScrollView scroll=new ScrollView(this);android.widget.GridLayout grid=new android.widget.GridLayout(this);grid.setColumnCount(3);grid.setUseDefaultMargins(true);scroll.addView(grid);LinearLayout.LayoutParams slp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(360));slp.topMargin=dp(7);sheet.addView(scroll,slp);search.setOnClickListener(v->{grid.removeAllViews();TextView loading=new TextView(this);loading.setText("Searching…");loading.setPadding(dp(10),dp(16),dp(10),dp(16));grid.addView(loading);bookVisualExecutor.execute(()->{try{java.util.List<GoogleBooksCoverSearch.Result> results=GoogleBooksCoverSearch.search(title.getText().toString(),author.getText().toString(),isbn.getText().toString());runOnUiThread(()->{grid.removeAllViews();if(results.isEmpty()){TextView none=new TextView(this);none.setText("No cover results");grid.addView(none);return;}for(GoogleBooksCoverSearch.Result r:results)addOnlineCoverResult(grid,file,r,scope,d);});}catch(Exception e){runOnUiThread(()->{grid.removeAllViews();TextView err=new TextView(this);err.setText(e.getMessage());grid.addView(err);});}});});presentBottomSheet(d,sheet,.92f);}
    private void addOnlineCoverResult(android.widget.GridLayout grid,File file,GoogleBooksCoverSearch.Result r,String scope,android.app.Dialog searchDialog){LinearLayout card=new LinearLayout(this);card.setOrientation(LinearLayout.VERTICAL);card.setPadding(dp(4),dp(4),dp(4),dp(4));ImageView image=new ImageView(this);image.setScaleType(ImageView.ScaleType.CENTER_CROP);image.setImageBitmap(placeholderBitmap(r.title,180,260));card.addView(image,new LinearLayout.LayoutParams(dp(96),dp(138)));TextView text=new TextView(this);text.setText(r.title);text.setTextSize(9f);text.setMaxLines(2);card.addView(text,new LinearLayout.LayoutParams(dp(96),dp(34)));bookVisualExecutor.execute(()->{try{Bitmap b=CustomCoverStore.downloadBitmap(r.imageUrl,220,320);runOnUiThread(()->{if(!isFinishing())image.setImageBitmap(b);});}catch(Exception ignored){}});card.setOnClickListener(v->showOnlineCoverPreview(file,r,scope,searchDialog));grid.addView(card,new android.widget.GridLayout.LayoutParams());}
    private void showOnlineCoverPreview(File file,GoogleBooksCoverSearch.Result r,String scope,android.app.Dialog searchDialog){android.app.Dialog d=new android.app.Dialog(this);d.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE);LinearLayout sheet=premiumSheet("Cover preview",r.title+(r.author.isEmpty()?"":" · "+r.author),d);ImageView image=new ImageView(this);image.setScaleType(ImageView.ScaleType.CENTER_CROP);image.setImageBitmap(placeholderBitmap(r.title,300,440));sheet.addView(image,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(360)));bookVisualExecutor.execute(()->{try{Bitmap b=CustomCoverStore.downloadBitmap(r.imageUrl,700,1000);runOnUiThread(()->{if(!isFinishing())image.setImageBitmap(b);});}catch(Exception ignored){}});TextView use=filterChoice("Use this cover",true);use.setTextColor(Color.WHITE);use.setBackground(roundRect(themeAccent(),dp(16),0,0));use.setOnClickListener(v->{use.setEnabled(false);bookVisualExecutor.execute(()->{try{String hash=stateDb==null?file.getName():stateDb.contentHash(file.getName());if((hash==null||hash.isEmpty())&&stateDb!=null)hash=stateDb.ensureHash(file,prefs);File saved=CustomCoverStore.importUrl(this,r.imageUrl,hash==null?file.getName():hash);String finalHash=hash;if(stateDb!=null)stateDb.updateCustomCover(file.getName(),saved.getAbsolutePath(),scope);prefs.edit().putLong("sync_updated_ms",System.currentTimeMillis()).apply();runOnUiThread(()->{d.dismiss();searchDialog.dismiss();refreshAfterBookEdit();maybeAutoGoogleSync();Toast.makeText(this,"Custom cover saved",Toast.LENGTH_SHORT).show();});}catch(Exception e){runOnUiThread(()->{use.setEnabled(true);Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show();});}});});LinearLayout.LayoutParams up=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(44));up.topMargin=dp(7);sheet.addView(use,up);presentBottomSheet(d,sheet,.82f);}

'''
s=s[:a]+edit+s[b:];main.write_text(s,encoding='utf-8')

# Reset metadata also updates DB.
rep(main,
'''            prefs.edit()\n                    .putString("library_title_" + file.getName(), resolvedTitle)''',
'''            if (stateDb != null) stateDb.updateBookMetadata(file.getName(), resolvedTitle, resolvedAuthor);\n            prefs.edit()\n                    .putString("library_title_" + file.getName(), resolvedTitle)''')

# Library visual resolver with scope awareness.
rep(main,
'''    private void loadBookVisual(File file, ImageView cover, TextView titleView, TextView metaView) {\n        bookVisualExecutor.execute(() -> {''',
'''    private void loadBookVisual(File file, ImageView cover, TextView titleView, TextView metaView) { loadBookVisual(file,cover,titleView,metaView,true); }\n    private void loadBookVisual(File file, ImageView cover, TextView titleView, TextView metaView, boolean libraryCardContext) {\n        bookVisualExecutor.execute(() -> {''')
rep(main,
'''            boolean customMetadata = prefs.getBoolean(customMetadataFlag(file), false);\n            String title = cachedLibraryTitle(file);\n            String author = cachedLibraryAuthor(file);\n            Bitmap bitmap = null;\n            try {\n                if (file.getName().toLowerCase(Locale.ROOT).endsWith(".epub")) {''',
'''            boolean customMetadata = (stateDb != null && stateDb.isLibraryIndexReady()) || prefs.getBoolean(customMetadataFlag(file), false);\n            String title = cachedLibraryTitle(file);\n            String author = cachedLibraryAuthor(file);\n            Bitmap bitmap = null;\n            try {\n                if (stateDb != null) { String path=stateDb.customCoverPath(file.getName()); String scope=stateDb.coverScope(file.getName()); if(path!=null&&!path.isEmpty()&&(libraryCardContext||"everywhere".equals(scope))) bitmap=CustomCoverStore.decodeSampled(new File(path),360,520); }\n                if (bitmap == null && file.getName().toLowerCase(Locale.ROOT).endsWith(".epub")) {''')
rep(main,'''                } else {\n                    bitmap = renderPdfCover(file);''','''                } else if (bitmap == null) {\n                    bitmap = renderPdfCover(file);''')
# Notes hub is not a Library Card: library_only cover should not bleed into it.
s=main.read_text(encoding='utf-8').replace('loadBookVisual(book, cover, title, dummyMeta);','loadBookVisual(book, cover, title, dummyMeta, false);',1);main.write_text(s,encoding='utf-8')

# Device cover picker result is copied/optimized immediately; no original photo is retained.
s=main.read_text(encoding='utf-8');needle='''        if(resultCode!=RESULT_OK||data==null)return;\n        if(requestCode==REQ_IMPORT){'''
replacement='''        if(resultCode!=RESULT_OK||data==null)return;\n        if(requestCode==REQ_COVER_IMAGE){ Uri imageUri=data.getData(); File targetBook=pendingCoverBook; String scope=pendingCoverScope; pendingCoverBook=null; if(imageUri==null||targetBook==null)return; bookVisualExecutor.execute(()->{try{String hash=stateDb==null?targetBook.getName():stateDb.contentHash(targetBook.getName());if((hash==null||hash.isEmpty())&&stateDb!=null)hash=stateDb.ensureHash(targetBook,prefs);File saved=CustomCoverStore.importUri(this,imageUri,hash==null?targetBook.getName():hash);if(stateDb!=null)stateDb.updateCustomCover(targetBook.getName(),saved.getAbsolutePath(),scope);prefs.edit().putLong("sync_updated_ms",System.currentTimeMillis()).apply();runOnUiThread(()->{refreshAfterBookEdit();maybeAutoGoogleSync();Toast.makeText(this,"Custom cover saved",Toast.LENGTH_SHORT).show();});}catch(Exception e){runOnUiThread(()->Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show());}});return;}\n        if(requestCode==REQ_IMPORT){'''
if needle not in s:raise SystemExit('onActivityResult cover anchor missing')
s=s.replace(needle,replacement,1);main.write_text(s,encoding='utf-8')

print('Applied Phase D: DB-backed custom covers, Google Books search, independent cover sync')
