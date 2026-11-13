"""수도권 실거래 지도 빌드 스크립트.
사용법: python3 build.py <rt_data.json> <출력 html> <요약 json>
rt_data.json 은 fetch.js 가 브라우저에서 내려받은 원본입니다.
"""
import json, sys, os, datetime, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
raw = json.load(open(sys.argv[1], encoding='utf-8'))
out_html, out_sum = sys.argv[2], sys.argv[3]
names = json.load(open(os.path.join(HERE, 'names.json'), encoding='utf-8'))
geo = json.load(open(os.path.join(HERE, 'geo.json'), encoding='utf-8'))
tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()

codes = sorted(f['properties']['c'] for f in geo['features'])
ci = {c: i for i, c in enumerate(codes)}
dates = [r[1] for r in raw['trade']]
d0 = datetime.date.fromisoformat(min(dates))
di = lambda s: (datetime.date.fromisoformat(s) - d0).days
apts, umds = {}, {}
def idx(t, k):
    if k not in t: t[k] = len(t)
    return t[k]
# ── 새로 신고된 거래 찾기 (2026-11-13) ──
# 국토부 자료에는 '신고일'이 없어서, 어제 받은 자료(배포된 state/rt_keys.json.gz)와 비교해 오늘 새로 생긴 거래를 찾습니다.
# 계약은 며칠~30일 전이어도 어제 새로 신고된 거래가 모두 잡힘 (다른 신고가 사이트들과 같은 기준).
import gzip, hashlib, collections
def rkey(*v): return hashlib.sha1('|'.join(map(str, v)).encode()).hexdigest()[:10]
def keys_of(rows, kind):
    g = collections.defaultdict(list)
    for r in rows:
        if kind == 'trade': g[f'{r[0]}|{r[1][:7]}'].append(rkey(r[1], r[2], r[3], r[4], r[5], r[6]))
        else: g[f'{r[0]}|{r[1][:7]}'].append(rkey(r[1], r[2], r[3], r[4]))
    return g
KEYS = {'asof': raw.get('asof'), 'trade': keys_of(raw['trade'], 'trade'), 'jeonse': keys_of(raw['jeonse'], 'jeonse')}
ok = raw.get('ok') or {}
for kind, okk in (('trade', 'trade'), ('jeonse', 'rent')):   # 오늘 실패한 달은 비교 대상에서 빼고(내일 다시 비교) 빈 달은 빈 목록으로 기록
    if ok.get(okk):
        KEYS[kind] = {g: KEYS[kind].get(g, []) for g in ok[okk]}
PREV = None
_pp = os.environ.get('PREV_KEYS', 'prev_keys.json.gz')
if os.path.exists(_pp):
    try:
        PREV = json.load(gzip.open(_pp, 'rt', encoding='utf-8'))
        if PREV.get('asof') == raw.get('asof'): PREV = PREV.get('prev')   # 같은 날 다시 돌린 경우: 그 전날 자료와 비교
    except Exception as e:
        print('어제 자료를 읽지 못했습니다:', e); PREV = None
def new_flags(rows, kind):
    """rows 와 같은 순서로 '새로 신고됨' True/False. 어제 자료가 없으면 None"""
    if not PREV or not PREV.get(kind): return None
    pk = PREV[kind]; pmax = max(g.split('|')[1] for g in pk)
    pa = PREV.get('asof') or '0000'
    cnt = {g: collections.Counter(v) for g, v in pk.items()}
    out = []
    for r in rows:
        g = f'{r[0]}|{r[1][:7]}'
        k = rkey(r[1], r[2], r[3], r[4], r[5], r[6]) if kind == 'trade' else rkey(r[1], r[2], r[3], r[4])
        if g in cnt:
            if cnt[g][k] > 0: cnt[g][k] -= 1; out.append(False)
            else: out.append(True)
        elif g.split('|')[1] > pmax: out.append(True)          # 어제는 없던 새 달
        else: out.append(r[1] >= pa)                            # 어제 받기 실패한 달: 어제 이후 계약만 새 거래로
    return out
