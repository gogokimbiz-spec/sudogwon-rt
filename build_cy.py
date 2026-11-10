"""수도권 청약 지도 빌드.
사용법: python3 build_cy.py <cy_data.json> <rt_data.json> <출력 html> <요약 json>
cy_data.json 은 fetch_cy.py, rt_data.json 은 fetch.py 결과입니다(시세 비교용).
"""
import json, sys, os, re, datetime, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
cy = json.load(open(sys.argv[1], encoding='utf-8'))
rt = json.load(open(sys.argv[2], encoding='utf-8'))
out_html, out_sum = sys.argv[3], sys.argv[4]
names = json.load(open(os.path.join(HERE, 'names.json'), encoding='utf-8'))
geo = json.load(open(os.path.join(HERE, 'geo.json'), encoding='utf-8'))
tpl = open(os.path.join(HERE, 'cy_template.html'), encoding='utf-8').read()
codes = sorted(f['properties']['c'] for f in geo['features'])
NM = [names[c] for c in codes]
today = cy['asof']
PY = 3.3058

def region(a, ar):
    a = a or ''
    if ar == '인천':
        if '검단' in a: return '인천 검단구'
        if '서해구' in a or '서구' in a: return '인천 서구'
        if '중구' in a or '영종' in a: return '인천 영종구'
        if '동구' in a or '제물포' in a: return '인천 제물포구'
        for g in ['계양구', '부평구', '미추홀구', '연수구', '남동구']:
            if g in a: return '인천 ' + g
    if ar == '서울':
        m = re.search(r'(\S+구)', a.replace('서울특별시', ''))
        return '서울 ' + m.group(1) if m else None
    if ar == '경기':
        for k, v in [('동탄', '화성 동탄구'), ('성남낙생', '성남 분당구'), ('부천역곡', '부천 소사구'), ('김포', '김포시'), ('평택', '평택시'),
                     ('남양주', '남양주시'), ('시흥', '시흥시'), ('구리', '구리시'), ('파주', '파주시'), ('광명', '광명시'), ('의정부', '의정부시'),
                     ('의왕', '의왕시'), ('양주', '양주시'), ('이천', '이천시'), ('오산', '오산시'), ('광주시', '광주시'), ('하남', '하남시'),
                     ('과천', '과천시'), ('군포', '군포시'), ('안성', '안성시'), ('동두천', '동두천시')]:
            if k in a: return v
        m = re.search(r'(수원|성남|안양|부천|안산|고양|용인|화성)\S*\s+(\S+구)', a)
        if m: return m.group(1) + ' ' + m.group(2)
    return None

# 실거래 시세 (최근 180일, 해제 제외): 법정동, 시군구 전체, 시군구 신축(10년 이내 준공)
tr = [r for r in rt['trade'] if r[8] != 'O' and r[4] > 0 and r[6] > 0 and r[0] in codes]
last = max(r[1] for r in tr)
cut_d = (datetime.date.fromisoformat(last) - datetime.timedelta(180)).isoformat()
NEWY = datetime.date.fromisoformat(today).year - 10
byU, byR, byN = {}, {}, {}
for code, date, apt, umd, area, fl, price, by, cd in tr:
    if date < cut_d: continue
    pp = price / area * PY; ri = codes.index(code)
    byU.setdefault((ri, umd), []).append(pp); byR.setdefault(ri, []).append(pp)
    if by >= NEWY: byN.setdefault(ri, []).append(pp)
med = lambda a: round(statistics.median(a)) if a and len(a) >= 10 else None

P, skip = [], []
RAW = {}
for c in cy['items']:
    rg = region(c.get('addr'), c['area'])
    if rg not in NM: skip.append(c['nm']); continue
    ri = NM.index(rg)
    RAW[c['pb']] = c
    umd = next((t for t in re.findall(r'[가-힣]+\d?(?:동|가)\d?', c.get('addr') or '') if (ri, t) in byU), None)
    ty = [dict(ty=t[0], ex=float(t[0][:7]) if re.match(r'\d{3}\.', t[0]) else None, g=t[2], s=t[3], p=t[4], a1=t[5], a2=t[6], gp=t[7], res=t[8]) for t in c['ty']]
    pw = [(t['p'], t['ex'], t['g'] + t['s']) for t in ty if t['p'] and t['ex']]
    unit = round(sum(p * w for p, e, w in pw) / sum(e * w for p, e, w in pw) * PY) if pw and sum(w for *_, w in pw) else None
    sc = c.get('sc', {})
    r1d = sc.get('r1') or sc.get('sp') or c['rcpt'][:10]
    res = ' '.join(t['res'] for t in ty)
    if '미도래' in res or r1d > today: st = '예정'
    elif not c['hasc']: st = '공공(결과 별도)'
    elif any(t['a1'] + t['a2'] < t['g'] for t in ty): st = '미달'
    elif all(t['a1'] >= t['g'] for t in ty): st = '1순위 마감'
    else: st = '2순위 마감'
    gps = [t['gp'] for t in ty if t['gp']]
    size = re.sub(r'[^\d]', '', c.get('size') or '')
    P.append(dict(pb=c['pb'], nm=c['nm'], r=ri, k=c['kind'], umd=umd, ad=c.get('addr'), ann=c['ann'], sp=sc.get('sp'), r1=sc.get('r1'), r2=sc.get('r2'),
                  win=c['win'], ct=sc.get('ct'), mv=c.get('move'), nt=c.get('note'), con=(c.get('con') or c.get('builder') or '').split(',')[0],
                  tot=sum(t['g'] + t['s'] for t in ty) or (int(size) if size else 0), g=sum(t['g'] for t in ty), a1=sum(t['a1'] for t in ty), a2=sum(t['a2'] for t in ty),
                  hasc=c['hasc'], st=st, unit=unit, refU=med(byU.get((ri, umd), [])) if umd else None, refN=med(byN.get(ri, [])), refR=med(byR.get(ri, [])),
                  ty=[[t['ty'], t['ex'], t['g'], t['s'], t['p'], t['a1'], t['gp'][0] if t['gp'] else None, t['gp'][2] if t['gp'] else None] for t in ty]))
