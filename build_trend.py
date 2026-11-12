"""시군구(구)별 아파트값 상승률 – 주간(최근 4주 vs 직전 4주) · 월간(지난달 vs 그 전달) (GitHub Actions 용, 매일 계산).
사용법: python build_trend.py rt_data.json site
결과: site/trend/summary.json, site/trend/week.png (상승·하락 TOP 5 카드), site/trend/month.png (색칠한 지도 카드)
- 값: 구마다 기간 안 매매 거래의 3.3㎡당 가격 중앙값 (해제 신고 제외). 두 기간 모두 거래 MIN_N 건 이상인 구만 순위에 넣음.
- 주간: 실행일 직전 일요일까지 4주(28일) vs 그 앞 4주. 월간: 실행일 기준 지난달 vs 그 전달.
- 실거래는 계약 후 30일 안에 신고하므로 최근 기간은 건수가 계속 늘어남(잠정치).
"""
import os, sys, json, glob, statistics, datetime
os.environ.setdefault('CARD_THEME', 'slate')   # 실거래 카드와 같은 테마
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
raw = json.load(open(sys.argv[1], encoding='utf-8'))
SITE = sys.argv[2]; OUT = os.path.join(SITE, 'trend'); os.makedirs(OUT, exist_ok=True)
names = json.load(open(os.path.join(HERE, 'names.json'), encoding='utf-8'))
geo = json.load(open(os.path.join(HERE, 'geo.json'), encoding='utf-8'))
codes = [f['properties']['c'] for f in geo['features']]
MIN_N = int(os.environ.get('TREND_MIN_N', '10') or 10)
PY = 3.3058
D = datetime.date.fromisoformat
asof = D((raw.get('asof') or datetime.date.today().isoformat())[:10])

# 거래: (코드, 날짜, 3.3㎡당 만원)
T = []
for code, date, apt, umd, area, floor, price, by, cd in raw['trade']:
    if cd == 'O' or code not in names or area <= 0 or price <= 0: continue
    T.append((code, D(date), price / area * PY))


def stat(a, b):
    """기간 [a, b] 의 구별 (중앙값, 건수)"""
    v = {}
    for c, d, p in T:
        if a <= d <= b: v.setdefault(c, []).append(p)
    return {c: (statistics.median(x), len(x)) for c, x in v.items()}


def sido_stat(a, b):
    out = {}
    for s, nm in (('11', '서울'), ('28', '인천'), ('41', '경기')):
        x = [p for c, d, p in T if a <= d <= b and c.startswith(s)]
        out[nm] = (statistics.median(x), len(x)) if x else (None, 0)
    x = [p for c, d, p in T if a <= d <= b]
    out['수도권'] = (statistics.median(x), len(x)) if x else (None, 0)
    return out


def compare(a1, b1, a0, b0):
    cur, prev = stat(a1, b1), stat(a0, b0)
    rows = []
    for c in codes:
        if c in cur and c in prev and cur[c][1] >= MIN_N and prev[c][1] >= MIN_N:
            rows.append({'code': c, 'region': names[c], 'pp_cur': round(cur[c][0]), 'pp_prev': round(prev[c][0]),
                         'n_cur': cur[c][1], 'n_prev': prev[c][1], 'chg': round((cur[c][0] / prev[c][0] - 1) * 100, 1)})
    rows.sort(key=lambda r: -r['chg'])
    sc, sp = sido_stat(a1, b1), sido_stat(a0, b0)
    sido = {k: {'pp_cur': round(sc[k][0]) if sc[k][0] else None, 'n_cur': sc[k][1],
                'chg': round((sc[k][0] / sp[k][0] - 1) * 100, 1) if sc[k][0] and sp[k][0] else None} for k in sc}
    return rows, sido


# ── 주간: 직전 일요일까지 4주 vs 그 앞 4주
sun = asof - datetime.timedelta(days=asof.weekday() + 1)
mon = sun + datetime.timedelta(1)                    # 이 주(글 올리는 주)의 월요일
w1a, w1b = sun - datetime.timedelta(27), sun
w0a, w0b = sun - datetime.timedelta(55), sun - datetime.timedelta(28)
wrows, wsido = compare(w1a, w1b, w0a, w0b)
week = {'key': f'{mon.isoformat()}_week', 'label': f'{mon.month}월 {(mon.day - 1) // 7 + 1}주차',
        'cur': [w1a.isoformat(), w1b.isoformat()], 'prev': [w0a.isoformat(), w0b.isoformat()], 'rows': wrows, 'sido': wsido}

# ── 월간: 지난달 vs 그 전달 + 최근 6개월 추이
def month_range(y, m):
    a = datetime.date(y, m, 1)
    b = (datetime.date(y + (m == 12), m % 12 + 1, 1) - datetime.timedelta(1))
    return a, b
def add_month(y, m, k):
    t = y * 12 + (m - 1) + k
    return t // 12, t % 12 + 1
