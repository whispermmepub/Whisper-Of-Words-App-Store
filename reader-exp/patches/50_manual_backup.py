#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve(); main=root/'app/src/main/java/com/whisper/wowreader/MainActivity.java'
if not main.is_file():raise SystemExit('MainActivity missing')

def rep(old,new):
 s=main.read_text(encoding='utf-8')
 if old not in s:raise SystemExit(f'Manual-backup anchor missing: {old[:140]!r}')
 main.write_text(s.replace(old,new,1),encoding='utf-8')

# Google connect must not enumerate 100k local files just to decide whether the library is empty.
rep('''                File[] local=libraryDir.listFiles(file->file.isFile()&&isBook(file.getName()));\n                boolean empty=local==null||local.length==0;''','''                boolean empty=stateDb==null||!stateDb.isLibraryIndexReady()?false:stateDb.totalBookCount()==0;''')

# Replace O(N²) SAF backup (findChild rescanned destination for every book) with on-disk destination index + DB-paged source.
s=main.read_text(encoding='utf-8'); a=s.index('    private void backupLibrary(Uri treeUri)'); b=s.index('    private Uri findChild(Uri treeUri,String name)',a)
new=r'''    private void backupLibrary(Uri treeUri){
        new Thread(()->{
            int count=0;File indexFile=null;android.database.sqlite.SQLiteDatabase index=null;
            try{
                if(stateDb==null||!stateDb.isLibraryIndexReady())throw new Exception("Library index is still preparing");
                indexFile=File.createTempFile("wow-saf-index-",".db",getCacheDir());
                index=android.database.sqlite.SQLiteDatabase.openOrCreateDatabase(indexFile,null);
                index.execSQL("CREATE TABLE docs(name TEXT PRIMARY KEY, document_id TEXT NOT NULL)");
                Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(treeUri,DocumentsContract.getTreeDocumentId(treeUri));
                Cursor dc=null;index.beginTransaction();
                try{
                    dc=getContentResolver().query(children,new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME},null,null,null);
                    if(dc!=null)while(dc.moveToNext()){String id=dc.getString(0),name=dc.getString(1);if(name==null||id==null)continue;android.content.ContentValues v=new android.content.ContentValues();v.put("name",name);v.put("document_id",id);index.insertWithOnConflict("docs",null,v,android.database.sqlite.SQLiteDatabase.CONFLICT_REPLACE);}
                    index.setTransactionSuccessful();
                }finally{if(dc!=null)dc.close();index.endTransaction();}
                LibraryQuerySpec all=new LibraryQuerySpec("","","all","","added");int offset=0;
                while(true){java.util.List<ReaderStateDb.LibraryBookRow> page=stateDb.pageLibraryBooks(all,offset,200);if(page.isEmpty())break;
                    for(ReaderStateDb.LibraryBookRow row:page){File file=row.asFile();if(!file.isFile())continue;Uri target=null;Cursor q=index.rawQuery("SELECT document_id FROM docs WHERE name=? LIMIT 1",new String[]{file.getName()});try{if(q.moveToFirst())target=DocumentsContract.buildDocumentUriUsingTree(treeUri,q.getString(0));}finally{q.close();}
                        if(target==null){String mime=file.getName().toLowerCase(Locale.ROOT).endsWith(".pdf")?"application/pdf":"application/epub+zip";target=DocumentsContract.createDocument(getContentResolver(),treeDocumentUri(treeUri),mime,file.getName());if(target!=null){android.content.ContentValues v=new android.content.ContentValues();v.put("name",file.getName());v.put("document_id",DocumentsContract.getDocumentId(target));index.insertWithOnConflict("docs",null,v,android.database.sqlite.SQLiteDatabase.CONFLICT_REPLACE);}}
                        if(target!=null)try(InputStream in=new FileInputStream(file);OutputStream out=getContentResolver().openOutputStream(target,"wt")){if(out!=null){copy(in,out);count++;}}
                    }
                    offset+=page.size();if(page.size()<200)break;
                }
                int n=count;runOnUiThread(()->Toast.makeText(this,"Backup complete: "+n+" books",Toast.LENGTH_LONG).show());
            }catch(Exception e){String message=e.getMessage();runOnUiThread(()->Toast.makeText(this,"Backup failed: "+message,Toast.LENGTH_LONG).show());}
            finally{try{if(index!=null)index.close();}catch(Exception ignored){}if(indexFile!=null)indexFile.delete();}
        },"wow-manual-backup").start();
    }

    private void restoreLibrary(Uri treeUri){
        new Thread(()->{int count=0;Cursor c=null;try{if(stateDb==null)stateDb=ReaderStateDb.initialize(this,prefs,libraryDir);Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(treeUri,DocumentsContract.getTreeDocumentId(treeUri));c=getContentResolver().query(children,new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME},null,null,null);if(c!=null)while(c.moveToNext()){String id=c.getString(0),name=c.getString(1);if(!isBook(name))continue;Uri doc=DocumentsContract.buildDocumentUriUsingTree(treeUri,id);File out=new File(libraryDir,name.replaceAll("[\\\\/:*?\"<>|]","_"));try(InputStream in=getContentResolver().openInputStream(doc);OutputStream os=new FileOutputStream(out)){if(in!=null){copy(in,os);long now=System.currentTimeMillis();stateDb.upsertImportedBook(out,"",stripExtension(out.getName()),"",now);count++;}}}long now=System.currentTimeMillis();prefs.edit().putLong("library_files_updated_ms",now).putLong("sync_updated_ms",now).apply();int n=count;runOnUiThread(()->{refreshLibrary();maybeAutoGoogleSync();Toast.makeText(this,"Restored: "+n+" books",Toast.LENGTH_LONG).show();});}catch(Exception e){String message=e.getMessage();runOnUiThread(()->Toast.makeText(this,"Restore failed: "+message,Toast.LENGTH_LONG).show());}finally{if(c!=null)c.close();}},"wow-manual-restore").start();
    }
'''
s=s[:a]+new+s[b:];main.write_text(s,encoding='utf-8')
print('Applied 100k-safe manual backup/restore: DB paging + one-pass SAF destination index')