NT, NJ = new_flags(raw['trade'], 'trade'), new_flags(raw['jeonse'], 'jeonse')
T, J, canc = [], [], 0
newT, newJ = [], []
for i, (code, date, apt, umd, area, floor, price, by, cd) in enumerate(raw['trade']):
    if cd == 'O': canc += 1; continue
    if code not in ci or area <= 0 or price <= 0: continue
    T.append((ci[code], di(date), round(area * 10), price, floor, by, idx(apts, apt), idx(umds, umd)))
    if NT and NT[i]: newT.append(T[-1])
for i, (code, date, umd, area, dep) in enumerate(raw['jeonse']):
    if code not in ci or area <= 0 or dep <= 0 or date < d0.isoformat(): continue
    J.append((ci[code], di(date), round(area * 10), dep, idx(umds, umd)))
    if NJ and NJ[i]: newJ.append(J[-1])
# 내일 비교용으로 오늘 자료 저장 (같은 날 다시 돌릴 때를 위해 비교에 쓴 자료도 함께)
_ko = os.environ.get('KEYS_OUT', 'site/state/rt_keys.json.gz')
os.makedirs(os.path.dirname(_ko), exist_ok=True)
KEYS['prev'] = {k: v for k, v in PREV.items() if k != 'prev'} if PREV else None
with gzip.open(_ko, 'wt', encoding='utf-8') as f: json.dump(KEYS, f, separators=(',', ':'))
T.sort(); J.sort()
cols = lambda rows, n: [[x[i] for x in rows] for i in range(n)]
data = {'d0': d0.isoformat(), 'codes': codes, 'names': [names[c] for c in codes],
        'apts': list(apts), 'umds': list(umds), 'T': cols(T, 8), 'J': cols(J, 5),
        'cancelled': canc, 'wolse': raw.get('wolse', 0)}
asof = raw.get('asof') or datetime.date.today().isoformat()
html = (tpl.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
           .replace('__GEO__', json.dumps(geo, separators=(',', ':')))
           .replace('__ASOF__', asof.replace('-', '.')))
if '--standalone' in sys.argv:  # GitHub Pages 등 일반 웹사이트용 완전한 문서
    html = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + html.replace('<div class="wrap">', '</head>\n<body>\n<div class="wrap">', 1) + '\n</body>\n</html>\n')
open(out_html, 'w', encoding='utf-8').write(html)

# 카카오 메시지용 요약: 어제 새로 신고된 거래 (어제 자료가 없거나 새 거래가 0건이면 예전처럼 마지막 계약일 거래)
maxd = max(x[1] for x in T)
WD = '월화수목금토일'
asof_d = datetime.date.fromisoformat(asof[:10])
fmt_day = lambda d: f"{d.month}월 {d.day}일({WD[d.weekday()]})"
if newT:
    basis = 'reported'
    dto = asof_d - datetime.timedelta(1)                                  # 오늘 아침 자료 = 어제까지 신고분
    dfrom = datetime.date.fromisoformat(PREV['asof'][:10]) if PREV.get('asof') else dto
    dfrom = min(dfrom, dto)
    dayT, dayJ = newT, newJ
    if dfrom == dto: label = fmt_day(dto)
    elif dfrom.month == dto.month: label = f"{dfrom.month}월 {dfrom.day}~{dto.day}일"
    else: label = f"{dfrom.month}월 {dfrom.day}일~{dto.month}월 {dto.day}일"
    print(f'새로 신고된 거래: 매매 {len(newT)}건 · 전세 {len(newJ)}건 ({label})')
else:
    basis = 'contract'
    print('어제 자료가 없거나 새 거래가 없어 마지막 계약일 기준으로 만듭니다')
    # 월요일 실행이면 토·일 거래를 합친 '주말' 글
    lo = hi = maxd
    if asof_d.weekday() == 0:
        sat, sun = asof_d - datetime.timedelta(2), asof_d - datetime.timedelta(1)
        if maxd >= di(sat.isoformat()):
            lo, hi = di(sat.isoformat()), di(sun.isoformat())
    dfrom, dto = d0 + datetime.timedelta(lo), d0 + datetime.timedelta(hi)
    if lo == hi: label = fmt_day(dto)
    elif dfrom.month == dto.month: label = f"{dfrom.month}월 {dfrom.day}~{dto.day}일(주말)"
    else: label = f"{dfrom.month}월 {dfrom.day}일~{dto.month}월 {dto.day}일(주말)"
    dayT = [x for x in T if lo <= x[1] <= hi]
    dayJ = [x for x in J if lo <= x[1] <= hi]
