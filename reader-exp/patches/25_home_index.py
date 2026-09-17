#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve(); java=root/'app/src/main/java/com/whisper/wowreader'
db=java/'ReaderStateDb.java'; main=java/'MainActivity.java'; ann=java/'ReaderAnnotationStore.java'

def rep(path,old,new):
    s=path.read_text(encoding='utf-8')
    if old not in s: raise SystemExit(f'Home-index anchor missing in {path.name}: {old[:100]!r}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')

rep(db,'private static final int DB_VERSION = 3;','private static final int DB_VERSION = 4;')
rep(db,'private static final String META_V2_MIGRATED = "library_metadata_migrated_v2";',
       'private static final String META_V2_MIGRATED = "library_metadata_migrated_v2";\n    private static final String META_HOME_INDEXED = "home_indexed_v4";')
rep(db,
'''                "title TEXT NOT NULL DEFAULT '', author TEXT NOT NULL DEFAULT ''," +\n                "file_size INTEGER NOT NULL DEFAULT 0,''',
'''                "title TEXT NOT NULL DEFAULT '', author TEXT NOT NULL DEFAULT '', annotation_count INTEGER NOT NULL DEFAULT 0," +\n                "file_size INTEGER NOT NULL DEFAULT 0,''')
rep(db,
'''        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_progress ON books(progress)");''',
'''        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_progress ON books(progress)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_annotations ON books(annotation_count,last_opened_at DESC)");''')
rep(db,
'''        }\n    }\n\n    boolean isLegacyMigrated() {''',
'''        }\n        if (oldVersion < 4) {\n            try { db.execSQL("ALTER TABLE books ADD COLUMN annotation_count INTEGER NOT NULL DEFAULT 0"); } catch (Exception ignored) {}\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_annotations ON books(annotation_count,last_opened_at DESC)");\n        }\n    }\n\n    boolean isLegacyMigrated() {''')
rep(db,
'''        db.migrateV2Async(prefs);\n        return db;''',
'''        db.migrateV2Async(prefs);\n        db.migrateHomeIndexAsync(prefs);\n        return db;''')

anchor='''    static final class LibraryBookRow {'''
insert=r'''    private void migrateHomeIndexAsync(SharedPreferences prefs) {
        if (prefs == null) return;
        WRITER.execute(() -> {
            Cursor marker=null;
            try { marker=getReadableDatabase().rawQuery("SELECT v FROM meta WHERE k=?",new String[]{META_HOME_INDEXED}); if(marker.moveToFirst()&&"1".equals(marker.getString(0)))return; }
            catch(Exception ignored) {} finally { if(marker!=null)marker.close(); }
            if(!isLibraryIndexReady())return;
            SQLiteDatabase sql=getWritableDatabase(); sql.beginTransaction(); Cursor c=null;
            try {
                c=sql.rawQuery("SELECT file_name FROM books",null);
                while(c.moveToNext()) {
                    String name=c.getString(0); ContentValues v=new ContentValues();
                    v.put("annotation_count",ReaderAnnotationStore.count(prefs,name));
                    sql.update("books",v,"file_name=?",new String[]{name});
                }
                ContentValues m=new ContentValues();m.put("k",META_HOME_INDEXED);m.put("v","1");
                sql.insertWithOnConflict("meta",null,m,SQLiteDatabase.CONFLICT_REPLACE);sql.setTransactionSuccessful();
            } catch(Exception ignored) {} finally { if(c!=null)c.close();sql.endTransaction(); }
        });
    }

'''
rep(db,anchor,insert+anchor)

