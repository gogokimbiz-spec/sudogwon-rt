"""토허제(토지거래허가구역) 40곳 주간 아파트값 카드 (2026-11-26, 매주 금요일 11시 toheo.yml – 부동산원 목요일 오후 발표분)
사용법: python make_cards_toheo.py site/toheo [raw.json]
        python make_cards_toheo.py --fetch-only raw.json      (자료만 받기 – PC 실행기 대비용, 표준 라이브러리만 사용)
  - 바탕: 환경변수 TOHEO_BG (news=신문 느낌 기본 / slate / white / cream)
  - raw.json 을 안 주면 한국부동산원 R-ONE Open API 에서 받음 (환경변수 REB_KEY = R-ONE 인증키).
    인증키가 없으면 sample 모드(한 번에 5건) – 지난 자료는 state/toheo_hist.json 에 보관하고 매주 지역마다 최근 3주만 받음.
결과: OUT/card.png, OUT/caption.txt, OUT/summary.json, OUT/raw.json
값: R-ONE '(주) 매매가격지수'(아파트, STATBL_ID T244183132827305) 의 최신 주 지수 / 전주 지수 − 1 (%, 소수 둘째 자리).
    부동산원 보도자료의 '주간 변동률'과 같은 값 (2026-11-23 기준 송파 -0.50, 기흥 +0.52 확인).
"""
import os, sys, json, glob, math, datetime, time, urllib.request, urllib.parse
os.environ.setdefault('CARD_THEME', 'slate')   # 공통 테마 바탕 (아래 TOHEO_BG 가 색을 덮어씀)
FETCH_ONLY = '--fetch-only' in sys.argv
if FETCH_ONLY: sys.argv.remove('--fetch-only')

HERE = os.path.dirname(os.path.abspath(__file__))
KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(KST).date()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join('site', 'toheo')
if not FETCH_ONLY: os.makedirs(OUT, exist_ok=True)
STATBL = 'T244183132827305'
API = 'https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do'

# 토허제 40곳: (시군구코드 geo.json, 카드 이름, 지도 이름, R-ONE 지역 CLS_ID)
REGIONS = [
    ('11110', '종로구', '종로', 50043), ('11140', '중구', '중구', 50044), ('11170', '용산구', '용산', 50045),
    ('11200', '성동구', '성동', 50047), ('11215', '광진구', '광진', 50048), ('11230', '동대문구', '동대문', 50049),
    ('11260', '중랑구', '중랑', 50050), ('11290', '성북구', '성북', 50051), ('11305', '강북구', '강북', 50052),
    ('11320', '도봉구', '도봉', 50053), ('11350', '노원구', '노원', 50054), ('11380', '은평구', '은평', 50056),
    ('11410', '서대문구', '서대문', 50057), ('11440', '마포구', '마포', 50058), ('11470', '양천구', '양천', 50060),
    ('11500', '강서구', '강서', 50061), ('11530', '구로구', '구로', 50062), ('11545', '금천구', '금천', 50063),
    ('11560', '영등포구', '영등포', 50064), ('11590', '동작구', '동작', 50065), ('11620', '관악구', '관악', 50066),
    ('11650', '서초구', '서초', 50067), ('11680', '강남구', '강남', 50068), ('11710', '송파구', '송파', 50069),
    ('11740', '강동구', '강동', 50070),
    ('41290', '과천시', '과천', 50071), ('41173', '안양 동안구', '동안', 50074), ('41430', '의왕시', '의왕', 50076),
    ('41131', '성남 수정구', '수정', 50078), ('41133', '성남 중원구', '중원', 50079), ('41135', '성남 분당구', '분당', 50080),
    ('41111', '수원 장안구', '장안', 50084), ('41115', '수원 팔달구', '팔달', 50086), ('41117', '수원 영통구', '영통', 50087),
    ('41463', '용인 기흥구', '기흥', 50090), ('41465', '용인 수지구', '수지', 50091), ('41210', '광명시', '광명', 50097),
    ('41310', '구리시', '구리', 50106), ('41450', '하남시', '하남', 50108), ('41597', '화성 동탄구', '동탄', 50259),
]
EXTRA = [('서울', 50008), ('경기', 50016)]   # 참고 표시용


