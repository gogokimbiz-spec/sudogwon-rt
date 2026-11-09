"""오늘의 부동산 타로 (블로그 글·카톡 공용).
카드 내용은 unse/index.html 의 CARDS(오늘의 부동산운)와 같습니다. 카드 문구를 바꾸면 두 곳을 같이 고쳐 주세요.
같은 날짜에는 블로그와 카톡에 같은 카드가 나오도록 날짜로 카드를 정합니다.
"""
import random, datetime, urllib.parse

SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
CARDS = [
    {"n": "황금 열쇠", "kw": "기회 · 시작", "score": 4, "act": "관심 단지 최근 실거래가 확인하기", "msg": "작은 정보 하나가 큰 문을 여는 날. 관심 있던 동네의 최근 거래를 살펴보세요."},
    {"n": "남향 창", "kw": "밝음 · 확신", "score": 5, "act": "햇살 좋은 남향 매물 구경하기", "msg": "분위기가 밝은 하루. 반가운 소식은 의외로 가까운 동네에서 들려올 수 있어요."},
    {"n": "청약 통장", "kw": "꾸준함 · 인내", "score": 3, "act": "청약통장 납입 내역 확인하기", "msg": "서두르기보다 꾸준함이 이기는 날. 오늘은 세워둔 계획을 지키는 것만으로 충분해요."},
    {"n": "모델하우스", "kw": "탐색 · 호기심", "score": 4, "act": "주말 임장 동선 짜보기", "msg": "궁금한 건 직접 확인하는 날. 발품이 손품을 이겨요."},
    {"n": "이사 트럭", "kw": "변화 · 이동", "score": 4, "act": "살고 싶은 동네 3곳 적어보기", "msg": "변화가 반가운 날. 평소 안 가보던 동네 시세를 구경해보세요."},
    {"n": "등기부등본", "kw": "확인 · 신중", "score": 4, "act": "계약 전 확인할 서류 목록 만들기", "msg": "확인 또 확인! 조건을 다시 읽어보는 것만으로 운이 지켜지는 날이에요."},
    {"n": "역세권", "kw": "연결 · 흐름", "score": 5, "act": "출퇴근 30분 안쪽 동네 찾아보기", "msg": "사람과 정보가 연결되는 날. 주변에서 듣는 집 이야기가 힌트가 될 수 있어요."},
    {"n": "새 아파트", "kw": "성취 · 결실", "score": 5, "act": "오늘의 신고가 소식 확인하기", "msg": "기분 좋은 소식이 들려올 수 있는 날. 오늘의 신고가 소식도 살펴보세요."},
    {"n": "계약서", "kw": "약속 · 결정", "score": 4, "act": "자금 계획표 한 장 정리하기", "msg": "약속을 지키면 신뢰가 쌓이는 날. 미뤄둔 상담 예약을 잡아보세요."},
    {"n": "리모델링", "kw": "개선 · 재도약", "score": 4, "act": "지난번 아쉬웠던 점 메모하기", "msg": "작은 변화로 분위기를 바꾸는 날. 정리정돈이 행운을 불러요."},
    {"n": "공원 뷰", "kw": "여유 · 균형", "score": 4, "act": "동네 산책하며 둘러보기", "msg": "산책하듯 가볍게 시세를 둘러보는 날. 마음이 편해야 판단도 정확해요."},
    {"n": "잠긴 문", "kw": "기다림 · 준비", "score": 3, "act": "다음 달 분양 일정 미리 보기", "msg": "무리하지 않는 게 이득인 날. 정보는 모아두고 결정은 내일로 미뤄요."}
]
DIRS = ["남향", "남동향", "남서향", "동향", "서향"]
WD = '월화수목금토일'

def kst_today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()

def today_card(day=None):
    day = day or kst_today()
    r = random.Random('unse-' + day.isoformat())
    i = r.randrange(len(CARDS))
    luck = {'floor': 2 + r.randrange(28), 'dir': r.randrange(len(DIRS)), 'num': 1 + r.randrange(9)}
    c = dict(CARDS[i], no=i + 1, day=day, luck=luck, dir=DIRS[luck['dir']])
    c['stars'] = '★' * c['score'] + '☆' * (5 - c['score'])
    c['label'] = f"{day.month}월 {day.day}일({WD[day.weekday()]})"
    c['image'] = f"{SITE}unse/cards/{i + 1}.png"
    c['url'] = SITE + 'unse/'   # '나도 카드 뽑기' → 새로 뽑는 화면
    c['result_url'] = SITE + 'unse/?' + urllib.parse.urlencode({'t': 'today', 'c': i + 1, 'f': luck['floor'], 'd': luck['dir'], 'n': luck['num']})
    return c

if __name__ == '__main__':
    import sys
    d = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    c = today_card(d)
    print(c['label'], c['no'], c['n'], c['stars'], c['msg'], c['url'])