# Add compact indexed Home/Notes/Authors APIs before hash update.
anchor='''    private void updateBookHash(File file, String hash) {'''
api=r'''    List<LibraryBookRow> recentBooks(int limit, boolean readingOnly) {
        int n=Math.max(1,Math.min(20,limit));List<LibraryBookRow> out=new ArrayList<>();Cursor c=null;
        try {String where=readingOnly?"progress>0 AND progress<100":"1=1";c=getReadableDatabase().rawQuery(
                "SELECT file_name,file_path,title,author,progress,added_at,last_opened_at FROM books WHERE "+where+" ORDER BY last_opened_at DESC,added_at DESC LIMIT "+n,null);
            while(c.moveToNext())out.add(new LibraryBookRow(c));}catch(Exception ignored){}finally{if(c!=null)c.close();}return out;
    }
    int totalAnnotationCount(){return (int)Math.min(Integer.MAX_VALUE,scalarLong("SELECT COALESCE(SUM(annotation_count),0) FROM books",null));}
    void updateAnnotationCount(String fileName,int count){if(fileName==null)return;ContentValues v=new ContentValues();v.put("annotation_count",Math.max(0,count));getWritableDatabase().update("books",v,"file_name=?",new String[]{fileName});}
    List<LibraryBookRow> annotatedBooks(int limit){int n=Math.max(1,Math.min(500,limit));List<LibraryBookRow> out=new ArrayList<>();Cursor c=null;try{c=getReadableDatabase().rawQuery(
            "SELECT file_name,file_path,title,author,progress,added_at,last_opened_at FROM books WHERE annotation_count>0 ORDER BY last_opened_at DESC,updated_at DESC LIMIT "+n,null);while(c.moveToNext())out.add(new LibraryBookRow(c));}catch(Exception ignored){}finally{if(c!=null)c.close();}return out;}
    static final class AuthorCount{final String author;final int count;AuthorCount(String a,int c){author=a;count=c;}}
    List<AuthorCount> authors(int limit){int n=Math.max(1,Math.min(1000,limit));List<AuthorCount> out=new ArrayList<>();Cursor c=null;try{c=getReadableDatabase().rawQuery(
            "SELECT author,COUNT(*) FROM books WHERE author<>'' GROUP BY author ORDER BY author COLLATE NOCASE ASC LIMIT "+n,null);while(c.moveToNext())out.add(new AuthorCount(c.getString(0),c.getInt(1)));}catch(Exception ignored){}finally{if(c!=null)c.close();}return out;}
    int totalAuthorCount(){return (int)Math.min(Integer.MAX_VALUE,scalarLong("SELECT COUNT(DISTINCT author) FROM books WHERE author<>''",null));}
    int totalBookCount(){return (int)Math.min(Integer.MAX_VALUE,scalarLong("SELECT COUNT(*) FROM books",null));}

'''
rep(db,anchor,api+anchor)

# Annotation writes keep the indexed count current.
rep(ann,
'''        prefs.edit()\n                .putString(key(bookName), arr.toString())\n                .putLong("sync_updated_ms", System.currentTimeMillis())\n                .apply();''',
'''        prefs.edit()\n                .putString(key(bookName), arr.toString())\n                .putLong("sync_updated_ms", System.currentTimeMillis())\n                .apply();\n        ReaderStateDb db = ReaderStateDb.peek();\n        if (db != null) db.updateAnnotationCount(bookName, items.size());''')

# Continue Reading: query max 8 indexed rows instead of scanning every file.
rep(main,
'''        File[] books = libraryDir.listFiles(file -> file.isFile() && isBook(file.getName()));\n        if (books == null) books = new File[0];\n        java.util.Arrays.sort(books, (a, b) -> {\n            long ao = openedTime(a), bo = openedTime(b);\n            if (ao != bo) return Long.compare(bo, ao);\n            return Long.compare(addedTime(b), addedTime(a));\n        });\n        java.util.List<File> preferred = new java.util.ArrayList<>();\n        for (File f : books) {\n            int p = ReadingProgressStore.get(prefs, f.getName());\n            if (p > 0 && p < 100) preferred.add(f);\n        }\n        if (preferred.isEmpty()) {\n            for (File f : books) preferred.add(f);\n        }''',
'''        java.util.List<File> preferred = new java.util.ArrayList<>();\n        if (stateDb != null && stateDb.isLibraryIndexReady()) {\n            java.util.List<ReaderStateDb.LibraryBookRow> rows = stateDb.recentBooks(8, true);\n            if (rows.isEmpty()) rows = stateDb.recentBooks(8, false);\n            for (ReaderStateDb.LibraryBookRow row : rows) preferred.add(row.asFile());\n        }''')

