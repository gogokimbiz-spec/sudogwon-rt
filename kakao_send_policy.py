"""이번 주 부동산 정책 카드 카톡 '나에게 보내기' (매주 금요일, policy.yml) – 2026-11-20
사용법: python kakao_send_policy.py policy_now/policy/summary.json
- SITE_URL(카드 공개 주소의 상위 폴더) 아래 policy/card.png 를 카드 이미지로, 블로그 글을 링크로 보냄
- summary.json 의 day 가 오늘일 때만 보냄
같은 작업에서 앞 단계가 토큰을 바꿨다면 .kakao_rt 파일의 새 값을 씁니다.
"""
import os, sys, json, datetime, subprocess, urllib.request, urllib.parse, urllib.error

path = [a for a in sys.argv[1:] if not a.startswith('--')][0]
try:
    S = json.load(open(path, encoding='utf-8'))
except Exception:
    print('정책 카드 자료가 없습니다'); sys.exit(0)
TODAY = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date().isoformat()
if S.get('day') != TODAY:
    print('오늘은 정책 카톡이 없습니다'); sys.exit(0)
K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if os.path.exists('.kakao_rt'):
    K['KAKAO_REFRESH_TOKEN'] = open('.kakao_rt').read().strip() or K['KAKAO_REFRESH_TOKEN']
if not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)

SITE = (os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/').rstrip('/') + '/'
VER = f"{os.environ.get('GITHUB_RUN_ID', '')}{os.environ.get('GITHUB_RUN_ATTEMPT', '')}" or str(int(__import__('time').time()))
rows = S['rows']
link = S.get('blog_url') or 'https://sudogwon-rt.blogspot.com/'
desc = '\n'.join(f"{i}. {r['short']}" for i, r in enumerate(rows, 1))
tpl = {'object_type': 'feed',
       'content': {'title': f"📢 {S['label']} 꼭 알아둘 부동산 정책",
                   'description': desc[:200],
                   'image_url': f'{SITE}policy/card.png?v={VER}', 'image_width': 1080, 'image_height': 1350,
                   'link': {'web_url': link, 'mobile_web_url': link}},
       'buttons': [{'title': '정책 자세히 보기', 'link': {'web_url': link, 'mobile_web_url': link}}]}

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
H = {'Authorization': 'Bearer ' + tok['access_token']}
try:
    res = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
          data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(), headers=H)))
    print('정책 카톡:', res)
except urllib.error.HTTPError as err:
    print('::warning::정책 카톡 실패:', err.read().decode('utf-8', 'replace')[:300])
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
