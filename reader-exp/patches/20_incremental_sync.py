#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
java = root / "app/src/main/java/com/whisper/wowreader"
db = java / "ReaderStateDb.java"
drive = java / "GoogleDriveSync.java"
if not db.is_file() or not drive.is_file():
    raise SystemExit("Phase B source files missing")

def rep(path, old, new):
    s = path.read_text(encoding="utf-8")
    if old not in s:
        raise SystemExit(f"Phase B anchor missing in {path.name}: {old[:120]!r}")
    path.write_text(s.replace(old, new, 1), encoding="utf-8")

# Pure Java helpers used by production sync code and tests.
(java / "DriveObjectNamer.java").write_text(r'''package com.whisper.wowreader;

import java.util.Locale;

final class DriveObjectNamer {
    private DriveObjectNamer() {}
    static String bookName(String hash, String format) {
        String h = hash == null ? "" : hash.trim().toLowerCase(Locale.ROOT);
        String f = "pdf".equalsIgnoreCase(format) ? "pdf" : "epub";
        return "wow_book_" + h + "." + f;
    }
    static String coverName(String hash) {
        String h = hash == null ? "" : hash.trim().toLowerCase(Locale.ROOT);
        return "wow_cover_" + h + ".jpg";
    }
}
''', encoding="utf-8")

(java / "SyncBatchPolicy.java").write_text(r'''package com.whisper.wowreader;

final class SyncBatchPolicy {
    private SyncBatchPolicy() {}
    static final int BOOK_BATCH = 25;
    static final int DELETE_BATCH = 25;
    static final int CHUNK_BYTES = 4 * 1024 * 1024;
    static boolean hasMore(int pendingBooks, int pendingDeletes) { return pendingBooks + pendingDeletes > 0; }
}
''', encoding="utf-8")

# DB v3: durable per-book transfer queue and tombstones.
rep(db, 'private static final int DB_VERSION = 2;', 'private static final int DB_VERSION = 3;')
rep(db,
'''                "pdf_page INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL DEFAULT 0)");''',
'''                "pdf_page INTEGER NOT NULL DEFAULT 0," +
                "remote_file_id TEXT NOT NULL DEFAULT '', remote_modified_time TEXT NOT NULL DEFAULT ''," +
                "sync_dirty INTEGER NOT NULL DEFAULT 1, upload_session_url TEXT NOT NULL DEFAULT ''," +
                "upload_offset INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL DEFAULT 0)");''')
rep(db,
'''        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_progress ON books(progress)");''',
'''        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_progress ON books(progress)");
        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_sync_dirty ON books(sync_dirty,updated_at)");
        db.execSQL("CREATE TABLE IF NOT EXISTS book_tombstones (content_hash TEXT PRIMARY KEY, file_name TEXT NOT NULL DEFAULT '', remote_file_id TEXT NOT NULL DEFAULT '', deleted_at INTEGER NOT NULL DEFAULT 0, sync_dirty INTEGER NOT NULL DEFAULT 1)");
        db.execSQL("CREATE INDEX IF NOT EXISTS idx_tombstones_dirty ON book_tombstones(sync_dirty,deleted_at)");''')

rep(db,
'''        }
    }

    boolean isLegacyMigrated() {''',
'''        }
        if (oldVersion < 3) {
            try { db.execSQL("ALTER TABLE books ADD COLUMN remote_file_id TEXT NOT NULL DEFAULT ''"); } catch (Exception ignored) {}
            try { db.execSQL("ALTER TABLE books ADD COLUMN remote_modified_time TEXT NOT NULL DEFAULT ''"); } catch (Exception ignored) {}
            try { db.execSQL("ALTER TABLE books ADD COLUMN sync_dirty INTEGER NOT NULL DEFAULT 1"); } catch (Exception ignored) {}
            try { db.execSQL("ALTER TABLE books ADD COLUMN upload_session_url TEXT NOT NULL DEFAULT ''"); } catch (Exception ignored) {}
            try { db.execSQL("ALTER TABLE books ADD COLUMN upload_offset INTEGER NOT NULL DEFAULT 0"); } catch (Exception ignored) {}
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_sync_dirty ON books(sync_dirty,updated_at)");
            db.execSQL("CREATE TABLE IF NOT EXISTS book_tombstones (content_hash TEXT PRIMARY KEY, file_name TEXT NOT NULL DEFAULT '', remote_file_id TEXT NOT NULL DEFAULT '', deleted_at INTEGER NOT NULL DEFAULT 0, sync_dirty INTEGER NOT NULL DEFAULT 1)");
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_tombstones_dirty ON book_tombstones(sync_dirty,deleted_at)");
        }
    }

    boolean isLegacyMigrated() {''')

