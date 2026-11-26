"""토허제 40곳 주간 아파트값 카톡 '나에게 보내기' (매주 금요일, toheo.yml) – 2026-11-26
사용법: python kakao_send_toheo.py <폴더>/toheo/summary.json
- 이미지: SITE_URL + toheo/card.png (toheo.yml 이 저장소에 올린 공개 주소), 버튼: 블로그 글
- 같은 조사 기준일은 한 번만 보냄: cards/toheo/<기준일>_kakao.txt 가 있으면 건너뜀 (toheo.yml 이 커밋)
같은 작업에서 앞 단계가 토큰을 바꿨다면 .kakao_rt 파일의 새 값을 씁니다.
"""
import os, sys, json, subprocess, urllib.request, urllib.parse, urllib.error

S = json.load(open(sys.argv[1], encoding='utf-8'))
MARK = os.path.join('cards', 'toheo', f"{S['base_day']}_kakao.txt")
if os.path.exists(MARK) and os.environ.get('TOHEO_FORCE') != '1':
    print('이번 주 토허제 카톡은 이미 보냈습니다'); sys.exit(0)
K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if os.path.exists('.kakao_rt'):
    K['KAKAO_REFRESH_TOKEN'] = open('.kakao_rt').read().strip() or K['KAKAO_REFRESH_TOKEN']
if not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)

SITE = (os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/').rstrip('/') + '/'
VER = f"{os.environ.get('GITHUB_RUN_ID', '')}{os.environ.get('GITHUB_RUN_ATTEMPT', '')}" or str(int(__import__('time').time()))
pc = lambda v: '0.00%' if abs(v) < 0.005 else f'{v:+.2f}%'
rows = S['rows']; top, bot = rows[0], rows[-1]
sx = ' · '.join(f'{k} {pc(v)}' for k, v in (S.get('extra') or {}).items() if v is not None)
link = S.get('blog_url') or 'https://sudogwon-rt.blogspot.com/'
tpl = {'object_type': 'feed',
       'content': {'title': f"🗺️ 토허제 {len(rows)}곳 주간 아파트값 ({S['label']})",
                   'description': f"1위 {top['name']} {pc(top['chg'])} · 꼴찌 {bot['name']} {pc(bot['chg'])}" + (f"\n{sx}" if sx else ''),
                   'image_url': f'{SITE}toheo/card.png?v={VER}', 'image_width': 1080, 'image_height': 1350,
                   'link': {'web_url': link, 'mobile_web_url': link}},
       'buttons': [{'title': '40곳 전체 보기', 'link': {'web_url': link, 'mobile_web_url': link}}]}

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
H = {'Authorization': 'Bearer ' + tok['access_token']}
try:
    res = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
          data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(), headers=H)))
    print('토허제 카톡:', res)
    os.makedirs(os.path.dirname(MARK), exist_ok=True); open(MARK, 'w').write('sent\n')
except urllib.error.HTTPError as err:
    print('::warning::토허제 카톡 실패:', err.read().decode('utf-8', 'replace')[:300])
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
