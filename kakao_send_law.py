"""주간 부동산 판례 카드 카톡 '나에게 보내기' – 2026-11-19
- 미리보기(수요일 저녁, law.yml):  python kakao_send_law.py --preview cards/law/<게시일>.json
    "내일 아침 올라갈 판례" + 카드 + [건너뛰기·다시 고르기] 버튼(Actions 실행 화면)
- 게시(목요일, daily.yml notify): python kakao_send_law.py law_summary.json   (배포된 law/summary.json, made 가 오늘일 때만)
같은 작업에서 앞 단계가 토큰을 바꿨다면 .kakao_rt 파일의 새 값을 씁니다.
"""
import os, sys, json, datetime, subprocess, urllib.request, urllib.parse, urllib.error

PREVIEW = '--preview' in sys.argv
path = [a for a in sys.argv[1:] if not a.startswith('--')][0]
try:
    S = json.load(open(path, encoding='utf-8'))
except Exception:
    print('판례 카드 자료가 없습니다 (목요일만)'); sys.exit(0)
TODAY = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date().isoformat()
if not PREVIEW and S.get('made') != TODAY:
    print('오늘은 판례 카톡이 없습니다'); sys.exit(0)
K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if os.path.exists('.kakao_rt'):
    K['KAKAO_REFRESH_TOKEN'] = open('.kakao_rt').read().strip() or K['KAKAO_REFRESH_TOKEN']
if not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)

SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
REPO = os.environ.get('GITHUB_REPOSITORY', 'gogokimbiz-spec/sudogwon-rt')
VER = f"{os.environ.get('GITHUB_RUN_ID', '')}{os.environ.get('GITHUB_RUN_ATTEMPT', '')}" or str(int(__import__('time').time()))
title1 = S['title'].replace('\n', ' ')
if PREVIEW:
    img = f"https://raw.githubusercontent.com/{REPO}/main/cards/law/{S['day']}.png"
    link = f'https://github.com/{REPO}/actions/workflows/law.yml'
    tpl = {'object_type': 'feed',
           'content': {'title': f"👀 [미리보기] {S['day'][5:].replace('-', '/')}(목) 아침 올라갈 판례",
                       'description': f"{title1}\n{S['case_no']} · 그대로 두면 목요일 아침 자동 게시 · 바꾸려면 Claude 에게 말씀",
                       'image_url': f'{img}?v={VER}', 'image_width': 1080, 'image_height': 1350,
                       'link': {'web_url': link, 'mobile_web_url': link}},
           'buttons': [{'title': '이번 주 건너뛰기', 'link': {'web_url': link, 'mobile_web_url': link}}]}
else:
    link = S.get('blog_url') or 'https://sudogwon-rt.blogspot.com/'
    tpl = {'object_type': 'feed',
           'content': {'title': f"⚖️ 이번 주 부동산 판례 | {title1}",
                       'description': S.get('one_line') or S['story'][-1][1],
                       'image_url': f'{SITE}law/card.png?v={VER}', 'image_width': 1080, 'image_height': 1350,
                       'link': {'web_url': link, 'mobile_web_url': link}},
           'buttons': [{'title': '판례 자세히 보기', 'link': {'web_url': link, 'mobile_web_url': link}}]}

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
H = {'Authorization': 'Bearer ' + tok['access_token']}
try:
    res = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
          data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(), headers=H)))
    print('판례 카톡' + (' 미리보기' if PREVIEW else '') + ':', res)
except urllib.error.HTTPError as err:
    print('::warning::판례 카톡 실패:', err.read().decode('utf-8', 'replace')[:300])
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
