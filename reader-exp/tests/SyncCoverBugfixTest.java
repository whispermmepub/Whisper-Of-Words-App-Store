package com.whisper.wowreader;

import java.nio.charset.StandardCharsets;
import java.util.List;

public final class SyncCoverBugfixTest {
    private static void ok(boolean v,String m){if(!v)throw new AssertionError(m);}
    public static void main(String[] args){
        String burmese="အလွန်ရှည်လျားသောမြန်မာစာအုပ်ဖိုင်နာမည်ကိုစမ်းသပ်ရန်အသုံးပြုထားသောစာသား.epub";
        ok(!DriveMetadataPolicy.isSafe("originalName",burmese+burmese),"long UTF-8 filename must exceed Drive property budget");
        String clipped=DriveMetadataPolicy.safeValue("originalName",burmese+burmese);
        ok(("originalName"+clipped).getBytes(StandardCharsets.UTF_8).length<=124,"safeValue must respect 124 UTF-8 bytes");
        String hash="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        ok(DriveMetadataPolicy.isSafe("contentHash",hash),"SHA-256 property must fit");

        List<String> q=CoverSearchPolicy.queries("Harry Potter","J. K. Rowling","");
        ok(q.contains("Harry Potter J. K. Rowling"),"plain title+author query required");
        ok(q.contains("Harry Potter"),"title-only fallback required");
        List<String> my=CoverSearchPolicy.queries("မြန်မာစာအုပ်","စာရေးသူ","");
        ok(my.get(0).contains("မြန်မာစာအုပ်"),"Unicode query must be preserved");
        ok(!my.get(0).contains("intitle:"),"search must not force strict Google field qualifier");
        System.out.println("SYNC_COVER_BUGFIX_TEST_PASS");
    }
}
