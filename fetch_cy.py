"""청약홈 수도권(서울·인천·경기) APT 분양정보·경쟁률 수집 (GitHub Actions 용).
결과: cy_data.json (build_cy.py 입력 형식). 인증키 필요 없음.
필요 패키지: beautifulsoup4
"""
import sys, json, time, datetime, urllib.request, urllib.parse
from bs4 import BeautifulSoup

KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
def ym(d, k):  # k개월 뒤 YYYYMM
    m = d.month - 1 + k
    return f'{d.year + m // 12}{m % 12 + 1:02d}'
BEGIN, END = ym(today, -10), ym(today, 1)  # 청약홈은 최대 12개월 조회
BASE = 'https://www.applyhome.co.kr'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      'Referer': BASE + '/ai/aia/selectAPTLttotPblancListView.do', 'Accept-Language': 'ko-KR,ko;q=0.9'}

def req(path, data=None):
    for a in range(5):
        try:
            r = urllib.request.Request(BASE + path, data=urllib.parse.urlencode(data).encode() if data else None, headers=UA)
            with urllib.request.urlopen(r, timeout=40) as f:
                return BeautifulSoup(f.read().decode('utf-8', 'replace'), 'html.parser')
        except Exception as e:
            err = e; time.sleep(2 + a * 2)
    raise RuntimeError(f'{path} 실패: {err}')

cells = lambda tr: [' '.join(c.get_text(' ').split()) for c in tr.find_all(['td', 'th'], recursive=False)]
cap = lambda t: (t.caption.get_text() if t.caption else '')
num = lambda s: (lambda v: v)(float(str(s).replace(',', '')) if str(s).replace(',', '').replace('.', '', 1).strip().isdigit() else None)

LIST = []
for area in ['서울', '인천', '경기']:
    p = 1
    while p <= 40:
        q = urllib.parse.urlencode({'beginPd': BEGIN, 'endPd': END, 'suplyAreaCode': area, 'houseNm': '', 'houseDetailSecd': '', 'rentSecd': '0', 'pageIndex': p})
        s = req('/ai/aia/selectAPTLttotPblancListView.do?' + q)
        rows = s.select('table tbody tr[data-pbno]')
        if not rows: break
        for r in rows:
            td = [' '.join(x.get_text(' ').split()) for x in r.find_all('td')]
            LIST.append({'pb': r['data-pbno'], 'hm': r['data-hmno'], 'nm': r.get('data-honm', ''), 'td': td, 'cp': bool(r.select_one('.btn_cp'))})
        p += 1; time.sleep(0.3)
print('공고', len(LIST), BEGIN, '~', END)
if not LIST:
    sys.exit('청약홈 목록을 받지 못했습니다')

OUT = []
for x in LIST:
    td = x['td']
    o = {'pb': x['pb'], 'nm': x['nm'], 'area': td[0], 'kind': td[1], 'builder': td[4], 'ann': td[6], 'rcpt': td[7], 'win': td[8]}
    d = req('/ai/aia/selectAPTLttotPblancDetail.do', {'houseManageNo': x['hm'], 'pblancNo': x['pb']})
    tb = d.find_all('table')
    t0 = next((t for t in tb if '주요정보' in cap(t)), None)
    if t0:
        for r in t0.find_all('tr'):
            c = cells(r)
            if c and c[0] == '공급위치': o['addr'] = c[1]
            if c and c[0] == '공급규모': o['size'] = c[1]
    t1 = next((t for t in tb if '청약일정' in cap(t)), None)
    sc = {}
    if t1:
        for r in t1.find_all('tr'):
            c = cells(r)
            if not c: continue
            k = {'특별공급': 'sp', '1순위': 'r1', '2순위': 'r2', '계약일': 'ct'}.get(c[0])
            if k and len(c) > 1: sc[k] = c[1]
    o['sc'] = sc
    t2 = next((t for t in tb if cap(t).strip().startswith('입주자모집공고 공급대상')), None)
    types = []
    if t2:
        for r in t2.find_all('tr')[2:]:
            c = cells(r)
            if not c or c[0] == '계': continue
            if len(c) == 7: c = c[1:]
            if len(c) >= 6:
                types.append({'ty': c[0], 'sa': num(c[1]), 'g': int(num(c[2]) or 0), 's': int(num(c[3]) or 0)})
    t4 = next((t for t in tb if '공급금액' in cap(t)), None)
    price = {}
    if t4:
        for r in t4.find_all('tr')[1:]:
            c = cells(r)
            if len(c) >= 2: price[c[0]] = num(c[1])
    txt = d.get_text('\n')
    import re
    m = re.search(r'입주예정월\s*:\s*([\d.]+)', txt); o['move'] = m.group(1) if m else None
    m = re.search(r'특이사항\s*:\s*([^\n]*)', txt); o['note'] = m.group(1).strip() if m else None
    t5 = next((t for t in tb if '기타사항' in cap(t)), None)
    if t5 and len(t5.find_all('tr')) > 1:
        c = cells(t5.find_all('tr')[1]); o['con'] = c[1] if len(c) > 1 else ''
    cmp = []
    if x['cp']:
        d2 = req('/ai/aia/selectAPTCompetitionPopup.do', {'houseManageNo': x['hm'], 'pblancNo': x['pb'], 'houseNm': x['nm']})
        t = d2.find('table')
        if t and t.tbody:
            cmp = [cells(r)[:11] for r in t.tbody.find_all('tr', recursive=False)]
    def ty_row(t):
        rows = [r for r in cmp if r and r[0] == t['ty']]
        a1 = sum(num(r[4]) or 0 for r in rows if len(r) > 4 and r[2] == '1순위')
        a2 = sum(num(r[4]) or 0 for r in rows if len(r) > 4 and r[2] == '2순위')
        gp = next((r for r in rows if len(r) >= 11 and num(r[8]) is not None and r[7] not in ('-', '해당없음', '')), None)
        res = next((r[6] for r in rows if len(r) > 6 and r[2] == '1순위'), '')
        return [t['ty'].strip(), t['sa'], t['g'], t['s'], price.get(t['ty']) or price.get(t['ty'].strip()), int(a1), int(a2),
                [num(gp[8]), num(gp[9]), num(gp[10])] if gp else None, res]
    o['ty'] = [ty_row(t) for t in types]
    o['hasc'] = bool(cmp)
    OUT.append(o)
    time.sleep(0.4)
json.dump({'asof': today.isoformat(), 'range': [BEGIN, END], 'items': OUT}, open('cy_data.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('저장', len(OUT), '건')
