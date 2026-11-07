#!/usr/bin/env python3
"""Non-destructive v0.74 forecast consistency patch for Kitebuddies v0.73 family.
Apply only to a copy of the latest secured S3/S4 source tree; never touches credentials.
Usage: python kb_v074_patch.py <web-beta-directory> [<android-assets-directory>]
"""
from pathlib import Path
import json,sys,re

UNIFIED=r'''/* Kitebuddies v0.74: one mathematical model mixer for spot and map-grid forecasts.
   Historical-learning weights stay DISABLED until independently validated. */
(function(root){
 'use strict';
 function finite(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null}
 function combine(entries){
  const good=(entries||[]).filter(x=>finite(x.wind)!==null&&finite(x.dir)!==null&&finite(x.weight)>0);
  if(!good.length)return null;
  let wx=0,weightSum=0,gustSum=0,gustWeights=0,vx=0,vy=0;
  for(const x of good){const w=Number(x.weight),v=Number(x.wind),a=Number(x.dir)*Math.PI/180;
   wx+=v*w;weightSum+=w;vx+=Math.cos(a)*w;vy+=Math.sin(a)*w;
   const g=finite(x.gust);if(g!==null){gustSum+=g*w;gustWeights+=w}
  }
  const wind=wx/weightSum,dir=((Math.atan2(vy,vx)*180/Math.PI)%360+360)%360;
  return {wind,dir,gust:gustWeights?gustSum/gustWeights:null,modelCount:good.length,
   modelKeys:good.map(x=>x.key||null).filter(Boolean),weightSum};
 }
 function weight(key,lat,lon,time,now=Date.now()){
  const region=root.KBRegionalModels?.region?.(lat,lon)||'global';
  const t=new Date(time).getTime(),lead=Number.isFinite(t)?Math.max(0,(t-now)/3600000):0;
  return Number(root.KBRegionalModels?.weight?.(key,region,lead))||0;
 }
 root.KBUnifiedForecast=Object.freeze({VERSION:'0.74',combine,weight,LEARNING_WEIGHTS_ACTIVE:false});
})(window);
'''

GEAR_CSS=r'''
/* v0.74: Owned tube and soft kites coexist; no mutually exclusive ownership. */
.kb-gear-card{border:1px solid #2d6173;border-radius:14px;padding:12px;margin-top:12px;background:#092632}
.kb-gear-card h3{margin:0 0 6px;font-size:16px}.kb-gear-fields{display:grid;grid-template-columns:1fr 90px;gap:8px}
.kb-gear-fields .kb-gear-name{grid-column:1/-1}
.kb-gear-fields input,.kb-gear-fields select{width:100%;min-height:42px;min-width:0;background:#071d29;color:inherit;border:1px solid #457586;border-radius:9px;padding:8px}
.kb-gear-fields button{min-height:42px;grid-column:1/-1}
.kb-gear-item{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 0;border-bottom:1px solid #284c58}
.kb-gear-item button{min-height:32px;padding:5px 9px}
.kb-owned-kite-suggestion{display:block;font-size:12px;line-height:1.45;color:#c9edf4;margin-top:5px}
.kb-owned-kite-badge{display:inline-block;margin:4px 5px 4px 0;padding:6px 9px;background:#143c49;border:1px solid #2c7180;border-radius:10px;font-size:12px}
.kb-kite-caution{font-size:11px;line-height:1.4;color:#ffc987;margin-top:8px}
html[data-theme="light"] .kb-gear-card{background:#f2fafc;color:#14313d}
html[data-theme="light"] .kb-gear-fields input,html[data-theme="light"] .kb-gear-fields select{background:#fff;color:#18333d}
'''

