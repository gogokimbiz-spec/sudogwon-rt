"""상장사 시세 + 재무 수집 (GitHub Actions 용).
환경변수 DATA_GO_KR_KEY (Decoding 키). 금융위원회 API 3종 사용:
  주식시세정보(매일) · KRX상장종목정보(법인등록번호 연결) · 기업 재무정보(요약재무제표, 캐시에 없을 때만)
대상: 코스피+코스닥 보통주 시가총액 상위 500 (스팩 제외)
결과: fin_data.json (build_fin.py 입력), fin_cache.json (재무 캐시, 저장소에 커밋해서 다음 실행에 재사용)
"""
import os, sys, json, time, datetime, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ['DATA_GO_KR_KEY'].strip()
B = 'https://apis.data.go.kr/1160100/service/'
PRICE = B + 'GetStockSecuritiesInfoService/getStockPriceInfo'
LIST = B + 'GetKrxListedInfoService/getItemInfo'
SUMM = B + 'GetFinaStatInfoService_V2/getSummFinaStat_V2'
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
TOP_N = 500
MAX_FIN_CALLS = 3000          # 하루 한도(10,000) 안에서 넉넉히
RETRY_EMPTY_DAYS = 14         # 재무가 비어 있던 회사는 2주 뒤 다시 조회
FIN_KW = ('금융', '은행', '보험', '증권', '생명', '화재', '캐피탈', '카드', '손해', '투자', '신탁', '리츠')


UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
      'Accept': 'application/json, */*'}


def raw_get(url, **p):
    """(HTTP 상태, 본문 앞부분) - 진단용. 키는 찍지 않음"""
    q = urllib.parse.urlencode({'serviceKey': KEY, 'resultType': 'json', **p})
    try:
        with urllib.request.urlopen(urllib.request.Request(url + '?' + q, headers=UA), timeout=60) as r:
            return r.status, r.read()[:300].decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode('utf-8', 'replace')
    except Exception as e:
        return 0, f'{type(e).__name__} {e}'


def call(url, **p):
    """한 페이지 호출 → (items, totalCount). 실패 시 None"""
    q = urllib.parse.urlencode({'serviceKey': KEY, 'resultType': 'json', **p})
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url + '?' + q, headers=UA), timeout=60) as r:
                body = json.loads(r.read().decode('utf-8', 'replace'))['response']
            if body['header'].get('resultCode') not in ('00', '0', '000'):
                raise RuntimeError(body['header'].get('resultMsg'))
            b = body.get('body') or {}
            items = (b.get('items') or {}).get('item') or []
            return ([items] if isinstance(items, dict) else items), int(b.get('totalCount') or 0)
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (401, 403): break      # 권한 문제는 재시도해도 같음
        except Exception as e:
            err = e
        time.sleep(1 + a)
    print(f'  호출 실패 ({url.rsplit("/", 1)[-1]}): {type(err).__name__} {str(err)[:120]}')
    return None


def call_all(url, **p):
    out, page = [], 1
    while True:
        r = call(url, numOfRows=1000, pageNo=page, **p)
        if r is None: return None
        items, total = r
        out += items
        if len(out) >= total or not items: return out
        page += 1


num = lambda v: None if v in (None, '', '-') else int(float(str(v).replace(',', '')))
code6 = lambda s: (s or '')[-6:]

