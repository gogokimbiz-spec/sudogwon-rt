"""상장사 재무 수집 (매출 상위 500, GitHub Actions 용).
환경변수 DATA_GO_KR_KEY (Decoding 키). 이용허락범위 '제한 없음' 인 금융위원회 API 2종만 사용합니다.
  - 기업 재무정보 (요약재무제표): 사업연도별 전체 기업을 한꺼번에 받아 매출 순으로 정렬
  - 기업기본정보 (기업개요): 상장 여부(코스피·코스닥)·업종 확인, 한 번 확인한 회사는 캐시
※ 주식시세·KRX상장종목정보는 공공누리 제4유형(상업적 이용금지)이라 쓰지 않습니다.
결과: fin_data.json (build_fin.py 입력), fin_cache.json (기업개요 캐시, 저장소에 보관)
"""
import os, sys, json, time, datetime, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ['DATA_GO_KR_KEY'].strip()
B = 'https://apis.data.go.kr/1160100/service/'
SUMM = B + 'GetFinaStatInfoService_V2/getSummFinaStat_V2'
OUTL = B + 'GetCorpBasicInfoService_V2/getCorpOutline_V2'
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
TOP_N = 500
MAX_LOOKUPS = 2500            # 하루 기업개요 조회 상한 (나머지는 다음 날 이어서)
RECHECK_DAYS = 90             # 상장 여부는 90일마다 다시 확인
FIN_SIC = ('금융', '보험', '은행', '증권', '신탁', '투자', '여신', '저축')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
      'Accept': 'application/json, */*'}


def get(url, **p):
    """→ (items, totalCount) / 실패 시 None. 403·401 은 재시도하지 않음"""
    q = urllib.parse.urlencode({'serviceKey': KEY, 'resultType': 'json', **p})
    err = None
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url + '?' + q, headers=UA), timeout=90) as r:
                raw = r.read().decode('utf-8', 'replace')
            body = json.loads(raw)['response']
            if body['header'].get('resultCode') not in ('00', '0', '000'):
                raise RuntimeError(body['header'].get('resultMsg'))
            b = body.get('body') or {}
            items = (b.get('items') or {}).get('item') or []
            return ([items] if isinstance(items, dict) else items), int(b.get('totalCount') or 0)
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code} {e.read()[:150].decode("utf-8", "replace")}'
            if e.code in (401, 403): break
        except Exception as e:
            err = f'{type(e).__name__} {str(e)[:150]}'
        time.sleep(2 + 2 * a)
    print(f'  호출 실패 ({url.rsplit("/", 1)[-1]} {p.get("bizYear", "")}{p.get("crno", "")} p{p.get("pageNo", "")}): {" ".join(str(err).split())}')
    return None


num = lambda v: None if v in (None, '', '-') else int(float(str(v).replace(',', '')))

# 0. 진단 (로그 확인용)
for name, url, p in [('재무 일괄(연도만)', SUMM, {'bizYear': str(today.year - 1)}), ('기업개요(삼성전자)', OUTL, {'crno': '1301110006246'})]:
    r = get(url, numOfRows=1, pageNo=1, **p)
    print(f'[진단] {name}: ' + ('실패' if r is None else f'totalCount={r[1]} 필드={list(r[0][0].keys()) if r[0] else "-"}'))
    if r and r[0] and name.startswith('기업개요'):
        o = r[0][0]
        print('[진단] 삼성전자 개요:', {k: o.get(k) for k in ('corpNm', 'enpPbanCmpyNm', 'corpRegMrktDcd', 'corpRegMrktDcdNm', 'enpXchgLstgDt', 'enpKosdaqLstgDt', 'sicNm')})


# 1. 사업연도별 요약재무제표 일괄 수집
def pick(rows):
    con = [i for i in rows if '연결' in (i.get('fnclDcdNm') or '')]
    i = (con or rows)[0]
    f = {'kind': '연결' if con else '별도', 'sales': num(i.get('enpSaleAmt')), 'op': num(i.get('enpBzopPft')),
         'ni': num(i.get('enpCrtmNpf')), 'assets': num(i.get('enpTastAmt')), 'debt': num(i.get('enpTdbtAmt')),
         'equity': num(i.get('enpTcptAmt'))}
    return f if any(v is not None for k, v in f.items() if k != 'kind') else None


def bulk(year):
    first = get(SUMM, bizYear=year, numOfRows=1000, pageNo=1)
    if first is None: return None
    items, total = first
    pages = min((total + 999) // 1000, 300)
    print(f'{year} 사업연도 재무: {total}건, {pages}쪽')
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda pg: get(SUMM, bizYear=year, numOfRows=1000, pageNo=pg), range(2, pages + 1)):
            if r: items += r[0]
    by = {}
    for i in items:
        c = (i.get('crno') or '').strip()
        if c: by.setdefault(c, []).append(i)
    out = {c: pick(v) for c, v in by.items()}
    return {c: f for c, f in out.items() if f}