GEAR_JS=r'''
/* v0.74: user-owned equipment is stored locally, independent of legacy calculator's selected kite type. */
const KB_OWNED_KITES_KEY='kb_owned_kites_v074';
function kbOwnedKites(){try{const x=safeJSON(localStorage.getItem(KB_OWNED_KITES_KEY),[]);return Array.isArray(x)?x.filter(k=>Number(k.size)>=3&&Number(k.size)<=25&&['tube','soft'].includes(k.type)).slice(0,60):[]}catch(e){return[]}}
function kbSaveOwnedKites(kites){try{localStorage.setItem(KB_OWNED_KITES_KEY,JSON.stringify(kites.slice(0,60)))}catch(e){}kbRenderOwnedKites();if(typeof kbForecastTableHtmlCache!=='undefined')kbForecastTableHtmlCache.clear();if(typeof kbDerivedCache!=='undefined')kbDerivedCache.clear();if(state.consensus?.length){renderForecast(false)}}
function kbEscapeGear(t){return String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function kbRenderOwnedKites(){const el=$('kbOwnedKitesList');if(!el)return;const kites=kbOwnedKites();el.innerHTML=kites.length?kites.map((k,i)=>`<div class="kb-gear-item"><span>${kbEscapeGear(k.name)} · ${Number(k.size).toLocaleString('de-DE')} m² · ${k.type==='soft'?'Softkite':'Tubekite'}</span><button type="button" data-kb-remove-gear="${i}" aria-label="Kite entfernen">Entfernen</button></div>`).join(''):'<div class="info-sub">Noch keine eigenen Kites hinterlegt. Beide Kitearten lassen sich gemeinsam hinzufügen.</div>';el.querySelectorAll('[data-kb-remove-gear]').forEach(b=>b.addEventListener('click',()=>{const l=kbOwnedKites();l.splice(Number(b.dataset.kbRemoveGear),1);kbSaveOwnedKites(l)}))}
function kbAddOwnedKite(){const name=String($('kbGearName')?.value||'').trim(),size=Number($('kbGearSize')?.value),type=$('kbGearType')?.value;if(!name||!Number.isFinite(size)||size<3||size>25||!['tube','soft'].includes(type)){showSortToast('Kitemodell, Kiteart und Größe (3–25 m²) eintragen');return}const kites=kbOwnedKites();if(kites.some(k=>k.name===name&&Number(k.size)===size&&k.type===type)){showSortToast('Dieser Kite ist bereits hinterlegt');return}kites.push({name:name.slice(0,80),size,type,id:'kite-'+Date.now()});kbSaveOwnedKites(kites);$('kbGearName').value='';$('kbGearSize').value='';showSortToast('Eigener Kite gespeichert')}
function kbGearRecommendations(point){const p=getProfile(),owned=kbOwnedKites();if(!point||!Number.isFinite(point.wind)||!owned.length)return[];const g=gustForProfile(point,p);const limit=(Number.isFinite(point.gust)&&point.wind>0)?point.gust/point.wind:1;
 const possible=owned.map(k=>{const calc=calculateKiteFor(point.wind,p.weight,p.level,k.type,p.board,g.value);if(!calc)return null;const ideal=calc.displayedExactSize;const difference=Math.abs(Number(k.size)-ideal);const tolerance=Math.max(1.25,ideal*.16);return{...k,ideal,difference,fit:difference<=tolerance,near:difference<=tolerance*1.8,spread:limit}}).filter(Boolean);
 return possible.sort((a,b)=>(b.fit?1:0)-(a.fit?1:0)||a.difference-b.difference).slice(0,5)
}
function kbGearRecommendationText(point){const options=kbGearRecommendations(point).filter(k=>k.fit).slice(0,3);return options.map(k=>`${k.size} m² ${k.type==='soft'?'Softkite':'Tubekite'} (${k.name})`).join(' · ')}
function kbInitOwnedKites(){kbRenderOwnedKites();$('kbAddGearBtn')?.addEventListener('click',kbAddOwnedKite)}
'''


def must_replace(s,old,new,label):
 if old not in s:raise RuntimeError(f'Missing required anchor {label}: {old[:100]!r}')
 return s.replace(old,new,1)

