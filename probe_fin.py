"""금융위원회 API 3종 응답 확인용 (한 번만 실행하는 시험 스크립트).
환경변수 DATA_GO_KR_KEY (Decoding 키) 사용. 키나 호출 주소는 로그에 찍지 않습니다.
"""
import os, json, datetime, urllib.request, urllib.parse, urllib.error

KEY = os.environ['DATA_GO_KR_KEY'].strip()
B = 'https://apis.data.go.kr/1160100/service/'
PRICE = B + 'GetStockSecuritiesInfoService/getStockPriceInfo'
LIST = B + 'GetKrxListedInfoService/getItemInfo'
FIN = B + 'GetFinaStatInfoService_V2/'
KST = datetime.timezone(datetime.timedelta(hours=9))


def call(url, **p):
    q = urllib.parse.urlencode({'serviceKey': KEY, 'resultType': 'json', 'pageNo': 1, **p})
    try:
        with urllib.request.urlopen(url + '?' + q, timeout=60) as r:
            raw = r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return None, f'HTTP {e.code} {e.read()[:200].decode("utf-8", "replace")}'
    except Exception as e:
        return None, f'ERR {type(e).__name__}'
    try:
        body = json.loads(raw)['response']
    except Exception:
        return None, 'NOT JSON: ' + raw[:200]
    h = body.get('header', {})
    b = body.get('body', {}) or {}
    items = (b.get('items') or {}).get('item') or []
    if isinstance(items, dict):
        items = [items]
    return {'code': h.get('resultCode'), 'msg': h.get('resultMsg'), 'total': b.get('totalCount'), 'items': items}, None


def show(title, res, err, n=2):
    print(f'\n===== {title} =====')
    if err:
        print(err); return
    print(f"resultCode={res['code']} msg={res['msg']} totalCount={res['total']} 받은건수={len(res['items'])}")
    if res['items']:
        print('필드:', ', '.join(res['items'][0].keys()))
        for it in res['items'][:n]:
            print(json.dumps(it, ensure_ascii=False)[:600])


# 1. 주식시세: 최근 영업일 찾기 + 한 번에 전 종목 받는지
day = datetime.datetime.now(KST).date()
basDt = None
for k in range(1, 10):
    d = (day - datetime.timedelta(days=k)).strftime('%Y%m%d')
    res, err = call(PRICE, basDt=d, numOfRows=3)
    if res and res['items']:
        basDt = d; show(f'주식시세 basDt={d} (3건)', res, err); break
print('최근 시세 기준일:', basDt)
if basDt:
    res, err = call(PRICE, basDt=basDt, numOfRows=5000)
    if res:
        its = res['items']
        print(f'\n전 종목 한 번에: totalCount={res["total"]} 받은건수={len(its)}')
        from collections import Counter
        print('시장 구분:', dict(Counter(i.get('mrktCtg') for i in its)))
        top = sorted(its, key=lambda i: -int(i.get('mrktTotAmt') or 0))[:5]
        for i in top:
            print(' 시총상위', i.get('srtnCd'), i.get('itmsNm'), i.get('mrktCtg'), i.get('mrktTotAmt'))
    else:
        print('전 종목 조회 실패', err)

# 2. KRX 상장종목정보: 법인등록번호(crno) 있는지
res, err = call(LIST, basDt=basDt or '', numOfRows=3)
show('KRX상장종목 (3건)', res, err)
res2, err2 = call(LIST, basDt=basDt or '', numOfRows=5000)
crno = None
if res2:
    print(f'상장종목 한 번에: totalCount={res2["total"]} 받은건수={len(res2["items"])}')
    sam = [i for i in res2['items'] if i.get('srtnCd', '').endswith('005930')]
    print('삼성전자 행:', json.dumps(sam[:1], ensure_ascii=False))
    if sam:
        crno = sam[0].get('crno')
crno = crno or '1301110006246'
print('시험용 crno:', crno)

# 3. 기업 재무정보
year = str(day.year - 1)
for op in ('getSummFinaStat_V2', 'getBs_V2', 'getIncoStat_V2'):
    res, err = call(FIN + op, crno=crno, bizYear=year, numOfRows=50)
    show(f'{op} 삼성전자 {year}', res, err, n=3)
# 연도만으로 일괄 조회 되는지 (crno 없이)
for y in (year, str(day.year - 2)):
    res, err = call(FIN + 'getSummFinaStat_V2', bizYear=y, numOfRows=5)
    show(f'getSummFinaStat_V2 crno 없이 bizYear={y}', res, err, n=2)
print('\n끝')
