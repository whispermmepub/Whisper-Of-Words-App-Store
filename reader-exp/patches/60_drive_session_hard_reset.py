#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
java=root/'app/src/main/java/com/whisper/wowreader'
db=java/'ReaderStateDb.java'
drive=java/'GoogleDriveSync.java'
if not db.is_file() or not drive.is_file():
    raise SystemExit('Phase H source files missing')

def rep(path,old,new):
    s=path.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit(f'Phase H anchor missing in {path.name}: {old[:160]!r}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')

# v6 deliberately invalidates resumable sessions created by earlier experimental
# metadata formats. The book/cover dirty flags remain, so nothing is lost; only
# the stale session URL/offset is discarded and a clean session is created.
rep(db,'private static final int DB_VERSION = 5;','private static final int DB_VERSION = 6;')
rep(db,
'''            try { db.execSQL("ALTER TABLE books ADD COLUMN cover_upload_offset INTEGER NOT NULL DEFAULT 0"); } catch (Exception ignored) {}
        }
    }''',
'''            try { db.execSQL("ALTER TABLE books ADD COLUMN cover_upload_offset INTEGER NOT NULL DEFAULT 0"); } catch (Exception ignored) {}
        }
        if (oldVersion < 6) {
            db.execSQL("UPDATE books SET upload_session_url='', upload_offset=0 WHERE sync_dirty=1");
            db.execSQL("UPDATE books SET cover_upload_session_url='', cover_upload_offset=0 WHERE cover_sync_dirty=1");
        }
    }''')

# Identity already lives in the Drive object name: wow_book_<sha256>.epub/pdf.
# Do not send *any* properties/appProperties on resumable-session creation.
# This removes the 124-byte UTF-8 property limit from book/cover uploads entirely.
rep(drive,
'''        if(!DriveAppPropertyPolicy.validContentHash(hash)) throw new Exception("Invalid content hash for Drive metadata");
        JSONObject props=new JSONObject();props.put("contentHash",hash);meta.put("appProperties",props);''',
'''        // No Drive properties/appProperties here. The SHA-256 identity is encoded in the object name.''')

# Make this failure distinguishable from chunk-upload and auth failures.
rep(drive,
'''        ensureSuccess(c); String location=c.getHeaderField("Location"); c.disconnect();''',
'''        try { ensureSuccess(c); }
        catch (Exception e) { c.disconnect(); throw new Exception("Google Drive resumable-session error: " + e.getMessage()); }
        String location=c.getHeaderField("Location"); c.disconnect();''')

print('Applied Phase H: remove Drive appProperties + reset stale resumable sessions on DB v6')