Y = today.year
data = {}
for y in (str(Y - 1), str(Y - 2), str(Y - 3)):
    d = bulk(y)
    if d: data[y] = d
    if len(data) == 2: break
if not data:
    sys.exit('재무 일괄 수집 실패 - 위 [진단] 줄을 확인하세요')
years = sorted(data, reverse=True)
# 최신 연도 공시가 아직 적으면(직전 연도의 30% 미만) 한 해 앞을 기준으로
FY = years[0] if len(years) == 1 or len(data[years[0]]) >= 0.3 * len(data[years[1]]) else years[1]
PY = str(int(FY) - 1)
if PY not in data:
    d = bulk(PY)
    if d: data[PY] = d
cur, prev = data[FY], data.get(PY, {})
print(f'기준 사업연도 {FY}: {len(cur)}개사 (비교 {PY}: {len(prev)}개사)')

# 2. 매출 순으로 상장 여부 확인 → 상장사 500곳
CACHE_F = 'fin_cache.json'
cache = json.load(open(CACHE_F, encoding='utf-8')) if os.path.exists(CACHE_F) else {}
OC = cache.setdefault('outline', {})   # crno → {m: KOSPI|KOSDAQ|'', n: 이름, s: 업종, t: 확인일}


def market(o):
    nm = o.get('corpRegMrktDcdNm') or ''
    if o.get('enpXchgLstgDt') and not o.get('enpXchgLstgAbolDt'): return 'KOSPI'
    if o.get('enpKosdaqLstgDt') and not o.get('enpKosdaqLstgAbolDt'): return 'KOSDAQ'
    if '유가' in nm: return 'KOSPI'
    if '코스닥' in nm: return 'KOSDAQ'
    return ''


def clean(n):
    n = (n or '').strip()
    for s in ('주식회사', '(주)', '㈜'):
        n = n.replace(s, '')
    return n.strip()


def look(crno):
    r = get(OUTL, crno=crno, numOfRows=1, pageNo=1)
    if r is None: return crno, None
    if not r[0]: return crno, {'m': '', 'n': '', 's': '', 't': today.isoformat()}
    o = r[0][0]
    return crno, {'m': market(o), 'n': clean(o.get('enpPbanCmpyNm') or o.get('corpNm')), 's': o.get('sicNm') or '', 't': today.isoformat()}


def fresh(c):
    o = OC.get(c)
    return o and (today - datetime.date.fromisoformat(o['t'])).days < RECHECK_DAYS


ranked = sorted((c for c, f in cur.items() if f.get('sales')), key=lambda c: -cur[c]['sales'])
listed, lookups, i = [], 0, 0
while len(listed) < TOP_N and i < len(ranked) and lookups < MAX_LOOKUPS:
    batch = []
    while i < len(ranked) and len(batch) < 60:
        c = ranked[i]; i += 1
        if fresh(c):
            if OC[c]['m']: listed.append(c)
        else:
            batch.append(c)
    if batch:
        lookups += len(batch)
        with ThreadPoolExecutor(3) as ex:
            for c, o in ex.map(look, batch):
                if o: OC[c] = o
        listed += [c for c in batch if OC.get(c, {}).get('m')]
    listed = sorted(set(listed), key=lambda c: -cur[c]['sales'])
listed = listed[:TOP_N]
json.dump(cache, open(CACHE_F, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f'기업개요 조회 {lookups}건, 상장사 {len(listed)}곳 확보 (매출 순위 {i}위까지 확인)')
if len(listed) < TOP_N:
    print(f'::warning::상장사 {len(listed)}곳 - 기업개요 조회가 덜 끝났거나 상장 판정이 안 됨 (다음 실행에 이어서)')

out = []
for rank, c in enumerate(listed, 1):
    o = OC[c]
    out.append({'rank': rank, 'crno': c, 'name': o['n'] or c, 'market': o['m'], 'sic': o['s'],
                'financial': any(k in o['s'] for k in FIN_SIC), 'fy': FY, 'f': cur[c], 'fp': prev.get(c)})
json.dump({'asof': today.isoformat(), 'fy': FY, 'companies': out}, open('fin_data.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'완료: 상장사 {len(out)}곳, 직전 연도 비교 가능 {sum(1 for x in out if x["fp"])}곳')
if len(out) < 100:
    sys.exit('상장사가 너무 적어 결과를 올리지 않습니다')