def patch_app(app):
 s=app.read_text()
 # Preserve head/title except version number; avoid treating older fallback as a release.
 s=s.replace('v0.73 Beta','v0.74 Beta').replace('versionCode 73','versionCode 74')
 s=s.replace('const KB_WEB_VERSION_CODE=73;','const KB_WEB_VERSION_CODE=74;').replace("const KB_WEB_VERSION_NAME='0.73 Beta';", "const KB_WEB_VERSION_NAME='0.74 Beta';")
 s=s.replace("const KB_SPOT_CACHE_SCHEMA=28", "const KB_SPOT_CACHE_SCHEMA=29")
 s=must_replace(s,'<script src="pro-regional-models.js"></script>','<script src="pro-regional-models.js"></script>\n<script src="kb-unified-forecast.js"></script>','unified script dependency')
 # Exact same weighted scalar / circular directions in core superforecast and grid.
 old='wind=weightedMean(speeds,weights),gust=weightedMean(gusts,weights),dir=vectorDir(dirs,weights)'
 new='mix=KBUnifiedForecast.combine(entries.map(e=>({key:e.m.key,wind:e.wind,gust:e.gust,dir:e.dir,weight:e.weight}))),wind=mix?.wind??null,gust=mix?.gust??null,dir=mix?.dir??null'
 s=must_replace(s,old,new,'core consensus mixer')
 # Eliminate DWD overlay spot replacement. Spot markers come exclusively from consensus snapshot.
 beg=s.index('function mapWindForSnapshot(');end=s.index('\nfunction displaySnapshot(',beg)
 s=s[:beg]+'''function mapWindForSnapshot(spot,snap,target){
 const wind=nullableNumber(snap?.wind),dir=nullableNumber(snap?.dir);
 return{wind,dir:dir==null?null:norm360(dir),time:snap?.time||target||null,source:'superforecast'};
}'''+s[end:]
 # Don't overwrite consensus confidence via DWD+ECMWF bespoke map calculator.
 s=s.replace("  loadMapConfidenceSnapshots().catch(e=>console.warn('Map confidence refresh failed',e));", "  // v0.74: no independent two-model confidence recalculation; only unified consensus.")
 # Replace model-specific quick-overview path; no ECMWF-only silent substitute.
 beg=s.index('async function loadSpotSnapshots(){');end=s.index('\nconst KB_SPOT_DOUBLE_TAP_MS=',beg)
 s=s[:beg]+'''async function loadSpotSnapshots(){
 seedFallbackSpotSnapshots(false);
 // Only complete or cached Superforecast bundles may feed map/spot overview.
 // Missing bundles remain missing until batch refresh succeeds; no single-model values.
 for(let i=0;i<spots.length;i++){
  const b=spotBundleFor(i);if(bundleUsable(b))bundleSnapshot(i,b);
 }
 renderSpotList();renderMapMarkers();renderFallbackPins();renderNearby();
}'''+s[end:]
 # Default focus: preserve map time in the detail forecast when opening a spot from map.
 old='function representativeIndex(){const entries=periodEntries();if(!entries.length)return nearestNow();'
 new='function representativeIndex(){const entries=periodEntries();if(!entries.length)return nearestNow();if(state.mapSelectedTime){const t=forecastDate(state.mapSelectedTime).getTime();if(Number.isFinite(t)){const match=entries.find(e=>Math.abs(forecastDate(e.p.time).getTime()-t)<=35*60000);if(match)return match.i;}}'
 s=must_replace(s,old,new,'time synchronization')
 # Mark unavailable instead of inventing scoring values.
 s=s.replace("hasScore?rawScore:50", "hasScore?rawScore:null")
 # v0.74: equipment list block in Tools.
 note='<div class="notice ok" id="profileNotice"'
 gear_html='''<div class="kb-gear-card full" id="kbOwnedGearCard"><h3>Meine eigenen Kites · Tube und Softkite gemeinsam</h3>
 <p class="info-sub">Mehrere Kitearten parallel speichern. Die App vergleicht jeden vorhandenen Kite mit dem gemeinsamen Superforecast, deiner Größe, deinem Fahrlevel und dem Board. Keine Freigabe zum Kiten.</p>
 <div class="kb-gear-fields"><input class="kb-gear-name" id="kbGearName" maxlength="80" placeholder="Modell, z. B. Soul 3 oder Evo SLS" aria-label="Kitemodell"><select id="kbGearType" aria-label="Kiteart"><option value="tube">Tubekite</option><option value="soft">Softkite / Matte</option></select><input id="kbGearSize" type="number" step="0.5" min="3" max="25" placeholder="m²" aria-label="Kitegröße in Quadratmetern"><button type="button" id="kbAddGearBtn" class="primary">Kite hinzufügen</button></div><div id="kbOwnedKitesList" aria-live="polite"></div></div>'''
 s=must_replace(s,note,gear_html+note,'add gear editor')
 s=s.replace('</style>',GEAR_CSS+'\n</style>',1)
 # Put equipment functions before renderForecast is invoked, plus after core helper definitions.
 before='function profileRecommendation(point)'
 s=must_replace(s,before,GEAR_JS+'\n'+before,'owned gear library')
 # For recommendation, preserve existing calculator as fallback but attach equipment list.
 old="return {calc:calculateKiteFor(point.wind,p.weight,p.level,p.kiteType,p.board,g.value),gust:g}"
 new="return {calc:calculateKiteFor(point.wind,p.weight,p.level,p.kiteType,p.board,g.value),gust:g,owned:kbGearRecommendations(point)}"
 s=must_replace(s,old,new,'profile recommendation enriched')
 s=must_replace(s,"$('personalKiteNow').textContent=pr?.calc?pr.calc.displayedSize+' m²':'Profil anlegen';$('personalKiteRange').textContent=pr?.calc?pr.calc.range+' · '+pr.gust.label:'';",
 "$('personalKiteNow').textContent=kbGearRecommendationText(n)|| (pr?.calc?pr.calc.displayedSize+' m² (rechnerisch)':'Profil anlegen');$('personalKiteRange').textContent=pr?.calc?((kbOwnedKites().length?'Alternativen aus deiner Ausrüstung · ':'Keine Ausrüstung hinterlegt · ')+pr.gust.label):'';",'personal gear selected')
 # Forecast table uses actual owned equipment alternatives if available.
 old="case'kite':return `<span class=\"kite-cell\">${r?.calc?r.calc.displayedSize+' m²':'–'}<span class=\"info-sub\">${r?.calc?r.calc.range:''}</span></span>`;"
 new="case'kite':{const owned=kbGearRecommendationText(x);return `<span class=\"kite-cell\">${owned?kbEscapeGear(owned):r?.calc?r.calc.displayedSize+' m²':'–'}<span class=\"info-sub\">${owned?'Eigene Kites · rechnerisch':r?.calc?r.calc.range:''}</span></span>`;}"
 s=must_replace(s,old,new,'forecast table kites')
 # Replace theoretical card render with owned kites if configured.
 start=s.index('function renderKiteSizeCards(){');end=s.index('\nfunction renderAll()',start)
 s=s[:start]+'''function renderKiteSizeCards(){const host=$('kiteSizeCards');if(!host)return;const n=currentPoint(),options=kbGearRecommendations(n),s=profileRecommendation(n)?.calc?.displayedSize||9;
 if(kbOwnedKites().length){host.innerHTML=options.length?options.slice(0,4).map(k=>`<div class="kite-size ${k.fit?'active':''}"><strong>${kbEscapeGear(k.name)} · ${Number(k.size)} m²</strong><span class="kb-owned-kite-suggestion">${k.type==='soft'?'Softkite':'Tubekite'} · ${k.fit?'rechnerisch passend':k.near?'Grenzbereich':'nicht empfohlen'}</span></div>`).join('')+'<div class="kb-kite-caution">Persönliche Orientierung, keine Sicherheitsfreigabe. Windbereich des Herstellers, Böen, Können und Spotbedingungen beachten.</div>':'<div class="info-sub">Keine passende Ausrüstung für diesen Forecast gefunden.</div>';return}
 const sizes=[clamp(s-3,3,20),clamp(s-1,3,20),clamp(s,3,20),clamp(s+2,3,20)];host.innerHTML=sizes.map((x,i)=>`<div class="kite-size ${i===2?'active':''}"><strong>${x} m²</strong>${i===2?'rechnerisch':i<2?'mehr Wind':'weniger Wind'}</div>`).join('')+'<div class="kb-kite-caution">Eigene Tube- und Softkites unter Tools hinterlegen.</div>'}
'''+s[end:]
 # Set up gear UI on startup alongside profile form, after DOM ready listeners.
 old='function initAlarmManager()'
 s=must_replace(s,old,'function initAlarmManager()', 'alarm initialization marker')
 # Put gear editor init in initAlarmManager which runs once on ready (verified).
 s=must_replace(s,"function initAlarmManager(){$('toolAlarmDetails')", "function initAlarmManager(){kbInitOwnedKites();$('toolAlarmDetails')",'gear setup')
 # Explicitly use consensus snapshot for in-app alarms / tests; filter out stale bundles.
 old="const fresh=bundleFresh(bundle);const pts=idx===selected&&state.consensus?.length&&(!bundle||fresh)?state.consensus:(fresh?bundle.consensus:null);"
 new="const fresh=bundleFresh(bundle);const pts=fresh?bundle.consensus:(idx===selected&&state.consensus?.length&&state.dataQuality?.mode==='current'?state.consensus:null);"
 s=must_replace(s,old,new,'inapp alarms verified inputs')
 # Add data origin in alarm notice. (Local alarms remain local.)
 s=s.replace('🔔 Gute Kitebedingungen!', '🔔 Kitebuddies-Superforecast: Kitebedingungen!')
 # Server-side push is not audited for this version. Never advertise push as ready.
 s=s.replace('Promise.resolve({pushReady:true}).then', 'Promise.resolve({pushReady:false}).then')
 s=s.replace("if(show)alarmStatus(`Lokal gespeichert · ${rules.length} Alarmregeln · In-App-Überwachung aktiv` ,'ok');", "if(show)alarmStatus(`Lokal gespeichert · ${rules.length} Regeln · In-App-Überwachung bei geöffneter App. Server-Push noch nicht geprüft` ,'ok');")
 s=s.replace('>Kite-Art</label>', '>Kiteart für theoretischen Rechner (eigene Kites dürfen gemischt sein)</label>')
 # Make fallback map DWD overlays label consistent in detail.
 s=s.replace("dwd?' · DWD':'',", "dwd?' · DWD':'',")
 # Model agreement is NOT probability: terminology corrected wherever possible.
 s=s.replace("' % Forecast-Vertrauen'", "' % Modellübereinstimmung'")
 s=s.replace(" % Forecast-Vertrauen", " % Modellübereinstimmung")
 app.write_text(s)


