"""주요 지역 신고가 1위 카드 (hero.png, 1080×1350) – 아파트 3D 사진을 꽉 채운 배경 위에 글씨 (GitHub Actions, 매일).
사용법: python make_hero.py site/summary.json site/cards
- 대상: summary 'major_tops' 중 신고가인 거래 가운데 가장 비싼 1건. 없으면 아무것도 만들지 않음(hero.png 삭제).
- 배경: 국토교통부 브이월드(디지털트윈국토) 위성 사진 (공공누리 제1유형·출처표시).
  ① 브이월드 검색 API(VWORLD_KEY)로 단지 좌표 → ② 브이월드 위성 WMTS 타일로 단지 중심 사진
  ③ 단지 사진을 못 가져오면 일반 배경(자동 그림). 카드는 항상 만들어짐.
  ※ 브이월드는 해외(GitHub 서버) 접속을 막아서, 사진 카드는 PC 실행기(hero_photo.yml)가 HERO_PHOTO_ONLY=1 로 다시 만듭니다. (2단계: 3D 비스듬한 사진으로 교체 예정)
- 글씨: 단지명(흰 글씨 + 글로우), 가격(빨강), 위치·준공·층·이전 최고, 같은 면적 3년 거래 그래프(반투명 판), 아래 표, 노란 버튼, 출처, @data_jaetech
필요: Pillow, 한글 폰트, 환경변수 VWORLD_KEY (없으면 일반 배경)
"""
import os, sys, json, glob, random, datetime, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat

S = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
DST = os.path.join(OUT, 'hero.png')
if os.path.exists(DST): os.remove(DST)
KEY = os.environ.get('VWORLD_KEY', '').strip()
W, H = 1080, 1350
RED, WHITE, INK, YEL = (255, 45, 61), (255, 255, 255), (30, 34, 40), (255, 204, 0)

cand = [t for t in (S.get('major_tops') or []) if t.get('new_high')]
if not cand:
    print('오늘은 주요 지역 신고가가 없어 1위 카드를 만들지 않습니다'); sys.exit(0)
T = max(cand, key=lambda t: t['price_man'])
DAY = datetime.date.fromisoformat(S['day'])
print('주요 지역 신고가 1위:', T['region'], T['apt'], T['area'], T['price_man'])


HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO_ONLY = os.environ.get('HERO_PHOTO_ONLY') == '1'          # PC 실행기용: 단지 사진을 못 받으면 카드를 만들지 않음


def font_path(weight):
    for pat in [os.path.join(HERE, 'fonts', f'NotoSansCJKkr-{weight}.otf'), f'/usr/share/fonts/**/NotoSansCJK-{weight}.ttc', f'/usr/share/fonts/**/NotoSansCJKkr-{weight}.otf', f'/usr/share/fonts/**/*CJK*{weight}*']:
        hits = glob.glob(pat, recursive=True)
        if hits: return hits[0]
    raise SystemExit('한글 폰트(Noto Sans CJK)를 찾지 못했습니다')
_fc = {}
def F(size, weight='Bold'):
    if (size, weight) in _fc: return _fc[size, weight]
    p = font_path(weight); f = None
    if p.endswith('.ttc'):
        for i in range(10):
            try:
                g = ImageFont.truetype(p, size, index=i)
                if 'KR' in g.getname()[0]: f = g; break
            except Exception: break
    _fc[size, weight] = f or ImageFont.truetype(p, size)
    return _fc[size, weight]
def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}' if m else f'{e}억') if e else f'{m:,}만'
def man_unit(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}만' if m else f'{e}억') if e else f'{m:,}만'


# ── 1. 단지 좌표 (브이월드 검색 API)
def geocode():
    if not KEY: return None
    city = T['region'].split(' ')[0]
    for q in (T['apt'], f"{T.get('umd', '')} {T['apt']}", f"{T['apt']} 아파트"):
        url = 'https://api.vworld.kr/req/search?' + urllib.parse.urlencode({
            'service': 'search', 'request': 'search', 'version': '2.0', 'crs': 'EPSG:4326', 'size': 10, 'page': 1,
            'query': q.strip(), 'type': 'place', 'format': 'json', 'errorformat': 'json', 'key': KEY,
            'domain': 'https://gogokimbiz-spec.github.io'})
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'Referer': 'https://gogokimbiz-spec.github.io/'}), timeout=30))
            items = ((r.get('response') or {}).get('result') or {}).get('items') or []
        except Exception as e:
            print('브이월드 검색 실패:', str(e)[:150]); items = []
        def score(it):
            a = json.dumps(it.get('address') or {}, ensure_ascii=False) + (it.get('title') or '')
            return (T.get('umd', '') in a) * 2 + (city in a) + ('아파트' in (it.get('category') or '') or '아파트' in a)
        items = sorted(items, key=score, reverse=True)
        if items and score(items[0]) >= 2:
            p = items[0]['point']; print('좌표:', items[0].get('title'), p); return float(p['x']), float(p['y'])
    return None


