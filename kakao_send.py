"""summary.json 으로 카카오톡 '나에게 보내기'를 합니다 (GitHub Actions 용).
필요한 Secret: KAKAO_REST_KEY, KAKAO_CLIENT_SECRET, KAKAO_REFRESH_TOKEN
선택 Secret: GH_PAT (카카오가 새 refresh_token 을 주면 KAKAO_REFRESH_TOKEN Secret 을 자동으로 바꿔 둠)
"""
import os, sys, json, datetime, subprocess, urllib.request, urllib.parse, urllib.error

K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)
SITE = os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
VER = f"{os.environ.get('GITHUB_RUN_ID', '')}{os.environ.get('GITHUB_RUN_ATTEMPT', '')}" or str(int(__import__('time').time()))  # 카카오가 같은 주소의 이미지를 캐시하므로 실행마다 다른 주소
S = json.load(open(sys.argv[1], encoding='utf-8'))

def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}' if m else f'{e}억') if e else f'{m:,}만'
def city(r):  # 신고가 줄: '광명시'→'광명', '서울 강남구'→'강남', '용인 기흥구'→'용인'
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' else p[0]
    if p[0] in ('서울', '인천'): return p[1][:-1] if len(p[1]) > 2 else r
    return p[0]
def area_name(r):  # 관심지역 줄: '서울 강남구'→'강남', '성남 분당구'→'성남 분당', '광명시'→'광명'
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' else p[0]
    g = p[1][:-1] if len(p[1]) > 2 else p[1]
    return g if p[0] == '서울' else f'{p[0]} {g}'
cut = lambda s, n=12: s if len(s) <= n else s[:n] + '…'
def man2(v):  # 3.3㎡당 가격: 1억 2,768만 / 7,460만
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}만' if m else f'{e}억') if e else f'{m:,}만'
d = datetime.date.fromisoformat(S['day']); wd = '월화수목금토일'[d.weekday()]
LB = S.get('label') or f"{d.month}월 {d.day}일({wd})"
link = S.get('blog_url') or SITE
L = [f"🏠 수도권 아파트 실거래 | {LB}", f"매매 {S['trade_count']}건 · 전세 {S['jeonse_count']}건", '']
if S.get('news'):
    L += [f"📰 {S['news']['title']}", '']
nh = S.get('new_highs') or []
if nh:
    L.append(f"🔺 신고가 {len(nh)}건 (최근 6개월 기준)")
    L += [f"· {city(t['region'])} {cut(t['apt'])} {t['area']}㎡ {man(t['price_man'])}" for t in nh[:3]]
    if len(nh) > 3: L.append(f"  외 {len(nh) - 3}건")
else:
    L.append('💰 거래가 상위 3건')
    L += [f"· {city(t['region'])} {cut(t['apt'])} {t['area']}㎡ {man(t['price_man'])}" for t in (S.get('day_trades') or S.get('top_trades') or [])[:3]]
w = S.get('watch') or []
if w:
    L += ['', '📊 관심지역 30일 (3.3㎡당)']
    L += [f"· {area_name(x['region'])} {man2(x['pp_man'])} {'▲' if x['chg'] >= 0 else '▼'}{abs(x['chg'])}%" for x in w]
L += ['', f'👉 {link}']
text = '\n'.join(L)
print(text)

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
tpl = {'object_type': 'text', 'text': text, 'link': {'web_url': link, 'mobile_web_url': link}, 'button_title': '자세히 보기'}
req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                             data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(),
                             headers={'Authorization': 'Bearer ' + tok['access_token']})
# 이미지가 있으면 글 메시지는 보내지 않고 이미지만 보냅니다 (이미지를 못 만든 날만 글로 대신 보냄)
_card = SITE.rstrip('/') + '/cards/latest.png'
try: _has_card = urllib.request.urlopen(urllib.request.Request(_card, method='HEAD'), timeout=20).status == 200
except Exception: _has_card = False
if not _has_card:
    res = json.load(urllib.request.urlopen(req))
    print('카카오 전송 결과:', res)
    if res.get('result_code') != 0:
        sys.exit('카카오 전송 실패')
