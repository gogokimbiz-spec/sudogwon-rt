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
day = (d0 + datetime.timedelta(maxd)).isoformat()
dayT = [x for x in T if x[1] == maxd]
dayJ = [x for x in J if x[1] == maxd]
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
summary = {'asof': asof, 'day': day, 'trade_count': len(dayT), 'jeonse_count': len(dayJ), 'by_sido': by_sido,
           'top_trades': [{'region': names[codes[x[0]]], 'apt': list(apts)[x[6]], 'area': round(x[2] / 10), 'price_man': x[3]} for x in top],
           'up3': [{'region': n, 'chg': round(v, 1)} for n, v in ch[:3]],
           'down3': [{'region': n, 'chg': round(v, 1)} for n, v in ch[::-1][:3]]}
json.dump(summary, open(out_sum, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('built', out_html, len(html), 'bytes;', len(T), 'trades', len(J), 'jeonse; last day', day, len(dayT))