# ── 2. 브이월드 위성(항공) 사진 – 공식 WMTS 타일을 받아 단지 중심으로 이어 붙임 (1단계. 3D 비스듬한 사진은 2단계에서)
import math, io
def satellite(lon, lat, z=18):
    n = 2 ** z
    fx = (lon + 180) / 360 * n
    fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    cx, cy = fx * 256, fy * 256                                  # 전체 픽셀 좌표
    need_w, need_h = int(W * 0.8), int(H * 0.8)                  # 조금 작게 받아 키움(너무 확대돼 흐려지지 않게)
    x0, y0 = int(cx - need_w / 2), int(cy - need_h / 2)
    tx0, ty0, tx1, ty1 = x0 // 256, y0 // 256, (x0 + need_w) // 256, (y0 + need_h) // 256
    canvas = Image.new('RGB', ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    ok = 0
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            url = f'https://api.vworld.kr/req/wmts/1.0.0/{KEY}/Satellite/{z}/{ty}/{tx}.jpeg'
            try:
                data = urllib.request.urlopen(urllib.request.Request(url, headers={'Referer': 'https://gogokimbiz-spec.github.io/'}), timeout=30).read()
                canvas.paste(Image.open(io.BytesIO(data)).convert('RGB'), ((tx - tx0) * 256, (ty - ty0) * 256)); ok += 1
            except Exception as e:
                print('위성 타일 실패:', tx, ty, str(e)[:80])
    total = (tx1 - tx0 + 1) * (ty1 - ty0 + 1)
    if ok < total * 0.9: raise RuntimeError(f'위성 타일 {ok}/{total}장만 받음')
    im = canvas.crop((x0 - tx0 * 256, y0 - ty0 * 256, x0 - tx0 * 256 + need_w, y0 - ty0 * 256 + need_h))
    st = ImageStat.Stat(im.convert('L'))
    if st.stddev[0] < 12: raise RuntimeError('위성 사진이 비어 보임')
    return im


def drawn_background():                                        # 마지막 대안: 자동 그림
    im = Image.new('RGB', (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        a = y / H; d.line((0, y, W, y), fill=tuple(int(c0 + (c1 - c0) * a) for c0, c1 in zip((92, 130, 170), (236, 196, 150))))
    random.seed(T['apt'])
    for layer, (col, win, lo, hi, n) in enumerate([((120, 128, 140), (160, 168, 180), 380, 620, 9), ((60, 66, 76), (255, 214, 120), 560, 900, 6)]):
        for k in range(n):
            x = k * (W // n) + random.randint(-20, 20); w = W // n - 20; top = H - random.randint(lo, hi)
            d.rectangle((x, top, x + w, H), fill=col)
            for yy in range(top + 24, H - 20, 30):
                for xx in range(x + 12, x + w - 14, 24):
                    if random.random() < 0.55: d.rectangle((xx, yy, xx + 11, yy + 14), fill=win)
    return im



# ── 2-2. 일반 지도 + 단지 노란 테두리 (2026-11-12 사용자 확정: 3D 대신 지도, 아파트는 노란 테두리로 표시)
def _ref_get(url, timeout=30):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'Referer': 'https://gogokimbiz-spec.github.io/'}), timeout=timeout).read()

def _in_poly(x, y, ring):
    ins = False; j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi: ins = not ins
        j = i
    return ins

def parcels(lon, lat):
    """단지가 있는 필지(연속지적도) 테두리들 [[(lon,lat),...], ...]. 못 받으면 []"""
    d = 0.0016
    url = 'https://api.vworld.kr/req/data?' + urllib.parse.urlencode({
        'service': 'data', 'request': 'GetFeature', 'data': 'LP_PA_CBND_BUBUN', 'key': KEY, 'format': 'json', 'geometry': 'true', 'attribute': 'true',
        'crs': 'EPSG:4326', 'size': 100, 'geomFilter': f'BOX({lon - d},{lat - d},{lon + d},{lat + d})', 'domain': 'https://gogokimbiz-spec.github.io'})
    try:
        r = json.loads(_ref_get(url).decode('utf-8'))
        feats = (((r.get('response') or {}).get('result') or {}).get('featureCollection') or {}).get('features') or []
    except Exception as e:
        print('필지 경계 실패:', str(e)[:150]); return []
    def rings(f):
        g = f.get('geometry') or {}; c = g.get('coordinates') or []
        polys = c if g.get('type') == 'MultiPolygon' else [c]
        return [[(float(a), float(b)) for a, b in pg[0]] for pg in polys if pg]
    hit = None
    for f in feats:
        if any(_in_poly(lon, lat, rg) for rg in rings(f)): hit = f; break
    if not hit: print('좌표가 든 필지를 못 찾음 (후보 %d개)' % len(feats)); return []
    jb = str((hit.get('properties') or {}).get('jibun', '')).split('-')[0].split(' ')[0]   # 같은 본번 필지(단지가 여러 필지일 때)
    umd_key = str((hit.get('properties') or {}).get('addr', '')).rsplit(' ', 1)[0]
    out = []
    for f in feats:
        pr = f.get('properties') or {}
        if f is hit or (jb and str(pr.get('jibun', '')).split('-')[0].split(' ')[0] == jb and str(pr.get('addr', '')).rsplit(' ', 1)[0] == umd_key):
            out += rings(f)
    print('필지 테두리', len(out), '개, 지번', (hit.get('properties') or {}).get('jibun'))
    return out

def _px(lon, lat, z):
    n = 2 ** z
    return (lon + 180) / 360 * n * 256, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n * 256

def map_card(lon, lat):
    rs = parcels(lon, lat)
    z = 18
    if rs:
        xs = [_px(a, b, 18)[0] for rg in rs for a, b in rg]; ys = [_px(a, b, 18)[1] for rg in rs for a, b in rg]
        if max(xs) - min(xs) > 520 or max(ys) - min(ys) > 400: z = 17
        ccx, ccy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        cx, cy = _px(lon, lat, 18); scale = 2 ** (z - 18); ccx, ccy = ccx * scale, ccy * scale
    else:
        ccx, ccy = _px(lon, lat, z)
    AX, AY = 420, 565                                         # 단지가 오는 화면 위치 (글씨·그래프와 안 겹치게 왼쪽 가운데)
    x0, y0 = int(ccx - AX), int(ccy - AY)
    tx0, ty0, tx1, ty1 = x0 // 256, y0 // 256, (x0 + W) // 256, (y0 + H) // 256
    canvas = Image.new('RGB', ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256), (235, 232, 224)); ok = 0
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            try:
                data = _ref_get(f'https://api.vworld.kr/req/wmts/1.0.0/{KEY}/Base/{z}/{ty}/{tx}.png')
                canvas.paste(Image.open(io.BytesIO(data)).convert('RGB'), ((tx - tx0) * 256, (ty - ty0) * 256)); ok += 1
            except Exception as e:
                print('지도 타일 실패:', tx, ty, str(e)[:80])
    total = (tx1 - tx0 + 1) * (ty1 - ty0 + 1)
    if ok < total * 0.9: raise RuntimeError(f'지도 타일 {ok}/{total}장만 받음')
    im0 = canvas.crop((x0 - tx0 * 256, y0 - ty0 * 256, x0 - tx0 * 256 + W, y0 - ty0 * 256 + H)).convert('RGBA')
    if ImageStat.Stat(im0.convert('L')).stddev[0] < 6: raise RuntimeError('지도가 비어 보임')
    # 글씨가 잘 읽히게 위·아래를 어둡게 (가운데 단지 주변은 밝게 유지)
    ov = Image.new('RGBA', (W, H)); od = ImageDraw.Draw(ov)
    for yy in range(H):
        a = 125 if yy < 380 else (125 - int(85 * (yy - 380) / 120) if yy < 500 else (40 if yy < 720 else (40 + int(70 * min(1, (yy - 720) / 120)))))
        od.line((0, yy, W, yy), fill=(0, 0, 0, a))
    im0.alpha_composite(ov)
    ly = Image.new('RGBA', (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(ly)
    def to_scr(a, b):
        px, py = _px(a, b, z); return (px - x0, py - y0)
    if rs:
        for rg in rs:
            pts = [to_scr(a, b) for a, b in rg]
            g.polygon(pts, fill=(255, 214, 0, 80))
            g.line(pts + [pts[0]], fill=(70, 55, 0, 200), width=15, joint='curve')
            g.line(pts + [pts[0]], fill=(255, 214, 0, 255), width=9, joint='curve')
        sx = [to_scr(a, b) for rg in rs for a, b in rg]
        top = (sum(p[0] for p in sx) / len(sx), min(p[1] for p in sx))
    else:                                                       # 필지를 못 받으면 노란 원
        cxp, cyp = to_scr(lon, lat); rad = 95 * (2 ** (z - 18)) * 1.0
        g.ellipse((cxp - rad, cyp - rad, cxp + rad, cyp + rad), fill=(255, 214, 0, 80), outline=(255, 214, 0, 255), width=9)
        top = (cxp, cyp - rad)
    nm = T['apt'] if len(T['apt']) <= 12 else T['apt'][:11] + '…'
    f = F(30, 'Black'); tw = g.textlength(nm, font=f); px_, py_ = min(max(top[0], tw / 2 + 24), W - tw / 2 - 24), max(top[1] - 20, 380)
    g.rounded_rectangle((px_ - tw / 2 - 18, py_ - 56, px_ + tw / 2 + 18, py_ - 6), 14, fill=(28, 28, 34, 240))
    g.polygon([(px_ - 14, py_ - 7), (px_ + 14, py_ - 7), (px_, py_ + 14)], fill=(28, 28, 34, 240))
    g.text((px_ - tw / 2, py_ - 51), nm, font=f, fill=(255, 255, 255, 255))
    im0.alpha_composite(ly)
    return im0.convert('RGB')

bg, src = None, ''
xy = geocode()
if xy and (os.environ.get('HERO_3D') == '1' or os.environ.get('HERO_MAP') == '1'):   # PC 실행기: 일반 지도 + 노란 테두리 (3D 는 건물이 입체로 안 나와 폐기)
    for attempt in (1, 2, 3):
        try:
            bg = map_card(*xy); src = '지도'; break
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f'지도 만들기 {attempt}번째 실패:', str(e)[:300])
if bg is None and PHOTO_ONLY:
    print('단지 사진을 못 받아 사진 카드를 만들지 않습니다 (새벽에 만든 일반 배경 카드를 그대로 씀)'); sys.exit(0)
if bg is None:                                                  # 단지 사진을 못 가져오면 일반 배경
    bg, src = drawn_background(), ''
    print('단지 사진을 못 가져와 일반 배경으로 만듭니다')
r = max(W / bg.width, H / bg.height); bg = bg.resize((int(bg.width * r) + 1, int(bg.height * r) + 1), Image.LANCZOS)
x0, y0 = (bg.width - W) // 2, (bg.height - H) // 2
im = bg.crop((x0, y0, x0 + W, y0 + H))


# ── 2-1. 같은 단지·면적 최근 3년 거래 (hist/ + rt_data.json, PC 에서는 새벽 카드가 저장한 값 HERO_SERIES 사용)
import statistics
def hero_series():
    sf = os.environ.get('HERO_SERIES', '')
    if sf and os.path.exists(sf):
        try: return [(datetime.date.fromisoformat(a), b) for a, b in json.load(open(sf, encoding='utf-8'))]
        except Exception: pass
    try: code = {v: k for k, v in json.load(open(os.path.join(HERE, 'names.json'), encoding='utf-8')).items()}.get(T['region'])
    except Exception: code = None
    if not code: return []
    apt, umd, ar = T['apt'], T.get('umd', ''), round(T['area'])
    cut = (DAY - datetime.timedelta(365 * 3)).isoformat()
    pts = set()
    try:
        for r in json.load(open('rt_data.json', encoding='utf-8'))['trade']:   # [code, date, apt, umd, area, floor, price, built, 해제]
            if r[0] == code and r[2] == apt and r[3] == umd and round(r[4]) == ar and r[8] != 'O' and r[1] >= cut: pts.add((r[1], r[5], r[6]))
    except Exception: pass
    for f in glob.glob(os.path.join('hist', code, '*.json')):
        try:
            for r in json.load(open(f, encoding='utf-8')):                      # [date, apt, umd, area, floor, price, 해제]
                if r[1] == apt and r[2] == umd and round(r[3]) == ar and r[6] != 'O' and r[0] >= cut: pts.add((r[0], r[4], r[5]))
        except Exception: pass
    return sorted((datetime.date.fromisoformat(dt), p) for dt, fl, p in pts)
SERIES = hero_series()
if all(not (p == T['price_man'] and dt == DAY) for dt, p in SERIES): SERIES = sorted(SERIES + [(DAY, T['price_man'])])
print('3년 거래 그래프 점:', len(SERIES))


def eok(v):
    return (f'{v / 10000:.1f}억'.replace('.0억', '억')) if v >= 10000 else f'{v / 10000:.2f}억'


def hero_chart(box):                                           # 반투명 어두운 판 위에 3년 거래 흐름
    global im
    bx0, by0, bx1, by1 = box
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(box, 22, fill=(18, 22, 28, 200))
    base = im.convert('RGBA'); base.alpha_composite(ov); im = base.convert('RGB'); d = ImageDraw.Draw(im)
    pts = SERIES
    t0, t1 = pts[0][0], pts[-1][0]
    ps = [p for _, p in pts]; lo, hi = min(ps), max(ps); pad = (hi - lo) * 0.15 or hi * 0.05; lo -= pad; hi += pad
    x0, x1, y0, y1 = bx0 + 100, bx1 - 30, by0 + 70, by1 - 44
    X = lambda t: x0 + (t - t0).days / max(1, (t1 - t0).days) * (x1 - x0)
    Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    mon = {}
    for t, v in pts: mon.setdefault((t.year, t.month), []).append(v)
    first, last = statistics.median(mon[min(mon)]), statistics.median(mon[max(mon)])
    nmon = (t1.year - t0.year) * 12 + t1.month - t0.month
    chg = (last / first - 1) * 100
    d.text((bx0 + 26, by0 + 18), '3년 거래 흐름', font=F(30, 'Black'), fill=WHITE)
    per = f"최근 {round(nmon / 12)}년" if nmon >= 24 else f"최근 {max(1, nmon)}개월"
    s2 = f"{per} {'+' if chg >= 0 else ''}{chg:.0f}% · {len(pts)}건"
    sf = F(27); col = (255, 90, 100) if chg >= 0 else (110, 170, 255)
    if len(pts) < 3: s2, col = f"최근 3년 거래 {len(pts)}건", (210, 216, 224)     # 거래가 적으면 상승률 대신 건수만
    d.text((bx1 - 26 - d.textlength(s2, font=sf), by0 + 21), s2, font=sf, fill=col)
    for k in range(3):
        v = lo + (hi - lo) * (k + 0.5) / 3; yy = Y(v)
        d.line((x0, yy, x1, yy), fill=(70, 78, 90), width=1)
        d.text((bx0 + 24, yy - 14), eok(v), font=F(22, 'Medium'), fill=(190, 198, 208))
    clamp = lambda t: min(max(t, t0), t1)
    line = [(X(clamp(datetime.date(y, m, 15))), Y(statistics.median(v))) for (y, m), v in sorted(mon.items())]
    for t, v in pts: d.ellipse((X(t) - 4, Y(v) - 4, X(t) + 4, Y(v) + 4), fill=(150, 160, 172))
    if len(line) > 1: d.line(line, fill=WHITE, width=4, joint='curve')
    hx, hy = X(DAY), Y(T['price_man']); d.ellipse((hx - 12, hy - 12, hx + 12, hy + 12), fill=RED, outline=WHITE, width=3)
    for t, right_ in ((t0, False), (t1, True)):
        s_ = f"{t.year % 100}.{t.month}"; w_ = d.textlength(s_, font=F(22, 'Medium'))
        d.text((x1 - w_ if right_ else x0, y1 + 10), s_, font=F(22, 'Medium'), fill=(190, 198, 208))


# ── 3. 글씨
def text(xy, s, f, fill, stroke=5):                            # 사진 위에서도 읽히게 테두리 + 그림자
    global im
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0] + 3, xy[1] + 4), s, font=f, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    base = im.convert('RGBA'); base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4))); im = base.convert('RGB')
    ImageDraw.Draw(im).text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(20, 22, 26))
