#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
java = root / "app/src/main/java/com/whisper/wowreader"
main = java / "MainActivity.java"
db = java / "ReaderStateDb.java"
if not main.is_file() or not db.is_file():
    raise SystemExit(f"WoW Reader source not found at {root}")

def replace_once(path: Path, old: str, new: str):
    s = path.read_text(encoding="utf-8")
    if old not in s:
        raise SystemExit(f"Expected patch anchor missing in {path}: {old[:100]!r}")
    path.write_text(s.replace(old, new, 1), encoding="utf-8")

# ---------- Pure Java query spec (unit-testable without Android) ----------
(java / "LibraryQuerySpec.java").write_text(r'''package com.whisper.wowreader;

import java.util.ArrayList;
import java.util.List;

/** Immutable, SQL-backed library query. Keeps 100k+ filtering/sorting out of Java heap. */
final class LibraryQuerySpec {
    final String search;
    final String author;
    final String status;
    final String shelf;
    final String sort;

    LibraryQuerySpec(String search, String author, String status, String shelf, String sort) {
        this.search = clean(search);
        this.author = clean(author);
        this.status = clean(status);
        this.shelf = clean(shelf);
        this.sort = clean(sort);
    }

    String whereSql() {
        List<String> parts = new ArrayList<>();
        parts.add("1=1");
        if (!search.isEmpty()) parts.add("(LOWER(title) LIKE ? OR LOWER(author) LIKE ? OR LOWER(file_name) LIKE ?)");
        if (!author.isEmpty()) parts.add("author=?");
        if ("reading".equals(status)) parts.add("progress>0 AND progress<100");
        else if ("unread".equals(status)) parts.add("progress=0");
        else if ("finished".equals(status)) parts.add("progress>=100");
        if (!shelf.isEmpty()) parts.add("EXISTS(SELECT 1 FROM shelf_books sb WHERE sb.file_name=books.file_name AND sb.shelf_name=?)");
        return join(parts, " AND ");
    }

    String[] args() {
        List<String> out = new ArrayList<>();
        if (!search.isEmpty()) {
            String q = "%" + search.toLowerCase(java.util.Locale.ROOT) + "%";
            out.add(q); out.add(q); out.add(q);
        }
        if (!author.isEmpty()) out.add(author);
        if (!shelf.isEmpty()) out.add(shelf);
        return out.toArray(new String[0]);
    }

    String orderSql() {
        if ("title_asc".equals(sort)) return "title COLLATE NOCASE ASC, file_name COLLATE NOCASE ASC";
        if ("title_desc".equals(sort)) return "title COLLATE NOCASE DESC, file_name COLLATE NOCASE DESC";
        if ("opened".equals(sort)) return "last_opened_at DESC, title COLLATE NOCASE ASC";
        return "added_at DESC, title COLLATE NOCASE ASC";
    }

    private static String clean(String s) { return s == null ? "" : s.trim(); }
    private static String join(List<String> values, String sep) {
        StringBuilder b = new StringBuilder();
        for (String v : values) { if (b.length() > 0) b.append(sep); b.append(v); }
        return b.toString();
    }
}
''', encoding="utf-8")

# ---------- DB v2: indexed metadata + shelves + page queries ----------
replace_once(db,
'''    private static final int DB_VERSION = 1;\n    private static final String META_LEGACY_MIGRATED = "legacy_migrated_v1";''',
'''    private static final int DB_VERSION = 2;\n    private static final String META_LEGACY_MIGRATED = "legacy_migrated_v1";\n    private static final String META_V2_MIGRATED = "library_metadata_migrated_v2";''')

replace_once(db,
'''        ReaderStateDb db = get(context);\n        if (!db.isLegacyMigrated()) db.migrateLegacyAsync(prefs, libraryDir);\n        return db;''',
'''        ReaderStateDb db = get(context);\n        if (!db.isLegacyMigrated()) db.migrateLegacyAsync(prefs, libraryDir);\n        db.migrateV2Async(prefs);\n        return db;''')

