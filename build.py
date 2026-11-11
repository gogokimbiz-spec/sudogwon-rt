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
T, J, canc = [], [], 0
for code, date, apt, umd, area, floor, price, by, cd in raw['trade']:
    if cd == 'O': canc += 1; continue
    if code not in ci or area <= 0 or price <= 0: continue
    T.append((ci[code], di(date), round(area * 10), price, floor, by, idx(apts, apt), idx(umds, umd)))
for code, date, umd, area, dep in raw['jeonse']:
    if code not in ci or area <= 0 or dep <= 0 or date < d0.isoformat(): continue
    J.append((ci[code], di(date), round(area * 10), dep, idx(umds, umd)))
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

# 카카오 메시지용 요약: 마지막 계약일 거래 + 최근 30일 vs 직전 30일 변동
maxd = max(x[1] for x in T)
WD = '월화수목금토일'
# 월요일 실행이면 토·일 거래를 합친 '주말' 글 (일요일 실행에서 토요일 글을 이미 올리므로, 월요일에도 새 글이 생기도록)
asof_d = datetime.date.fromisoformat(asof[:10])
lo = hi = maxd
if asof_d.weekday() == 0:
    sat, sun = asof_d - datetime.timedelta(2), asof_d - datetime.timedelta(1)
    if maxd >= di(sat.isoformat()):
        lo, hi = di(sat.isoformat()), di(sun.isoformat())
dfrom, dto = d0 + datetime.timedelta(lo), d0 + datetime.timedelta(hi)
day = dto.isoformat()
if lo == hi:
    label = f"{dto.month}월 {dto.day}일({WD[dto.weekday()]})"
elif dfrom.month == dto.month:
    label = f"{dfrom.month}월 {dfrom.day}~{dto.day}일(주말)"
else:
    label = f"{dfrom.month}월 {dfrom.day}일~{dto.month}월 {dto.day}일(주말)"
dayT = [x for x in T if lo <= x[1] <= hi]
dayJ = [x for x in J if lo <= x[1] <= hi]
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
hist = {}
for x in T:
    hist.setdefault((x[0], x[6], x[7], round(x[2] / 10)), []).append(x)
apt_l, umd_l = list(apts), list(umds)
def trade_dict(x):
    k = (x[0], x[6], x[7], round(x[2] / 10))
    prev = [y for y in hist[k] if y[1] < x[1]]
    pm = max(prev, key=lambda y: y[3]) if prev else None
    d = {'region': names[codes[x[0]]], 'apt': apt_l[x[6]], 'umd': umd_l[x[7]], 'area': round(x[2] / 10),
         'floor': x[4], 'built': x[5], 'price_man': x[3], 'pp_man': round(x[3] / (x[2] / 10) * 3.3058)}
    if pm and x[3] > pm[3]:
        d['new_high'] = True; d['prev_high_man'] = pm[3]; d['prev_high_date'] = (d0 + datetime.timedelta(pm[1])).isoformat()
    return d
day_list = [trade_dict(x) for x in sorted(dayT, key=lambda x: -x[3])]
# 주요 지역 최고가: 아래 지역마다 그날(월요일은 주말) 계약 중 가장 비싼 1건, 비싼 순 (2026-11-11 추가)
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
summary = {'asof': asof, 'day': day, 'day_from': dfrom.isoformat(), 'label': label, 'label_full': f'{dfrom.year}년 {label}', 'trade_count': len(dayT), 'jeonse_count': len(dayJ), 'by_sido': by_sido,
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
