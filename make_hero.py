"""주요 지역 신고가 1위 카드 (hero.png, 1080×1350) – 아파트 3D 사진을 꽉 채운 배경 위에 글씨 (GitHub Actions, 매일).
사용법: python make_hero.py site/summary.json site/cards
- 대상: summary 'major_tops' 중 신고가인 거래 가운데 가장 비싼 1건. 없으면 아무것도 만들지 않음(hero.png 삭제).
- 배경: 국토교통부 브이월드(디지털트윈국토) 위성 사진 (공공누리 제1유형·출처표시).
  ① 브이월드 검색 API(VWORLD_KEY)로 단지 좌표 → ② 브이월드 위성 WMTS 타일로 단지 중심 사진
  ③ 단지 사진을 못 가져오면 일반 배경(자동 그림). 카드는 항상 만들어짐. (2단계: 3D 비스듬한 사진으로 교체 예정)
- 글씨: 단지명(흰 글씨 + 글로우), 가격(빨강), 위치·준공·층·이전 최고, 아래 표, 노란 버튼, 출처, @data_jaetech
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


def font_path(weight):
    for pat in [f'/usr/share/fonts/**/NotoSansCJK-{weight}.ttc', f'/usr/share/fonts/**/NotoSansCJKkr-{weight}.otf', f'/usr/share/fonts/**/*CJK*{weight}*']:
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


bg, src = None, ''
xy = geocode()
if xy:
    try:
        bg = satellite(*xy); src = '항공사진'
    except Exception as e:
        print('위성 사진을 못 받음:', str(e)[:200])
if bg is None:                                                  # 단지 사진을 못 가져오면 일반 배경
    bg, src = drawn_background(), ''
    print('단지 사진을 못 가져와 일반 배경으로 만듭니다')
r = max(W / bg.width, H / bg.height); bg = bg.resize((int(bg.width * r) + 1, int(bg.height * r) + 1), Image.LANCZOS)
x0, y0 = (bg.width - W) // 2, (bg.height - H) // 2
im = bg.crop((x0, y0, x0 + W, y0 + H))


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
credit = '자료 국토교통부 실거래가' + (f' · {src} 국토교통부 브이월드' if src else ' · 배경은 예시 그림')
text((60, 1282), credit, F(21, 'Medium'), WHITE, 3)
text((W - 60 - tl('@data_jaetech', F(26)), 1278), '@data_jaetech', F(26), WHITE, 3)
im.save(DST)
json.dump({'apt': T['apt'], 'region': T['region'], 'price_man': T['price_man'], 'area': T['area'], 'src': src or '그림'},
          open(os.path.join(OUT, 'hero.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('주요 지역 신고가 1위 카드 →', DST, '(배경:', src or '자동 그림', ')')
