#!/usr/bin/env python3
"""Kitebuddies v0.78 GPS/launcher-icon hotfix from verified RC4 source.

This deliberately changes only version metadata, native geolocation permissions,
WebChromeClient geolocation permission handling, and launcher drawable.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

BASE = Path('buildsrc/app')
gradle = BASE / 'build.gradle'
manifest = BASE / 'src/main/AndroidManifest.xml'
mainjava = BASE / 'src/main/java/de/kitebuddies/forecast/prc/MainActivity.java'
for file in (gradle, manifest, mainjava):
    if not file.is_file():
        raise SystemExit(f'Verified RC4 file missing: {file}')


def swap_once(text, original, replacement, label):
    count = text.count(original)
    if count != 1:
        raise ValueError(f'{label}: expected exact match once, found {count}')
    return text.replace(original, replacement, 1)


# 1. Preserve the existing Android app identity, increment only version code.
g = gradle.read_text('utf-8')
assert "applicationId 'de.kitebuddies.forecast.prc'" in g, 'Wrong Android package'
g = swap_once(g, 'versionCode 82', 'versionCode 84', 'RC4 versionCode')
g = swap_once(g, "versionName '0.77 Beta RC4'", "versionName '0.78 Beta'", 'RC4 versionName')
gradle.write_text(g, encoding='utf-8')

# 2. Android runtime location permissions and native launcher icon.
m = manifest.read_text('utf-8')
assert 'ACCESS_FINE_LOCATION' not in m and 'ACCESS_COARSE_LOCATION' not in m, 'Unexpected existing location permissions'
assert 'android:icon=' not in m, 'Unexpected existing launcher icon'
m = swap_once(
    m,
    '    <application ',
    '    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>\n'
    '    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>\n'
    '    <application ',
    'Insert Android location permissions'
)
label = re.search(r'android:label="[^"]+"', m)
assert label, 'App label missing'
m = swap_once(m, label.group(), label.group() + ' android:icon="@drawable/kb_launcher" android:roundIcon="@drawable/kb_launcher"', 'Set launcher icon')
ET.fromstring(m)
manifest.write_text(m, encoding='utf-8')

# Simple vector logo matching the existing Web/PWA style: cyan circular mark with a dark K.
# No external icon files, fonts, or images are required.
icon = '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#07202A"
        android:pathData="M54,4 A50,50 0,1 1,54,104 A50,50 0,1 1,54,4 Z"/>
    <path android:fillColor="#02D5C4"
        android:pathData="M54,12 A42,42 0,1 1,54,96 A42,42 0,1 1,54,12 Z"/>
    <path android:fillColor="#063241"
        android:pathData="M33,31 L46,31 L46,51 L62,31 L77,31 L58,54 L78,78 L62,78 L46,58 L46,78 L33,78 Z"/>
</vector>
'''
ET.fromstring(icon)
icon_path = BASE / 'src/main/res/drawable/kb_launcher.xml'
icon_path.parent.mkdir(parents=True, exist_ok=True)
if icon_path.exists():
    raise SystemExit('Refusing to overwrite a pre-existing native icon')
icon_path.write_text(icon, encoding='utf-8')

# 3. Keep the RC4 ChromeClient (including Spot-JSON file selection) intact.
j = mainjava.read_text('utf-8')
for must in (
    'private static final String ANDROID_HOME="https://api.kitebuddies-nord.de/web-beta/android.php";',
    'syncSavedWindPush();', 'registerAdminBetaPush();',
    'webView.setWebChromeClient(new WebChromeClient(){',
    'onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params)',
    'webView.addJavascriptInterface(new SpotFileBridge(),"AndroidSpotFiles")',
    'private static final int REQ_RECONNECT_NOTIFICATIONS=5203;',
):
    assert must in j, f'RC4 Android native anchor missing: {must}'
assert 'onGeolocationPermissionsShowPrompt' not in j, 'Native geolocation implementation already exists; stop to avoid duplicate patch'

j = swap_once(j, 'import android.webkit.WebChromeClient;',
              'import android.webkit.WebChromeClient;\nimport android.webkit.GeolocationPermissions;',
              'WebChromeClient import')
j = swap_once(j,
              '    private static final int REQ_RECONNECT_NOTIFICATIONS=5203;',
              '    private static final int REQ_RECONNECT_NOTIFICATIONS=5203;\n'
              '    private static final int REQ_GEOLOCATION=5210;\n'
              '    private GeolocationPermissions.Callback pendingGeoCallback=null;\n'
              '    private String pendingGeoOrigin=null;',
              'GPS request state')
j = swap_once(j, 's.setJavaScriptEnabled(true);',
              's.setJavaScriptEnabled(true); s.setGeolocationEnabled(true);',
              'WebView geolocation setting')

geo_chrome = '''            @Override public void onGeolocationPermissionsShowPrompt(String origin,GeolocationPermissions.Callback callback){
                // Only the authenticated Kitebuddies HTTPS origin can obtain GPS access.
                if(!isTrustedGeoOrigin(origin)){callback.invoke(origin,false,false);return;}
                if(hasNativeLocationPermission()){callback.invoke(origin,true,false);return;}
                // Do not lose an earlier WebView callback on rapid repeated taps.
                if(pendingGeoCallback!=null){pendingGeoCallback.invoke(pendingGeoOrigin,false,false);}
                pendingGeoCallback=callback;
                pendingGeoOrigin=origin;
                requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION},REQ_GEOLOCATION);
            }
'''
j = swap_once(j,
              '        webView.setWebChromeClient(new WebChromeClient(){\n',
              '        webView.setWebChromeClient(new WebChromeClient(){\n' + geo_chrome,
              'Insert GPS callback without changing Spot file chooser')

methods = '''    private boolean isTrustedGeoOrigin(String origin){
        try{
            Uri uri=Uri.parse(origin);
            return "https".equalsIgnoreCase(uri.getScheme())
                && "api.kitebuddies-nord.de".equalsIgnoreCase(uri.getHost())
                && (uri.getPort()==-1||uri.getPort()==443);
        }catch(Exception ignored){return false;}
    }
    private boolean hasNativeLocationPermission(){
        return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED
            || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED;
    }
    private void showLocationSettingsHelp(){
        new android.app.AlertDialog.Builder(this)
            .setTitle("Standort für Kitebuddies freigeben")
            .setMessage("Android hat den Standortzugriff blockiert. Unter App-Info → Berechtigungen → Standort kannst du ihn wieder freigeben.")
            .setPositiveButton("App-Einstellungen öffnen",(dialog,which)->{
                try{
                    Intent intent=new Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                        Uri.fromParts("package",getPackageName(),null));
                    startActivity(intent);
                }catch(Exception ignored){}
            })
            .setNegativeButton("Abbrechen",(dialog,which)->{})
            .show();
    }
'''
j = swap_once(j,
              '    private volatile boolean windPushSyncInProgress=false;',
              methods + '    private volatile boolean windPushSyncInProgress=false;',
              'Add isolated native GPS helpers')

permission_code = '''
        if(req==REQ_GEOLOCATION){
            boolean granted=hasNativeLocationPermission();
            GeolocationPermissions.Callback cb=pendingGeoCallback;
            String origin=pendingGeoOrigin;
            pendingGeoCallback=null;pendingGeoOrigin=null;
            if(cb!=null&&origin!=null)cb.invoke(origin,granted,false);
            if(!granted && !shouldShowRequestPermissionRationale(Manifest.permission.ACCESS_FINE_LOCATION)
                && !shouldShowRequestPermissionRationale(Manifest.permission.ACCESS_COARSE_LOCATION)){
                showLocationSettingsHelp();
            }
            return;
        }
'''
j = swap_once(j,
              'super.onRequestPermissionsResult(req,p,g);if(req==REQ_NOTIFICATIONS)',
              'super.onRequestPermissionsResult(req,p,g);' + permission_code +
              '        if(req==REQ_NOTIFICATIONS)',
              'Handle GPS result without modifying push notification results')

# All existing native paths, file handlers, and push hooks must remain intact.
for must in ('onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params)',
             'syncSavedWindPush();','registerAdminBetaPush();','onActivityResult(int requestCode',
             'AndroidSpotFiles','REQ_RECONNECT_NOTIFICATIONS','ACTION_CREATE_DOCUMENT',
             'ANDROID_HOME="https://api.kitebuddies-nord.de/web-beta/android.php"'):
    assert must in j, f'Native function unexpectedly lost: {must}'
assert j.count('onGeolocationPermissionsShowPrompt') == 1
assert j.count('onRequestPermissionsResult(') == 2  # declaration + super call
mainjava.write_text(j, encoding='utf-8')
print('OK: Android GPS runtime prompt, secure WebView GPS, app-settings fallback, teal K launcher, code 84')
