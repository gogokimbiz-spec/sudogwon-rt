"""브이월드 3D 지도로 단지를 비스듬히 내려다본 사진 찍기 (PC 실행기 전용 – 브이월드는 해외 접속 차단).
make_hero.py 가 HERO_3D=1 일 때 oblique(lon, lat) 를 부릅니다. 실패하면 예외 → 위성 사진으로 넘어감.
- 화면 없는 Edge/Chrome(Playwright)으로 브이월드 WebGL 3D API 페이지를 띄움.
  API 키가 github.io 주소로 등록돼 있어서, 페이지 주소를 https://gogokimbiz-spec.github.io/sudogwon-rt/hero3d.html 로
  가짜로 띄우고(page.route 로 내용 직접 제공) 키는 Secret(VWORLD_KEY)에서만 넣음 → 저장소·사이트에 키가 남지 않음.
- 카메라: 단지 남쪽(HEADING 기준 뒤쪽) 하늘에서 TILT 각도로 내려다봄. 값은 환경변수로 조정 가능.
- 시험용 기록: OUT/3d_debug.png(찍힌 화면), OUT/3d_log.txt
"""
import os, io, json, math, time

TILT = float(os.environ.get('HERO_3D_TILT', '-32'))      # -90 = 수직, -30 = 비스듬
ALT = float(os.environ.get('HERO_3D_ALT', '330'))        # 카메라 높이(m)
HEADING = float(os.environ.get('HERO_3D_HEADING', '20'))  # 0 = 북쪽을 바라봄
PAGE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/hero3d.html'

HTML = """<!doctype html><html><head><meta charset="utf-8">
<style>html,body,#vmap{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#000}</style>
<script>window.__st={step:'start',err:[]};window.onerror=function(m){window.__st.err.push(String(m).slice(0,200))};</script>
<script src="https://map.vworld.kr/js/webglMapInit.js.do?version=3.0&apiKey=__KEY__"></script>
</head><body><div id="vmap"></div>
<script>
var CAM=__CAM__;
function pos(){return new vw.CameraPosition(new vw.CoordZ(CAM.lon,CAM.lat,CAM.alt),new vw.Direction(CAM.heading,CAM.tilt,0));}
function go(){
  try{
    if(typeof vw==='undefined'){window.__st.step='no-vw';return;}
    var o=new vw.MapOptions(vw.BasemapType.PHOTO,'',vw.DensityType.EMPTY,vw.DensityType.BASIC,false,pos(),pos());
    window.map=new vw.Map('vmap',o);
    window.__st.step='map';
  }catch(e){window.__st.err.push('map:'+e);window.__st.step='map-fail';}
}
window.addEventListener('load',function(){setTimeout(go,300);});
window.__aim=function(){                       // 첫 화면 애니메이션이 카메라를 되돌리는 경우 대비 → 다시 맞춤
  var done=[];
  try{if(window.map&&map.moveTo){map.moveTo(pos());done.push('moveTo');}}catch(e){window.__st.err.push('moveTo:'+e);}
  try{
    var v=(window.ws3d&&ws3d.viewer)||null, C=window.Cesium||(window.ws3d&&ws3d.Cesium);
    if(v&&C){v.camera.cancelFlight&&v.camera.cancelFlight();
      v.camera.setView({destination:C.Cartesian3.fromDegrees(CAM.lon,CAM.lat,CAM.alt),
        orientation:{heading:C.Math.toRadians(CAM.heading),pitch:C.Math.toRadians(CAM.tilt),roll:0}});done.push('setView');}
  }catch(e){window.__st.err.push('setView:'+e);}
  return done.join(',');
};
window.__state=function(){
  var v=(window.ws3d&&ws3d.viewer)||null, s={step:window.__st.step,err:window.__st.err.slice(-5),vw:typeof vw,ws3d:!!window.ws3d,viewer:!!v};
  try{if(v){v.scene.requestRender();s.tiles=v.scene.globe.tilesLoaded;
    var c=v.camera.positionCartographic;s.cam=[c.longitude*57.29578,c.latitude*57.29578,c.height,v.camera.pitch*57.29578];}}catch(e){s.serr=String(e);}
  return s;
};
</script></body></html>"""


