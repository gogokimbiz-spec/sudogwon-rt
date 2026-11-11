"""동네 대표기업 수집 (PC 실행기, fetch_fin.py 다음에 실행).
- fin_bulk.json(그해 전체 기업 매출·순이익)을 매출 순으로 보면서 금융위원회 기업기본정보(기업개요)로 본사 주소·종업원·평균급여를 확인
- 하루 최대 MAX_LOOKUPS 건씩 이어서 확인하고, 확인한 회사는 region_cache.json 에 1년 보관
- 주요 12개 지역(구)별 매출 TOP 30 (동 표시) → region_data.json
비상장사 포함. 이용허락 '제한 없음' 자료만 사용.
"""
import os, re, sys, json, time, datetime, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ['DATA_GO_KR_KEY'].strip()
OUTL = 'https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline_V2'
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
MAX_LOOKUPS = int(os.environ.get('REGION_LOOKUPS', '6000'))   # 기업기본정보 개발계정 하루 10,000건 안에서
RECHECK_DAYS = 365
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36'}

# 지역: 키, 표시 이름, 실거래 시군구 코드
REGIONS = [('gangnam', '서울 강남구', '11680'), ('seocho', '서울 서초구', '11650'), ('songpa', '서울 송파구', '11710'),
           ('yongsan', '서울 용산구', '11170'), ('seongdong', '서울 성동구', '11200'), ('mapo', '서울 마포구', '11440'),
           ('bundang', '성남 분당구', '41135'), ('gwacheon', '과천시', '41290'), ('yeongtong', '수원 영통구', '41117'),
           ('suji', '용인 수지구', '41465'), ('dongtan', '화성 동탄구', '41597'), ('yeonsu', '인천 연수구', '28185')]
DONGTAN = {'반송동', '석우동', '능동', '청계동', '영천동', '오산동', '방교동', '중동', '신동', '목동', '산척동', '장지동', '송동', '금곡동', '여울동'}


def dong_of(addr):
    """주소에서 법정동 찾기: '(삼평동, ○○빌딩)' 같은 괄호 안 → 없으면 '○○동/가' 낱말"""
    for inner in re.findall(r'\(([^)]*)\)', addr):
        for t in re.split(r'[,\s]+', inner):
            if re.fullmatch(r'[가-힣]+\d*(동|가|\d가)', t):
                return re.sub(r'\d+(동|가)$', r'\1', t)
    for t in addr.split():
        t = t.strip(',')
        if re.fullmatch(r'[가-힣]+\d*동', t) and not t.endswith(('로동',)):
            return re.sub(r'\d+동$', '동', t)
    return ''


def region_of(a, dong):
    if '서울' in a:
        for k, gu in [('gangnam', '강남구'), ('seocho', '서초구'), ('songpa', '송파구'), ('yongsan', '용산구'), ('seongdong', '성동구'), ('mapo', '마포구')]:
            if gu in a: return k
    if '성남' in a and '분당구' in a: return 'bundang'
    if '과천' in a and '경기' in a: return 'gwacheon'
    if '수원' in a and '영통구' in a: return 'yeongtong'
    if '용인' in a and '수지구' in a: return 'suji'
    if '화성' in a and ('동탄' in a or dong in DONGTAN): return 'dongtan'
    if '인천' in a and '연수구' in a: return 'yeonsu'
    return None


def clean(n):
    n = (n or '').strip()
    for s in ('주식회사', '(주)', '㈜', '유한회사', '(유)'):
        n = n.replace(s, '')
    return ' '.join(n.split())


num = lambda v: None if v in (None, '', '-') else int(float(str(v).replace(',', '')))


def get(crno):
    q = urllib.parse.urlencode({'serviceKey': KEY, 'resultType': 'json', 'numOfRows': 1, 'pageNo': 1, 'crno': crno})
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(OUTL + '?' + q, headers=UA), timeout=60) as r:
                body = json.loads(r.read().decode('utf-8', 'replace'))['response']
            if body['header'].get('resultCode') not in ('00', '0', '000'):
                raise RuntimeError(body['header'].get('resultMsg'))
            items = ((body.get('body') or {}).get('items') or {}).get('item') or []
            return crno, ([items] if isinstance(items, dict) else items)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403): return crno, None
        except Exception:
            pass
        time.sleep(2 + 2 * a)
    return crno, None