old_create = '''        db.execSQL("CREATE TABLE IF NOT EXISTS books (" +\n                "file_name TEXT PRIMARY KEY, content_hash TEXT UNIQUE, file_path TEXT, format TEXT," +\n                "file_size INTEGER NOT NULL DEFAULT 0, modified_at INTEGER NOT NULL DEFAULT 0," +\n                "added_at INTEGER NOT NULL DEFAULT 0, last_opened_at INTEGER NOT NULL DEFAULT 0," +\n                "progress INTEGER NOT NULL DEFAULT 0, finished_at INTEGER NOT NULL DEFAULT 0," +\n                "epub_spine INTEGER NOT NULL DEFAULT 0, epub_offset INTEGER NOT NULL DEFAULT 0," +\n                "pdf_page INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL DEFAULT 0)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_hash ON books(content_hash)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_last_opened ON books(last_opened_at DESC)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_finished ON books(finished_at DESC)");'''
new_create = '''        db.execSQL("CREATE TABLE IF NOT EXISTS books (" +\n                "file_name TEXT PRIMARY KEY, content_hash TEXT UNIQUE, file_path TEXT, format TEXT," +\n                "title TEXT NOT NULL DEFAULT '', author TEXT NOT NULL DEFAULT ''," +\n                "file_size INTEGER NOT NULL DEFAULT 0, modified_at INTEGER NOT NULL DEFAULT 0," +\n                "added_at INTEGER NOT NULL DEFAULT 0, last_opened_at INTEGER NOT NULL DEFAULT 0," +\n                "progress INTEGER NOT NULL DEFAULT 0, finished_at INTEGER NOT NULL DEFAULT 0," +\n                "epub_spine INTEGER NOT NULL DEFAULT 0, epub_offset INTEGER NOT NULL DEFAULT 0," +\n                "pdf_page INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL DEFAULT 0)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_hash ON books(content_hash)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_last_opened ON books(last_opened_at DESC)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_added ON books(added_at DESC)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title COLLATE NOCASE)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_author ON books(author COLLATE NOCASE)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_progress ON books(progress)");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_finished ON books(finished_at DESC)");\n        db.execSQL("CREATE TABLE IF NOT EXISTS shelves (name TEXT PRIMARY KEY, updated_at INTEGER NOT NULL DEFAULT 0)");\n        db.execSQL("CREATE TABLE IF NOT EXISTS shelf_books (shelf_name TEXT NOT NULL, file_name TEXT NOT NULL, added_at INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(shelf_name,file_name))");\n        db.execSQL("CREATE INDEX IF NOT EXISTS idx_shelf_books_file ON shelf_books(file_name)");'''
replace_once(db, old_create, new_create)

replace_once(db,
'''    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {}''',
'''    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {\n        if (oldVersion < 2) {\n            try { db.execSQL("ALTER TABLE books ADD COLUMN title TEXT NOT NULL DEFAULT ''"); } catch (Exception ignored) {}\n            try { db.execSQL("ALTER TABLE books ADD COLUMN author TEXT NOT NULL DEFAULT ''"); } catch (Exception ignored) {}\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_added ON books(added_at DESC)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title COLLATE NOCASE)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_author ON books(author COLLATE NOCASE)");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_books_progress ON books(progress)");\n            db.execSQL("CREATE TABLE IF NOT EXISTS shelves (name TEXT PRIMARY KEY, updated_at INTEGER NOT NULL DEFAULT 0)");\n            db.execSQL("CREATE TABLE IF NOT EXISTS shelf_books (shelf_name TEXT NOT NULL, file_name TEXT NOT NULL, added_at INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(shelf_name,file_name))");\n            db.execSQL("CREATE INDEX IF NOT EXISTS idx_shelf_books_file ON shelf_books(file_name)");\n        }\n    }''')

# Add metadata values to every future upsert.
replace_once(db,
'''        if (prefs != null) {\n            v.put("added_at", prefs.getLong("added_at_" + name, 0L));''',
'''        if (prefs != null) {\n            String fallbackTitle = stripExtension(name);\n            String title = prefs.getString("library_title_" + name, fallbackTitle);\n            String author = prefs.getString("library_author_" + name, "");\n            v.put("title", title == null || title.trim().isEmpty() ? fallbackTitle : title.trim());\n            v.put("author", author == null ? "" : author.trim());\n            v.put("added_at", prefs.getLong("added_at_" + name, 0L));''')

