"""다음 달부터 달라지는 부동산 9가지 – 카톡 '나에게 보내기' (policy_month.yml) – 2026-11-27
- 미리보기(inbox 가 올라왔을 때): python kakao_send_policy_month.py --preview cards/policy_month/<month>.json
    "말일 15시에 올라갈 카드" + 카드 + [건너뛰기·다시 만들기] 버튼(Actions 화면)
- 게시(말일 15시): python kakao_send_policy_month.py <폴더>/policy_month/summary.json   (SITE_URL 아래 policy_month/card.png)
같은 작업에서 앞 단계가 토큰을 바꿨다면 .kakao_rt 파일의 새 값을 씁니다.
"""
import os, sys, json, subprocess, urllib.request, urllib.parse, urllib.error

PREVIEW = '--preview' in sys.argv
path = [a for a in sys.argv[1:] if not a.startswith('--')][0]
try:
    S = json.load(open(path, encoding='utf-8'))
except Exception:
    print('정책 9가지 카드 자료가 없습니다'); sys.exit(0)
K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if os.path.exists('.kakao_rt'):
    K['KAKAO_REFRESH_TOKEN'] = open('.kakao_rt').read().strip() or K['KAKAO_REFRESH_TOKEN']
if not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)

SITE = (os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/').rstrip('/') + '/'
REPO = os.environ.get('GITHUB_REPOSITORY', 'gogokimbiz-spec/sudogwon-rt')
VER = f"{os.environ.get('GITHUB_RUN_ID', '')}{os.environ.get('GITHUB_RUN_ATTEMPT', '')}" or str(int(__import__('time').time()))
m = int(S['month'][5:7])
items = S['items'][:9]
head = f"{S.get('head1') or f'{m}월부터 달라지는'} {S.get('head2') or '부동산'} {len(items)}가지"
desc = ' · '.join(it['title'] for it in items[:4]) + (' 외' if len(items) > 4 else '')
if PREVIEW:
    img = f"https://raw.githubusercontent.com/{REPO}/main/cards/policy_month/{S['month']}.png"
    link = f'https://github.com/{REPO}/actions/workflows/policy_month.yml'
    d = S.get('day', '')
    tpl = {'object_type': 'feed',
           'content': {'title': f"👀 [미리보기] {d[5:].replace('-', '/')} 15시에 올라갈 카드",
                       'description': f"{head}\n그대로 두면 자동 게시 · 바꾸려면 Claude 에게 말씀",
                       'image_url': f'{img}?v={VER}', 'image_width': 1080, 'image_height': 1350,
                       'link': {'web_url': link, 'mobile_web_url': link}},
           'buttons': [{'title': '건너뛰기·다시 만들기', 'link': {'web_url': link, 'mobile_web_url': link}}]}
else:
    link = S.get('blog_url') or 'https://sudogwon-rt.blogspot.com/'
    tpl = {'object_type': 'feed',
           'content': {'title': f"📅 {head}", 'description': desc,
                       'image_url': f'{SITE}policy_month/card.png?v={VER}', 'image_width': 1080, 'image_height': 1350,
                       'link': {'web_url': link, 'mobile_web_url': link}},
           'buttons': [{'title': '자세히 보기', 'link': {'web_url': link, 'mobile_web_url': link}}]}

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
H = {'Authorization': 'Bearer ' + tok['access_token']}
try:
    res = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
          data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(), headers=H)))
    print('정책 9가지 카톡' + (' 미리보기' if PREVIEW else '') + ':', res)
except urllib.error.HTTPError as err:
    print('::warning::정책 9가지 카톡 실패:', err.read().decode('utf-8', 'replace')[:300])
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
