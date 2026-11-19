"""주간 부동산 판례 카드 만들기 (API 키 없음) – 2026-11-19 개편
사용법: python law_make.py law_inbox/<게시일>.json
- 매주 수요일 저녁 Claude(사장님 Claude 앱 예약 작업)가 판례 1건을 골라 기승전결로 요약한 JSON 을
  Chrome 으로 저장소 law_inbox/<게시일 YYYY-MM-DD>.json 에 올림 → law.yml 이 이 스크립트로 카드를 만듦
- 결과: cards/law/<게시일>.json, cards/law/<게시일>.png (+ used.json 갱신 – 같은 사건을 다시 안 쓰도록)
inbox JSON 키: case_no, case_name, court_date, result, title(\n 2줄), story[[기,…],[승,…],[전,…],[결,…]], tip, one_line,
               source_url, post_title, blog{title,intro,sections[[제목,본문]…],keywords}, hashtags
"""
import os, re, sys, json, datetime
from make_law_story import make

SRC = sys.argv[1]
DAY = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(SRC)).group(1)
DIR = 'cards/law'; os.makedirs(DIR, exist_ok=True)
JS, PNG, SKIP, USED = f'{DIR}/{DAY}.json', f'{DIR}/{DAY}.png', f'{DIR}/{DAY}.skip', f'{DIR}/used.json'

C = json.load(open(SRC, encoding='utf-8-sig'))
need = ['case_no', 'court_date', 'title', 'story', 'tip']
miss = [k for k in need if not C.get(k)]
if miss or len(C['story']) != 4:
    sys.exit(f'판례 JSON 형식이 맞지 않습니다 (빠진 값: {miss}, story {len(C.get("story") or [])}줄)')
C['story'] = [[str(k), str(v)] for k, v in C['story']]
C.update({'day': DAY, 'made': datetime.date.today().isoformat(), 'date': C['court_date'],
          'case': f"대법원 {C['court_date']} 선고 {C['case_no']} {C.get('case_name', '')} · {C.get('result', '')}".replace('  ', ' ').strip(' ·')})
if os.path.exists(SKIP): os.remove(SKIP)
json.dump(C, open(JS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
make(C, PNG)
used = json.load(open(USED, encoding='utf-8')) if os.path.exists(USED) else []
used = [u for u in used if u.get('day') != DAY] + [{'day': DAY, 'case_no': C['case_no']}]
json.dump(used, open(USED, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"이번 주 판례: {C['case_no']} → {JS}, {PNG}")
