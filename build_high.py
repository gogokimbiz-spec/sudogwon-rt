"""역대 최고가 표 만들기 (GitHub Actions 'high.yml', 매일 오후).
결과: state/high/<시군구코드>.json = {"from": "2006-01", "to": "2026-05", "months": [...], "max": {"단지|법정동|전용㎡": [최고가(만원), "계약일"]}}
- build.py 가 '신고가'를 판단할 때 최근 7개월(rt_data) + 이 표를 함께 봅니다.
- 처음에는 2006년 1월~6개월 전까지 약 1만 9천 번 호출이 필요해서, 하루 HIGH_MAX_CALLS(기본 5000)번씩 최근 달부터 거꾸로 채웁니다 (4일쯤이면 완성).
- 다 채운 뒤에는 매달 새로 6개월이 지난 달 하나씩만 받습니다 (한 달에 77번).
- hist/ 폴더(1위 카드 그래프용으로 받아 둔 달)가 있으면 다시 받지 않고 씁니다.
- 해제(취소)된 거래는 빼고 셉니다.
필요: 환경변수 DATA_GO_KR_KEY, 같은 폴더의 names.json
"""
import os, sys, json, time, datetime, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ.get('DATA_GO_KR_KEY', '').strip()
OUT = os.environ.get('HIGH_DIR', 'state/high')
HIST = 'hist'
MAX = int(os.environ.get('HIGH_MAX_CALLS', '5000') or 5000)
START = os.environ.get('HIGH_START', '2006-01')
CODES = sorted(json.load(open('names.json', encoding='utf-8')))
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()


def ym_add(y, m, k):
    m += k
    while m <= 0: y, m = y - 1, m + 12
    while m > 12: y, m = y + 1, m - 12
    return y, m


cy, cm = ym_add(today.year, today.month, -6)        # rt_data(0~6개월 전)와 한 달 겹치게 → 달이 바뀌는 날에도 빈틈 없음
CUT = f'{cy}-{cm:02d}'
months = []
y, m = cy, cm
while f'{y}-{m:02d}' >= START:
    months.append(f'{y}-{m:02d}'); y, m = ym_add(y, m, -1)   # 최근 달부터

os.makedirs(OUT, exist_ok=True)
T = {}
for c in CODES:
    fp = os.path.join(OUT, f'{c}.json')
    T[c] = json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {'months': [], 'max': {}}
    T[c]['_done'] = set(T[c]['months'])


def add(c, rows):
    mx = T[c]['max']
    for date, apt, umd, area, price, cd in rows:
        if cd == 'O' or price <= 0 or area <= 0: continue
        k = f'{apt}|{umd}|{round(round(area * 10) / 10)}'
        if k not in mx or price > mx[k][0] or (price == mx[k][0] and date < mx[k][1]):
            mx[k] = [price, date]


def finish(c):
    t = T[c]; done = t['_done']
    t['months'] = sorted(done)
    # 6개월 전부터 거꾸로 빈틈없이 채워진 가장 오래된 달
    frm = None
    for ym in months:
        if ym in done: frm = ym
        else: break
    t['from'], t['to'] = frm, CUT
    json.dump({k: v for k, v in t.items() if k != '_done'}, open(os.path.join(OUT, f'{c}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))


# 1) hist/ 에 이미 받아 둔 달은 호출 없이 반영
for c in CODES:
    for ym in months:
        fp = os.path.join(HIST, c, ym.replace('-', '') + '.json')
        if ym not in T[c]['_done'] and os.path.exists(fp):
            rows = json.load(open(fp, encoding='utf-8'))      # [계약일, 단지, 법정동, 면적, 층, 거래가, 해제]
            add(c, [(r[0], r[1], r[2], r[3], r[5], r[6]) for r in rows]); T[c]['_done'].add(ym)

# 2) 남은 달: 최근 달부터, 모든 지역을 고르게
jobs = [(c, ym) for ym in months for c in CODES if ym not in T[c]['_done']]
print(f'역대 최고가 표: 기준 {START}~{CUT}, 남은 (지역·달) {len(jobs)}개, 오늘 최대 {MAX}번 호출')
if not KEY:
    print('DATA_GO_KR_KEY 가 없어 받기를 건너뜁니다'); jobs = []
URL = 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev'
num = lambda s: float((s or '0').replace(',', '').strip() or 0)
STOP = {'v': False}
calls = {'n': 0}


def get(code, ym, page):
    q = urllib.parse.urlencode({'serviceKey': KEY, 'LAWD_CD': code, 'DEAL_YMD': ym.replace('-', ''), 'numOfRows': 1000, 'pageNo': page})
    for a in range(5):
        if STOP['v']: return None
        try:
            calls['n'] += 1
            with urllib.request.urlopen(URL + '?' + q, timeout=60) as r:
                body = r.read()
            root = ET.fromstring(body)
            rc = root.findtext('.//resultCode') or root.findtext('.//returnReasonCode')
            if rc in ('000', '00'): return root
            if rc in ('22', '20', '30', '31', '32'):        # 일일 한도 초과·키 문제 → 오늘은 그만
                print('API 응답 코드', rc, '- 오늘은 여기까지'); STOP['v'] = True; return None
        except Exception:
            pass
        time.sleep(1 + a)
    return None


def job(args):
    code, ym = args
    rows, page = [], 1
    while True:
        if STOP['v'] or calls['n'] >= MAX: return args, None
        root = get(code, ym, page)
        if root is None: return args, None
        total = int(root.findtext('.//totalCount') or 0)
        its = root.findall('.//item')
        for it in its:
            t = lambda tag: (it.findtext(tag) or '').strip()
            rows.append((f"{t('dealYear')}-{t('dealMonth').zfill(2)}-{t('dealDay').zfill(2)}", t('aptNm'), t('umdNm'),
                         num(t('excluUseAr')), int(num(t('dealAmount'))), t('cdealType')))
        if len(rows) >= total or not its: break
        page += 1
    return args, rows


ok = fail = 0
t0 = time.time()
with ThreadPoolExecutor(3) as ex:
    for (code, ym), rows in ex.map(job, jobs[:MAX]):
        if rows is None: fail += 1; continue
        add(code, rows); T[code]['_done'].add(ym); ok += 1
        if ok % 500 == 0:
            print(f'  {ok}개 달 완료 ({time.time() - t0:.0f}초, 호출 {calls["n"]})')
            for c in CODES: finish(c)                   # 중간 저장 (시간 초과 대비)
for c in CODES: finish(c)
left = sum(1 for ym in months for c in CODES if ym not in T[c]['_done'])
froms = [T[c].get('from') for c in CODES]
print(f'받은 달 {ok}개, 못 받은 달 {fail}개, 호출 {calls["n"]}번, 남은 (지역·달) {left}개')
print('모든 지역이 채워진 시작 달:', max(f for f in froms if f) if all(froms) else '아직 비어 있는 지역 있음')
