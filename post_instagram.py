"""인스타그램 자동 게시 (GitHub Actions insta.yml, 매일 07:55 KST – 새벽 daily 가 만든 posts.json 사용).
- build_insta.py 가 만든 insta/posts.json(오늘 올릴 게시물, JPEG 주소, 캡션)을 사이트에서 받아 올립니다.
  실거래: 매일 캐러셀 / 청약: 월·수·금 / 기업재무: 화·금
- 같은 게시물이 이미 올라가 있으면(최근 게시물 캡션 첫 줄이 같으면) 건너뜁니다 → 수동 재실행해도 중복 없음
- 토큰 자동 갱신: 실행할 때마다 장기 토큰(60일)을 새로 받아 IG_TOKEN Secret 에 저장 (GH_TOKEN 필요)
필요한 Secret: IG_USER_ID, IG_TOKEN / 선택: GH_PAT(GH_TOKEN 으로 전달)
옵션: --dry (게시하지 않고 내용만 출력)
"""
import os, sys, json, time, datetime, subprocess, urllib.request, urllib.parse, urllib.error

SITE = (os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/').rstrip('/') + '/'
UID, TOKEN = os.environ.get('IG_USER_ID', '').strip(), os.environ.get('IG_TOKEN', '').strip()
DRY = '--dry' in sys.argv
G = 'https://graph.instagram.com'
VER = os.environ.get('GITHUB_RUN_ID') or str(int(time.time()))
TODAY = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).date().isoformat()

if not DRY and not (UID and TOKEN):
    print('IG_USER_ID / IG_TOKEN 이 없어 인스타 게시를 건너뜁니다.'); sys.exit(0)


def api(path, params=None, post=False):
    params = dict(params or {}); params['access_token'] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f'{G}/{path}' if post else f'{G}/{path}?{data.decode()}'
    req = urllib.request.Request(url, data=data if post else None, method='POST' if post else 'GET')
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{path}: {e.code} {e.read().decode("utf-8", "replace")[:400]}')


def wait_ready(cid):
    for _ in range(30):                      # 최대 약 2분 30초
        st = api(cid, {'fields': 'status_code'}).get('status_code')
        if st == 'FINISHED': return
        if st in ('ERROR', 'EXPIRED'): raise RuntimeError(f'미디어 처리 실패: {cid} {st}')
        time.sleep(5)
    raise RuntimeError(f'미디어 처리 시간 초과: {cid}')


# ── 1. 토큰 갱신 (발급 24시간 안이면 갱신 안 됨 → 그대로 사용)
if not DRY:
    try:
        new = api('refresh_access_token', {'grant_type': 'ig_refresh_token'}).get('access_token')
        if new and new != TOKEN:
            TOKEN = new
            if os.environ.get('GH_TOKEN'):
                subprocess.run(['gh', 'secret', 'set', 'IG_TOKEN', '--body', new], check=True)
                print('새 인스타 토큰을 IG_TOKEN Secret 에 저장했습니다.')
            else:
                print('::warning::인스타 토큰을 갱신했지만 GH_PAT 가 없어 저장하지 못했습니다.')
    except Exception as e:
        print('토큰 갱신 건너뜀:', str(e)[:200])

# ── 2. 오늘 게시물 목록
try:
    P = json.load(urllib.request.urlopen(f'{SITE}insta/posts.json?t={VER}', timeout=30))
except Exception as e:
    sys.exit(f'posts.json 을 받지 못했습니다: {e}')
if P.get('day') != TODAY:
    print(f"::warning::posts.json 날짜({P.get('day')})가 오늘({TODAY})이 아니라 게시하지 않습니다 (배포 실패 등)"); sys.exit(0)
posts = P.get('posts') or []
if not posts:
    print('오늘 올릴 인스타 게시물이 없습니다.'); sys.exit(0)

# ── 3. 중복 확인용 최근 캡션 첫 줄
recent = set()
if not DRY:
    try:
        for m in api(f'{UID}/media', {'fields': 'caption', 'limit': 15}).get('data', []):
            recent.add((m.get('caption') or '').split('\n')[0].strip())
    except Exception as e:
        print('최근 게시물 확인 실패 (계속 진행):', str(e)[:200])

# ── 4. 게시
failed = 0
for p in posts:
    first = p['caption'].split('\n')[0].strip()
    urls = [SITE + u + f'?v={VER}' for u in p['images']][:10]
    print(f"\n[{p['title']}] 이미지 {len(urls)}장 · {first}")
    if DRY:
        print('\n'.join(urls)); print(p['caption']); continue
    if first in recent:
        print('이미 올라간 게시물이라 건너뜁니다.'); continue
    try:
        if len(urls) == 1:
            cid = api(f'{UID}/media', {'image_url': urls[0], 'caption': p['caption']}, post=True)['id']
        else:
            kids = []
            for u in urls:
                k = api(f'{UID}/media', {'image_url': u, 'is_carousel_item': 'true'}, post=True)['id']
                wait_ready(k); kids.append(k)
            cid = api(f'{UID}/media', {'media_type': 'CAROUSEL', 'children': ','.join(kids), 'caption': p['caption']}, post=True)['id']
        wait_ready(cid)
        mid = api(f'{UID}/media_publish', {'creation_id': cid}, post=True)['id']
        print('게시 완료:', mid)
        time.sleep(10)
    except Exception as e:
        failed += 1
        print(f"::warning::인스타 게시 실패 [{p['title']}]:", str(e)[:400])
if failed:
    sys.exit(f'인스타 게시 {failed}건 실패')