day = dto.isoformat()
by_sido = {s: sum(1 for x in dayT if codes[x[0]].startswith(s)) for s in ('11', '28', '41')}
top = sorted(dayT, key=lambda x: -x[3])[:3]
def chg(rows, a, b, pa, pb):
    cur, prev = {}, {}
    for x in rows:
        pp = x[3] / (x[2] / 10) * 3.3058
        if a <= x[1] <= b: cur.setdefault(x[0], []).append(pp)
        elif pa <= x[1] <= pb: prev.setdefault(x[0], []).append(pp)
    res = []
    for r in cur:
        if len(cur[r]) >= 10 and len(prev.get(r, [])) >= 10:
            res.append((names[codes[r]], (statistics.median(cur[r]) / statistics.median(prev[r]) - 1) * 100))
    return sorted(res, key=lambda x: -x[1])
ch = chg(T, maxd - 29, maxd, maxd - 59, maxd - 30)
# 신고가: 같은 지역·단지·법정동·전용면적(㎡ 반올림)의 이전 거래 최고가 초과
# 비교 대상 = 최근 7개월(rt_data) + 역대 최고가 표(state/high/<지역코드>.json, build_high.py 가 2006년부터 쌓음)
hist = {}
for x in T:
    hist.setdefault((x[0], x[6], x[7], round(x[2] / 10)), []).append(x)
apt_l, umd_l = list(apts), list(umds)
HIGH, high_from = {}, {}
_hd = os.environ.get('HIGH_DIR', 'state/high')
for i, c in enumerate(codes):
    fp = os.path.join(_hd, f'{c}.json')
    if os.path.exists(fp):
        h = json.load(open(fp, encoding='utf-8')); HIGH[i] = h.get('max', {}); high_from[c] = h.get('from')
def trade_dict(x):
    k = (x[0], x[6], x[7], round(x[2] / 10))
    prev = [y for y in hist[k] if y[1] < x[1]]
    pm = max(prev, key=lambda y: y[3]) if prev else None
    pmax, pdate = (pm[3], (d0 + datetime.timedelta(pm[1])).isoformat()) if pm else (0, None)
    dx = (d0 + datetime.timedelta(x[1])).isoformat()
    hh = HIGH.get(x[0], {}).get(f'{apt_l[x[6]]}|{umd_l[x[7]]}|{round(x[2] / 10)}')
    if hh and hh[1] < dx and hh[0] > pmax: pmax, pdate = hh[0], hh[1]
    d = {'region': names[codes[x[0]]], 'apt': apt_l[x[6]], 'umd': umd_l[x[7]], 'area': round(x[2] / 10),
         'floor': x[4], 'built': x[5], 'price_man': x[3], 'pp_man': round(x[3] / (x[2] / 10) * 3.3058), 'date': dx}
    if pdate and x[3] > pmax:
        d['new_high'] = True; d['prev_high_man'] = pmax; d['prev_high_date'] = pdate
    return d
# 신고가 비교 기간 문구: 모든 지역의 역대 표가 몇 년부터 채워졌는지 (가장 늦은 지역 기준)
_hf = [high_from.get(c) for c in codes]
if all(_hf):
    _y = max(int(v[:4]) for v in _hf)
    high_text = '2006년 이후 역대 최고가' if _y <= 2006 else f'{_y}년 이후 최고가'
else:
    high_text = '최근 6개월 최고가'
day_list = [trade_dict(x) for x in sorted(dayT, key=lambda x: -x[3])]
# 주요 지역 최고가: 아래 지역마다 오늘 목록 중 가장 비싼 1건, 비싼 순 (2026-11-11 추가)
MAJOR = ['서울 강남구', '서울 서초구', '서울 송파구', '서울 용산구', '서울 성동구', '서울 마포구',
         '성남 분당구', '과천시', '수원 영통구', '용인 수지구', '화성 동탄구']
