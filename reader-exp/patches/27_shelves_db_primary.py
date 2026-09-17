#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve(); java=root/'app/src/main/java/com/whisper/wowreader'; db=java/'ReaderStateDb.java'; shelf=java/'LibraryShelfStore.java'

def rep(path,old,new):
    s=path.read_text(encoding='utf-8')
    if old not in s:raise SystemExit(f'Shelf patch anchor missing in {path.name}: {old[:120]!r}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')

anchor='''    private void updateBookHash(File file, String hash) {'''
api=r'''    List<String> shelfNames(){List<String> out=new ArrayList<>();Cursor c=null;try{c=getReadableDatabase().rawQuery("SELECT name FROM shelves ORDER BY name COLLATE NOCASE ASC",null);while(c.moveToNext())out.add(c.getString(0));}catch(Exception ignored){}finally{if(c!=null)c.close();}return out;}
    boolean createShelfRow(String name){if(name==null||name.trim().isEmpty())return false;ContentValues v=new ContentValues();v.put("name",name.trim());v.put("updated_at",System.currentTimeMillis());return getWritableDatabase().insertWithOnConflict("shelves",null,v,SQLiteDatabase.CONFLICT_IGNORE)!=-1;}
    boolean renameShelfRow(String oldName,String newName){if(oldName==null||newName==null||newName.trim().isEmpty())return false;SQLiteDatabase sql=getWritableDatabase();sql.beginTransaction();try{ContentValues nv=new ContentValues();nv.put("name",newName.trim());nv.put("updated_at",System.currentTimeMillis());if(sql.insertWithOnConflict("shelves",null,nv,SQLiteDatabase.CONFLICT_IGNORE)==-1)return false;sql.execSQL("INSERT OR IGNORE INTO shelf_books(shelf_name,file_name,added_at) SELECT ?,file_name,added_at FROM shelf_books WHERE shelf_name=?",new Object[]{newName.trim(),oldName});sql.delete("shelf_books","shelf_name=?",new String[]{oldName});sql.delete("shelves","name=?",new String[]{oldName});sql.setTransactionSuccessful();return true;}catch(Exception e){return false;}finally{sql.endTransaction();}}
    boolean deleteShelfRow(String name){if(name==null)return false;SQLiteDatabase sql=getWritableDatabase();sql.beginTransaction();try{sql.delete("shelf_books","shelf_name=?",new String[]{name});int n=sql.delete("shelves","name=?",new String[]{name});sql.setTransactionSuccessful();return n>0;}finally{sql.endTransaction();}}
    boolean shelfContains(String shelf,String fileName){return shelf!=null&&fileName!=null&&scalarLong("SELECT COUNT(*) FROM shelf_books WHERE shelf_name=? AND file_name=?",new String[]{shelf,fileName})>0;}
    int shelfBookCount(String shelf){return shelf==null?0:(int)Math.min(Integer.MAX_VALUE,scalarLong("SELECT COUNT(*) FROM shelf_books WHERE shelf_name=?",new String[]{shelf}));}
    void setShelfMembershipRow(String shelf,String fileName,boolean included){if(shelf==null||fileName==null)return;createShelfRow(shelf);SQLiteDatabase sql=getWritableDatabase();if(included){ContentValues v=new ContentValues();v.put("shelf_name",shelf);v.put("file_name",fileName);v.put("added_at",System.currentTimeMillis());sql.insertWithOnConflict("shelf_books",null,v,SQLiteDatabase.CONFLICT_IGNORE);}else sql.delete("shelf_books","shelf_name=? AND file_name=?",new String[]{shelf,fileName});}
    void removeBookFromShelves(String fileName){if(fileName!=null)getWritableDatabase().delete("shelf_books","file_name=?",new String[]{fileName});}

'''
rep(db,anchor,api+anchor)

# Replace whole store with DB-primary facade + untouched JSON fallback for migration/early startup.
s=shelf.read_text(encoding='utf-8')
# inject helper after KEY
s=s.replace('''    private static final String KEY = "library_shelves_json";''','''    private static final String KEY = "library_shelves_json";\n    private static ReaderStateDb db(){ReaderStateDb d=ReaderStateDb.peek();return d!=null&&d.isLibraryIndexReady()?d:null;}''',1)
# method front guards
s=s.replace('''        List<String> result = new ArrayList<>();\n        if (prefs == null) return result;''','''        ReaderStateDb d=db(); if(d!=null)return d.shelfNames();\n        List<String> result = new ArrayList<>();\n        if (prefs == null) return result;''',1)
s=s.replace('''        if (prefs == null) return false;\n        String name = cleanName(shelfName);''','''        if (prefs == null) return false;\n        String name = cleanName(shelfName);\n        ReaderStateDb d=db();if(d!=null)return d.createShelfRow(name);''',1)
s=s.replace('''        if (prefs == null) return false;\n        String oldName = cleanName(oldShelfName);''','''        if (prefs == null) return false;\n        String oldName = cleanName(oldShelfName);''',1)
s=s.replace('''        String newName = cleanName(newShelfName);\n        if (oldName.isEmpty() || newName.isEmpty()) return false;''','''        String newName = cleanName(newShelfName);\n        if (oldName.isEmpty() || newName.isEmpty()) return false;\n        ReaderStateDb d=db();if(d!=null)return d.renameShelfRow(oldName,newName);''',1)
s=s.replace('''        if (prefs == null) return false;\n        String name = cleanName(shelfName);\n        if (name.isEmpty()) return false;''','''        if (prefs == null) return false;\n        String name = cleanName(shelfName);\n        if (name.isEmpty()) return false;\n        ReaderStateDb d=db();if(d!=null)return d.deleteShelfRow(name);''',1)
# contains unique anchor
s=s.replace('''        if (prefs == null || bookName == null) return false;\n        String name = cleanName(shelfName);\n        if (name.isEmpty()) return false;''','''        if (prefs == null || bookName == null) return false;\n        String name = cleanName(shelfName);\n        if (name.isEmpty()) return false;\n        ReaderStateDb d=db();if(d!=null)return d.shelfContains(name,bookName);''',1)
s=s.replace('''        if (prefs == null || bookName == null || bookName.trim().isEmpty()) return;\n        String name = cleanName(shelfName);\n        if (name.isEmpty()) return;''','''        if (prefs == null || bookName == null || bookName.trim().isEmpty()) return;\n        String name = cleanName(shelfName);\n        if (name.isEmpty()) return;\n        ReaderStateDb d=db();if(d!=null){d.setShelfMembershipRow(name,bookName,included);prefs.edit().putLong("sync_updated_ms",System.currentTimeMillis()).apply();return;}''',1)
s=s.replace('''        if (prefs == null) return 0;\n        JSONObject root = object(prefs.getString(KEY, "{}"));''','''        if (prefs == null) return 0;\n        ReaderStateDb d=db();if(d!=null)return d.shelfBookCount(cleanName(shelfName));\n        JSONObject root = object(prefs.getString(KEY, "{}"));''',1)
s=s.replace('''        if (prefs == null || bookName == null) return;\n        try {''','''        if (prefs == null || bookName == null) return;\n        ReaderStateDb d=db();if(d!=null){d.removeBookFromShelves(bookName);return;}\n        try {''',1)
shelf.write_text(s,encoding='utf-8')
print('Applied DB-primary shelves: no giant membership JSON rewrite at 100k scale')