print('단지', len(P), '제외', skip)

data = {'today': today, 'codes': codes, 'names': NM, 'P': P}
html = tpl.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':'))).replace('__GEO__', json.dumps(geo, separators=(',', ':')))
if '--standalone' in sys.argv:
    html = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + html.replace('<div class="wrap">', '</head>\n<body>\n<div class="wrap">', 1) + '\n</body>\n</html>\n')
os.makedirs(os.path.dirname(out_html) or '.', exist_ok=True)
open(out_html, 'w', encoding='utf-8').write(html)

# 주간 요약: 이번 주(월~일) 일정 + 지난주(월~일) 1순위 결과
T0 = datetime.date.fromisoformat(today)
W0 = T0 - datetime.timedelta(T0.weekday())   # 이번 주 월요일 (주간을 월~일로 고정)
w0, w1 = W0.isoformat(), (W0 + datetime.timedelta(6)).isoformat()
p0 = (W0 - datetime.timedelta(7)).isoformat()   # 지난주 월~일
def gap(p):
    if not p['unit'] or re.search('토지임대|지분적립', p['nm']): return None
    ref = p['refN'] or p['refR']
    return round((p['unit'] / ref - 1) * 100) if ref else None
def card(p, extra=None):
    d = {'name': p['nm'], 'region': NM[p['r']], 'umd': p['umd'], 'units': p['tot'], 'general': p['g'], 'pp_man': p['unit'], 'gap_new': gap(p),
         'kind': p['k'], 'builder': p['con'], 'url': f"https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancDetail.do?houseManageNo={p['pb']}&pblancNo={p['pb']}"}
    if p['hasc'] and p['st'] != '예정' and p['g']:
        d['rate'] = round(p['a1'] / p['g'], 2); d['status'] = p['st']; d['apps'] = p['a1']
    if extra: d.update(extra)
    return d
inw = lambda s: s and w0 <= s[:10] <= w1
first = lambda p: (p['r1'] or p['sp'] or '')[:10]
summary = {'asof': today, 'week': [w0, w1],
           'rank1': [card(p, {'date': p['r1'][:10], 'sp_date': (p['sp'] or '')[:10]}) for p in sorted([p for p in P if inw(p['r1']) or inw(p['sp'])], key=first)],
           'winners': [card(p, {'date': p['win'][:10]}) for p in sorted([p for p in P if inw(p['win'])], key=lambda p: p['win'])],
           'contracts': [card(p, {'date': p['ct'][:10]}) for p in P if inw(p['ct'])],
           'last_week': [card(p, {'date': p['r1'][:10]}) for p in sorted([p for p in P if p['r1'] and p0 <= p['r1'][:10] < w0 and p['hasc']],
                                                                          key=lambda p: -(p['a1'] / p['g'] if p['g'] else 0))],
           'total': len(P)}
# ── 요일별 글 재료 (수: 줍줍·로또·결과 / 금·토: 단지분석)
DD = datetime.timedelta
WED = W0 + DD(2); WED = WED if T0 >= WED else WED - DD(7)        # 기준 수요일 (월·화는 지난 수요일)
FRI = W0 + DD(4); FRI = FRI if T0 >= FRI else FRI - DD(7)        # 기준 금요일 (월~목은 지난 금요일)
iso = lambda d: d.isoformat()
zw0, zw1 = iso(WED), iso(WED + DD(6))                            # 줍줍: 수요일 ~ 다음 주 화요일 접수
def base_name(n): return re.sub(r'\(.*?\)|\s*\d+차$|조합원\s*취소분', '', n).strip()
def orig_of(nm):
    b = base_name(nm)
    return next((p for p in sorted(P, key=lambda p: p['ann'], reverse=True) if b and (b in p['nm'] or base_name(p['nm']) in b) and len(base_name(p['nm'])) >= 4), None)
