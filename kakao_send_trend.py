"""구별 아파트값 상승률 카톡 '나에게 보내기' (매주 월요일 주간 · 매월 첫째 월요일 월간). 입력: 배포된 trend/summary.json
summary 의 today(오늘 올리는 종류)마다 카드 이미지(feed) 1개. 이미지가 없으면 글 메시지로 대신 보냅니다.
같은 작업에서 앞 단계가 토큰을 바꿨다면 .kakao_rt 파일의 새 값을 씁니다.
"""
import os, sys, json, subprocess, urllib.request, urllib.parse, urllib.error
VER = f"{os.environ.get('GITHUB_RUN_ID', '')}{os.environ.get('GITHUB_RUN_ATTEMPT', '')}" or str(int(__import__('time').time()))  # 카카오 이미지 캐시 피하기

S = json.load(open(sys.argv[1], encoding='utf-8'))
modes = [m for m in (S.get('today') or []) if (S.get(m) or {}).get('rows')]
if not modes:
    print('오늘은 구별 상승률 카톡이 없습니다'); sys.exit(0)
K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if os.path.exists('.kakao_rt'):
    K['KAKAO_REFRESH_TOKEN'] = open('.kakao_rt').read().strip() or K['KAKAO_REFRESH_TOKEN']
DRY = '--dry' in sys.argv
if not DRY and not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
pct = lambda v: f'{v:+.1f}%'
def short(r):
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' and len(p[0]) > 2 else p[0]
    if p[0] in ('서울', '인천'): return p[1] if len(p[1]) > 2 else f'{p[0]} {p[1]}'
    return f'{p[0]} {p[1][:-1]}'

msgs = []
for m in modes:
    P = S[m]; rows = P['rows']; link = P.get('blog_url') or SITE
    up = [r for r in rows if r['chg'] > 0][:3]; dn = [r for r in rows[::-1] if r['chg'] < 0][:3]
    title = (f"📈 {P['label']} 구별 아파트값 상승률 (최근 4주)" if m == 'week' else f"🗺 {P['label']} 구별 아파트값 순위 (전월 대비)")
    text = '\n'.join([title, ''] + (['🔺 ' + ' · '.join(f"{short(r['region'])} {pct(r['chg'])}" for r in up)] if up else [])
                     + (['🔻 ' + ' · '.join(f"{short(r['region'])} {pct(r['chg'])}" for r in dn)] if dn else []) + ['', f'👉 {link}'])[:200]
    msgs.append((m, title, text, link))
    print(text, '\n')
if DRY: sys.exit(0)

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
SEND = 'https://kapi.kakao.com/v2/api/talk/memo/default/send'
H = {'Authorization': 'Bearer ' + tok['access_token']}
for m, title, text, link in msgs:
    card = f'{SITE}trend/{m}.png'
    try: ok_img = urllib.request.urlopen(urllib.request.Request(card, method='HEAD'), timeout=20).status == 200
    except Exception: ok_img = False
    if ok_img:
        tpl = {'object_type': 'feed', 'content': {'title': title, 'description': '이미지를 눌러 크게 보기',
               'image_url': f'{card}?v={VER}', 'image_width': 1080, 'image_height': 1350,
               'link': {'web_url': link, 'mobile_web_url': link}},
               'buttons': [{'title': '구별 전체 순위 보기', 'link': {'web_url': link, 'mobile_web_url': link}}]}
    else:
        tpl = {'object_type': 'text', 'text': text, 'link': {'web_url': link, 'mobile_web_url': link}, 'button_title': '블로그 글 보기'}
    try:
        res = json.load(urllib.request.urlopen(urllib.request.Request(SEND, data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(), headers=H)))
        print(f'구별 상승률({m}) 카톡:', res)
    except urllib.error.HTTPError as err:
        print(f'::warning::구별 상승률({m}) 카톡 실패:', err.read().decode('utf-8', 'replace')[:300])
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
