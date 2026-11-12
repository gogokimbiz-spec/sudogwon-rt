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
import math

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

TODAY_MODES = [m for m in os.environ.get('TREND_MODES', '').split() if m in ('week', 'month')]   # daily.yml 이 정함 (월요일 week, 첫째 월요일 month)
summary = {'asof': asof.isoformat(), 'min_n': MIN_N, 'today': TODAY_MODES, 'week': week, 'month': month}
json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
# 인스타·스레드 게시 문구 (build_insta.py 가 오늘 올릴 때 사용)
def _short(r):
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' and len(p[0]) > 2 else p[0]
    if p[0] in ('서울', '인천'): return p[1] if len(p[1]) > 2 else f'{p[0]} {p[1]}'
    return f'{p[0]} {p[1][:-1]}'
def _tag(r): return '#' + _short(r).replace(' ', '') + '아파트'
_pc = lambda v: '-' if v is None else f'{v:+.1f}%'
_md = lambda s: f'{D(s).month}.{D(s).day}'
for m, P_ in (('week', week), ('month', month)):
    rs = P_['rows']
    if not rs: continue
    up_ = [r for r in rs if r['chg'] > 0][:5]; dn_ = [r for r in rs[::-1] if r['chg'] < 0][:5]
    sd_ = P_['sido']
    head = (f"📈 {P_['label']} 구별 아파트값 상승률 (최근 4주)" if m == 'week' else f"🗺 {P_['label']} 구별 아파트값 순위 (전월 대비)")
    L = [head, (f"{_md(P_['cur'][0])}~{_md(P_['cur'][1])} vs {_md(P_['prev'][0])}~{_md(P_['prev'][1])} · 3.3㎡당 중앙값" if m == 'week'
                else f"수도권 {_pc(sd_['수도권']['chg'])} · 서울 {_pc(sd_['서울']['chg'])} · 인천 {_pc(sd_['인천']['chg'])} · 경기 {_pc(sd_['경기']['chg'])}"), '']
    if up_: L += ['🔺 상승 TOP ' + str(len(up_))] + [f"{i}. {_short(r['region'])} {_pc(r['chg'])}" for i, r in enumerate(up_, 1)] + ['']
    if dn_: L += ['🔻 하락 TOP ' + str(len(dn_))] + [f"{i}. {_short(r['region'])} {_pc(r['chg'])}" for i, r in enumerate(dn_, 1)] + ['']
    L += [f'※ 두 기간 모두 거래 {MIN_N}건 이상 지역 · 최근 기간은 신고가 다 안 들어온 잠정치', '자료: 국토교통부 실거래가 · 참고용 정보',
          '', '구별 전체 순위는 프로필 링크에서 👆', '',
          ' '.join(dict.fromkeys(['#데이터로보는재테크', '#아파트값', '#집값'] + [_tag(r['region']) for r in (up_[:1] + dn_[:1])]))]
    open(os.path.join(OUT, f'caption_{m}.txt'), 'w', encoding='utf-8').write('\n'.join(L))
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


# 지도 색 (지도 사이트와 같은 구간: ±1 보합, 3, 6, 10%)
UPC = [(248, 198, 192), (236, 133, 122), (212, 68, 58), (158, 28, 28)]
DNC = [(198, 217, 244), (130, 170, 228), (59, 116, 204), (27, 69, 148)]
def color(v):
    if v is None: return (90, 99, 110)
    a = abs(v)
    if a <= 1: return (245, 245, 245)
    k = 0 if a <= 3 else 1 if a <= 6 else 2 if a <= 10 else 3
    return (UPC if v > 0 else DNC)[k]