ly, lm = add_month(asof.year, asof.month, -1)
py_, pm = add_month(ly, lm, -1)
m1a, m1b = month_range(ly, lm); m0a, m0b = month_range(py_, pm)
mrows, msido = compare(m1a, m1b, m0a, m0b)
first = min(d for _, d, _ in T)
months = []
for k in range(5, -1, -1):
    y, m = add_month(ly, lm, -k)
    a, b = month_range(y, m)
    if a >= first: months.append((y, m, a, b))
series = {}
for nm in ('수도권', '서울', '인천', '경기'):
    series[nm] = []
for y, m, a, b in months:
    s = sido_stat(a, b)
    for nm in series: series[nm].append({'month': f'{y}-{m:02d}', 'pp': round(s[nm][0]) if s[nm][0] else None, 'n': s[nm][1]})
month = {'key': f'{ly}-{lm:02d}_month', 'label': f'{ly}년 {lm}월', 'cur': [m1a.isoformat(), m1b.isoformat()],
         'prev': [m0a.isoformat(), m0b.isoformat()], 'rows': mrows, 'sido': msido, 'series': series}

summary = {'asof': asof.isoformat(), 'min_n': MIN_N, 'week': week, 'month': month}
json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"주간 {week['label']} ({week['cur'][0]}~{week['cur'][1]} vs {week['prev'][0]}~{week['prev'][1]}): {len(wrows)}곳")
print(f"월간 {month['label']} vs 전월: {len(mrows)}곳, 6개월 추이 {len(months)}개월")

# ─────────────────────────── 카드 이미지 ───────────────────────────
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
import card_style as C
W, SH = C.W, C.SH
def short(r):   # '서울 강남구'→'강남구', '성남 분당구'→'성남 분당', '광명시'→'광명'
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' and len(p[0]) > 2 else p[0]
    if p[0] in ('서울', '인천'): return p[1] if len(p[1]) > 2 else f'{p[0]} {p[1]}'   # '서구'·'중구'는 앞에 시 이름
    return f'{p[0]} {p[1][:-1]}'
def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}만' if m else f'{e}억') if e else f'{m:,}만'
md = lambda s: f'{D(s).month}.{D(s).day}'
pct = lambda v: f'{v:+.1f}%'