# Replace hash caching: DB is primary after migration; legacy prefs only help transition.
s = db.read_text(encoding="utf-8")
a = s.index("    String ensureHash(File file, SharedPreferences prefs) throws Exception {")
b = s.index("    void upsertBook(File file, String hash, SharedPreferences prefs) {", a)
ensure = r'''    String ensureHash(File file, SharedPreferences prefs) throws Exception {
        if (file == null || !file.isFile()) return "";
        Cursor c = null;
        try {
            c = getReadableDatabase().rawQuery("SELECT content_hash,file_size,modified_at FROM books WHERE file_name=? LIMIT 1", new String[]{file.getName()});
            if (c.moveToFirst()) {
                String cached = c.getString(0);
                if (cached != null && !cached.isEmpty() && c.getLong(1) == file.length() && c.getLong(2) == file.lastModified()) return cached;
            }
        } catch (Exception ignored) {} finally { if (c != null) c.close(); }
        String sig = file.length() + ":" + file.lastModified();
        String legacy = prefs == null ? "" : prefs.getString("content_hash_" + file.getName(), "");
        String legacySig = prefs == null ? "" : prefs.getString("content_hash_sig_" + file.getName(), "");
        if (legacy != null && !legacy.isEmpty() && sig.equals(legacySig)) {
            updateBookHash(file, legacy); return legacy;
        }
        String hash = FileIdentityUtil.sha256(file);
        if (!isLibraryIndexReady() && prefs != null)
            prefs.edit().putString("content_hash_" + file.getName(), hash).putString("content_hash_sig_" + file.getName(), sig).apply();
        updateBookHash(file, hash);
        return hash;
    }

'''
db.write_text(s[:a] + ensure + s[b:], encoding="utf-8")

# Durable sync queue API.
anchor = "    private void updateBookHash(File file, String hash) {"
sync_api = r'''    static final class PendingSyncRow {
        final String fileName, filePath, format, hash, remoteId, sessionUrl;
        final long offset;
        PendingSyncRow(Cursor c) {
            fileName=c.getString(0); filePath=c.getString(1); format=c.getString(2); hash=c.getString(3);
            remoteId=c.getString(4); sessionUrl=c.getString(5); offset=c.getLong(6);
        }
        File file() { return new File(filePath); }
    }
    static final class TombstoneRow {
        final String hash, fileName, remoteId;
        TombstoneRow(Cursor c) { hash=c.getString(0); fileName=c.getString(1); remoteId=c.getString(2); }
    }

    List<PendingSyncRow> pendingBookUploads(int limit) {
        int n=Math.max(1,Math.min(100,limit)); List<PendingSyncRow> out=new ArrayList<>(); Cursor c=null;
        try {
            c=getReadableDatabase().rawQuery("SELECT file_name,file_path,format,content_hash,remote_file_id,upload_session_url,upload_offset FROM books WHERE sync_dirty=1 ORDER BY updated_at ASC LIMIT "+n,null);
            while(c.moveToNext()) out.add(new PendingSyncRow(c));
        } catch(Exception ignored) {} finally { if(c!=null)c.close(); }
        return out;
    }
    int pendingBookUploadCount() { return (int)Math.min(Integer.MAX_VALUE, scalarLong("SELECT COUNT(*) FROM books WHERE sync_dirty=1",null)); }
    List<TombstoneRow> pendingTombstones(int limit) {
        int n=Math.max(1,Math.min(100,limit)); List<TombstoneRow> out=new ArrayList<>(); Cursor c=null;
        try { c=getReadableDatabase().rawQuery("SELECT content_hash,file_name,remote_file_id FROM book_tombstones WHERE sync_dirty=1 ORDER BY deleted_at ASC LIMIT "+n,null); while(c.moveToNext())out.add(new TombstoneRow(c)); }
        catch(Exception ignored) {} finally { if(c!=null)c.close(); } return out;
    }
    int pendingTombstoneCount() { return (int)Math.min(Integer.MAX_VALUE, scalarLong("SELECT COUNT(*) FROM book_tombstones WHERE sync_dirty=1",null)); }
    void saveUploadCheckpoint(String fileName,String session,long offset) {
        ContentValues v=new ContentValues(); v.put("upload_session_url",session==null?"":session); v.put("upload_offset",Math.max(0L,offset));
        getWritableDatabase().update("books",v,"file_name=?",new String[]{fileName});
    }
    void markBookSynced(String fileName,String remoteId,String modifiedTime) {
        ContentValues v=new ContentValues(); v.put("remote_file_id",remoteId==null?"":remoteId); v.put("remote_modified_time",modifiedTime==null?"":modifiedTime);
        v.put("sync_dirty",0); v.put("upload_session_url",""); v.put("upload_offset",0L);
        getWritableDatabase().update("books",v,"file_name=?",new String[]{fileName});
    }
    void markTombstoneSynced(String hash) { if(hash!=null&&!hash.isEmpty())getWritableDatabase().delete("book_tombstones","content_hash=?",new String[]{hash}); }

'''
rep(db, anchor, sync_api + anchor)