# 0. 진단: API 3종에 한 번씩 호출해서 응답 상태를 남김 (403 이면 본문에 이유가 있음)
_d = (today - datetime.timedelta(days=4)).strftime('%Y%m%d')
for _name, _url, _p in [('주식시세', PRICE, {'basDt': _d}), ('상장종목', LIST, {'basDt': _d}), ('재무', SUMM, {'crno': '1301110006246', 'bizYear': str(today.year - 1)}),
                        ('(비교) 국토부 실거래', 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev', {'LAWD_CD': '11110', 'DEAL_YMD': today.strftime('%Y%m')})]:
    _c, _b = raw_get(_url, numOfRows=1, pageNo=1, **_p)
    print(f'[진단] {_name}: HTTP {_c} | {" ".join(_b.split())[:160]}')

# 1. 최근 영업일 시세 (전 영업일 자료는 다음 영업일 오후에 올라오므로 며칠 거슬러 찾기)
basDt = None
for k in range(0, 12):
    d = (today - datetime.timedelta(days=k)).strftime('%Y%m%d')
    r = call(PRICE, basDt=d, numOfRows=1, pageNo=1)
    if r and r[0]:
        basDt = d; break
if not basDt:
    sys.exit('시세 기준일을 찾지 못했습니다')
prices = call_all(PRICE, basDt=basDt)
if not prices:
    sys.exit('시세 수집 실패')
print(f'시세 기준일 {basDt}: {len(prices)}종목, 필드 {list(prices[0].keys())}')

stocks = [p for p in prices
          if p.get('mrktCtg') in ('KOSPI', 'KOSDAQ')
          and code6(p.get('srtnCd')).endswith('0')            # 보통주만 (우선주 코드는 5·7·9·K 등으로 끝남)
          and '스팩' not in (p.get('itmsNm') or '')
          and (num(p.get('mrktTotAmt')) or 0) > 0]
stocks.sort(key=lambda p: -num(p['mrktTotAmt']))
top = stocks[:TOP_N]

# 2. 법인등록번호 연결
listed = call_all(LIST, basDt=basDt) or []
if not listed:   # 상장종목정보는 갱신이 하루 늦을 수 있음
    for k in range(1, 8):
        d = (datetime.date(int(basDt[:4]), int(basDt[4:6]), int(basDt[6:])) - datetime.timedelta(days=k)).strftime('%Y%m%d')
        listed = call_all(LIST, basDt=d) or []
        if listed: break
crno_of = {code6(x.get('srtnCd')): (x.get('crno') or '').strip() for x in listed}
print(f'상장종목 {len(listed)}건, 필드 {list(listed[0].keys()) if listed else "-"}')

# 3. 요약재무제표 (캐시)
CACHE_F = 'fin_cache.json'
cache = json.load(open(CACHE_F, encoding='utf-8')) if os.path.exists(CACHE_F) else {}
Y = today.year
YEARS = [str(Y - 1), str(Y - 2), str(Y - 3)]   # 최신 사업연도 + 비교용 직전 연도
logged = [False]


def pick(items):
    if not items: return None
    if not logged[0]:
        print('요약재무 필드:', list(items[0].keys())); logged[0] = True
    con = [i for i in items if '연결' in (i.get('fnclDcdNm') or '')]
    i = (con or items)[0]
    f = {'kind': '연결' if con else '별도',
         'sales': num(i.get('enpSaleAmt')), 'op': num(i.get('enpBzopPft')), 'ni': num(i.get('enpCrtmNpf')),
         'pre_tax': num(i.get('iclsPalClcAmt')), 'assets': num(i.get('enpTastAmt')), 'debt': num(i.get('enpTdbtAmt')),
         'equity': num(i.get('enpTcptAmt')), 'capital': num(i.get('enpCptlAmt'))}
    return f if any(v is not None for k, v in f.items() if k != 'kind') else None


def need(crno, y):
    c = cache.get(crno, {})
    if y in c and c[y]: return False
    t = c.get('_t', {}).get(y)
    return not t or (today - datetime.date.fromisoformat(t)).days >= RETRY_EMPTY_DAYS


def fin_job(a):
    crno, y = a
    r = call(SUMM, crno=crno, bizYear=y, numOfRows=20, pageNo=1)
    return a, (None if r is None else pick(r[0])), r is not None


jobs = []
for p in top:
    crno = crno_of.get(code6(p['srtnCd']))
    if not crno: continue
    c = cache.get(crno, {})
    # 최신 연도(Y-1)가 아직 없으면 Y-2, Y-3 까지 확보 (직전 연도 비교용)
    for y in YEARS:
        if need(crno, y):
            jobs.append((crno, y))
jobs = jobs[:MAX_FIN_CALLS]
print(f'재무 조회 {len(jobs)}건 (캐시 {len(cache)}개사)')
ok_calls = 0
with ThreadPoolExecutor(3) as ex:
    for (crno, y), f, ok in ex.map(fin_job, jobs):
        if not ok: continue
        ok_calls += 1
        c = cache.setdefault(crno, {})
        c[y] = f
        c.setdefault('_t', {})[y] = today.isoformat()
json.dump(cache, open(CACHE_F, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f'재무 조회 성공 {ok_calls}/{len(jobs)}')

# 4. 결과
out = []
for rank, p in enumerate(top, 1):
    code = code6(p['srtnCd']); crno = crno_of.get(code, '')
    name = p.get('itmsNm', '')
    c = cache.get(crno, {})
    fy = next((y for y in YEARS if c.get(y)), None)
    py_ = str(int(fy) - 1) if fy else None
    out.append({'rank': rank, 'code': code, 'name': name, 'market': p['mrktCtg'], 'crno': crno,
                'close': num(p.get('clpr')), 'chg': float(p.get('fltRt') or 0), 'cap': num(p['mrktTotAmt']),
                'shares': num(p.get('lstgStCnt')),
                'financial': any(k in name for k in FIN_KW),
                'fy': fy, 'f': c.get(fy) if fy else None, 'fp': c.get(py_) if py_ else None})
have = sum(1 for x in out if x['f'])
print(f'상위 {len(out)}개사 중 재무 있음 {have}')
if have < len(out) * 0.3:
    print('::warning::재무 데이터가 30% 미만입니다 - 필드 이름이나 활용신청 상태를 확인하세요')
json.dump({'basDt': f'{basDt[:4]}-{basDt[4:6]}-{basDt[6:]}', 'asof': today.isoformat(), 'companies': out},
          open('fin_data.json', 'w', encoding='utf-8'), ensure_ascii=False)
