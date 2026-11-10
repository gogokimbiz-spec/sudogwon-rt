"""DART 오픈API 로 최신 분기 실적을 붙입니다 (fetch_fin.py 다음에 실행).
환경변수 DART_KEY. 입력·출력: fin_data.json (각 회사에 q, stock 추가), fin_cache.json ('dart' 매핑 캐시)
- 회사 매핑: DART 고유번호 목록(corpCode.xml)에서 이름으로 찾고, 기업개황(company.json)의 법인등록번호로 확인
- 실적: 다중회사 주요계정(fnlttMultiAcnt) 100곳씩, 최신 보고서부터 (3분기 → 반기 → 1분기 → 사업보고서)
"""
import os, sys, io, json, time, zipfile, datetime, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ.get('DART_KEY', '').strip()
if not KEY:
    print('DART_KEY 가 없어 분기 실적은 건너뜁니다'); sys.exit(0)
API = 'https://opendart.fss.or.kr/api/'
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36'}
D = json.load(open('fin_data.json', encoding='utf-8'))
CACHE_F = 'fin_cache.json'
cache = json.load(open(CACHE_F, encoding='utf-8')) if os.path.exists(CACHE_F) else {}
MAP = cache.setdefault('dart', {})     # crno → {c: 고유번호, s: 종목코드, t: 확인일}


def get(path, **p):
    q = urllib.parse.urlencode({'crtfc_key': KEY, **p})
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + path + '?' + q, headers=UA), timeout=90) as r:
                return r.read()
        except Exception as e:
            err = e
        time.sleep(2 + 2 * a)
    print(f'  DART 호출 실패 {path}: {type(err).__name__} {str(err)[:120]}')
    return None


def norm(n):
    n = (n or '').replace(' ', '')
    for s in ('주식회사', '(주)', '㈜'):
        n = n.replace(s, '')
    return n


# 1. 회사 매핑 (처음 한 번, 이후 캐시)
C = D['companies']
todo = [x for x in C if x['crno'] not in MAP or (not MAP[x['crno']].get('c') and (today - datetime.date.fromisoformat(MAP[x['crno']]['t'])).days >= 30)]
if todo:
    raw = get('corpCode.xml')
    if raw is None: sys.exit('DART 고유번호 목록을 받지 못했습니다')
    if raw[:2] != b'PK':
        sys.exit('DART 고유번호 목록 오류: ' + raw[:200].decode('utf-8', 'replace'))
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(raw)).read('CORPCODE.xml'))
    by_name = {}
    for e in root.iter('list'):
        sc = (e.findtext('stock_code') or '').strip()
        if sc:
            by_name.setdefault(norm(e.findtext('corp_name')), []).append((e.findtext('corp_code'), sc))
    print(f'DART 상장사 목록 {sum(len(v) for v in by_name.values())}곳, 매핑할 회사 {len(todo)}곳')

    def check(x):
        for cc, sc in by_name.get(norm(x['name']), []):
            r = get('company.json', corp_code=cc)
            try: j = json.loads(r)
            except Exception: continue
            if (j.get('jurir_no') or '').replace('-', '') == x['crno']:
                return x['crno'], {'c': cc, 's': sc, 't': today.isoformat()}
        return x['crno'], {'c': None, 't': today.isoformat()}
    with ThreadPoolExecutor(3) as ex:
        for crno, m in ex.map(check, todo):
            MAP[crno] = m
json.dump(cache, open(CACHE_F, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
mapped = [x for x in C if MAP.get(x['crno'], {}).get('c')]
print(f'DART 매핑 {len(mapped)}/{len(C)}곳')
for x in C:
    x['stock'] = MAP.get(x['crno'], {}).get('s')

# 2. 최신 보고서부터 다중회사 주요계정
Y = today.year
PERIODS = [(Y, '11014'), (Y, '11012'), (Y, '11013'), (Y - 1, '11011'), (Y - 1, '11014')]
LABEL = {'11013': ('1분기', '1~3월 누적'), '11012': ('반기', '1~6월 누적'), '11014': ('3분기', '1~9월 누적'), '11011': ('연간', '1~12월')}
amt = lambda v: None if v in (None, '', '-') else int(str(v).replace(',', ''))
ACC = {'sales': ('매출액', '수익(매출액)', '영업수익'), 'op': ('영업이익',), 'ni': ('당기순이익',),
       'assets': ('자산총계',), 'debt': ('부채총계',), 'equity': ('자본총계',)}


def parse(rows, rc):
    fs = 'CFS' if any(r.get('fs_div') == 'CFS' for r in rows) else 'OFS'
    q = {'fs': '연결' if fs == 'CFS' else '별도'}
    for r in rows:
        if r.get('fs_div') != fs: continue
        nm = (r.get('account_nm') or '').replace(' ', '')
        for k, names in ACC.items():
            if k in q or not any(nm.startswith(n) for n in names): continue
            if r.get('sj_div') == 'IS' and rc != '11011':
                q[k] = amt(r.get('thstrm_add_amount')) if amt(r.get('thstrm_add_amount')) is not None else amt(r.get('thstrm_amount'))
                q[k + '_p'] = amt(r.get('frmtrm_add_amount')) if amt(r.get('frmtrm_add_amount')) is not None else amt(r.get('frmtrm_amount'))
            else:
                q[k] = amt(r.get('thstrm_amount'))
                if r.get('sj_div') == 'IS': q[k + '_p'] = amt(r.get('frmtrm_amount'))
    return q if q.get('sales') is not None or q.get('op') is not None else None


left = {MAP[x['crno']]['c']: x for x in mapped}
calls = 0
for y, rc in PERIODS:
    if not left: break
    codes = list(left)
    got = 0
    for i in range(0, len(codes), 100):
        raw = get('fnlttMultiAcnt.json', corp_code=','.join(codes[i:i + 100]), bsns_year=str(y), reprt_code=rc)
        calls += 1
        if raw is None: continue
        j = json.loads(raw)
        if j.get('status') != '000':
            if j.get('status') != '013': print(f'  DART {y} {rc}: {j.get("status")} {j.get("message")}')
            continue
        rows = {}
        for r in j.get('list', []):
            rows.setdefault(r.get('corp_code'), []).append(r)
        for cc, rs in rows.items():
            q = parse(rs, rc)
            if q and cc in left:
                q['period'] = f'{y}년 {LABEL[rc][0]}'; q['span'] = LABEL[rc][1]; q['rc'] = rc; q['year'] = y
                left.pop(cc)['q'] = q; got += 1
    print(f'{y}년 {LABEL[rc][0]} 보고서: {got}곳')
print(f'DART 호출 {calls}건, 분기 실적 확보 {sum(1 for x in C if x.get("q"))}/{len(C)}곳')
json.dump(D, open('fin_data.json', 'w', encoding='utf-8'), ensure_ascii=False)
