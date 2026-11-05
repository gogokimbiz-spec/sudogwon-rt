"""네이버 뉴스 검색 API 로 오늘의 부동산 뉴스 1건을 골라 summary.json 에 넣습니다 (GitHub Actions 용).
필요한 Secret: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET  (없으면 건너뜀)
기사 본문은 가져오지 않고 제목·언론사·링크만 씁니다.
"""
import os, sys, json, re, html, datetime, urllib.request, urllib.parse
from email.utils import parsedate_to_datetime

cid, sec = os.environ.get('NAVER_CLIENT_ID', '').strip(), os.environ.get('NAVER_CLIENT_SECRET', '').strip()
if not (cid and sec):
    print('네이버 API 설정값이 없어 뉴스를 건너뜁니다.'); sys.exit(0)
path = sys.argv[1]
S = json.load(open(path, encoding='utf-8'))

PRESS = {'yna.co.kr': '연합뉴스', 'chosun.com': '조선일보', 'joongang.co.kr': '중앙일보', 'donga.com': '동아일보', 'hani.co.kr': '한겨레',
         'khan.co.kr': '경향신문', 'mk.co.kr': '매일경제', 'hankyung.com': '한국경제', 'sedaily.com': '서울경제', 'edaily.co.kr': '이데일리',
         'mt.co.kr': '머니투데이', 'fnnews.com': '파이낸셜뉴스', 'heraldcorp.com': '헤럴드경제', 'asiae.co.kr': '아시아경제', 'newsis.com': '뉴시스',
         'news1.kr': '뉴스1', 'kbs.co.kr': 'KBS', 'imbc.com': 'MBC', 'sbs.co.kr': 'SBS', 'jtbc.co.kr': 'JTBC', 'ytn.co.kr': 'YTN',
         'hankookilbo.com': '한국일보', 'seoul.co.kr': '서울신문', 'kmib.co.kr': '국민일보', 'munhwa.com': '문화일보', 'biz.chosun.com': '조선비즈'}
def press(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    for k, v in PRESS.items():
        if host.endswith(k): return v
    return host.replace('www.', '')
clean = lambda s: html.unescape(re.sub(r'<[^>]+>', '', s)).strip()

KEY = ['아파트', '집값', '부동산', '전세', '매매', '분양', '재건축', '주택', '청약', '대출', '금리']
now = datetime.datetime.now(datetime.timezone.utc)
cands = []
for q in ['부동산 시장', '아파트 매매', '수도권 집값']:
    url = 'https://openapi.naver.com/v1/search/news.json?' + urllib.parse.urlencode({'query': q, 'display': 30, 'sort': 'sim'})
    req = urllib.request.Request(url, headers={'X-Naver-Client-Id': cid, 'X-Naver-Client-Secret': sec})
    for it in json.load(urllib.request.urlopen(req, timeout=30)).get('items', []):
        try: pub = parsedate_to_datetime(it['pubDate'])
        except Exception: continue
        age = (now - pub).total_seconds() / 3600
        if age > 30: continue
        title = clean(it['title'])
        score = sum(k in title for k in KEY) * 2 - age / 12 + (1 if q == '부동산 시장' else 0)
        if any(w in title for w in ['[포토]', '[사진]', '[부고]', '[인사]', '광고']): score -= 10
        cands.append((score, title, it))
if not cands:
    print('최근 30시간 안의 부동산 뉴스를 찾지 못했습니다.'); sys.exit(0)
cands.sort(key=lambda x: -x[0])
_, title, it = cands[0]
orig = it.get('originallink') or it['link']
link = it['link'] if 'n.news.naver.com' in it['link'] else orig
S['news'] = {'title': title, 'link': link, 'source': press(orig)}
json.dump(S, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('오늘의 뉴스:', S['news'])
