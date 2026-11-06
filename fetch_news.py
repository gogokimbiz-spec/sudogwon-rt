"""언론사 부동산 RSS 에서 오늘의 부동산 뉴스 1건을 골라 summary.json 에 넣습니다 (GitHub Actions 용).
API 키가 필요 없습니다. 기사 본문은 가져오지 않고 제목·언론사·링크만 씁니다.
"""
import sys, json, re, html, datetime, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEEDS = [('한국경제', 'https://www.hankyung.com/feed/realestate'),
         ('매일경제', 'https://www.mk.co.kr/rss/50300009/')]
GOOD = ['아파트', '집값', '전세', '매매', '서울', '수도권', '재건축', '재개발', '분양', '청약', '대출', '금리', '신고가', '거래', '규제', '공급', '매물']
BAD = ['근무복', '봉사', '기부', '후원', '수상', '인사', '부고', '포토', '사진', '광고', 'MAI부동산', '이벤트', '채용', 'CEO', '협약', 'MOU']

path = sys.argv[1]
S = json.load(open(path, encoding='utf-8'))
now = datetime.datetime.now(datetime.timezone.utc)
cands = []
for src, url in FEEDS:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (rt-briefing)'})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
    except Exception as e:
        print(f'{src} RSS 읽기 실패: {e}'); continue
    for it in root.iter('item'):
        title = html.unescape(re.sub(r'<[^>]+>', '', it.findtext('title') or '')).strip()
        link = (it.findtext('link') or '').strip()
        raw = (it.findtext('pubDate') or '').strip()
        try:
            pub = parsedate_to_datetime(re.sub(r'([+-]\d{2}):(\d{2})$', r'\1\2', raw))  # '+09:00' → '+0900'
        except Exception:
            continue
        if pub.tzinfo is None:  # 시간대 표시가 없으면 한국 시간으로 간주
            pub = pub.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        age = (now - pub).total_seconds() / 3600
        if not title or not link or age > 30: continue
        score = sum(k in title for k in GOOD) * 2 - sum(k in title for k in BAD) * 10 - age / 8
        cands.append((score, title, link, src))
    print(f'{src}: 후보 누적 {len(cands)}건')
if not cands:
    print('최근 30시간 안의 부동산 뉴스를 찾지 못했습니다.'); sys.exit(0)
cands.sort(key=lambda x: -x[0])
_, title, link, src = cands[0]
S['news'] = {'title': title, 'link': link, 'source': src}
json.dump(S, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('오늘의 뉴스:', S['news'])