zz = []
for r in cy.get('remndr') or []:
    if not (r['r1'] >= zw0 and r['r0'] <= zw1): continue
    o = orig_of(r['nm'])
    rg = region(r.get('addr'), r['area'])
    prices = [t[2] for t in r['ty'] if t[2]]
    zz.append({'name': r['nm'], 'region': rg if rg in NM else r['area'], 'kind': r['kind'], 'units': r['size'], 'r0': r['r0'], 'r1': r['r1'], 'win': r['win'],
               'p_min': min(prices) if prices else None, 'p_max': max(prices) if prices else None,
               'areas': sorted({round(float(t[0][:7])) for t in r['ty'] if re.match(r'\d{3}\.', t[0])}),
               'orig_pp': o['unit'] if o else None, 'orig_gap': gap(o) if o else None, 'url': r.get('url') or ''})
zz.sort(key=lambda x: (x['r0'], x['r1']))
c6 = iso(T0 - DD(182))
cheap = sorted([p for p in P if p['ann'] >= c6 and p['k'] == '민영' and gap(p) is not None], key=gap)[:5]
cut = {}
for p in P:
    c = RAW[p['pb']]
    if p['ann'] < c6 or p['k'] != '민영': continue
    for t in c['ty']:
        if not t[7] or not t[7][0] or not re.match(r'\d{3}\.', t[0]): continue
        e = float(t[0][:7]); bnd = '60㎡ 이하' if e < 60 else '60~85㎡' if e < 86 else None
        if bnd: cut.setdefault(c['area'], {}).setdefault(bnd, []).append(t[7])
cutline = {a: {b: {'min_med': round(statistics.median(x[0] for x in v)), 'avg': round(statistics.mean(x[2] for x in v)), 'n': len(v)} for b, v in d.items()} for a, d in cut.items()}
res0, res1 = iso(WED - DD(7)), iso(WED - DD(1))
results = [card(p, {'date': p['r1'][:10]}) for p in sorted([p for p in P if p['r1'] and res0 <= p['r1'][:10] <= res1 and p['hasc'] and p['g']],
                                                       key=lambda p: -(p['a1'] / p['g']))]
results = [x for x in results if 'rate' in x]
# 단지분석: 기준 금요일 전 7일 안에 당첨자 발표(가점 공개)가 난 민영 단지 중 1순위 접수가 가장 많은 곳
def pick_from(lo, hi, key, gmin):
    cs = [p for p in P if p['k'] == '민영' and p['hasc'] and p['g'] >= gmin and p.get(key) and lo <= p[key][:10] <= hi]
    return max(cs, key=lambda p: p['a1']) if cs else None
pk = pick_from(iso(FRI - DD(7)), iso(FRI - DD(1)), 'win', 100) or pick_from(iso(FRI - DD(14)), iso(FRI - DD(1)), 'r1', 50) \
     or pick_from(iso(FRI - DD(30)), iso(FRI - DD(1)), 'r1', 1)
pick = None
if pk:
    c = RAW[pk['pb']]
    near = {}
    for code, date, apt, umd, area, fl, price, by, cd in tr:
        if code != codes[pk['r']] or umd != pk['umd'] or by < NEWY or date < cut_d: continue
        n = near.setdefault(apt, {'apt': apt, 'built': by, 'n': 0, 'p59': [], 'p84': []}); n['n'] += 1
        if 57 <= area < 61: n['p59'].append(price)
        if 82 <= area < 86: n['p84'].append(price)
    near = sorted(near.values(), key=lambda x: -x['n'])[:5]
    for n in near:
        n['m59'], n['n59'] = (round(statistics.median(n['p59'])) if n['p59'] else None), len(n['p59'])
        n['m84'], n['n84'] = (round(statistics.median(n['p84'])) if n['p84'] else None), len(n['p84'])
        del n['p59'], n['p84']
    pick = card(pk, {'pb': pk['pb'], 'addr': pk['ad'], 'ann': pk['ann'], 'sp': pk['sp'], 'r1': pk['r1'], 'r2': pk['r2'], 'win': pk['win'], 'ct': pk['ct'],
                     'move': pk['mv'], 'note': pk['nt'], 'ref_new': pk['refN'], 'ref_umd': pk['refU'],
                     'types': [[t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7]] for t in c['ty']],   # 주택형, 공급면적, 일반, 특공, 분양가, 1순위, 2순위, [가점 최저·최고·평균]
                     'sp_stat': c.get('sp_stat'), 'near': near})
summary.update({'wed': iso(WED), 'zz_range': [zw0, zw1], 'zz': zz, 'cheap5': [card(p, {'ann': p['ann']}) for p in cheap],
                'cutline': cutline, 'results': results, 'results_range': [res0, res1], 'fri': iso(FRI), 'pick': pick})
print('수요일 줍줍', len(zz), '· 로또', len(cheap), '· 결과', len(results), '/ 금요일 단지분석:', pick and pick['name'])
json.dump(summary, open(out_sum, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('built', out_html, len(html), 'bytes; 이번 주 접수', len(summary['rank1']), '당첨발표', len(summary['winners']), '지난주 결과', len(summary['last_week']))
