"""신고가 단지 카드의 '최근 3년 거래 흐름' 그래프용 과거 실거래 모으기 (GitHub Actions, 매일 build 단계).
사용법: python fetch_hist.py site/summary.json   →  hist/<시군구코드>/<YYYYMM>.json
- rt_data.json 이 이미 가진 최근 7개월(0~6개월 전)은 빼고, 7~36개월 전 달만 받습니다.
- 오늘 카드에 나올 단지(신고가 최대 8곳, 없으면 거래가 상위 5곳)의 지역만 받습니다.
- 한 번 받은 달은 저장소에 보관해 다시 받지 않습니다(지난 달 거래는 거의 바뀌지 않음). 실패한 달은 다음 날 다시 시도.
- 하루 최대 HIST_MAX_CALLS(기본 300) 번 호출 – 공공데이터 일일 한도 안에서 여유 있게.
행 형식: [계약일, 단지명, 법정동, 전용면적, 층, 거래가(만원), 해제여부]
필요: 환경변수 DATA_GO_KR_KEY (fetch.py 와 같은 키), 같은 폴더의 names.json
"""
import os, sys, json, time, datetime, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ.get('DATA_GO_KR_KEY', '').strip()
if not KEY:
    print('DATA_GO_KR_KEY 가 없어 과거 거래 수집을 건너뜁니다'); sys.exit(0)
S = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = 'hist'
MAX = int(os.environ.get('HIST_MAX_CALLS', '300') or 300)
CODE_OF = {v: k for k, v in json.load(open('names.json', encoding='utf-8')).items()}
items = (S.get('new_highs') or [])[:8] or (S.get('day_trades') or [])[:5]     # make_cards.py 단지별 카드와 같은 기준
codes = list(dict.fromkeys(CODE_OF[t['region']] for t in items if t['region'] in CODE_OF))
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
months = []
for k in range(7, 37):
    y, m = today.year, today.month - k
    while m <= 0: y, m = y - 1, m + 12
    months.append(f'{y}{m:02d}')
jobs = [(c, ym) for c in codes for ym in months if not os.path.exists(os.path.join(OUT, c, f'{ym}.json'))][:MAX]
print(f'과거 거래: 지역 {len(codes)}곳, 받을 달 {len(jobs)}개 (최대 {MAX})')
if not jobs: sys.exit(0)

URL = 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev'
num = lambda s: float((s or '0').replace(',', '').strip() or 0)


def get(code, ym, page):
    q = urllib.parse.urlencode({'serviceKey': KEY, 'LAWD_CD': code, 'DEAL_YMD': ym, 'numOfRows': 1000, 'pageNo': page})
    for a in range(5):
        try:
            with urllib.request.urlopen(URL + '?' + q, timeout=60) as r:
                root = ET.fromstring(r.read())
            if root.findtext('.//resultCode') in ('000', '00'): return root
        except Exception:
            pass
        time.sleep(1 + a)
    return None


def job(args):
    code, ym = args
    rows, page = [], 1
    while True:
        root = get(code, ym, page)
        if root is None: return args, None
        total = int(root.findtext('.//totalCount') or 0)
        its = root.findall('.//item')
        for it in its:
            t = lambda tag: (it.findtext(tag) or '').strip()
            rows.append([f"{t('dealYear')}-{t('dealMonth').zfill(2)}-{t('dealDay').zfill(2)}", t('aptNm'), t('umdNm'),
                         num(t('excluUseAr')), int(num(t('floor'))), int(num(t('dealAmount'))), t('cdealType')])
        if len(rows) >= total or not its: break
        page += 1
    return args, rows


ok = fail = 0
with ThreadPoolExecutor(3) as ex:
    for (code, ym), rows in ex.map(job, jobs):
        if rows is None: fail += 1; continue
        os.makedirs(os.path.join(OUT, code), exist_ok=True)
        json.dump(rows, open(os.path.join(OUT, code, f'{ym}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        ok += 1
print(f'과거 거래 저장 {ok}개 달, 실패 {fail}개 (실패한 달은 다음 실행 때 다시 받음)')