anchor = '''    private void updateBookHash(File file, String hash) {'''
insert = r'''    boolean isLibraryIndexReady() {
        if (!isLegacyMigrated()) return false;
        Cursor c = null;
        try {
            c = getReadableDatabase().rawQuery("SELECT v FROM meta WHERE k=?", new String[]{META_V2_MIGRATED});
            return c.moveToFirst() && "1".equals(c.getString(0));
        } catch (Exception ignored) { return false; }
        finally { if (c != null) c.close(); }
    }

    private void migrateV2Async(SharedPreferences prefs) {
        if (prefs == null || isLibraryIndexReady()) return;
        WRITER.execute(() -> {
            if (!isLegacyMigrated() || isLibraryIndexReady()) return;
            SQLiteDatabase sql = getWritableDatabase();
            sql.beginTransaction();
            Cursor c = null;
            try {
                c = sql.rawQuery("SELECT file_name FROM books", null);
                while (c.moveToNext()) {
                    String name = c.getString(0);
                    String fallback = stripExtension(name);
                    String title = prefs.getString("library_title_" + name, fallback);
                    String author = prefs.getString("library_author_" + name, "");
                    ContentValues v = new ContentValues();
                    v.put("title", title == null || title.trim().isEmpty() ? fallback : title.trim());
                    v.put("author", author == null ? "" : author.trim());
                    sql.update("books", v, "file_name=?", new String[]{name});
                }
                if (c != null) { c.close(); c = null; }
                JSONObject shelves = object(prefs.getString("library_shelves_json", "{}"));
                Iterator<String> keys = shelves.keys();
                while (keys.hasNext()) {
                    String shelf = keys.next();
                    ContentValues sv = new ContentValues(); sv.put("name", shelf); sv.put("updated_at", System.currentTimeMillis());
                    sql.insertWithOnConflict("shelves", null, sv, SQLiteDatabase.CONFLICT_IGNORE);
                    org.json.JSONArray books = shelves.optJSONArray(shelf);
                    if (books == null) continue;
                    for (int i = 0; i < books.length(); i++) {
                        String fileName = books.optString(i, ""); if (fileName.isEmpty()) continue;
                        ContentValues bv = new ContentValues(); bv.put("shelf_name", shelf); bv.put("file_name", fileName); bv.put("added_at", 0L);
                        sql.insertWithOnConflict("shelf_books", null, bv, SQLiteDatabase.CONFLICT_IGNORE);
                    }
                }
                ContentValues marker = new ContentValues(); marker.put("k", META_V2_MIGRATED); marker.put("v", "1");
                sql.insertWithOnConflict("meta", null, marker, SQLiteDatabase.CONFLICT_REPLACE);
                sql.setTransactionSuccessful();
            } catch (Exception ignored) {
            } finally {
                if (c != null) c.close();
                sql.endTransaction();
            }
        });
    }

    static final class LibraryBookRow {
        final String fileName, filePath, title, author;
        final int progress;
        final long addedAt, lastOpenedAt;
        LibraryBookRow(Cursor c) {
            fileName = c.getString(0); filePath = c.getString(1); title = c.getString(2); author = c.getString(3);
            progress = c.getInt(4); addedAt = c.getLong(5); lastOpenedAt = c.getLong(6);
        }
        File asFile() { return new File(filePath); }
    }

    int countLibraryBooks(LibraryQuerySpec spec) {
        if (spec == null) spec = new LibraryQuerySpec("", "", "all", "", "added");
        return (int)Math.min(Integer.MAX_VALUE, scalarLong("SELECT COUNT(*) FROM books WHERE " + spec.whereSql(), spec.args()));
    }

    List<LibraryBookRow> pageLibraryBooks(LibraryQuerySpec spec, int offset, int limit) {
        if (spec == null) spec = new LibraryQuerySpec("", "", "all", "", "added");
        int o = Math.max(0, offset), n = Math.max(1, Math.min(250, limit));
        List<LibraryBookRow> out = new ArrayList<>(); Cursor c = null;
        try {
            String sql = "SELECT file_name,file_path,title,author,progress,added_at,last_opened_at FROM books WHERE " +
                    spec.whereSql() + " ORDER BY " + spec.orderSql() + " LIMIT " + n + " OFFSET " + o;
            c = getReadableDatabase().rawQuery(sql, spec.args());
            while (c.moveToNext()) out.add(new LibraryBookRow(c));
        } catch (Exception ignored) {} finally { if (c != null) c.close(); }
        return out;
    }

    String indexedTitle(String fileName, String fallback) {
        String v = scalarString("SELECT title FROM books WHERE file_name=?", new String[]{fileName});
        return v.isEmpty() ? fallback : v;
    }
    String indexedAuthor(String fileName) { return scalarString("SELECT author FROM books WHERE file_name=?", new String[]{fileName}); }

'''
replace_once(db, anchor, insert + anchor)