def draw_map(d, rows, box, nlabel=3):
    """구별 변동률로 수도권 지도를 색칠. box=(x0,y0,x1,y1).
    상승 1~nlabel위는 지도 왼쪽, 하락은 오른쪽에 이름표를 두고 화살표로 그 구를 가리킴(구는 굵은 테두리로 강조)."""
    import math
    chg = {r['code']: r['chg'] for r in rows}
    pts = [pt for f in geo['features'] for ring in (f['geometry']['coordinates'] if f['geometry']['type'] == 'Polygon'
           else [r for poly in f['geometry']['coordinates'] for r in poly]) for pt in ring]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts); y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    kx = math.cos(math.radians((y0 + y1) / 2))
    s_ = min((box[2] - box[0]) / ((x1 - x0) * kx), (box[3] - box[1]) / (y1 - y0))
    mw, mh = (x1 - x0) * kx * s_, (y1 - y0) * s_
    ox = box[0] + ((box[2] - box[0]) - mw) / 2; oy = box[1] + ((box[3] - box[1]) - mh) / 2
    P = lambda p: (ox + (p[0] - x0) * kx * s_, oy + (y1 - p[1]) * s_)
    cent, rings = {}, {}
    for f in geo['features']:
        c = f['properties']['c']
        polys = [f['geometry']['coordinates']] if f['geometry']['type'] == 'Polygon' else f['geometry']['coordinates']
        big = max(polys, key=lambda pl: len(pl[0]))
        rings[c] = [[P(p) for p in pl[0]] for pl in polys]
        for ring in rings[c]:
            d.polygon(ring, fill=color(chg.get(c)), outline=C.T['bg'])
        xs = [P(p) for p in big[0]]; cent[c] = (sum(x for x, _ in xs) / len(xs), sum(y for _, y in xs) / len(xs))
    DARK = (30, 34, 40)
    # 지도 영역 마스크 (이름표가 지도 위에 올라가지 않게)
    mask = Image.new('L', (W, SH), 0); md_ = ImageDraw.Draw(mask)
    for c in rings:
        for ring in rings[c]: md_.polygon(ring, fill=255)
    area = (44, box[1] - 4, W - 44, box[3] + 4)          # 이름표를 둘 수 있는 범위
    placed = []
    def free(rc):
        if rc[0] < area[0] or rc[1] < area[1] or rc[2] > area[2] or rc[3] > area[3]: return False
        if mask.crop(tuple(int(v) for v in (rc[0] - 6, rc[1] - 6, rc[2] + 6, rc[3] + 6))).getbbox(): return False
        return not any(not (rc[2] + 8 < q[0] or rc[0] - 8 > q[2] or rc[3] + 8 < q[1] or rc[1] - 8 > q[3]) for q in placed)
    labels = [(r, C.UP) for r in [x for x in rows if x['chg'] > 0][:nlabel]] + [(r, C.DOWN) for r in [x for x in rows[::-1] if x['chg'] < 0][:nlabel]]
    for r, col in labels:
        if r['code'] not in cent: continue
        cx, cy = cent[r['code']]
        t = f"{short(r['region'])} {pct(r['chg'])}"; tf = F(25, 'Black'); tw = tf.getlength(t); h = 25 + 18; w = tw + 24
        best = None
        for rad in range(30, 700, 12):                     # 가까운 곳부터: 지도 밖 빈자리 중 구에서 가장 가까운 위치
            for k in range(36):
                ang = math.radians(k * 10)
                px, py = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
                rc = (px - w / 2, py - h / 2, px + w / 2, py + h / 2)
                if free(rc):
                    dist = math.hypot(max(rc[0] - cx, 0, cx - rc[2]), max(rc[1] - cy, 0, cy - rc[3]))
                    if best is None or dist < best[0]: best = (dist, rc)
            if best and best[0] < rad - 30: break
        if not best: continue
        rc = best[1]; placed.append(rc)
        # 구 강조: 굵은 테두리
        for ring in rings[r['code']]:
            d.line(ring + [ring[0]], fill=DARK, width=7); d.line(ring + [ring[0]], fill=col, width=3)
        # 화살표: 이름표에서 가장 가까운 점 → 구 중심
        ax, ay = min(max(cx, rc[0]), rc[2]), min(max(cy, rc[1]), rc[3])
        d.line((ax, ay, cx, cy), fill=DARK, width=6); d.line((ax, ay, cx, cy), fill=col, width=3)
        ang = math.atan2(cy - ay, cx - ax); L_, Wd = 16, 9
        base = (cx - L_ * math.cos(ang), cy - L_ * math.sin(ang))
        d.polygon([(cx, cy), (base[0] + Wd * math.sin(ang), base[1] - Wd * math.cos(ang)), (base[0] - Wd * math.sin(ang), base[1] + Wd * math.cos(ang))],
                  fill=col, outline=DARK)
        d.rounded_rectangle(rc, 8, fill=DARK, outline=col, width=2)
        d.text((rc[0] + 12, rc[1] + 7), t, font=tf, fill=col)