# ─────────────────────────── 자료 받기 ───────────────────────────
HIST_WEEKS = 210          # 연속 상승·하락 주수 계산용 (약 4년)


def wk_id(d):
    y, w, _ = d.isocalendar(); return f'{y}{w:02d}'


HIST = os.path.join(HERE, 'state', 'toheo_hist.json')   # 지난 자료 보관 {CLS_ID: {주: [조사일, 지수]}} – 매주 최근 몇 주만 새로 받음 (toheo.yml 이 커밋)


def get(cls_id, start, end=None):
    """한 지역 자료. 실패하면 3번까지 다시 시도 후 SystemExit (GitHub 서버가 막히면 바로 PC 로 넘어가게)"""
    q = {'Type': 'json', 'STATBL_ID': STATBL, 'DTACYCLE_CD': 'WK', 'CLS_ID': cls_id, 'START_WRTTIME': start}
    if end: q['END_WRTTIME'] = end
    if os.environ.get('REB_KEY'): q.update(KEY=os.environ['REB_KEY'], pIndex=1, pSize=1000)
    url = API + '?' + urllib.parse.urlencode(q)
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as r:
                j = json.loads(r.read().decode('utf-8'))
            if 'SttsApiTblData' not in j: return []          # INFO-200 (자료 없음)
            return [[x['CLS_ID'], x['CLS_FULLNM'], x['WRTTIME_IDTFR_ID'], x['WRTTIME_DESC'], x['DTA_VAL']]
                    for x in j['SttsApiTblData'][1].get('row', [])]
        except Exception as e:
            print('  다시 시도', cls_id, start, e); time.sleep(4 + k * 6)
    raise SystemExit(f'R-ONE 응답 없음 (CLS_ID {cls_id}) – 접속이 막힌 것 같습니다')


def load_hist():
    try: return {int(k): v for k, v in json.load(open(HIST, encoding='utf-8')).items()}
    except Exception: return {}


def fetch():
    """보관 자료(state/toheo_hist.json) + 지역마다 최근 3주만 새로 받기 (한 번에 하나씩, 천천히 – 2026-11-26 GitHub 서버에서
    병렬로 많이 부르면 '연결 끊김'으로 막혀서 바꿈). 보관 자료가 없는 지역만 5주씩 나눠 약 4년치를 받음."""
    H = load_hist(); rows = []
    start = wk_id(TODAY - datetime.timedelta(days=21))
    mondays = [TODAY - datetime.timedelta(days=TODAY.weekday() + 7 * k) for k in range(HIST_WEEKS, -1, -1)]
    for cid in IDS:
        if len(H.get(cid, {})) >= 20:
            got = get(cid, start)
        else:
            got = []
            for i in range(0, len(mondays), 5):
                got += get(cid, wk_id(mondays[i]), wk_id(mondays[min(i + 4, len(mondays) - 1)])); time.sleep(0.4)
        for c, _, wk, desc, v in got: H.setdefault(int(c), {})[wk] = [desc, v]
        time.sleep(0.5)
    names = {cid: n for _, n, _, cid in REGIONS}; names.update({cid: n for n, cid in EXTRA})
    for cid, wks in H.items():
        for wk, (desc, v) in wks.items(): rows.append([cid, names.get(cid, ''), wk, desc, v])
    return rows