def glow(xy, s, f, fill):                                      # 단지명: 흰 글로우
    global im
    g = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).text(xy, s, font=f, fill=(255, 255, 255, 230), stroke_width=6, stroke_fill=(255, 255, 255, 230))
    g = g.filter(ImageFilter.GaussianBlur(12)); base = im.convert('RGBA')
    for _ in range(2): base.alpha_composite(g)
    im = base.convert('RGB'); ImageDraw.Draw(im).text(xy, s, font=f, fill=fill, stroke_width=3, stroke_fill=(20, 22, 26))
tl = lambda s, f: ImageDraw.Draw(im).textlength(s, font=f)

text((60, 50), f'주요 지역 신고가 1위 · {DAY.month}월 {DAY.day}일 계약', F(36), WHITE, 4)
size = 76
while size > 48 and tl(T['apt'], F(size, 'Black')) > W - 120: size -= 4
glow((56, 104 + (76 - size) // 2), T['apt'], F(size, 'Black'), WHITE)
pr = man(T['price_man'])
text((56, 200), pr, F(110, 'Black'), RED, 7)
sub = f"전용 {T['area']}㎡ · 신고가"
sx = 56 + tl(pr, F(110, 'Black')) + 30
if sx + tl(sub, F(44)) > W - 40: sx, sy = 60, 345
else: sy = 250
text((sx, sy), sub, F(44), WHITE, 5)
p_ = T['region'].split(' ')
place = f"{T['region']} {T.get('umd', '')}".strip()
prev = T['prev_high_man']; pd = datetime.date.fromisoformat(T['prev_high_date'])
for j, s in enumerate([place, f"{T['built']}년 준공 · {T['floor']}층", f"이전 최고 {man_unit(prev)} ({pd.month}.{pd.day})"]):
    f = F(40, 'Black') if j == 0 else F(36); text((W - 60 - tl(s, f), 420 + j * 56), s, f, WHITE, 5)
if SERIES:                                                     # 그래프는 항상 (거래가 이번 1건뿐이어도)
    hero_chart((60, 744, 700, 994))                            # 표 바로 위, 왼쪽에 좁게 (사진이 더 보이게)
d = ImageDraw.Draw(im)
diff = T['price_man'] - prev
cols = [('전용', f"{T['area']}㎡"), ('층', f"{T['floor']}층"), ('거래가', man(T['price_man'])), ('계약일', f'{DAY.month}.{DAY.day}'), ('상승', f'▲{man_unit(diff)}')]
ty = 1010; cw = (W - 120) / len(cols)
for k, (h, v) in enumerate(cols):
    x = 60 + k * cw; vf = F(36, 'Black')
    while d.textlength(v, font=vf) > cw - 20 and vf.size > 22: vf = F(vf.size - 2, 'Black')
    d.rectangle((x, ty, x + cw - 6, ty + 54), fill=INK); d.text((x + (cw - 6 - d.textlength(h, font=F(28))) / 2, ty + 9), h, font=F(28), fill=WHITE)
    d.rectangle((x, ty + 54, x + cw - 6, ty + 128), fill=WHITE)
    d.text((x + (cw - 6 - d.textlength(v, font=vf)) / 2, ty + 91 - vf.size * 0.62), v, font=vf, fill=(210, 40, 40) if k >= 2 else INK)
d.rounded_rectangle((60, 1172, W - 60, 1252), 40, fill=YEL)
m = '오늘의 실거래 전체 → 프로필 링크'; d.text(((W - d.textlength(m, font=F(36))) / 2, 1188), m, font=F(36), fill=INK)
credit = '자료 국토교통부 실거래가' + (' · 지도 국토교통부 브이월드' if src else ' · 배경은 예시 그림')
text((60, 1282), credit, F(21, 'Medium'), WHITE, 3)
text((W - 60 - tl('@data_jaetech', F(26)), 1278), '@data_jaetech', F(26), WHITE, 3)
im.save(DST)
im.convert('RGB').save(os.path.join(OUT, 'hero.jpg'), quality=90)   # 인스타·카톡용
json.dump({'apt': T['apt'], 'region': T['region'], 'umd': T.get('umd', ''), 'price_man': T['price_man'], 'area': T['area'], 'floor': T['floor'],
           'built': T['built'], 'prev_high_man': T['prev_high_man'], 'day': S['day'], 'src': src or '그림',
           'series': [[a.isoformat(), b] for a, b in SERIES]},
          open(os.path.join(OUT, 'hero.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('주요 지역 신고가 1위 카드 →', DST, '(배경:', src or '자동 그림', ')')
