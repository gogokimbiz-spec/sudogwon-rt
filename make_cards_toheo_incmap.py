"""토허제 40곳 지도 2개 나란히: 왼쪽 = 지난주 아파트값 변동률, 오른쪽 = 사는 곳 기준 평균 연봉 (2026-11-27 시안 2)
사용법: python make_cards_toheo_incmap.py OUT raw.json
  - make_cards_toheo_income.py 의 데이터(그룹·연봉)까지 불러 씀
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
_s = open(os.path.join(HERE, 'make_cards_toheo_income.py'), encoding='utf-8').read()
_s = _s[:_s.index('# ─────────────────────────── 카드')]
__file__ = os.path.join(HERE, 'make_cards_toheo_income.py')
exec(compile(_s, 'make_cards_toheo_income.py', 'exec'))

# 연봉 색 구간 (만원): 파랑 4단계 · 빨강 4단계, 가운데 ≈ 40곳 중앙값(약 4,950만)
INC_EDGES = [4000, 4500, 4800, 5000, 5500, 6000, 7000]
def inc_color(v):
    k = sum(v >= e for e in INC_EDGES)               # 0..7
    return (DNC[::-1] + UPC)[k]
INC_LAB = ['4천 미만', '', '', '5천', '', '', '7천 이상']


def draw_map2(im, box, colfn, valfn):
    geo = json.load(open(os.path.join(HERE, 'geo.json'), encoding='utf-8'))
    val = {r['code']: r for r in rows}
    polys = {}
    for f in geo['features']:
        g = f['geometry']; polys[f['properties']['c']] = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    pts = [p for c in val for pl in polys.get(c, []) for p in pl[0]]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts); y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    kx = math.cos(math.radians((y0 + y1) / 2)); bw, bh = box[2] - box[0], box[3] - box[1]; pad = 6
    s_ = min((bw - 2 * pad) / ((x1 - x0) * kx), (bh - 2 * pad) / (y1 - y0))
    ox = (bw - (x1 - x0) * kx * s_) / 2; oy = (bh - (y1 - y0) * s_) / 2
    P = lambda p: (ox + (p[0] - x0) * kx * s_, oy + (y1 - p[1]) * s_)
    layer = Image.new('RGB', (bw, bh), C.T['bg']); d = ImageDraw.Draw(layer)
    for c, pl in polys.items():
        if c in val: continue
        for poly in pl: d.polygon([P(p) for p in poly[0]], fill=OFF, outline=C.T['bg'])
    labels = []
    for c, r in val.items():
        if c not in polys: continue
        for poly in polys[c]: d.polygon([P(p) for p in poly[0]], fill=colfn(r), outline=C.T['bg'])
        big = max(polys[c], key=lambda q: len(q[0])); labels.append((centroid([P(p) for p in big[0]]), r))
    for c in val:
        for poly in polys.get(c, []):
            q = [P(p) for p in poly[0]]; d.line(q + [q[0]], fill=C.T['bg'], width=2)
    for (cx, cy), r in labels:
        t = r['short']; f = F(19 if len(t) <= 2 else 15, 'Black'); col = colfn(r)
        dx, dy = NUDGE.get(t, (0, 0)); dx, dy = dx * 0.9, dy * 0.9
        d.text((cx + dx - d.textlength(t, font=f) / 2, cy + dy - 11), t, font=f, fill=on(col))
    im.paste(layer, (box[0], box[1]))


def legend2(d, x, y, cols, left, right, mid=None):
    n = len(cols); w = 34
    for i, c in enumerate(cols): d.rectangle((x + i * w, y, x + i * w + w - 3, y + 16), fill=c)
    lf = F(17, 'Medium'); e = x + n * w
    d.text((x, y + 20), left, font=lf, fill=C.INK2)
    d.text((e - 3 - d.textlength(right, font=lf), y + 20), right, font=lf, fill=C.INK2)
    if mid: d.text((x + n * w / 2 - d.textlength(mid, font=lf) / 2, y + 20), mid, font=lf, fill=C.INK2)


im, d = C.canvas()
ink = C.INK
d.rectangle((40, 28, W - 40, 34), fill=ink); d.line((40, 40, W - 40, 40), fill=ink, width=2)
wd = '월화수목금토일'[pub_day.weekday()]
d.text((44, 50), f'{pub_day.year}년 {pub_day.month}월 {pub_day.day}일 ({wd})  ·  {base_day.month}월 {base_day.day}일 조사 · 한국부동산원 · 국세청',
       font=F(21, 'Medium'), fill=C.INK2)
d.line((40, 86, W - 40, 86), fill=ink, width=1)
d.text((40, 96), '집값 지도 vs 연봉 지도', font=FS(76, 'Black'), fill=ink)
d.line((40, 206, W - 40, 206), fill=ink, width=2); d.rectangle((40, 212, W - 40, 218), fill=ink)

# 지도 두 개 (11-27 사용자: 아래 표 삭제, 지도 크게) – 폭이 한계라 바깥 여백·가운데 틈을 줄임
mid = W // 2; GW = 5; L0, R1 = 12, W - 12
MW = mid - GW - L0; MH = int(MW * 1.345) + 12
MT = 316; MB_ = MT + MH
titles = ['전주대비 부동산 상승률', '평균 연봉']
subs = [f'{label} · 한국부동산원', '사는 곳 기준 · 2024년 · 국세청']
for k in range(2):
    x0 = 40 if k == 0 else mid + 16; x1 = mid - 16 if k == 0 else W - 40
    d.text((x0, 230), titles[k], font=FS(40, 'Black'), fill=ink)
    d.text((x0 + 2, 280 - 4), subs[k], font=F(19, 'Medium'), fill=C.INK2)
draw_map2(im, (L0, MT, mid - GW, MB_), lambda r: color(r['chg']), None)
draw_map2(im, (mid + GW, MT, R1, MB_), lambda r: inc_color(r['income']), None)
d = ImageDraw.Draw(im)
d.line((mid, 232, mid, MB_ + 150), fill=C.T['line'], width=2)
legend2(d, 50, MB_ + 22, DNC[::-1] + [FLAT] + UPC, '하락', '상승', '보합')
legend2(d, mid + 30, MB_ + 22, DNC[::-1] + UPC, '4천만 미만', '7천만 이상', '5천만')
up3 = ' · '.join(r['short'] for r in rows[:3])
inc3 = ' · '.join(r['short'] for r in sorted(rows, key=lambda r: -r['income'])[:3])
for k, (t1, t2) in enumerate((('가장 많이 오른 곳', up3), ('연봉 가장 높은 곳', inc3))):
    x = 50 if k == 0 else mid + 30
    d.text((x, MB_ + 84), t1, font=F(20, 'Medium'), fill=C.INK2)
    d.text((x, MB_ + 110), t2, font=FS(30, 'Black'), fill=ink)
d.line((40, 1244, W - 40, 1244), fill=ink, width=2)
d.text((44, 1252), '연봉 = 국세청 2024년 귀속 근로소득 연말정산(사는 곳 기준) 1인당 평균 총급여 · 경기 일반구는 소속 시 값',
       font=F(17, 'Medium'), fill=C.INK2)
d.line((40, 1290, W - 40, 1290), fill=ink, width=2)
C.footer(d, F, '자료 한국부동산원 주간아파트가격동향 · 국세청 국세통계')
import random
random.seed(7); g_ = Image.effect_noise((W // 2, SH // 2), 18).resize((W, SH)).convert('L')
im = Image.composite(im, Image.blend(im, Image.new('RGB', (W, SH), (120, 100, 70)), 0.06), g_.point(lambda v: 255 if v > 120 else 200))
im.save(os.path.join(OUT, 'card_incmap.png')); print('카드 →', os.path.join(OUT, 'card_incmap.png'))