def cam_for(lon, lat):
    off = ALT / math.tan(math.radians(abs(TILT)))          # 단지에서 카메라까지 수평 거리
    back = math.radians(HEADING + 180)
    return {'lon': lon + off * math.sin(back) / (111320 * math.cos(math.radians(lat))),
            'lat': lat + off * math.cos(back) / 111320, 'alt': ALT, 'heading': HEADING, 'tilt': TILT}


def oblique(lon, lat, key, out_dir, w=864, h=1080):
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageStat
    log = []
    say = lambda *a: (log.append(' '.join(str(x) for x in a)), print('[3D]', *a))
    cam = cam_for(lon, lat)
    say('카메라', json.dumps(cam))
    html = HTML.replace('__KEY__', key).replace('__CAM__', json.dumps(cam))
    shot = None
    try:
        with sync_playwright() as p:
            b = None
            for ch in ('msedge', 'chrome', None):
                try:
                    b = p.chromium.launch(channel=ch, headless=True, args=['--ignore-gpu-blocklist', '--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']) if ch else \
                        p.chromium.launch(headless=True, args=['--ignore-gpu-blocklist', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
                    say('브라우저', ch or 'chromium'); break
                except Exception as e:
                    say('브라우저 실패', ch, str(e)[:120])
            if b is None: raise RuntimeError('브라우저를 띄우지 못함')
            pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1.25)
            pg.on('console', lambda m: m.type in ('error', 'warning') and say('console', m.type, m.text[:160]))
            pg.route(PAGE, lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=html))
            pg.goto(PAGE, wait_until='load', timeout=60000)
            t0, aimed, ok_n = time.time(), 0, 0
            while time.time() - t0 < 100:
                time.sleep(2)
                st = pg.evaluate('window.__state ? window.__state() : null') or {}
                if st.get('step') in ('no-vw', 'map-fail'):
                    say('상태', json.dumps(st, ensure_ascii=False)); raise RuntimeError('3D 지도 시작 실패: ' + st.get('step'))
                if st.get('step') == 'map' and time.time() - t0 > 8 and aimed < 3 and (aimed == 0 or time.time() - t0 > 8 + aimed * 10):
                    say('카메라 맞춤', pg.evaluate('window.__aim()')); aimed += 1; ok_n = 0
                ok_n = ok_n + 1 if (st.get('tiles') and aimed >= 2) else 0
                if int(time.time() - t0) % 10 < 2: say('상태', json.dumps(st, ensure_ascii=False))
                if ok_n >= 3: break                              # 타일 다 받은 상태가 6초 이상 유지
            if not st.get('viewer') and aimed == 0:
                pg.evaluate('window.__aim && window.__aim()'); time.sleep(15)
            time.sleep(4)
            say('마지막 상태', json.dumps(pg.evaluate('window.__state()'), ensure_ascii=False))
            shot = pg.screenshot()
            b.close()
    finally:
        if shot: open(os.path.join(out_dir, '3d_debug.png'), 'wb').write(shot)
        open(os.path.join(out_dir, '3d_log.txt'), 'w', encoding='utf-8').write('\n'.join(log))
    im = Image.open(io.BytesIO(shot)).convert('RGB')
    st = ImageStat.Stat(im.convert('L'))
    say('밝기', round(st.mean[0]), '대비', round(st.stddev[0]))
    open(os.path.join(out_dir, '3d_log.txt'), 'w', encoding='utf-8').write('\n'.join(log))
    if st.stddev[0] < 18 or st.mean[0] < 25: raise RuntimeError('3D 사진이 비어 보임')
    return im
