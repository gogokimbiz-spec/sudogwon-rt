"""국평·소형 최고 실거래가 TOP 16 카드 4장 카톡 '나에게 보내기' (매월 3일). 입력: 배포된 top84/summary.json
summary 의 made(만든 날)가 오늘일 때만 보냅니다. 같은 작업에서 앞 단계가 토큰을 바꿨다면 .kakao_rt 파일의 새 값을 씁니다.
"""
import os, sys, json, datetime, subprocess, urllib.request, urllib.parse, urllib.error
VER = f"{os.environ.get('GITHUB_RUN_ID', '')}{os.environ.get('GITHUB_RUN_ATTEMPT', '')}" or str(int(__import__('time').time()))

try:
    S = json.load(open(sys.argv[1], encoding='utf-8'))
except Exception:
    print('국평·소형 TOP 16 자료가 없습니다 (매월 3일만 만듦)'); sys.exit(0)
TODAY = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date().isoformat()
if S.get('made') != TODAY:
    print('오늘은 국평·소형 TOP 16 카톡이 없습니다'); sys.exit(0)
K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if os.path.exists('.kakao_rt'):
    K['KAKAO_REFRESH_TOKEN'] = open('.kakao_rt').read().strip() or K['KAKAO_REFRESH_TOKEN']
if not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
link = S.get('blog_url') or SITE
NAME = {'seoul_84': ('서울', '국평 84㎡'), 'gg_84': ('경기', '국평 84㎡'), 'seoul_59': ('서울', '소형 59㎡'), 'gg_59': ('경기', '소형 59㎡')}

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
H = {'Authorization': 'Bearer ' + tok['access_token']}
for k in S.get('cards') or list(NAME):
    rows = S.get(k)
    if not rows: continue
    card = f'{SITE}top84/{k}.png'
    try: ok_img = urllib.request.urlopen(urllib.request.Request(card, method='HEAD'), timeout=20).status == 200
    except Exception: ok_img = False
    if not ok_img: print(k, '카드 없음'); continue
    area, kind = NAME[k]; t0 = dict(rows[0]); t0['apt'] = __import__('re').sub(r'\([^()]*\d+동\)', '', t0['apt']).strip() or t0['apt']
    tpl = {'object_type': 'feed',
           'content': {'title': f"🏆 {S['short']} {area} {kind} 최고 실거래가 TOP {len(rows)}",
                       'description': f"1위 {t0['apt']} {t0['price_man'] / 10000:.2f}억 · 이미지를 눌러 크게 보기",
                       'image_url': f'{card}?v={VER}', 'image_width': 1080, 'image_height': 1350,
                       'link': {'web_url': link, 'mobile_web_url': link}},
           'buttons': [{'title': '전체 순위 보기', 'link': {'web_url': link, 'mobile_web_url': link}}]}
    try:
        res = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
              data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(), headers=H)))
        print(f'TOP 16 카톡 ({area} {kind}):', res)
    except urllib.error.HTTPError as err:
        print(f'::warning::TOP 16 카톡 실패 ({area} {kind}):', err.read().decode('utf-8', 'replace')[:300])
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
