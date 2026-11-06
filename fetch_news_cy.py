"""언론사 부동산 RSS 에서 최근 1주일 청약·분양 뉴스 3건을 골라 청약 summary.json 에 넣습니다 (GitHub Actions 용).
API 키가 필요 없습니다. 기사 본문은 가져오지 않고 제목·언론사·링크만 씁니다.
사용법: python fetch_news_cy.py site/cheongyak/summary.json
"""
import sys, json, re, html, datetime, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEEDS = [('한국경제', 'https://www.hankyung.com/feed/realestate'),
         ('매일경제', 'https://www.mk.co.kr/rss/50300009/')]
MUST = ['청약', '분양', '모집공고', '당첨', '경쟁률', '미분양', '줍줍', '무순위', '사전청약', '분양가', '특별공급', '특공', '가점']
GOOD = ['수도권', '서울', '경기', '인천', '아파트', '1순위', '마감', '신혼', '생애최초', '공공분양', '상한제', '로또', '입주']
BAD = ['근무복', '봉사', '기부', '후원', '수상', '인사', '부고', '포토', '사진', '광고', '이벤트', '채용', 'CEO', '협약', 'MOU', '분양광고', '[분양]', '모델하우스 오픈']

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
        try: pub = parsedate_to_datetime(it.findtext('pubDate'))
        except Exception: continue
        age = (now - pub).total_seconds() / 3600
        if not title or not link or age > 7 * 24 or not any(k in title for k in MUST): continue
        score = sum(k in title for k in MUST) * 3 + sum(k in title for k in GOOD) - sum(k in title for k in BAD) * 10 - age / 24
        cands.append((score, title, link, src, pub.astimezone(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()))
    print(f'{src}: 후보 누적 {len(cands)}건')
cands.sort(key=lambda x: -x[0])
picked = []
for c in cands:
    if c[0] < 0: break
    words = set(re.findall(r'[가-힣A-Za-z0-9]{2,}', c[1]))
    # 같은 사건을 다룬 비슷한 제목은 하나만
    if any(len(words & set(re.findall(r'[가-힣A-Za-z0-9]{2,}', p['title']))) >= max(3, len(words) // 2) for p in picked): continue
    picked.append({'title': c[1], 'link': c[2], 'source': c[3], 'date': c[4]})
    if len(picked) == 3: break
S['news'] = picked
json.dump(S, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('청약 뉴스:', picked if picked else '없음')