# Add stripExtension helper if absent in DB.
replace_once(db,
'''    private static boolean isBook(String name) {''',
'''    private static String stripExtension(String name) {\n        int dot = name == null ? -1 : name.lastIndexOf('.');\n        return dot > 0 ? name.substring(0, dot) : (name == null ? "Book" : name);\n    }\n    private static boolean isBook(String name) {''')

# ---------- MainActivity: DB source + bounded async page cache ----------
replace_once(main,
'''    private LibraryAdapter libraryAdapter;\n    private final List<File> visibleBooks = new ArrayList<>();''',
'''    private LibraryAdapter libraryAdapter;\n    private ReaderStateDb stateDb;\n    private volatile int libraryResultCount = 0;\n    private final java.util.concurrent.ExecutorService libraryQueryExecutor = java.util.concurrent.Executors.newSingleThreadExecutor(r -> {\n        Thread t = new Thread(r, "wow-library-query"); t.setDaemon(true); return t;\n    });''')

replace_once(main,
'''        prefs = getSharedPreferences("wow_reader", MODE_PRIVATE);\n        ReadingProgressStore.init(this, prefs);''',
'''        prefs = getSharedPreferences("wow_reader", MODE_PRIVATE);\n        stateDb = ReaderStateDb.initialize(this, prefs, libraryDir);\n        ReadingProgressStore.init(this, prefs);''')

start = main.read_text(encoding="utf-8")
old_refresh_start = start.index("    private void refreshLibrary() {")
old_sort_start = start.index("    private void sortLibraryFiles(File[] files) {", old_refresh_start)
new_refresh = r'''    private void refreshLibrary() {
        if (stateDb == null) stateDb = ReaderStateDb.initialize(this, prefs, libraryDir);
        if (!stateDb.isLibraryIndexReady()) {
            libraryResultCount = 0;
            if (libraryAdapter != null) libraryAdapter.resetPaged(new LibraryQuerySpec("", "", "all", "", sortMode), 0);
            if (countView != null) countView.setText("Indexing library…");
            if (libraryRecycler != null) libraryRecycler.postDelayed(this::refreshLibrary, 550L);
            return;
        }
        LibraryQuerySpec spec = new LibraryQuerySpec(searchQuery, authorFilter, libraryStatusFilter, shelfFilter, sortMode);
        final int total = stateDb.countLibraryBooks(spec);
        libraryResultCount = total;
        if (libraryAdapter != null) libraryAdapter.resetPaged(spec, total);
        if (countView != null) {
            String suffix = total == 1 ? " book" : " books";
            String filters = libraryFilterDescription();
            countView.setText(total + suffix + (filters.isEmpty() ? "" : " · " + filters));
        }
        if (sortButton != null) sortButton.setText(sortButtonLabel());
        if (authorButton != null) authorButton.setText(authorButtonLabel());
        updateLibraryFilterChips();
        updateReadingStatsSummary();
        updateNotesHubSummary();
    }

'''
start = start[:old_refresh_start] + new_refresh + start[old_sort_start:]
main.write_text(start, encoding="utf-8")