if not os.path.exists('fin_bulk.json'):
    sys.exit('fin_bulk.json 이 없어 동네 대표기업은 건너뜁니다')
B = json.load(open('fin_bulk.json', encoding='utf-8'))
FY, cur = B['fy'], B['cur']
CF = 'region_cache.json'
cache = json.load(open(CF, encoding='utf-8')) if os.path.exists(CF) else {}
HIT = cache.setdefault('hit', {})   # 대상 지역 회사: crno → {n, r, d, a, e, s, t}
CHK = cache.setdefault('chk', {})   # 대상 밖 회사: crno → 확인일(YYMMDD)
ymd = today.strftime('%y%m%d')


def fresh(c):
    if c in HIT and 'w' not in HIT[c]: return False      # 근속연수 없는 예전 기록은 다시 확인
    t = HIT[c]['t'] if c in HIT else CHK.get(c)
    if not t: return False
    return (today - datetime.datetime.strptime(t, '%y%m%d').date()).days < RECHECK_DAYS


ranked = sorted((c for c, v in cur.items() if v[0]), key=lambda c: -cur[c][0])
todo = [c for c in ranked if not fresh(c)][:MAX_LOOKUPS]
print(f'{FY}년 매출 있는 회사 {len(ranked)}곳, 오늘 확인 {len(todo)}곳 (누적 확인 {len(HIT) + len(CHK)}곳)')
shown, no_dong = 0, 0
with ThreadPoolExecutor(4) as ex:
    for c, items in ex.map(get, todo):
        if items is None: continue
        if not items:
            CHK[c] = ymd; continue
        o = items[0]
        a = ' '.join(x for x in (o.get('enpBsadr'), o.get('enpDtadr')) if x)
        if shown < 3 and a:
            print('[진단] 주소 예:', a, '| 종업원', o.get('enpEmpeCnt'), '| 평균급여', o.get('enpPn1AvgSlryAmt'), '| 근속', o.get('empeAvgCnwkTermCtt')); shown += 1
        d = dong_of(a)
        r = region_of(a, d)
        if r:
            if not d: no_dong += 1
            HIT[c] = {'n': clean(o.get('enpPbanCmpyNm') or o.get('corpNm')), 'r': r, 'd': d, 'a': a[:80],
                      'e': num(o.get('enpEmpeCnt')), 's': num(o.get('enpPn1AvgSlryAmt')), 'w': (o.get('empeAvgCnwkTermCtt') or '').strip(),
                      'l': 1 if (o.get('enpXchgLstgDt') or o.get('enpKosdaqLstgDt')) else 0, 't': ymd}
            CHK.pop(c, None)
        else:
            CHK[c] = ymd; HIT.pop(c, None)
json.dump(cache, open(CF, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
done = sum(1 for c in ranked if fresh(c))
last = next((cur[c][0] for c in reversed(ranked) if fresh(c)), 0) if done else 0
print(f'대상 지역 회사 {len(HIT)}곳 (동을 못 찾은 곳 {no_dong}곳), 매출 상위 {done}곳까지 확인')


# 동별 TOP 10
def sal_man(v):
    """평균급여를 만원 단위로 (원·천원·만원 단위 모두 대비)"""
    if not v: return None
    return round(v / 10000) if v >= 1_000_000 else round(v / 10) if v >= 20000 else v


out = {}
for key, name, code in REGIONS:
    rows = []
    for c, h in HIT.items():
        if h['r'] != key or c not in cur or not cur[c][0]: continue
        v = cur[c]
        rows.append({'n': h['n'], 'dong': h['d'], 'sales': v[0], 'op': v[2] if len(v) > 2 else None, 'emp': h['e'],
                     'sal': sal_man(h['s']), 'tenure': h.get('w') or '', 'listed': h.get('l', 0), 'crno': c})
    rows.sort(key=lambda x: -x['sales'])
    for i, x in enumerate(rows, 1): x['rank'] = i
    out[key] = {'name': name, 'code': code, 'companies': len(rows), 'top': rows[:30]}
    print(f'  {name}: 회사 {len(rows)}곳 · 1위 ' + (f"{rows[0]['n']}({rows[0]['dong'] or '-'})" if rows else '-'))
json.dump({'asof': today.isoformat(), 'fy': FY, 'checked': done, 'min_sales': last, 'regions': out},
          open('region_data.json', 'w', encoding='utf-8'), ensure_ascii=False)
