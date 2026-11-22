"""매매·전세 갭 카드 카톡 '나에게 보내기' (매주 화요일). 입력: 배포된 gap/summary.json  (2026-11-23)
summary 의 made(만든 날)가 오늘일 때만 보냅니다. 같은 작업에서 앞 단계가 토큰을 바꿨다면 .kakao_rt 파일의 새 값을 씁니다.
"""
import os, sys, json, datetime, subprocess, urllib.request, urllib.parse, urllib.error
VER = f"{os.environ.get('GITHUB_RUN_ID', '')}{os.environ.get('GITHUB_RUN_ATTEMPT', '')}" or str(int(__import__('time').time()))

try:
    S = json.load(open(sys.argv[1], encoding='utf-8'))
except Exception:
    print('갭 카드 자료가 없습니다 (매주 화요일만 만듦)'); sys.exit(0)
TODAY = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date().isoformat()
if S.get('made') != TODAY:
    print('오늘은 갭 카톡이 없습니다'); sys.exit(0)
K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if os.path.exists('.kakao_rt'):
    K['KAKAO_REFRESH_TOKEN'] = open('.kakao_rt').read().strip() or K['KAKAO_REFRESH_TOKEN']
if not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
link = S.get('blog_url') or f"{SITE}r/{S['code']}.html"
card = f'{SITE}gap/card.png'


def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억' + (f' {m:,}' if m else '')) if e else f'{m:,}만'


rows = sorted(S['rows'], key=lambda r: r[6] - r[7], reverse=True)
b, s = rows[0], rows[-1]
tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
H = {'Authorization': 'Bearer ' + tok['access_token']}
tpl = {'object_type': 'feed',
       'content': {'title': f"🏠 {S['name']} 아파트 매매·전세 갭",
                   'description': f"갭 최대 {b[0]} {man(b[6] - b[7])} · 최소 {s[0]} {man(s[6] - s[7])}",
                   'image_url': f'{card}?v={VER}', 'image_width': 1080, 'image_height': 1350,
                   'link': {'web_url': link, 'mobile_web_url': link}},
       'buttons': [{'title': '단지별 갭 전체 보기', 'link': {'web_url': link, 'mobile_web_url': link}}]}
try:
    res = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
          data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(), headers=H)))
    print('갭 카톡:', res)
except urllib.error.HTTPError as err:
    print('::warning::갭 카톡 실패:', err.read().decode('utf-8', 'replace')[:300])
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