def save_hist(raw):
    H = {}
    for cid, _, wk, desc, v in raw: H.setdefault(str(cid), {})[wk] = [desc, v]
    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    json.dump(H, open(HIST, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'), sort_keys=True)


IDS = [cid for *_, cid in REGIONS] + [cid for _, cid in EXTRA]
if FETCH_ONLY:
    raw = fetch(); json.dump(raw, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'R-ONE 자료 {len(raw)}건 → {OUT}'); sys.exit(0 if len(raw) > 2000 else 1)
raw = json.load(open(sys.argv[2], encoding='utf-8')) if len(sys.argv) > 2 else fetch()
json.dump(raw, open(os.path.join(OUT, 'raw.json'), 'w', encoding='utf-8'), ensure_ascii=False)
if os.environ.get('TOHEO_SAVE_HIST') == '1': save_hist(raw)   # toheo.yml 이 state/toheo_hist.json 을 갱신·커밋
ser = {}
for cid, _, wk, desc, v in raw: ser.setdefault(cid, {})[wk] = (desc, v)
weeks = sorted({wk for s in ser.values() for wk in s})
last = weeks[-1]
if sum(1 for *_, c in REGIONS if last in ser.get(c, {})) < len(REGIONS) // 2 and len(weeks) > 1: last = weeks[-2]   # 반쯤만 올라온 주는 건너뜀
prev = max(w for w in weeks if w < last)
base_day = datetime.date.fromisoformat(next(s[last][0] for s in ser.values() if last in s))   # 조사 기준일(월)
pub_day = base_day + datetime.timedelta(days=3)                                                 # 발표일(목)
MAX_AGE = int(os.environ.get('TOHEO_MAX_AGE') or 6)   # 금요일 실행 기준 조사일(월)은 4일 전. 6일보다 오래되면 이번 주 발표가 없는 것(명절 등)
if (TODAY - base_day).days > MAX_AGE:
    print(f'::warning::최신 자료가 {base_day} 기준이라 이번 주 발표가 아직 없습니다 – 게시하지 않습니다'); sys.exit(2)


def chg(cid):
    s = ser.get(cid, {})
    if last in s and prev in s: return round((s[last][1] / s[prev][1] - 1) * 100, 2)
    return None


def streak(cid):
    """최신 주부터 거꾸로, 같은 방향(소수 둘째 자리 기준 +/−)이 몇 주 이어졌나. 보합(0.00)이면 0. (값, 자료 처음까지 이어졌나)"""
    s = ser.get(cid, {}); w = sorted(k for k in s if k <= last)
    ch = [round((s[w[i]][1] / s[w[i - 1]][1] - 1) * 100, 2) for i in range(1, len(w))]
    if not ch or ch[-1] == 0: return 0, False
    sg = 1 if ch[-1] > 0 else -1; n = 0
    for v in reversed(ch):
        if v * sg > 0: n += 1
        else: break
    return sg * n, n == len(ch)


rows = []
for c, n, sn, cid in REGIONS:
    v = chg(cid)
    if v is None: continue
    st, full = streak(cid)
    rows.append({'code': c, 'name': n, 'short': sn, 'chg': v, 'streak': st, 'streak_full': full})
rows.sort(key=lambda r: -r['chg'])
for i, r in enumerate(rows, 1): r['rank'] = i
extra = {nm: chg(cid) for nm, cid in EXTRA}
n_up = sum(r['chg'] > 0 for r in rows); n_dn = sum(r['chg'] < 0 for r in rows); n_eq = len(rows) - n_up - n_dn
nth = (base_day.day - 1) // 7 + 1
label = f'{base_day.month}월 {nth}주'
pc = lambda v: '0.00%' if abs(v) < 0.005 else f'{v:+.2f}%'
print(f'{label} ({base_day} 기준, {prev}→{last}) {len(rows)}곳: 오름 {n_up} · 내림 {n_dn} · 보합 {n_eq}')


# ─────────────────────────── 카드 이미지 (지도형 + 연속 기록, 2026-11-26 시안 3) ───────────────────────────
from PIL import Image, ImageDraw, ImageFont


def font_path(weight):
    for pat in [os.path.join(HERE, 'fonts', f'NotoSansCJKkr-{weight}.otf'), f'/usr/share/fonts/**/NotoSansCJKkr-{weight}.otf',
                f'/usr/share/fonts/**/NotoSansCJK-{weight}.ttc', f'/usr/share/fonts/**/*CJK*{weight}*']:
        hits = glob.glob(pat, recursive=True)
        if hits: return hits[0]
    raise SystemExit('한글 폰트(Noto Sans CJK)를 찾지 못했습니다')
_fc = {}
def F(size, weight='Bold'):
    if (size, weight) not in _fc:
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

# 색 구간 (주간 변동률 %): 보합 ±0.005, 0.1, 0.2, 0.35
UPC = [(250, 214, 208), (240, 150, 138), (220, 80, 68), (168, 30, 30)]
DNC = [(208, 224, 246), (140, 178, 232), (64, 120, 208), (28, 70, 150)]
FLAT, OFF = (238, 238, 238), (74, 81, 90)

# 바탕색 (환경변수 TOHEO_BG = slate / white / cream, 2026-11-26 비교용)
BGS = {
    'white': dict(bg=(255, 255, 255), head=(255, 255, 255), ink=(25, 31, 40), ink2=(118, 126, 136), line=(226, 229, 233),
                  card=(243, 245, 247), h_ink=(25, 31, 40), h_ink2=(118, 126, 136), off=(214, 218, 223), flat=(226, 226, 226),
                  up=(214, 52, 42), down=(30, 100, 210)),
    'cream': dict(bg=(240, 230, 208), head=(240, 230, 208), ink=(42, 34, 26), ink2=(122, 108, 88), line=(214, 200, 172),
                  card=(230, 217, 190), h_ink=(42, 34, 26), h_ink2=(122, 108, 88), off=(212, 199, 174), flat=(250, 246, 236),
                  up=(200, 50, 38), down=(32, 96, 196)),
    # 신문 느낌 (2026-11-26 사용자: "짙은 크림색인데 조금 더 신문 느낌") – 먹색 글씨, 명조 제목, 이중 괘선, 검정 배지, 톤 다운한 빨강·파랑, 종이 질감
    'news':  dict(bg=(236, 225, 201), head=(236, 225, 201), ink=(30, 25, 20), ink2=(108, 96, 78), line=(188, 173, 146),
                  card=(228, 215, 188), h_ink=(30, 25, 20), h_ink2=(108, 96, 78), off=(216, 204, 179), flat=(247, 241, 227),
                  accent=(30, 25, 20), pill=(30, 25, 20), pill_t=(236, 225, 201), flat_=True,
                  up=(168, 34, 26), down=(34, 70, 128)),
}
_bg = os.environ.get('TOHEO_BG') or 'news'   # 2026-11-26 사용자 확정: 신문 느낌
if _bg in BGS:
    b_ = BGS[_bg]
    C.T = dict(C.T, **{k: v for k, v in b_.items() if k not in ('off', 'flat', 'up', 'down', 'flat_')})
    C.INK, C.INK2, C.LINE, C.UP, C.DOWN = b_['ink'], b_['ink2'], b_['line'], b_['up'], b_['down']
    OFF, FLAT = b_['off'], b_['flat']
NEWS = _bg == 'news'
if NEWS:   # 신문 인쇄처럼 채도를 낮춘 색
    UPC = [(234, 200, 184), (214, 146, 124), (180, 70, 54), (128, 28, 22)]
    DNC = [(200, 210, 222), (146, 168, 198), (70, 102, 152), (32, 56, 102)]


def FS(size, weight='Bold'):
    """명조(세리프) 글꼴 – 신문 제목용. 저장소 fonts/NotoSerifCJKkr-{Black,Bold}.otf (한글 서브셋)"""
    key = ('serif', size, weight)
    if key not in _fc:
        p = os.path.join(HERE, 'fonts', f'NotoSerifCJKkr-{weight}.otf'); f = None
        if not os.path.exists(p):
            hits = glob.glob(f'/usr/share/fonts/**/NotoSerifCJK-{weight}.ttc', recursive=True)
            if hits:
                for i in range(10):
                    try:
                        g = ImageFont.truetype(hits[0], size, index=i)
                        if 'KR' in g.getname()[0]: f = g; break
                    except Exception: break
            if f is None: return F(size, 'Black' if weight == 'Black' else 'Bold')
        _fc[key] = f or ImageFont.truetype(p, size)
    return _fc[key]
def color(v):
    if v is None: return OFF
    a = abs(v)
    if a < 0.005: return FLAT
    k = 0 if a <= 0.1 else 1 if a <= 0.2 else 2 if a <= 0.35 else 3
    return (UPC if v > 0 else DNC)[k]
def on(c): return (30, 34, 40) if sum(c) > 480 else (255, 255, 255)


def centroid(ring):
    a = cx = cy = 0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        k = x0 * y1 - x1 * y0; a += k; cx += (x0 + x1) * k; cy += (y0 + y1) * k
    if abs(a) < 1e-9: return sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    return cx / (3 * a), cy / (3 * a)


# 좁은 곳 이름 위치 보정 (지도 픽셀, 오른쪽+ 아래+)
NUDGE = {'종로': (-4, -4), '서대문': (-4, 4), '동대문': (4, 4), '중구': (0, 2), '성북': (0, -4), '중랑': (2, -4), '구리': (4, 6),
         '영등포': (2, 2), '양천': (-2, 0), '금천': (7, 2), '광명': (-4, 6), '팔달': (-8, -2), '영통': (-3, 12), '수정': (-2, 0)}


def draw_map(im, box):
    geo = json.load(open(os.path.join(HERE, 'geo.json'), encoding='utf-8'))
    val = {r['code']: r for r in rows}
    polys = {}
    for f in geo['features']:
        g = f['geometry']; polys[f['properties']['c']] = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    pts = [p for c in val for pl in polys.get(c, []) for p in pl[0]]          # 화면 범위 = 토허제 지역 경계 상자
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts); y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    kx = math.cos(math.radians((y0 + y1) / 2)); bw, bh = box[2] - box[0], box[3] - box[1]; pad = 14
    s_ = min((bw - 2 * pad) / ((x1 - x0) * kx), (bh - 2 * pad) / (y1 - y0))
    ox = (bw - (x1 - x0) * kx * s_) / 2; oy = (bh - (y1 - y0) * s_) / 2
    P = lambda p: (ox + (p[0] - x0) * kx * s_, oy + (y1 - p[1]) * s_)
    layer = Image.new('RGB', (bw, bh), C.T['bg']); d = ImageDraw.Draw(layer)
    for c, pl in polys.items():                       # 토허제 아닌 곳: 어두운 회색
        if c in val: continue
        for poly in pl: d.polygon([P(p) for p in poly[0]], fill=OFF, outline=C.T['bg'])
    labels = []
    for c, r in val.items():
        if c not in polys: continue
        for poly in polys[c]: d.polygon([P(p) for p in poly[0]], fill=color(r['chg']), outline=C.T['bg'])
        big = max(polys[c], key=lambda q: len(q[0])); labels.append((centroid([P(p) for p in big[0]]), r))
    for c in val:
        for poly in polys.get(c, []):
            q = [P(p) for p in poly[0]]; d.line(q + [q[0]], fill=C.T['bg'], width=2)
    for poly in polys.get(rows[0]['code'], []):       # 1위 지역 노란 테두리
        q = [P(p) for p in poly[0]]; d.line(q + [q[0]], fill=C.T['accent'], width=5)
    for (cx, cy), r in labels:
        t = r['short']; f = F(18 if len(t) <= 2 else 15, 'Black'); col = color(r['chg'])
        dx, dy = NUDGE.get(t, (0, 0))
        d.text((cx + dx - d.textlength(t, font=f) / 2, cy + dy - 11), t, font=f, fill=on(col))
    im.paste(layer, (box[0], box[1]))


def draw_list(d, box):
    x0, y0, x1, y1 = box; half = (len(rows) + 1) // 2; colw = (x1 - x0 - 18) / 2; rh = (y1 - y0) / half
    for i, r in enumerate(rows):
        cx = x0 + (i // half) * (colw + 18); cy = y0 + (i % half) * rh
        col = color(r['chg'])
        if NEWS and i % half: d.line((cx, cy, cx + colw, cy), fill=C.T['line'], width=1)     # 신문 표처럼 가는 줄
        if r['rank'] == 1: d.rounded_rectangle((cx - 6, cy + 2, cx + colw + 4, cy + rh - 2), 1 if NEWS else 7, outline=C.T['accent'], width=3)
        d.text((cx + 2, cy + (rh - 24) / 2 - 4), f"{r['rank']}", font=F(20, 'Medium'), fill=C.INK2)
        nx = cx + 30
        if ' ' in r['name']:                           # '용인 기흥구' → 작은 회색 '용인' + '기흥구'
            city, gu = r['name'].split(' ', 1)
            d.text((nx, cy + (rh - 18) / 2 - 3), city, font=F(17, 'Medium'), fill=C.INK2)
            nx += d.textlength(city, font=F(17, 'Medium')) + 5
        else: gu = r['name']
        d.text((nx, cy + (rh - 26) / 2 - (7 if NEWS else 5)), gu, font=FS(24, 'Bold') if NEWS else F(24, 'Bold'), fill=C.INK)
        v = pc(r['chg']); vf = F(22, 'Black'); vw = d.textlength(v, font=vf)
        bx = cx + colw - vw - 14
        d.rounded_rectangle((bx, cy + 7, cx + colw, cy + rh - 7), 1 if NEWS else 7, fill=col)
        d.text((bx + 7, cy + (rh - 23) / 2 - 5), v, font=vf, fill=on(col))


def short_nm(n): return n.split(' ')[-1]     # '용인 수지구' → '수지구'


def panel_streak(d, box):
    """지도 아래: 연속 상승·하락 최장 TOP 3 (2026-11-26 사용자 요청으로 지도 버전에 추가)"""
    x0, y0, x1, y1 = box
    if NEWS:   # 상자 대신 위 굵은 괘선 + 가는 괘선
        d.rectangle((x0, y0, x1, y0 + 4), fill=C.INK); d.line((x0, y0 + 9, x1, y0 + 9), fill=C.INK, width=1)
        d.line((x0, y1, x1, y1), fill=C.INK, width=1)
    else:
        d.rounded_rectangle(box, 10, fill=C.T.get('card', (62, 69, 78)))
    ups = sorted([r for r in rows if r['streak'] > 0], key=lambda r: -r['streak'])[:3]
    dns = sorted([r for r in rows if r['streak'] < 0], key=lambda r: r['streak'])[:3]
    hw = (x1 - x0) / 2; lh = (y1 - y0 - 66) / 3
    for i, (title, rs, col) in enumerate((('연속 상승', ups, C.UP), ('연속 하락', dns, C.DOWN))):
        cx0 = x0 + i * hw + 16; cx1 = x0 + (i + 1) * hw - 14; y = y0 + (20 if NEWS else 12)
        d.text((cx0, y), title, font=FS(27, 'Black') if NEWS else F(25, 'Black'), fill=col); y += 48
        for r in rs:
            d.text((cx0, y - (2 if NEWS else 0)), short_nm(r['name']), font=FS(23, 'Bold') if NEWS else F(23, 'Medium'), fill=C.INK)
            t = f"{abs(r['streak'])}주"; tf = F(24, 'Black')
            d.text((cx1 - d.textlength(t, font=tf), y - 1), t, font=tf, fill=col); y += lh
    d.line((x0 + hw, y0 + 16, x0 + hw, y1 - 16), fill=C.T['line'], width=2)


def legend(d, x, y):
    for i, c in enumerate(DNC[::-1] + [FLAT] + UPC):
        d.rectangle((x + i * 30, y, x + i * 30 + 26, y + 14), fill=c)
    e = x + 9 * 30
    d.text((x, y + 17), '하락', font=F(17, 'Medium'), fill=C.INK2)
    d.text((e - 4 - d.textlength('상승', font=F(17, 'Medium')), y + 17), '상승', font=F(17, 'Medium'), fill=C.INK2)
    d.rectangle((e + 16, y, e + 42, y + 14), fill=OFF, outline=C.INK2)
    d.text((e + 50, y - 4), '토허제 아님', font=F(17, 'Medium'), fill=C.INK2)


def header_news(d):
    """신문 1면 머리: 위 이중 괘선 · 작은 발행 줄 · 명조 큰 제목 · 오른쪽 지표 상자 · 아래 이중 괘선"""
    ink = C.INK
    d.rectangle((40, 28, W - 40, 34), fill=ink); d.line((40, 40, W - 40, 40), fill=ink, width=2)
    wd = '월화수목금토일'[pub_day.weekday()]
    meta = f'{pub_day.year}년 {pub_day.month}월 {pub_day.day}일 ({wd})  ·  {base_day.month}월 {base_day.day}일 조사 · 한국부동산원 · 전주 대비'
    mf = F(21, 'Medium'); d.text((44, 50), meta, font=mf, fill=C.INK2)
    d.line((40, 86, W - 40, 86), fill=ink, width=1)
    d.text((40, 96), f'토허제 {len(rows)}곳 주간 아파트값', font=FS(66, 'Black'), fill=ink)
    # 오른쪽 지표 상자
    bx0, by0, bx1, by1 = W - 250, 100, W - 40, 190
    d.rectangle((bx0, by0, bx1, by1), outline=ink, width=2)
    y = by0 + 8
    for k, v in extra.items():
        if v is None: continue
        t = pc(v); tf = F(28, 'Black'); tw = d.textlength(t, font=tf)
        d.text((bx1 - 14 - tw, y), t, font=tf, fill=C.UP if v > 0 else C.DOWN if v < 0 else ink)
        d.text((bx0 + 14, y + 3), k, font=FS(24, 'Bold'), fill=ink); y += 38
    d.line((40, 202, W - 40, 202), fill=ink, width=2); d.rectangle((40, 208, W - 40, 214), fill=ink)


def header(d):
    """짧은 머리: 날짜 칩 + 제목 + 오른쪽 서울·경기 (2026-11-26 사용자: 부제 줄·노란 버튼 삭제, 내용·지도 크게)"""
    d.rectangle((40, 30, W - 40, 36), fill=C.T['ink'])
    pill = f'{base_day.month}월 {base_day.day}일 기준 · 한국부동산원 · 전주 대비'; pf = F(28)
    d.rounded_rectangle((44, 54, 44 + d.textlength(pill, font=pf) + 40, 102), 8, fill=C.T['pill'])
    d.text((64, 59), pill, font=pf, fill=C.T.get('pill_t', C.WHITE))
    d.text((40, 112), f'토허제 {len(rows)}곳 주간 아파트값', font=F(68, 'Black'), fill=C.T['h_ink'])
    y = 58
    for k, v in extra.items():
        if v is None: continue
        t = pc(v); tf = F(30, 'Black'); tw = d.textlength(t, font=tf)
        d.text((W - 44 - tw, y), t, font=tf, fill=C.UP if v > 0 else C.DOWN if v < 0 else C.INK)
        d.text((W - 44 - tw - 10 - d.textlength(k, font=F(24, 'Medium')), y + 5), k, font=F(24, 'Medium'), fill=C.INK2)
        y += 42
    d.rectangle((40, 206, W - 40, 214), fill=C.T['ink'])


im, d = C.canvas()
header_news(d) if NEWS else header(d)
draw_list(d, (48, 228, 548, 1284))
draw_map(im, (556, 222, W - 22, 980))
d = ImageDraw.Draw(im); d._image = im
panel_streak(d, (564, 988, W - 36, 1218))
if NEWS: d.rectangle((556, 222, W - 22, 980), outline=C.INK, width=1)
legend(d, 570, 1236)
if NEWS: d.line((40, 1290, W - 40, 1290), fill=C.INK, width=2)
C.footer(d, F, '자료 한국부동산원 주간아파트가격동향 · 연속 주수는 최근 4년 자료 기준')
if NEWS:   # 종이 질감 (아주 옅은 잡티)
    import random
    random.seed(7); g = Image.effect_noise((W // 2, SH // 2), 18).resize((W, SH)).convert('L')
    im = Image.composite(im, Image.blend(im, Image.new('RGB', (W, SH), (120, 100, 70)), 0.06), g.point(lambda v: 255 if v > 120 else 200))
im.save(os.path.join(OUT, 'card.png')); print('카드 →', os.path.join(OUT, 'card.png'))


# ─────────────────────────── 캡션 · 요약 ───────────────────────────
tag = lambda n: '#' + n.split(' ')[-1]
sx = ' · '.join(f'{k} {pc(v)}' for k, v in extra.items() if v is not None)
up_, dn_ = [r for r in rows if r['chg'] > 0][:5], [r for r in rows[::-1] if r['chg'] < 0][:5]
L = [f'🗺️ 토허제 {len(rows)}곳 주간 아파트값 | {label} ({base_day.month}/{base_day.day} 기준)', '']
if sx: L += [f'· {sx}', '']
if up_: L += ['🔺 상승 TOP ' + str(len(up_))] + [f"· {r['rank']}위 {r['name']} {pc(r['chg'])}" for r in up_] + ['']
if dn_: L += ['🔻 하락 TOP ' + str(len(dn_))] + [f"· {r['name']} {pc(r['chg'])}" for r in dn_] + ['']
_su = sorted([r for r in rows if r['streak'] > 0], key=lambda r: -r['streak'])[:3]
_sd = sorted([r for r in rows if r['streak'] < 0], key=lambda r: r['streak'])[:3]
if _su or _sd:
    L += ['📈 연속 기록'] + [f"· {r['name']} {r['streak']}주 연속 상승" for r in _su] + [f"· {r['name']} {-r['streak']}주 연속 하락" for r in _sd] + ['']
L += [f'오름 {n_up} · 내림 {n_dn}' + (f' · 보합 {n_eq}' if n_eq else '') + ' (토지거래허가구역 = 서울 25개 구 + 경기 15곳)',
      '자료: 한국부동산원 주간아파트가격동향(매매가격지수 전주 대비) · 참고용 정보', '',
      '40곳 전체 표는 프로필 링크에서 👆', '',
      ' '.join(dict.fromkeys(['#토허제', '#아파트값', '#데이터로보는재테크', '#토지거래허가구역', '#집값', '#주간아파트가격동향']   # build_insta trim_tags(…, 6) → 브랜드+토허제+아파트값+1위·꼴찌 지역
                             + [tag(rows[0]['name']), tag(rows[-1]['name'])]))]
open(os.path.join(OUT, 'caption.txt'), 'w', encoding='utf-8').write('\n'.join(L))
summary = {'made': TODAY.isoformat(), 'key': f'{base_day.isoformat()}_toheo', 'label': label, 'base_day': base_day.isoformat(),
           'pub_day': pub_day.isoformat(), 'week': last, 'prev_week': prev, 'extra': extra,
           'n_up': n_up, 'n_dn': n_dn, 'n_eq': n_eq, 'rows': rows}
old = os.path.join(OUT, 'summary.json')
if os.path.exists(old):
    try:
        o = json.load(open(old, encoding='utf-8'))
        if o.get('key') == summary['key'] and o.get('blog_url'): summary['blog_url'] = o['blog_url']
    except Exception: pass
json.dump(summary, open(old, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n'.join(L))