def week_card():
    if not wrows: return
    up = [r for r in wrows if r['chg'] > 0][:5]; dn = [r for r in wrows[::-1] if r['chg'] < 0][:5]
    im, d = C.canvas()
    C.header(d, F, f"{week['label']} · 최근 4주", '구별 아파트값 상승률', '',
             f"{md(week['cur'][0])}~{md(week['cur'][1])} vs {md(week['prev'][0])}~{md(week['prev'][1])} · 3.3㎡당 중앙값")
    secs = [('상승 TOP', up, C.UP), ('하락 TOP', dn, C.DOWN)]
    secs = [s for s in secs if s[1]]
    n = sum(len(s[1]) for s in secs)
    rh = min(92, (SH - 180 - 340 - 58 * len(secs) - 20) // max(1, n))   # 한 줄짜리 행
    y = 340
    for si, (title, rows, col) in enumerate(secs):
        if si: y += 20
        d.text((64, y), f'{title} {len(rows)}', font=F(34, 'Black'), fill=col)
        y += 58
        for i, r in enumerate(rows, 1):
            C.row_box(d, y, rh - 8); cy = y + (rh - 8) // 2
            d.text((64, cy - 22), f'{i}', font=F(36, 'Black'), fill=C.INK)
            cw = C.chip(d, F, 104, cy - 21, short(r['region']), 28)
            d.text((104 + cw + 16, cy - 15), f"3.3㎡당 {man(r['pp_cur'])} · {r['n_cur']}건", font=F(24, 'Medium'), fill=C.INK2)
            v = pct(r['chg']); vf = F(46, 'Black')
            d.text((W - 64 - d.textlength(v, font=vf), cy - 30), v, font=vf, fill=col)
            y += rh
    C.cta(d, F, '구별 전체 순위 → 프로필 링크')
    C.footer(d, F, f'자료 국토교통부 실거래가 · 두 기간 모두 거래 {MIN_N}건 이상 지역')
    im.save(os.path.join(OUT, 'week.png')); print('주간 카드 → trend/week.png')


# 지도 색 (지도 사이트와 같은 구간: ±1 보합, 3, 6, 10%)
UPC = [(248, 198, 192), (236, 133, 122), (212, 68, 58), (158, 28, 28)]
DNC = [(198, 217, 244), (130, 170, 228), (59, 116, 204), (27, 69, 148)]
def color(v):
    if v is None: return (90, 99, 110)
    a = abs(v)
    if a <= 1: return (245, 245, 245)
    k = 0 if a <= 3 else 1 if a <= 6 else 2 if a <= 10 else 3
    return (UPC if v > 0 else DNC)[k]


def month_card():
    if not mrows: return
    chg = {r['code']: r['chg'] for r in mrows}
    im, d = C.canvas()
    sd = month['sido']['수도권']
    C.header(d, F, f"{month['label']} · 전월 대비", '구별 아파트값 변동', pct(sd['chg']) if sd['chg'] is not None else '',
             f"3.3㎡당 매매가 중앙값 · 거래 {MIN_N}건 이상 지역만 색칠 (잠정)")
    # 지도 투영
    pts = [pt for f in geo['features'] for ring in (f['geometry']['coordinates'] if f['geometry']['type'] == 'Polygon'
           else [r for poly in f['geometry']['coordinates'] for r in poly]) for pt in ring]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts); y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    import math
    kx = math.cos(math.radians((y0 + y1) / 2))
    box = (60, 330, W - 60, 960)
    s = min((box[2] - box[0]) / ((x1 - x0) * kx), (box[3] - box[1]) / (y1 - y0))
    ox = box[0] + ((box[2] - box[0]) - (x1 - x0) * kx * s) / 2; oy = box[1] + ((box[3] - box[1]) - (y1 - y0) * s) / 2
    P = lambda p: (ox + (p[0] - x0) * kx * s, oy + (y1 - p[1]) * s)
    cent = {}
    for f in geo['features']:
        c = f['properties']['c']
        polys = [f['geometry']['coordinates']] if f['geometry']['type'] == 'Polygon' else f['geometry']['coordinates']
        big = max(polys, key=lambda pl: len(pl[0]))
        for pl in polys:
            d.polygon([P(p) for p in pl[0]], fill=color(chg.get(c)), outline=C.T['bg'])
        xs = [P(p) for p in big[0]]; cent[c] = (sum(x for x, _ in xs) / len(xs), sum(y for _, y in xs) / len(xs))
    # 상승·하락 1~2위 이름표 (겹치면 아래로 비킴)
    placed = []
    for rows, col in ((mrows[:2], C.UP), (mrows[::-1][:2], C.DOWN)):
        for r in rows:
            if r['code'] not in cent: continue
            cx, cy = cent[r['code']]; t = f"{short(r['region'])} {pct(r['chg'])}"; tf = F(24, 'Black'); tw = d.textlength(t, font=tf)
            bx = min(max(cx - tw / 2 - 10, 50), W - 50 - tw - 20)
            box_ = [bx, cy - 18, bx + tw + 20, cy + 18]
            while any(not (box_[2] < q[0] or box_[0] > q[2] or box_[3] < q[1] or box_[1] > q[3]) for q in placed):
                box_[1] += 40; box_[3] += 40
            placed.append(box_)
            d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(30, 34, 40))
            if box_[1] != cy - 18: d.line((cx, cy, (box_[0] + box_[2]) / 2, box_[1]), fill=(30, 34, 40), width=3)
            d.rounded_rectangle(box_, 8, fill=(30, 34, 40))
            d.text((box_[0] + 10, box_[1] + 3), t, font=tf, fill=col)
    # 범례
    ly_ = 980; items = [('하락', None)] + [(None, c) for c in DNC[::-1]] + [(None, (245, 245, 245))] + [(None, c) for c in UPC] + [('상승', None)]
    x = 140
    d.text((64, ly_ - 4), '하락', font=F(24, 'Medium'), fill=C.INK2)
    for c in DNC[::-1] + [(245, 245, 245)] + UPC:
        d.rectangle((x, ly_, x + 56, ly_ + 22), fill=c); x += 60
    d.text((x + 10, ly_ - 4), '상승', font=F(24, 'Medium'), fill=C.INK2)
    d.text((x + 90, ly_ - 4), '회색: 거래 부족', font=F(22, 'Regular'), fill=C.INK2)
    # 아래: 상승·하락 3곳
    y = 1030
    for i, (title, rows, col) in enumerate((('상승', mrows[:3], C.UP), ('하락', mrows[::-1][:3], C.DOWN))):
        x = 64 + i * 480
        d.text((x, y), f'{title} TOP 3', font=F(28, 'Black'), fill=C.INK)
        for k, r in enumerate(rows):
            d.text((x, y + 42 + k * 36), f"{k + 1}. {short(r['region'])}", font=F(26, 'Medium'), fill=C.INK)
            v = pct(r['chg']); d.text((x + 420 - d.textlength(v, font=F(26, 'Black')), y + 42 + k * 36), v, font=F(26, 'Black'), fill=col)
    C.cta(d, F, '구별 전체 순위 → 프로필 링크')
    C.footer(d, F, '자료 국토교통부 실거래가 · 계약 후 30일 안 신고라 최근 달은 잠정치')
    im.save(os.path.join(OUT, 'month.png')); print('월간 지도 카드 → trend/month.png')


try:
    week_card(); month_card()
except SystemExit as e:
    print('카드 건너뜀:', e)
