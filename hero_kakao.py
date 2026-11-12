"""오늘의 신고가 1위 카드를 카카오톡 '나에게 보내기'로 하루 한 번 보냅니다 (GitHub 서버용).
- hero_photo.yml: PC 가 사진 카드를 만든 직후(보통 6시 전후) 실행 → 사진 카드 (사진을 못 받았으면 일반 배경 카드)
- insta.yml(07:55): PC 가 꺼져 있어 아직 안 보냈으면 일반 배경 카드로 대신 보냄
- 보낸 날은 cards/rt/<날짜>_hero_sent.txt(보낸 종류)를 남겨 두 번 보내지 않음. 단 그림 카드를 먼저 보냈는데 나중에 사진 카드가 생기면 사진으로 한 번 더 보냄
필요한 Secret: KAKAO_REST_KEY, KAKAO_CLIENT_SECRET, KAKAO_REFRESH_TOKEN / 선택: GH_PAT(GH_TOKEN) / 자동: GITHUB_TOKEN
"""
import os, sys, json, time, base64, subprocess, urllib.request, urllib.parse, urllib.error

K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
REPO = os.environ['GITHUB_REPOSITORY']
BRANCH = os.environ.get('GITHUB_REF_NAME') or 'main'
RAW = f'https://raw.githubusercontent.com/{REPO}/{BRANCH}/'
GH = {'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'], 'Accept': 'application/vnd.github+json', 'User-Agent': 'hero-kakao'}
VER = str(int(time.time()))
get = lambda u: json.load(urllib.request.urlopen(f'{u}?t={VER}', timeout=30))


def exists(path):                                   # 저장소 파일 확인 (raw 캐시를 피하려고 API 사용)
    try:
        urllib.request.urlopen(urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}', headers=GH), timeout=30)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404: return False
        raise


def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}' if m else f'{e}억') if e else f'{m:,}만'


S = get(SITE + 'summary.json')
D = S['day']
try:
    hj = get(SITE + 'cards/hero.json')
except Exception:
    hj = None
if not hj or hj.get('day') != D:
    print('오늘은 신고가 1위 카드가 없습니다'); sys.exit(0)
mark = f'cards/rt/{D}_hero_sent.txt'
photo_sha = None                                    # PC 가 만든 사진 카드(json)의 버전 – 카드를 다시 만들면 바뀜
try:
    photo_sha = json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/cards/rt/{D}_hero.jpg?ref={BRANCH}', headers=GH), timeout=30))['sha'][:12]
except urllib.error.HTTPError as e:
    if e.code != 404: raise
photo = bool(photo_sha) and exists(f'cards/rt/{D}_hero.json')
sent, mark_sha = None, None                         # 이미 보낸 종류('사진' / '일반 배경')
try:
    j = json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/{mark}?ref={BRANCH}', headers=GH), timeout=30))
    mark_sha, sent = j['sha'], base64.b64decode(j['content']).decode('utf-8', 'replace').strip()
except urllib.error.HTTPError as e:
    if e.code != 404: raise
if (sent and not photo) or sent == f'사진:{photo_sha}':   # 같은 사진 카드는 다시 안 보냄 (다시 만든 카드면 보냄)
    print(f'오늘 1위 카드는 이미 카톡으로 보냈습니다 ({sent})'); sys.exit(0)
if sent:
    print(f'이전에 보낸 카드({sent})와 달라 새 사진 카드를 한 번 더 보냅니다')

if photo:                                           # PC 가 만든 사진 카드
    img, kind = RAW + f'cards/rt/{D}_hero.jpg', f'사진:{photo_sha}'
else:                                               # 일반 배경 카드 (새벽에 만든 것)
    img, kind = SITE + 'cards/hero.png', '일반 배경'
link = S.get('blog_url') or SITE
print('보낼 카드:', kind, img)

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
feed = {'object_type': 'feed', 'content': {'title': f"오늘의 신고가 1위 | {hj['apt']} {man(hj['price_man'])}",
        'description': f"{hj['region']} · 전용 {hj['area']}㎡", 'image_url': f'{img}?v={VER}', 'image_width': 1080, 'image_height': 1350,
        'link': {'web_url': link, 'mobile_web_url': link}},
        'buttons': [{'title': '자세히 보기', 'link': {'web_url': link, 'mobile_web_url': link}}]}
res = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
      data=urllib.parse.urlencode({'template_object': json.dumps(feed, ensure_ascii=False)}).encode(),
      headers={'Authorization': 'Bearer ' + tok['access_token']})))
print('1위 카드 카톡 전송 결과:', res)

# 보냈다는 표시 남기기
body = {'message': f'{mark} (1위 카드 카톡 {kind})', 'branch': BRANCH, 'content': base64.b64encode(kind.encode()).decode()}
if mark_sha: body['sha'] = mark_sha
try:
    urllib.request.urlopen(urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/{mark}',
                           data=json.dumps(body).encode(), headers=GH, method='PUT'), timeout=30)
except urllib.error.HTTPError as e:
    print('::warning::보낸 표시 저장 실패:', e.read().decode('utf-8', 'replace')[:200])

new_rt = tok.get('refresh_token')
if new_rt:
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
    else:
        print('::warning::카카오가 새 refresh_token 을 발급했지만 GH_PAT 가 없어 저장하지 못했습니다.')