# Prefer DB metadata without growing Java-side scans.
replace_once(main,
'''    private String cachedLibraryTitle(File file) {\n        String fallback = stripExtension(file.getName());\n        String value = prefs.getString("library_title_" + file.getName(), fallback);\n        return value == null || value.trim().isEmpty() ? fallback : value.trim();\n    }\n\n    private String cachedLibraryAuthor(File file) {\n        String value = prefs.getString("library_author_" + file.getName(), "");\n        return value == null ? "" : value.trim();\n    }''',
'''    private String cachedLibraryTitle(File file) {\n        String fallback = stripExtension(file.getName());\n        if (stateDb != null && stateDb.isLibraryIndexReady()) return stateDb.indexedTitle(file.getName(), fallback);\n        String value = prefs.getString("library_title_" + file.getName(), fallback);\n        return value == null || value.trim().isEmpty() ? fallback : value.trim();\n    }\n\n    private String cachedLibraryAuthor(File file) {\n        if (stateDb != null && stateDb.isLibraryIndexReady()) return stateDb.indexedAuthor(file.getName());\n        String value = prefs.getString("library_author_" + file.getName(), "");\n        return value == null ? "" : value.trim();\n    }''')

# Avoid metadata warmup scanning the whole library after v2 index is ready.
replace_once(main,
'''    private void warmSortMetadataIfNeeded(File[] files) {\n        if (metadataWarmupRunning || files == null || files.length == 0) return;''',
'''    private void warmSortMetadataIfNeeded(File[] files) {\n        if (stateDb != null && stateDb.isLibraryIndexReady()) return;\n        if (metadataWarmupRunning || files == null || files.length == 0) return;''')

# Span lookup no longer depends on an in-memory all-books list.
s = main.read_text(encoding="utf-8").replace("visibleBooks.isEmpty()", "libraryResultCount == 0")
main.write_text(s, encoding="utf-8")

