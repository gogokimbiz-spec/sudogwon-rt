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
# 청약 당첨운 (unse/index.html 의 cy 문구·별점, CARDS 와 같은 순서)
CY = [
    {"score": 4, "msg": "열쇠는 자격을 뜻해요. 청약 가점과 통장 납입 횟수를 한 번 점검해보면 생각보다 가까운 기회가 보일 수 있어요."},
    {"score": 4, "msg": "밝은 기운이 들어오는 카드. 이번 주 접수 단지 중 내 조건과 맞는 곳이 있는지 가볍게 살펴보세요."},
    {"score": 5, "msg": "청약운이 가장 강한 카드! 납입을 빠뜨리지 않았는지, 1순위 조건은 채웠는지 확인해보세요."},
    {"score": 4, "msg": "분양 소식과 인연이 있는 카드. 입주자모집공고를 꼼꼼히 읽어보면 숨은 포인트가 보여요."},
    {"score": 3, "msg": "새 보금자리로 옮겨가는 카드. 거주지역 요건과 우선공급 조건을 다시 확인해보세요."},
    {"score": 3, "msg": "작은 실수가 당첨을 흔들 수 있어요. 자격 요건과 제출 서류를 미리 챙겨두면 든든해요."},
    {"score": 4, "msg": "교통과 인연이 있는 카드. 새 노선 근처 분양 일정을 눈여겨보세요."},
    {"score": 5, "msg": "당첨의 기운이 반짝이는 카드. 망설였던 단지가 있다면 조건을 다시 검토해볼 만해요."},
    {"score": 4, "msg": "신청 버튼을 누를 용기가 생기는 카드. 접수 마감일을 달력에 적어두세요."},
    {"score": 4, "msg": "재도전의 카드. 지난번 아쉬웠던 경험이 이번엔 전략이 돼요."},
    {"score": 3, "msg": "여유가 필요한 시기. 무리한 도전보다 나에게 맞는 단지를 고르는 눈이 중요해요."},
    {"score": 2, "msg": "이번엔 쉬어가도 괜찮은 카드. 다음 기회를 위해 가점과 자금 계획을 정리해두세요."}
]
DIRS = ["남향", "남동향", "남서향", "동향", "서향"]
WD = '월화수목금토일'

def kst_today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()

def today_card(day=None, theme='today'):
    """theme: 'today'(오늘의 부동산운, 매일) / 'cy'(청약 당첨운, 청약 주간 글)"""
    day = day or kst_today()
    r = random.Random(('unse-' if theme == 'today' else f'unse-{theme}-') + day.isoformat())
    i = r.randrange(len(CARDS))
    luck = {'floor': 2 + r.randrange(28), 'dir': r.randrange(len(DIRS)), 'num': 1 + r.randrange(9)}
    c = dict(CARDS[i], no=i + 1, day=day, luck=luck, dir=DIRS[luck['dir']])
    if theme == 'cy':
        c.update(CY[i])
    c['theme'] = theme
    c['stars'] = '★' * c['score'] + '☆' * (5 - c['score'])
    c['label'] = f"{day.month}월 {day.day}일({WD[day.weekday()]})"
    c['image'] = f"{SITE}unse/cards/{i + 1}.png"
    c['url'] = SITE + 'unse/' + ('?t=cy' if theme == 'cy' else '')   # '나도 카드 뽑기' → 새로 뽑는 화면(테마 미리 선택)
    c['result_url'] = SITE + 'unse/?' + urllib.parse.urlencode({'t': 'today', 'c': i + 1, 'f': luck['floor'], 'd': luck['dir'], 'n': luck['num']})
    return c

def blog_html(c, heading):
    """블로그 글에 넣는 타로 칸 HTML (id="tarot")"""
    from html import escape as esc
    return ('<div id="tarot" style="margin:0 0 22px;padding:16px;border-radius:16px;background:linear-gradient(135deg,#0f2742,#1f4f8f);color:#fff;text-align:center">'
            f'<div style="font-size:13px;color:#e8b94a;font-weight:bold;letter-spacing:.02em">🔮 {esc(heading)}</div>'
            f'<img src="{c["image"]}" alt="부동산 타로 카드 {esc(c["n"])}" style="width:180px;max-width:60%;height:auto;margin:10px auto 6px;display:block;border-radius:10px">'
            f'<div style="font-size:20px;font-weight:bold;color:#fff">{esc(c["n"])} <span style="color:#e8b94a;font-size:16px">{c["stars"]}</span></div>'
            f'<div style="font-size:12.5px;color:#b9c8dc;margin:2px 0 8px">{esc(c["kw"])}</div>'
            f'<div style="font-size:15px;line-height:1.6;color:#fff;margin:0 auto 10px;max-width:440px">{esc(c["msg"])}</div>'
            f'<div style="font-size:13px;color:#d6e2f2;margin-bottom:12px">행운의 층 <b style="color:#fff">{c["luck"]["floor"]}층</b> · 행운의 방향 <b style="color:#fff">{c["dir"]}</b> · 행운의 숫자 <b style="color:#fff">{c["luck"]["num"]}</b></div>'
            f'<a href="{c["url"]}" style="display:inline-block;background:#ff5c5c;color:#fff;font-weight:bold;font-size:16px;padding:11px 22px;border-radius:999px;text-decoration:none">🔮 나도 카드 뽑기 ›</a>'
            '<div style="font-size:11px;color:#93a6bf;margin-top:10px">재미로 보는 운세이며 투자·청약 판단의 근거가 아닙니다</div></div>')

if __name__ == '__main__':
    import sys
    d = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    for th in ('today', 'cy'):
        c = today_card(d, th)
        print(th, c['label'], c['no'], c['n'], c['stars'], c['msg'], c['url'])