def patch_overlay(path):
 s=path.read_text()
 s=s.replace('8d-hourly-v030','7d-mix-v074')
 # Avoid stale DWD cache and silent fallback after update.
 s=s.replace('kb-pro-wind-grid-v030','kb-pro-wind-grid-v074')
 s=s.replace('kb_pro_wind_pkg_v030_', 'kb_pro_wind_pkg_v074_').replace('kb_pro_wind_pkg_index_v030', 'kb_pro_wind_pkg_index_v074')
 s=s.replace('end=now+8*24*hourMs','end=now+7*24*hourMs')
 s=s.replace('DWD ICON','Superforecast')
 s=s.replace('DWD-Windpaket','Superforecast-Modellmix')
 s=s.replace("'Grundwind · DWD ICON", "'Grundwind · Superforecast")
 s=s.replace('Grundwind · DWD ICON ·', 'Grundwind · Superforecast ·')
 s=s.replace('Wetterfeld','Windfeld')
 start=s.index('async function requestPackage(grid,signal){'); end=s.index('\nasync function ensurePackage(){',start)
 block=r'''async function requestPackage(grid,signal){
  const region=KBRegionalModels.region(grid.points[Math.floor(grid.points.length/2)].lat,grid.points[Math.floor(grid.points.length/2)].lon);
  const selected=KBRegionalModels.select(grid.points[Math.floor(grid.points.length/2)].lat,grid.points[Math.floor(grid.points.length/2)].lon,[]).models;
  const models=selected.filter(m=>['dwd','dmi','ecmwf','gfs'].includes(m.server));
  const lats=grid.points.map(p=>p.lat).join(','),lons=grid.points.map(p=>p.lon).join(',');
  const results=[];
  // Two concurrent backend requests avoid flooding PHP or blocking touch/scroll.
  for(let i=0;i<models.length;i+=2){
   const batch=await Promise.allSettled(models.slice(i,i+2).map(async m=>{
    // Use the SAME platform-aware, secured weather client as the spot forecast.
    // Never bypass its Web/iOS proxy or Android bridge with a hard-coded relative URL.
    const url=window.KBWeatherAPI?.modelUrl?.(m.server,lats,lons,{hourly:['wind_speed_10m','wind_direction_10m'],days:7,timezone:'UTC',cell:'nearest'});
    if(!url)throw new Error('Weather API client unavailable');
    const response=await fetch(url,{signal,cache:'no-store'});
    const env=await response.json();if(!response.ok||!env?.ok)throw new Error('Modell '+m.server+': '+(env?.error||response.status));
    const list=Array.isArray(env.data)?env.data:[env.data];if(list.length!==grid.points.length)throw new Error('Unvollständiges Windfeld '+m.server);
    return {m,list,serverSource:env.source||'server',savedAt:env.saved_at_utc||null};
   }));
   for(const b of batch)if(b.status==='fulfilled')results.push(b.value);
  }
  if(results.length<2)throw new Error('Mindestens 2 verfügbare Modelle für ein Superforecast-Windfeld erforderlich');
  const first=results[0].list[0]?.hourly?.time||[];
  // The wind-grid request explicitly asks for UTC. API timestamps may omit 'Z'.
  // Interpret zone-less times as UTC, not as the user's Berlin/Cape Town profile zone.
  const utcApiMs=t=>{const value=String(t||'').trim();return Date.parse(/[zZ]$|[+\-]\d{2}:?\d{2}$/.test(value)?value:value+'Z')};
  const times=first.map(t=>new Date(utcApiMs(t)).toISOString());
  if(!times.length)throw new Error('Superforecast ohne Zeitachse');
  const timeMillis=times.map(x=>Date.parse(x)),now=Date.now();
  const windArrays=times.map(()=>new Array(grid.points.length)),dirArrays=times.map(()=>new Array(grid.points.length));
  const modelArrays=results.map(({m,list})=>({m,byPoint:list.map(item=>{
   const h=item?.hourly||{},indexes=new Map();(h.time||[]).forEach((t,i)=>{const ms=utcApiMs(t);if(Number.isFinite(ms))indexes.set(Math.round(ms/3600000),i)});
   return{indexes,winds:h.wind_speed_10m||[],dirs:h.wind_direction_10m||[]};
  })}));
  for(let ti=0;ti<times.length;ti++)for(let pi=0;pi<grid.points.length;pi++){
   const p=grid.points[pi],entries=[];
   for(const source of modelArrays){const q=source.byPoint[pi],idx=q.indexes.get(Math.round(timeMillis[ti]/3600000));if(idx==null)continue;
    const wind=Number(q.winds[idx]),dir=Number(q.dirs[idx]);if(!Number.isFinite(wind)||!Number.isFinite(dir))continue;
    const weight=Number(KBRegionalModels.weight(source.m.key,KBRegionalModels.region(p.lat,p.lon),Math.max(0,(timeMillis[ti]-now)/3600000)))||0;
    if(weight>0)entries.push({key:source.m.key,wind,dir,weight});
   }
   const mix=KBUnifiedForecast.combine(entries);
   if(!mix||mix.modelCount<2)throw new Error('Unzureichende Modellabdeckung im Windfeld');
   windArrays[ti][pi]=Number(mix.wind.toFixed(3));dirArrays[ti][pi]=Number(mix.dir.toFixed(2));
  }
  return {key:packageKey(grid),grid,times,winds:windArrays,dirs:dirArrays,
   startMs:timeMillis[0],endMs:timeMillis[timeMillis.length-1],savedAt:Date.now(),
   source:'Kitebuddies Superforecast / identischer regionaler Modellmix',serverSource:'weighted_models',
   modelKeys:results.map(x=>x.m.key),modelCount:results.length,packageVersion:74};
}'''
 s=s[:start]+block+s[end:]
 s=s.replace('const timeout=setTimeout(()=>ac.abort(),15000)', 'const timeout=setTimeout(()=>ac.abort(),35000)')
 s=s.replace('Grundwind · Superforecast · ${PRO_WIND.points.length} Rasterpunkte','Grundwind · Superforecast (${pkg.modelCount||"?"} Modelle) · ${PRO_WIND.points.length} Rasterpunkte')
 # Keep UI truthful if model field fails entirely: no old DWD grid fallback.
 s=s.replace("'Grundwind · DWD ICON'", "'Grundwind · Superforecast'")
 s=s.replace('Grundwind · DWD', 'Grundwind · Superforecast')
 path.write_text(s)


