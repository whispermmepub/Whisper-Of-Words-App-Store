#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
java=root/'app/src/main/java/com/whisper/wowreader'
drive=java/'GoogleDriveSync.java'
if not drive.is_file(): raise SystemExit('GoogleDriveSync missing')

(java/'DriveAppPropertyPolicy.java').write_text(r'''package com.whisper.wowreader;

import java.nio.charset.StandardCharsets;

final class DriveAppPropertyPolicy {
    private DriveAppPropertyPolicy() {}
    static final int MAX_BYTES = 124;

    static boolean fits(String key,String value) {
        String k=key==null?"":key, v=value==null?"":value;
        return (k+v).getBytes(StandardCharsets.UTF_8).length <= MAX_BYTES;
    }

    static boolean validContentHash(String hash) {
        if(hash==null || !hash.matches("[0-9a-fA-F]{64}")) return false;
        return fits("contentHash",hash);
    }
}
''',encoding='utf-8')

s=drive.read_text(encoding='utf-8')
old='''        JSONObject props=new JSONObject();props.put("contentHash",hash);meta.put("appProperties",props);'''
new='''        if(!DriveAppPropertyPolicy.validContentHash(hash)) throw new Exception("Invalid content hash for Drive metadata");
        JSONObject props=new JSONObject();props.put("contentHash",hash);meta.put("appProperties",props);'''
if old not in s: raise SystemExit('Drive property guard anchor missing')
drive.write_text(s.replace(old,new,1),encoding='utf-8')
print('Applied Phase G: Drive appProperties byte-limit guard')
