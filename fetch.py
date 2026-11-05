"""국토교통부 아파트 매매·전월세 실거래 수집 (GitHub Actions 용).
환경변수 DATA_GO_KR_KEY 에 공공데이터포털 일반 인증키(Decoding)를 넣어 실행합니다.
결과: rt_data.json (build.py 입력 형식)
"""
import os, sys, json, time, datetime, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ['DATA_GO_KR_KEY'].strip()
CODES = ['11110','11140','11170','11200','11215','11230','11260','11290','11305','11320','11350','11380','11410','11440','11470','11500','11530','11545','11560','11590','11620','11650','11680','11710','11740',
 '28125','28155','28177','28185','28200','28237','28245','28275','28290',
 '41111','41113','41115','41117','41131','41133','41135','41150','41171','41173','41192','41194','41196','41210','41220','41250','41271','41273','41281','41285','41287','41290','41310','41360','41370','41390','41410','41430','41450','41461','41463','41465','41480','41500','41550','41570','41591','41593','41595','41597','41610','41630']
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
MONTHS = []
for k in range(6, -1, -1):
    y, m = today.year, today.month - k
    while m <= 0: y, m = y - 1, m + 12
    MONTHS.append(f'{y}{m:02d}')
BASE = 'https://apis.data.go.kr/1613000/'
PATH = {'trade': 'RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev', 'rent': 'RTMSDataSvcAptRent/getRTMSDataSvcAptRent'}
num = lambda s: float((s or '0').replace(',', '').strip() or 0)

def get(kind, code, ym, page):
    q = urllib.parse.urlencode({'serviceKey': KEY, 'LAWD_CD': code, 'DEAL_YMD': ym, 'numOfRows': 1000, 'pageNo': page})
    for a in range(8):
        try:
            with urllib.request.urlopen(BASE + PATH[kind] + '?' + q, timeout=60) as r:
                root = ET.fromstring(r.read())
            rc = root.findtext('.//resultCode')
            if rc in ('000', '00'):
                return root
        except Exception as e:
            err = e
        time.sleep(1 + a)
    return None

def job(args):
    kind, code, ym = args
    recs, page = [], 1
    while True:
        root = get(kind, code, ym, page)
        if root is None: return args, None
        total = int(root.findtext('.//totalCount') or 0)
        items = root.findall('.//item')
        for it in items:
            t = lambda tag: (it.findtext(tag) or '').strip()
            date = f"{t('dealYear')}-{t('dealMonth').zfill(2)}-{t('dealDay').zfill(2)}"
            if kind == 'trade':
                recs.append([code, date, t('aptNm'), t('umdNm'), num(t('excluUseAr')), int(num(t('floor'))), int(num(t('dealAmount'))), int(num(t('buildYear'))), t('cdealType')])
            else:
                recs.append([code, date, t('aptNm'), t('umdNm'), num(t('excluUseAr')), int(num(t('deposit'))), int(num(t('monthlyRent')))])
        if len(recs) >= total or not items: break
        page += 1
    return args, recs

jobs = [(k, c, m) for c in CODES for m in MONTHS for k in ('trade', 'rent')]
raw, failed = {'trade': [], 'rent': []}, []
with ThreadPoolExecutor(3) as ex:
    for (args, recs) in ex.map(job, jobs):
        if recs is None: failed.append(args)
        else: raw[args[0]].extend(recs)
if failed:  # 한 번 더, 천천히
    for args in list(failed):
        a, recs = job(args)
        if recs is not None:
            raw[a[0]].extend(recs); failed.remove(args)
print(f'months {MONTHS[0]}~{MONTHS[-1]} jobs {len(jobs)} failed {len(failed)} trade {len(raw["trade"])} rent {len(raw["rent"])}')
if len(failed) > len(jobs) * 0.05 or not raw['trade']:
    sys.exit('too many failures: ' + str(failed[:5]))
out = {'asof': today.isoformat(), 'trade': raw['trade'],
       'jeonse': [[r[0], r[1], r[3], r[4], r[5]] for r in raw['rent'] if r[6] == 0],
       'wolse': sum(1 for r in raw['rent'] if r[6] > 0)}
json.dump(out, open('rt_data.json', 'w', encoding='utf-8'), ensure_ascii=False)