_best = {}
for x in dayT:
    n = names[codes[x[0]]]
    if n in MAJOR and (n not in _best or x[3] > _best[n][3]): _best[n] = x
major_tops = [trade_dict(x) for x in sorted(_best.values(), key=lambda x: -x[3])]
# 관심지역: 며칠마다 자동으로 바뀜 (서울 1 · 경기 1 · 인천/경기 1). 날짜로 정해지므로 같은 기간엔 항상 같은 지역.
import random
def stat30(code_i, a, b):
    v = [x[3] / (x[2] / 10) * 3.3058 for x in T if x[0] == code_i and a <= x[1] <= b]
    return (statistics.median(v), len(v)) if v else (None, 0)
watch_days = int(os.environ.get('WATCH_DAYS', '3') or 3)
fixed = [c.strip() for c in os.environ.get('WATCH_FIXED', '').split(',') if c.strip() in ci]
elig = {}
for i, c in enumerate(codes):
    m1, n1 = stat30(i, maxd - 29, maxd); m0, n0 = stat30(i, maxd - 59, maxd - 30)
    if n1 >= 20 and n0 >= 20: elig[c] = (m1, n1, (m1 / m0 - 1) * 100)
period = (d0 + datetime.timedelta(maxd)).toordinal() // watch_days
def pick(pool, k):
    # 전체 지역을 고정 순서로 섞어 두고(거래량과 무관하게 순서가 변하지 않음), 기간마다 차례로 k곳.
    # 차례가 된 지역이 거래 부족이면 다음 지역으로 넘어감.
    pool = sorted(pool)
    if not pool: return []
    random.Random(20261106).shuffle(pool)
    out, j = [], 0
    while len(out) < k and j < len(pool):
        c = pool[(period * k + j) % len(pool)]
        if c in elig and c not in out: out.append(c)
        j += 1
    return out
if fixed:
    wcodes = [c for c in fixed if c in elig][:3]
else:
    wcodes = pick([c for c in codes if c.startswith('11')], 1) + pick([c for c in codes if c.startswith('41')], 1) + \
             pick([c for c in codes if c.startswith('28') or c.startswith('41')], 1)
    wcodes = list(dict.fromkeys(wcodes))
watch = [{'region': names[c], 'pp_man': round(elig[c][0]), 'n': elig[c][1], 'chg': round(elig[c][2], 1)} for c in wcodes]
period_start = datetime.date.fromordinal(period * watch_days)
summary = {'asof': asof, 'basis': basis, 'high_text': high_text, 'day': day, 'day_from': dfrom.isoformat(), 'label': label, 'label_full': f'{dfrom.year}년 {label}', 'trade_count': len(dayT), 'jeonse_count': len(dayJ), 'by_sido': by_sido,
           'top_trades': [{'region': names[codes[x[0]]], 'apt': list(apts)[x[6]], 'area': round(x[2] / 10), 'price_man': x[3]} for x in top],
           'up3': [{'region': n, 'chg': round(v, 1)} for n, v in ch[:3]],
           'down3': [{'region': n, 'chg': round(v, 1)} for n, v in ch[::-1][:3]],
           'up5': [{'region': n, 'chg': round(v, 1)} for n, v in ch[:5]],
           'down5': [{'region': n, 'chg': round(v, 1)} for n, v in ch[::-1][:5]],
           'new_highs': [d for d in day_list if d.get('new_high')],
           'watch': watch, 'watch_period': [period_start.isoformat(), (period_start + datetime.timedelta(watch_days - 1)).isoformat()],
           'day_trades': day_list[:20],
           'major_tops': major_tops, 'major_regions': MAJOR,
           'trade_median_man': statistics.median([x[3] for x in dayT]) if dayT else None,
           'jeonse_median_man': statistics.median([x[3] for x in dayJ]) if dayJ else None}
json.dump(summary, open(out_sum, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('built', out_html, len(html), 'bytes;', len(T), 'trades', len(J), 'jeonse; last day', day, len(dayT))
