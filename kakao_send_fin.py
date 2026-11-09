"""기업재무 요약(fin/summary.json)으로 카카오톡 '나에게 보내기' (화·금요일, GitHub Actions 용).
필요한 Secret: KAKAO_REST_KEY, KAKAO_CLIENT_SECRET, KAKAO_REFRESH_TOKEN (실거래 알림과 같은 값)
선택 Secret: GH_PAT (새 refresh_token 을 Secret 에 자동 저장)
같은 작업에서 kakao_send.py 등이 먼저 토큰을 바꿨다면 .kakao_rt 파일의 새 값을 씁니다.
"""
import os, sys, json, datetime, subprocess, urllib.request, urllib.parse, urllib.error

S = json.load(open(sys.argv[1], encoding='utf-8'))
P = S.get('post')
if not P:
    print('오늘은 기업재무 카톡이 없습니다'); sys.exit(0)
K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if os.path.exists('.kakao_rt'):
    K['KAKAO_REFRESH_TOKEN'] = open('.kakao_rt').read().strip() or K['KAKAO_REFRESH_TOKEN']
DRY = '--dry' in sys.argv
if not DRY and not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)
SITE = (os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/').rstrip('/') + '/fin/'
link = S.get('blog_url') or SITE
bd = datetime.date.fromisoformat(S['basDt'])
R = S['rank']
cut = lambda s, n=9: s if len(s) <= n else s[:n] + '…'
fmt = {'per': lambda v: f'{v:,.1f}배', 'pbr': lambda v: f'{v:.2f}배', 'opm': lambda v: f'{v:.1f}%',
       'dr': lambda v: f'{v:,.0f}%', 'gr': lambda v: f'{v:+.1f}%',
       'op': lambda v: f'{v / 1e12:,.1f}조' if abs(v) >= 1e12 else f'{v / 1e8:,.0f}억'}
NAME = {'opm': ('영업이익률 TOP', 'opm'), 'low_debt': ('부채비율 낮은 기업', 'dr'), 'growth': ('매출 성장률 TOP', 'gr'),
        'turn': ('흑자전환 기업', 'op'), 'low_per': ('PER 낮은 순', 'per'), 'low_pbr': ('PBR 낮은 순', 'pbr')}


def compose(n):
    if P['kind'] == 'rank':
        t, k = NAME[P['keys'][0]]
        L = [f"📊 기업재무 | {t}", f"{S['fy']} 사업연도 · 시총 상위 500", '']
        L += [f"{i}. {cut(x['name'])} {fmt[k](x[k])}" for i, x in enumerate(R[P['keys'][0]][:n], 1)]
    else:
        L = [f"📉 저평가 지표 | {bd.month}.{bd.day} 종가", '시총 상위 500 · PER·PBR 낮은 순']
        for key in P['keys']:
            t, k = NAME[key]
            L += ['', t] + [f"{i}. {cut(x['name'])} {fmt[k](x[k])}" for i, x in enumerate(R[key][:n], 1)]
    L += ['', f'👉 {link}']
    return '\n'.join(L)


for n in (5, 4, 3, 2, 1):   # 카카오 텍스트는 200자 안팎이 넘으면 잘릴 수 있어 줄입니다
    text = compose(n)
    if len(text) <= 200: break
print(text, f'\n({len(text)}자)')
if DRY: sys.exit(0)

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
SEND = 'https://kapi.kakao.com/v2/api/talk/memo/default/send'
H = {'Authorization': 'Bearer ' + tok['access_token']}
tpl = {'object_type': 'text', 'text': text, 'link': {'web_url': link, 'mobile_web_url': link}, 'button_title': '블로그 글 보기'}
res = json.load(urllib.request.urlopen(urllib.request.Request(SEND, data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(), headers=H)))
print('카카오 전송 결과:', res)
if res.get('result_code') != 0:
    sys.exit('카카오 전송 실패')
# 카드 이미지
card = SITE + 'cards/latest.png'
try: ok_img = urllib.request.urlopen(urllib.request.Request(card, method='HEAD'), timeout=20).status == 200
except Exception: ok_img = False
if ok_img:
    feed = {'object_type': 'feed', 'content': {'title': S.get('title') or text.split('\n')[0],
            'description': '이미지를 눌러 크게 보기', 'image_url': f"{card}?d={S.get('day', '')}", 'image_width': 1080, 'image_height': 1350,
            'link': {'web_url': link, 'mobile_web_url': link}},
            'buttons': [{'title': '500곳 전체 표', 'link': {'web_url': SITE, 'mobile_web_url': SITE}}]}
    try:
        r2 = json.load(urllib.request.urlopen(urllib.request.Request(SEND, data=urllib.parse.urlencode({'template_object': json.dumps(feed, ensure_ascii=False)}).encode(), headers=H)))
        print('재무 이미지 전송 결과:', r2)
    except urllib.error.HTTPError as err:
        print('::warning::재무 이미지 전송 실패:', err.read().decode('utf-8', 'replace')[:300])
else:
    print('재무 카드 이미지가 없어 이미지 메시지는 건너뜁니다')
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
