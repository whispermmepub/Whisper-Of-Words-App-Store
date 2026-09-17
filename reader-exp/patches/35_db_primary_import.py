#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve(); java=root/'app/src/main/java/com/whisper/wowreader'; db=java/'ReaderStateDb.java'; main=java/'MainActivity.java'

def rep(path,old,new):
    s=path.read_text(encoding='utf-8')
    if old not in s:raise SystemExit(f'DB-import anchor missing in {path.name}: {old[:120]!r}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')

anchor='''    private void updateBookHash(File file, String hash) {'''
api=r'''    void upsertImportedBook(File file,String hash,String title,String author,long addedAt) {
        if(file==null||!file.isFile())return;
        SQLiteDatabase sql=getWritableDatabase();ContentValues v=new ContentValues();String name=file.getName();
        v.put("file_name",name);v.put("file_path",file.getAbsolutePath());v.put("format",name.toLowerCase(Locale.ROOT).endsWith(".pdf")?"pdf":"epub");
        v.put("title",title==null||title.trim().isEmpty()?stripExtension(name):title.trim());v.put("author",author==null?"":author.trim());
        if(hash!=null&&!hash.isEmpty())v.put("content_hash",hash);v.put("file_size",file.length());v.put("modified_at",file.lastModified());v.put("added_at",Math.max(0L,addedAt));
        v.put("sync_dirty",1);v.put("updated_at",System.currentTimeMillis());
        sql.insertWithOnConflict("books",null,v,SQLiteDatabase.CONFLICT_REPLACE);
    }

'''
rep(db,anchor,api+anchor)
rep(main,
'''                long now=System.currentTimeMillis();\n                prefs.edit()\n                        .putLong("added_at_"+out.getName(),now)\n                        .putString("library_title_"+out.getName(),displayTitle)\n                        .putString("library_author_"+out.getName(),displayAuthor)\n                        .putBoolean("library_owned_"+out.getName(),true)\n                        .putString("content_hash_"+out.getName(),hash)\n                        .putString("content_hash_sig_"+out.getName(),out.length()+":"+out.lastModified())\n                        .putLong("library_files_updated_ms",now)\n                        .putLong("sync_updated_ms",now)\n                        .apply();\n                stateDb.upsertBook(out,hash,prefs);''',
'''                long now=System.currentTimeMillis();\n                // 100k-safe path: one indexed DB row, not six SharedPreferences keys per imported book.\n                stateDb.upsertImportedBook(out,hash,displayTitle,displayAuthor,now);\n                prefs.edit().putLong("library_files_updated_ms",now).putLong("sync_updated_ms",now).apply();''')
print('Applied DB-primary import: new 100k libraries do not create per-book metadata/hash preference keys')
