#!/usr/bin/env python3
"""Upgrade the verified RC4 native project to v0.78 without modifying Firebase, push or routes."""
from pathlib import Path
import re
p=Path('buildsrc/app/build.gradle')
s=p.read_text(encoding='utf-8')
assert re.search(r"\bversionCode\s+82\b",s), 'RC4 versionCode unexpectedly differs'
assert "versionName '0.77 Beta RC4'" in s, 'RC4 versionName unexpectedly differs'
assert "applicationId 'de.kitebuddies.forecast.prc'" in s, 'Unexpected package ID'
s,count=re.subn(r'\bversionCode\s+82\b','versionCode 83',s,count=1)
assert count==1
s=s.replace("versionName '0.77 Beta RC4'","versionName '0.78 Beta'",1)
p.write_text(s,encoding='utf-8')
main=Path('buildsrc/app/src/main/java/de/kitebuddies/forecast/prc/MainActivity.java').read_text(encoding='utf-8')
assert 'ANDROID_HOME="https://api.kitebuddies-nord.de/web-beta/android.php"' in main,'Android WebView entry unexpectedly changed'
assert 'syncSavedWindPush();' in main, 'RC4 alarm synchronization missing'
assert 'registerAdminBetaPush();' in main, 'RC4 admin push registration missing'
assert 'AndroidSpotFiles' in main, 'Existing spot export missing'
assert 'onShowFileChooser' in main, 'Existing file picker missing'
print('v0.78 metadata patched; RC4 WebView URL, push and spot import/export preserved')
