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
cut = (datetime.date.fromisoformat(last) - datetime.timedelta(180)).isoformat()
NEWY = datetime.date.fromisoformat(today).year - 10
byU, byR, byN = {}, {}, {}
for code, date, apt, umd, area, fl, price, by, cd in tr:
    if date < cut: continue
    pp = price / area * PY; ri = codes.index(code)
    byU.setdefault((ri, umd), []).append(pp); byR.setdefault(ri, []).append(pp)
    if by >= NEWY: byN.setdefault(ri, []).append(pp)
med = lambda a: round(statistics.median(a)) if a and len(a) >= 10 else None

P, skip = [], []
for c in cy['items']:
    rg = region(c.get('addr'), c['area'])
    if rg not in NM: skip.append(c['nm']); continue
    ri = NM.index(rg)
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

# 주간 요약: 이번 주(오늘~6일 뒤) 일정 + 지난 7일 결과
T0 = datetime.date.fromisoformat(today)
w0, w1 = today, (T0 + datetime.timedelta(6)).isoformat()
p0 = (T0 - datetime.timedelta(7)).isoformat()
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
           'last_week': [card(p, {'date': p['r1'][:10]}) for p in sorted([p for p in P if p['r1'] and p0 <= p['r1'][:10] < today and p['hasc']],
                                                                          key=lambda p: -(p['a1'] / p['g'] if p['g'] else 0))],
           'total': len(P)}
json.dump(summary, open(out_sum, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('built', out_html, len(html), 'bytes; 이번 주 접수', len(summary['rank1']), '당첨발표', len(summary['winners']), '지난주 결과', len(summary['last_week']))