# Deleting locally creates a durable cloud-delete tombstone before the row disappears.
s = db.read_text(encoding="utf-8")
a = s.index("    void removeBook(String fileName) {")
b = s.index("\n\n\n    RangeSummary summarizeRange", a)
remove = r'''    void removeBook(String fileName) {
        if (fileName == null) return;
        WRITER.execute(() -> {
            SQLiteDatabase sql = getWritableDatabase();
            Cursor c = null;
            try {
                c=sql.rawQuery("SELECT content_hash,remote_file_id FROM books WHERE file_name=? LIMIT 1",new String[]{fileName});
                if(c.moveToFirst()) {
                    String hash=c.getString(0), remote=c.getString(1);
                    if(hash!=null&&!hash.isEmpty()) {
                        ContentValues t=new ContentValues(); t.put("content_hash",hash); t.put("file_name",fileName); t.put("remote_file_id",remote==null?"":remote);
                        t.put("deleted_at",System.currentTimeMillis()); t.put("sync_dirty",1);
                        sql.insertWithOnConflict("book_tombstones",null,t,SQLiteDatabase.CONFLICT_REPLACE);
                    }
                }
            } catch(Exception ignored) {} finally { if(c!=null)c.close(); }
            sql.delete("books", "file_name=?", new String[]{fileName});
            // Keep book_day history so Reading Calendar remains historical after a local book is removed.
        });
    }
'''
db.write_text(s[:a] + remove + s[b:], encoding="utf-8")

# ---------- Google Drive: per-book incremental + resumable primary sync ----------
s = drive.read_text(encoding="utf-8")
s = s.replace("import java.io.OutputStream;", "import java.io.OutputStream;\nimport java.io.RandomAccessFile;", 1)
s = s.replace("    static void smartBackup(Activity activity, String token, File libraryDir, File fontsDir,\n                           SharedPreferences prefs, SyncCallback callback) {",
              "    private static void legacySmartBackup(Activity activity, String token, File libraryDir, File fontsDir,\n                           SharedPreferences prefs, SyncCallback callback) {", 1)