# Replace adapter with bounded LRU pages. Keep submit() only as a compatibility shim.
s = main.read_text(encoding="utf-8")
a = s.index("    private final class LibraryAdapter extends RecyclerView.Adapter<LibraryHolder> {")
b = s.index("    private static final class LibraryHolder", a)
new_adapter = r'''    private final class LibraryAdapter extends RecyclerView.Adapter<LibraryHolder> {
        private static final int HOME_HEADER = 0, LIBRARY_SECTION = 1, BOOK = 2, EMPTY = 3, LIBRARY_HEADER = 4, HOME_SECTION = 5;
        private static final int PAGE_SIZE = 120;
        private static final int MAX_CACHED_PAGES = 6;
        private final java.util.LinkedHashMap<Integer, java.util.List<File>> pages =
                new java.util.LinkedHashMap<Integer, java.util.List<File>>(8, .75f, true) {
                    @Override protected boolean removeEldestEntry(java.util.Map.Entry<Integer, java.util.List<File>> e) {
                        return size() > MAX_CACHED_PAGES;
                    }
                };
        private final java.util.HashSet<Integer> loadingPages = new java.util.HashSet<>();
        private LibraryQuerySpec spec = new LibraryQuerySpec("", "", "all", "", "added");
        private int total = 0;
        private int generation = 0;

        void resetPaged(LibraryQuerySpec nextSpec, int nextTotal) {
            generation++;
            spec = nextSpec == null ? new LibraryQuerySpec("", "", "all", "", "added") : nextSpec;
            total = Math.max(0, nextTotal);
            synchronized (pages) { pages.clear(); loadingPages.clear(); }
            notifyDataSetChanged();
            if (total > 0) requestPage(0);
        }

        void submit(List<File> next) {
            generation++;
            total = next == null ? 0 : next.size();
            synchronized (pages) {
                pages.clear(); loadingPages.clear();
                if (next != null && !next.isEmpty()) pages.put(0, new ArrayList<>(next.subList(0, Math.min(PAGE_SIZE, next.size()))));
            }
            notifyDataSetChanged();
        }

        private int shownBookCount() { return homeMode ? Math.min(4, total) : total; }
        private File fileAt(int index) {
            int page = index / PAGE_SIZE, inPage = index % PAGE_SIZE;
            java.util.List<File> rows;
            synchronized (pages) { rows = pages.get(page); }
            if (rows == null || inPage >= rows.size()) { requestPage(page); return null; }
            return rows.get(inPage);
        }
        private void requestPage(int page) {
            if (page < 0 || stateDb == null || total <= 0) return;
            final int requestGeneration = generation;
            synchronized (pages) {
                if (pages.containsKey(page) || loadingPages.contains(page)) return;
                loadingPages.add(page);
            }
            final LibraryQuerySpec requestSpec = spec;
            libraryQueryExecutor.execute(() -> {
                int start = page * PAGE_SIZE;
                java.util.List<ReaderStateDb.LibraryBookRow> rows = stateDb.pageLibraryBooks(requestSpec, start, PAGE_SIZE);
                java.util.List<File> files = new ArrayList<>(rows.size());
                for (ReaderStateDb.LibraryBookRow row : rows) files.add(row.asFile());
                runOnUiThread(() -> {
                    synchronized (pages) {
                        loadingPages.remove(page);
                        if (requestGeneration != generation) return;
                        pages.put(page, files);
                    }
                    if (requestGeneration == generation && !files.isEmpty())
                        notifyItemRangeChanged(2 + start, Math.min(files.size(), Math.max(0, shownBookCount() - start)));
                });
            });
        }

        @Override public int getItemCount() { int shown = shownBookCount(); return 2 + (shown == 0 ? 1 : shown); }
        @Override public int getItemViewType(int position) {
            if (position == 0) return homeMode ? HOME_HEADER : LIBRARY_HEADER;
            if (position == 1) return homeMode ? HOME_SECTION : LIBRARY_SECTION;
            if (shownBookCount() == 0) return EMPTY;
            return BOOK;
        }
        @Override public LibraryHolder onCreateViewHolder(ViewGroup parent, int viewType) {
            if (viewType == HOME_HEADER) return new LibraryHolder(buildLibraryHeader());
            if (viewType == LIBRARY_HEADER) return new LibraryHolder(buildLibraryOnlyHeader());
            if (viewType == HOME_SECTION) return new LibraryHolder(buildHomeBooksSectionHeader());
            if (viewType == LIBRARY_SECTION) return new LibraryHolder(buildLibrarySectionHeader());
            if (viewType == EMPTY) return new LibraryHolder(buildEmptyState());
            FrameLayout shell = new FrameLayout(MainActivity.this); shell.setPadding(dp(7), 0, dp(7), dp(14)); return new LibraryHolder(shell);
        }
        @Override public void onBindViewHolder(LibraryHolder holder, int position) {
            int type = getItemViewType(position);
            if (type == LIBRARY_SECTION) { if (countView != null) countView.setText(total + (total == 1 ? " book" : " books")); return; }
            if (type == HOME_SECTION || type == HOME_HEADER || type == LIBRARY_HEADER) return;
            if (type == EMPTY) { ((TextView) holder.itemView).setText(searchQuery.isEmpty() ?
                    "Your library is ready.\nTap Add book to add an EPUB or PDF." : "No books match your search."); return; }
            int index = position - 2; if (index < 0 || index >= shownBookCount()) return;
            FrameLayout shell = (FrameLayout) holder.itemView; shell.removeAllViews();
            File file = fileAt(index);
            if (file == null) {
                TextView loading = new TextView(MainActivity.this); loading.setText("Loading…"); loading.setGravity(Gravity.CENTER);
                loading.setTextColor(themeSecondaryText()); loading.setMinHeight(dp(gridMode ? 190 : 92)); shell.addView(loading);
                return;
            }
            View card = gridMode ? createGridCard(file, libraryCardWidth()) : createListCard(file);
            shell.addView(card, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        }
    }

'''
s = s[:a] + new_adapter + s[b:]
main.write_text(s, encoding="utf-8")

# Bounded visual extraction workers: fast scrolling must not spawn unbounded threads.
replace_once(main,
'''    private void loadBookVisual(File file, ImageView cover, TextView titleView, TextView metaView) {\n        new Thread(() -> {''',
'''    private final java.util.concurrent.ExecutorService bookVisualExecutor = java.util.concurrent.Executors.newFixedThreadPool(3, r -> {\n        Thread t = new Thread(r, "wow-book-visual"); t.setDaemon(true); return t;\n    });\n\n    private void loadBookVisual(File file, ImageView cover, TextView titleView, TextView metaView) {\n        bookVisualExecutor.execute(() -> {''')
replace_once(main,
'''        }, "wow-book-visual").start();\n    }''',
'''        });\n    }''')

print("Applied Phase A: 100k DB-indexed library paging + bounded cover workers")