rep(main,
'''        int annotationCount = 0;\n        File[] books = libraryDir.listFiles(file -> file.isFile() && isBook(file.getName()));\n        if (books != null) for (File f : books) annotationCount += ReaderAnnotationStore.count(prefs, f.getName());''',
'''        int annotationCount = stateDb != null && stateDb.isLibraryIndexReady() ? stateDb.totalAnnotationCount() : 0;''')

rep(main,
'''    private void updateNotesHubSummary() {\n        if (notesSummaryView == null || prefs == null || libraryDir == null) return;\n        File[] books = libraryDir.listFiles(file -> file.isFile() && isBook(file.getName()));\n        int itemCount = 0;\n        if (books != null) for (File book : books) itemCount += ReaderAnnotationStore.count(prefs, book.getName());\n        notesSummaryView.setText(String.valueOf(itemCount));\n    }''',
'''    private void updateNotesHubSummary() {\n        if (notesSummaryView == null) return;\n        int itemCount = stateDb != null && stateDb.isLibraryIndexReady() ? stateDb.totalAnnotationCount() : 0;\n        notesSummaryView.setText(String.valueOf(itemCount));\n    }''')

# Notes hub: bounded latest annotated books. No 100k JSON scan/UI inflation.
s=main.read_text(encoding='utf-8'); a=s.index('    private void showNotesHighlightsHub() {'); dialog=s.index('        android.app.Dialog dialog = new android.app.Dialog(this);',a)
prefix=r'''    private void showNotesHighlightsHub() {
        java.util.List<File> annotatedBooks = new java.util.ArrayList<>();
        if (stateDb != null && stateDb.isLibraryIndexReady()) {
            for (ReaderStateDb.LibraryBookRow row : stateDb.annotatedBooks(200)) annotatedBooks.add(row.asFile());
        }

'''
s=s[:a]+prefix+s[dialog:];main.write_text(s,encoding='utf-8')

# Authors dialog: SQL GROUP BY, bounded UI rows.
s=main.read_text(encoding='utf-8'); a=s.index('    private void showAuthorsDialog() {'); dialog=s.index('        android.app.Dialog dialog = new android.app.Dialog(this);',a)
prefix=r'''    private void showAuthorsDialog() {
        java.util.Map<String, Integer> counts = new java.util.HashMap<>();
        java.util.List<String> authors = new java.util.ArrayList<>();
        if (stateDb != null && stateDb.isLibraryIndexReady()) {
            for (ReaderStateDb.AuthorCount row : stateDb.authors(500)) { authors.add(row.author); counts.put(row.author,row.count); }
        }
        final int totalBooks = stateDb == null ? 0 : stateDb.totalBookCount();
        final int totalAuthors = stateDb == null ? authors.size() : stateDb.totalAuthorCount();

'''
s=s[:a]+prefix+s[dialog:]
s=s.replace('LinearLayout sheet = premiumSheet("Authors", authors.isEmpty() ? "No author metadata yet" : authors.size() + " authors", dialog);',
            'LinearLayout sheet = premiumSheet("Authors", authors.isEmpty() ? "No author metadata yet" : totalAuthors + " authors", dialog);',1)
s=s.replace('        final int totalBooks = files.length;\n','',1)
s=s.replace('        warmSortMetadataIfNeeded(files);\n','',1)
main.write_text(s,encoding='utf-8')

print('Applied Phase C: indexed Home/Notes/Authors paths for 100k libraries')