insert_at = s.index("    private static void legacySmartBackup(")
new_sync = r'''    static void smartBackup(Activity activity, String token, File libraryDir, File fontsDir,
                           SharedPreferences prefs, SyncCallback callback) {
        if (prefs.getBoolean("google_use_legacy_zip_sync", false)) {
            legacySmartBackup(activity, token, libraryDir, fontsDir, prefs, callback); return;
        }
        new Thread(() -> {
            File stateArchive = null;
            try {
                ReaderStateDb db = ReaderStateDb.initialize(activity, prefs, libraryDir);
                if (!db.isLibraryIndexReady()) {
                    prefs.edit().putLong("sync_updated_ms", System.currentTimeMillis()).apply();
                    activity.runOnUiThread(() -> callback.onSuccess("Preparing library index for sync"));
                    return;
                }
                int uploaded=0, deleted=0;
                for (ReaderStateDb.PendingSyncRow row : db.pendingBookUploads(SyncBatchPolicy.BOOK_BATCH)) {
                    File file=row.file();
                    if(!file.isFile()) continue;
                    syncOneBook(token, db, prefs, row, file);
                    uploaded++;
                }
                for (ReaderStateDb.TombstoneRow row : db.pendingTombstones(SyncBatchPolicy.DELETE_BATCH)) {
                    deleteOneBook(token, db, row); deleted++;
                }
                int remainingBooks=db.pendingBookUploadCount();
                int remainingDeletes=db.pendingTombstoneCount();
                boolean more=SyncBatchPolicy.hasMore(remainingBooks,remainingDeletes);
                if (!more) {
                    stateArchive=buildStateBackup(activity,prefs);
                    BackupInfo state=findFileInfo(token,STATE_BACKUP_NAME);
                    if(state==null) createNamedZip(token,STATE_BACKUP_NAME,stateArchive);
                    else updateNamedFile(token,state.id,"application/zip",stateArchive);
                } else {
                    // Force GoogleAutoSync to schedule the next small batch instead of considering the giant bootstrap finished.
                    prefs.edit().putLong("sync_updated_ms",System.currentTimeMillis()).apply();
                }
                prefs.edit().putLong("google_last_backup_ms",System.currentTimeMillis()).apply();
                final int u=uploaded,d=deleted,r=remainingBooks+remainingDeletes;
                activity.runOnUiThread(() -> callback.onSuccess(r>0 ?
                        "Synced "+u+" books · "+r+" queued" : "Google Drive incremental sync is up to date"));
            } catch(Exception e) {
                String message=friendly(e); activity.runOnUiThread(() -> callback.onError(message));
            } finally { if(stateArchive!=null)stateArchive.delete(); }
        },"wow-google-incremental-sync").start();
    }

    private static void syncOneBook(String token, ReaderStateDb db, SharedPreferences prefs,
                                    ReaderStateDb.PendingSyncRow row, File file) throws Exception {
        String hash=row.hash;
        if(hash==null||hash.isEmpty()) hash=db.ensureHash(file,prefs);
        if(hash==null||hash.isEmpty()) throw new Exception("Unable to identify "+file.getName());
        String objectName=DriveObjectNamer.bookName(hash,row.format);
        BackupInfo remote=null;
        if(row.remoteId!=null&&!row.remoteId.isEmpty()) { remote=new BackupInfo(); remote.id=row.remoteId; }
        else remote=findFileInfo(token,objectName);
        String session=row.sessionUrl;
        long offset=Math.max(0L,row.offset);
        if(session==null||session.isEmpty()) {
            session=startResumable(token,objectName,file,hash,remote==null?"":remote.id);
            offset=0L; db.saveUploadCheckpoint(row.fileName,session,0L);
        }
        BackupInfo done;
        try { done=uploadResumable(token,file,session,offset,db,row.fileName); }
        catch(ResumableExpiredException expired) {
            session=startResumable(token,objectName,file,hash,remote==null?"":remote.id);
            db.saveUploadCheckpoint(row.fileName,session,0L);
            done=uploadResumable(token,file,session,0L,db,row.fileName);
        }
        String remoteId=done.id;
        if((remoteId==null||remoteId.isEmpty())&&remote!=null)remoteId=remote.id;
        db.markBookSynced(row.fileName,remoteId,done.modifiedTime);
    }

    private static void deleteOneBook(String token, ReaderStateDb db, ReaderStateDb.TombstoneRow row) throws Exception {
        String id=row.remoteId;
        if((id==null||id.isEmpty())&&row.hash!=null&&!row.hash.isEmpty()) {
            String format=row.fileName!=null&&row.fileName.toLowerCase(java.util.Locale.ROOT).endsWith(".pdf")?"pdf":"epub";
            BackupInfo info=findFileInfo(token,DriveObjectNamer.bookName(row.hash,format)); if(info!=null)id=info.id;
        }
        if(id!=null&&!id.isEmpty()) {
            HttpURLConnection c=open("https://www.googleapis.com/drive/v3/files/"+id,"DELETE",token);
            int code=c.getResponseCode(); c.disconnect();
            if(code!=404&&code!=204&&!(code>=200&&code<300)) throw new Exception("Google Drive delete error "+code);
        }
        db.markTombstoneSynced(row.hash);
    }

    private static String startResumable(String token,String name,File file,String hash,String remoteId) throws Exception {
        boolean updating=remoteId!=null&&!remoteId.isEmpty();
        String url=updating ? "https://www.googleapis.com/upload/drive/v3/files/"+remoteId+"?uploadType=resumable&fields=id,modifiedTime" :
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=id,modifiedTime";
        HttpURLConnection c=open(url,"POST",token);
        if(updating)c.setRequestProperty("X-HTTP-Method-Override","PATCH");
        c.setRequestProperty("Content-Type","application/json; charset=UTF-8");
        c.setRequestProperty("X-Upload-Content-Type", file.getName().toLowerCase(java.util.Locale.ROOT).endsWith(".pdf")?"application/pdf":"application/epub+zip");
        c.setRequestProperty("X-Upload-Content-Length",Long.toString(file.length())); c.setDoOutput(true);
        JSONObject meta=new JSONObject(); meta.put("name",name);
        if(!updating){JSONArray parents=new JSONArray();parents.put("appDataFolder");meta.put("parents",parents);}
        JSONObject props=new JSONObject();props.put("originalName",file.getName());props.put("contentHash",hash);meta.put("appProperties",props);
        byte[] body=meta.toString().getBytes(StandardCharsets.UTF_8); c.setFixedLengthStreamingMode(body.length);
        try(OutputStream out=c.getOutputStream()){out.write(body);}
        ensureSuccess(c); String location=c.getHeaderField("Location"); c.disconnect();
        if(location==null||location.trim().isEmpty())throw new Exception("Google Drive resumable session unavailable");
        return location;
    }

    private static BackupInfo uploadResumable(String token,File file,String session,long start,
                                               ReaderStateDb db,String fileName) throws Exception {
        long total=file.length(); long offset=Math.max(0L,Math.min(start,total));
        try(RandomAccessFile raf=new RandomAccessFile(file,"r")) {
            while(offset<total) {
                int len=(int)Math.min((long)SyncBatchPolicy.CHUNK_BYTES,total-offset); long end=offset+len-1;
                HttpURLConnection c=open(session,"PUT",token); c.setDoOutput(true);
                c.setRequestProperty("Content-Type",file.getName().toLowerCase(java.util.Locale.ROOT).endsWith(".pdf")?"application/pdf":"application/epub+zip");
                c.setRequestProperty("Content-Range","bytes "+offset+"-"+end+"/"+total); c.setFixedLengthStreamingMode(len);
                raf.seek(offset); byte[] buffer=new byte[64*1024]; int remain=len;
                try(OutputStream out=new BufferedOutputStream(c.getOutputStream())) {
                    while(remain>0){int n=raf.read(buffer,0,Math.min(buffer.length,remain));if(n<0)throw new Exception("Unexpected end of book file");out.write(buffer,0,n);remain-=n;}
                }
                int code=c.getResponseCode();
                if(code==404||code==410){c.disconnect();throw new ResumableExpiredException();}
                if(code==308){String range=c.getHeaderField("Range");c.disconnect();offset=parseNextOffset(range,end+1);db.saveUploadCheckpoint(fileName,session,offset);continue;}
                if(code>=200&&code<300){byte[] data;try(InputStream in=c.getInputStream()){data=readAll(in);}finally{c.disconnect();}BackupInfo info=new BackupInfo();if(data.length>0){JSONObject o=new JSONObject(new String(data,StandardCharsets.UTF_8));info.id=o.optString("id","");info.modifiedTime=o.optString("modifiedTime","");}return info;}
                InputStream err=c.getErrorStream();String detail=err==null?"":new String(readAll(err),StandardCharsets.UTF_8);c.disconnect();throw new Exception("Google Drive upload error "+code+(detail.isEmpty()?"":": "+detail));
            }
        }
        BackupInfo info=new BackupInfo();return info;
    }
    private static long parseNextOffset(String range,long fallback){
        if(range!=null){int dash=range.lastIndexOf('-');if(dash>=0)try{return Long.parseLong(range.substring(dash+1).trim())+1L;}catch(Exception ignored){}}
        return fallback;
    }
    private static final class ResumableExpiredException extends Exception {}

'''
s = s[:insert_at] + new_sync + s[insert_at:]
drive.write_text(s, encoding="utf-8")

print("Applied Phase B: durable incremental per-book Google Drive sync with resumable checkpoints")