else:
    print('카드 이미지가 있어 글 메시지는 생략합니다')

# 오늘의 신고가 이미지 (사이트에 올라간 cards/latest.png) 를 피드 메시지로 한 번 더
card = SITE.rstrip('/') + '/cards/latest.png'
try:
    ok_img = urllib.request.urlopen(urllib.request.Request(card, method='HEAD'), timeout=20).status == 200
except Exception:
    ok_img = False
if ok_img:
    nhn = len(S.get('new_highs') or [])
    feed = {'object_type': 'feed',
            'content': {'title': f"{LB} 수도권 아파트 " + (f"신고가 {nhn}건" if nhn else '거래가 TOP'),
                        'description': '이미지를 눌러 크게 보기',
                        'image_url': f"{card}?v={VER}", 'image_width': 1080, 'image_height': 1350,
                        'link': {'web_url': link, 'mobile_web_url': link}},
            'buttons': [{'title': '자세히 보기', 'link': {'web_url': link, 'mobile_web_url': link}}]}
    req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                                 data=urllib.parse.urlencode({'template_object': json.dumps(feed, ensure_ascii=False)}).encode(),
                                 headers={'Authorization': 'Bearer ' + tok['access_token']})
    try:
        print('카카오 이미지 전송 결과:', json.load(urllib.request.urlopen(req)))
    except urllib.error.HTTPError as e:
        print('::warning::카카오 이미지 전송 실패:', e.read().decode('utf-8', 'replace')[:200])
else:
    print('오늘의 카드 이미지가 없어 이미지 메시지는 건너뜁니다.')

# 오늘의 부동산 타로 (블로그 글의 타로 칸으로 연결 – 블로그 방문 유도)
try:
    from tarot import today_card
    t = today_card()
    ok_t = urllib.request.urlopen(urllib.request.Request(t['image'], method='HEAD'), timeout=20).status == 200
except Exception as e:
    ok_t = False; print('타로 카드 이미지를 확인하지 못해 타로 메시지는 건너뜁니다:', e)
if ok_t:
    tl = (S.get('blog_url') or SITE) + ('#tarot' if S.get('blog_url') else '')
    feed = {'object_type': 'feed', 'content': {'title': f"🔮 {t['label']} 부동산 타로 · {t['n']} {t['stars']}",
            'description': t['msg'], 'image_url': t['image'], 'image_width': 800, 'image_height': 800,
            'link': {'web_url': tl, 'mobile_web_url': tl}},
            'buttons': [{'title': '🔮 나도 카드 뽑기', 'link': {'web_url': tl, 'mobile_web_url': tl}}]}
    try:
        r3 = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
             data=urllib.parse.urlencode({'template_object': json.dumps(feed, ensure_ascii=False)}).encode(),
             headers={'Authorization': 'Bearer ' + tok['access_token']})))
        print('타로 전송 결과:', r3)
    except urllib.error.HTTPError as err:
        print('::warning::타로 전송 실패:', err.read().decode('utf-8', 'replace')[:300])
# 인스타 게시용 페이지 링크만 따로 한 통 ("인스타용")
INSTA = SITE.rstrip('/') + '/insta/'
tpl_i = {'object_type': 'text', 'text': f'인스타용\n{INSTA}', 'link': {'web_url': INSTA, 'mobile_web_url': INSTA}, 'button_title': '인스타용'}
try:
    r4 = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
         data=urllib.parse.urlencode({'template_object': json.dumps(tpl_i, ensure_ascii=False)}).encode(),
         headers={'Authorization': 'Bearer ' + tok['access_token']})))
    print('인스타용 링크 전송 결과:', r4)
except urllib.error.HTTPError as err:
    print('::warning::인스타용 링크 전송 실패:', err.read().decode('utf-8', 'replace')[:300])
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)  # 같은 작업의 청약 알림이 새 토큰을 쓰도록
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
    else:
        print('::warning::카카오가 새 refresh_token 을 발급했지만 GH_PAT 가 없어 저장하지 못했습니다. 약 1개월 안에 KAKAO_REFRESH_TOKEN 을 다시 발급해 넣어 주세요.')
