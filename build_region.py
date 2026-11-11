"""동네 대표기업: 오늘 올릴 지역·순위 구간을 정하고 site/dong/summary.json 을 만듭니다 (GitHub Actions, 매주 목요일 – 인스타·스레드 전용).
12개 지역을 한 바퀴 돌 때마다 순위 구간이 10씩 내려갑니다: 1바퀴 1~10위, 2바퀴 11~20위, 3바퀴 21~30위 → 끝 (최대 36주)
사용법: python build_region.py region_data.json site
수동 실행: 환경변수 REGION_POST=next(이번 차례) 또는 지역 키(gangnam, bundang …, 그 지역의 이번 바퀴 구간)
"""
import os, sys, json, datetime

D = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = os.path.join(sys.argv[2], 'dong'); os.makedirs(OUT, exist_ok=True)
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
ORDER = ['gangnam', 'bundang', 'seocho', 'songpa', 'yeonsu', 'mapo', 'yongsan', 'seongdong', 'yeongtong', 'suji', 'dongtan', 'gwacheon']
ROUNDS = 3                             # 30위까지만
START = datetime.date(2026, 11, 12)    # 첫 게시 (목)
DAYS = (3,)                            # 목 (월=0)
MIN_ROWS = 5                           # 구간에 이만큼도 없으면 그 차례는 다음 지역으로
env = os.environ.get('REGION_POST', '').strip()

n = sum(1 for i in range((today - START).days + 1) if (START + datetime.timedelta(days=i)).weekday() in DAYS)
slot = max(n - 1, 0)
post = None
if env in D['regions'] or today.weekday() in DAYS or env == 'next':
    cands = [(env, slot // len(ORDER))] if env in D['regions'] else \
            [(ORDER[(slot + k) % len(ORDER)], (slot + k) // len(ORDER)) for k in range(len(ORDER))]
    for key, rnd in cands:
        if rnd >= ROUNDS: continue
        R = D['regions'].get(key) or {}
        rows = [x for x in R.get('top', []) if rnd * 10 < x['rank'] <= rnd * 10 + 10]
        if len(rows) >= MIN_ROWS:
            post = {'key': key, 'name': R['name'], 'code': R['code'], 'companies': R['companies'], 'round': rnd,
                    'start': rnd * 10 + 1, 'end': rnd * 10 + len(rows), 'rows': rows}
            break
if post:
    print(f"오늘 동네 대표기업: {post['name']} {post['start']}~{post['end']}위")
elif slot // len(ORDER) >= ROUNDS:
    print('30위까지 모두 발행해서 동네 대표기업 시리즈는 끝났습니다')
else:
    print('오늘은 동네 대표기업 글이 없습니다 (목요일만, 또는 자료 부족)')
json.dump({'day': today.isoformat(), 'asof': D['asof'], 'fy': D['fy'], 'post': post},
          open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