def patch_root(root):
 root=Path(root)
 if not (root/'pro-wind-overlay.js').is_file():raise RuntimeError(f'Missing pro-wind-overlay.js in {root}')
 app=(root/'app.html') if (root/'app.html').exists() else (root/'index.html')
 if not app.is_file():raise RuntimeError(f'Missing app.html or index.html in {root}')
 if (root/'kb-unified-forecast.js').exists():raise RuntimeError('Already patched; refusing to apply twice')
 (root/'kb-unified-forecast.js').write_text(UNIFIED)
 patch_app(app)
 patch_overlay(root/'pro-wind-overlay.js')
 manifest=root/'manifest.webmanifest'
 if manifest.exists():manifest.write_text(manifest.read_text().replace('0.73','0.74').replace('v0.71','v0.74'))
 version=root/'web-version.json'
 if version.exists():
  x=json.loads(version.read_text());x['versionCode']=74;x['versionName']='0.74 Beta';x['changes']=["Gemeinsamer Modellmix für Kartenwindfeld und Spot-/Forecast-Werte.","Identische Prognosezeit, Confidence und KiteScore für Spot und Detail.","Tube- und Softkite-Ausrüstung nebeneinander mit persönlichen Vorschlägen.","In-App-Alarme verwenden die gemeinsamen Forecast-Daten."]
  version.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
 sw=root/'service-worker.js'
 if sw.exists():
  swsrc=sw.read_text().replace('0.73','0.74').replace('v073','v074').replace('v0.73','v0.74').replace('const KB_WEB_VERSION_CODE = 73;', 'const KB_WEB_VERSION_CODE = 74;')
  swsrc=swsrc.replace("  '/web-beta/pro-regional-models.js',", "  '/web-beta/pro-regional-models.js',\n  '/web-beta/kb-unified-forecast.js',")
  sw.write_text(swsrc)
 return app

if __name__=='__main__':
 if len(sys.argv)<2:raise SystemExit('Usage: python kb_v074_patch.py <web-beta-dir> [<android-assets-dir>]')
 for a in sys.argv[1:]:print('Patched',patch_root(a))