def legend(d, y):
    d.text((64, y - 4), '하락', font=F(24, 'Medium'), fill=C.INK2)
    x = 140
    for c in DNC[::-1] + [(245, 245, 245)] + UPC:
        d.rectangle((x, y, x + 56, y + 22), fill=c); x += 60
    d.text((x + 10, y - 4), '상승', font=F(24, 'Medium'), fill=C.INK2)
    d.text((x + 90, y - 4), '회색: 거래 부족', font=F(22, 'Regular'), fill=C.INK2)


def top_lists(d, rows, y, n, size=26, gap=36):
    for i, (title, rs, col) in enumerate((('상승', [r for r in rows if r['chg'] > 0][:n], C.UP),
                                          ('하락', [r for r in rows[::-1] if r['chg'] < 0][:n], C.DOWN))):
        x = 64 + i * 480
        d.text((x, y), f'{title} TOP {len(rs)}', font=F(28, 'Black'), fill=col)
        for k, r in enumerate(rs):
            d.text((x, y + 42 + k * gap), f"{k + 1}. {short(r['region'])}", font=F(size, 'Medium'), fill=C.INK)
            v = pct(r['chg']); d.text((x + 420 - d.textlength(v, font=F(size, 'Black')), y + 42 + k * gap), v, font=F(size, 'Black'), fill=col)


def week_card():
    """주간: 색칠한 지도 + 아래 상승 TOP 5 · 하락 TOP 5 (2026-11-12 사용자 요청으로 지도형으로 변경)"""
    if not wrows: return
    im, d = C.canvas()
    sd = week['sido']['수도권']
    C.header(d, F, f"{week['label']} · 최근 4주", '구별 아파트값 상승률', pct(sd['chg']) if sd['chg'] is not None else '',
             f"{md(week['cur'][0])}~{md(week['cur'][1])} vs {md(week['prev'][0])}~{md(week['prev'][1])} · 3.3㎡당 중앙값")
    draw_map(d, wrows, (60, 326, W - 60, 862))
    legend(d, 880)
    top_lists(d, wrows, 922, 5, 25, 33)
    C.cta(d, F, '구별 전체 순위 → 프로필 링크')
    C.footer(d, F, f'자료 국토교통부 실거래가 · 두 기간 모두 거래 {MIN_N}건 이상 지역')
    im.save(os.path.join(OUT, 'week.png')); print('주간 지도 카드 → trend/week.png')


def month_card():
    if not mrows: return
    im, d = C.canvas()
    sd = month['sido']['수도권']
    C.header(d, F, f"{month['label']} · 전월 대비", '구별 아파트값 변동', pct(sd['chg']) if sd['chg'] is not None else '',
             f"3.3㎡당 매매가 중앙값 · 거래 {MIN_N}건 이상 지역만 색칠 (잠정)")
    draw_map(d, mrows, (60, 326, W - 60, 862))
    legend(d, 880)
    top_lists(d, mrows, 922, 5, 25, 33)
    C.cta(d, F, '구별 전체 순위 → 프로필 링크')
    C.footer(d, F, '자료 국토교통부 실거래가 · 계약 후 30일 안 신고라 최근 달은 잠정치')
    im.save(os.path.join(OUT, 'month.png')); print('월간 지도 카드 → trend/month.png')


try:
    week_card(); month_card()
except SystemExit as e:
    print('카드 건너뜀:', e)
