"""스레드(Threads) 자동 게시 (GitHub Actions insta.yml, 인스타 게시 바로 뒤).
- 인스타와 같은 insta/posts.json(오늘 게시물·JPEG)을 씁니다. 실거래 매일, 주요 지역 신고가 1위(있는 날, 별도 게시물), 청약 월~금, 기업재무 토.
- 스레드는 글 500자 제한이라 캡션을 짧게 줄이고, 그날 블로그 글 링크(스레드는 링크가 눌림)와 주제 태그 1개를 붙입니다.
- 같은 날 다시 실행해도 최근 게시물 첫 줄이 같으면 건너뜁니다(중복 방지).
- 토큰 자동 갱신: 실행마다 장기 토큰(60일)을 새로 받아 THREADS_TOKEN Secret 에 저장 (GH_TOKEN 필요)
필요한 Secret: THREADS_TOKEN / 선택: THREADS_APP_SECRET(처음 넣은 토큰이 1시간짜리일 때 장기 토큰으로 바꿈), GH_PAT(GH_TOKEN 으로 전달)
옵션: --dry (게시하지 않고 글만 출력)
"""
import os, sys, json, time, datetime, subprocess, urllib.request, urllib.parse, urllib.error

SITE = (os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/').rstrip('/') + '/'
BLOG = 'https://sudogwon-rt.blogspot.com/'
TOKEN = os.environ.get('THREADS_TOKEN', '').strip()
SECRET = os.environ.get('THREADS_APP_SECRET', '').strip()
DRY = '--dry' in sys.argv
G = 'https://graph.threads.net/v1.0'
VER = os.environ.get('GITHUB_RUN_ID') or str(int(time.time()))
NOW = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
TODAY, WD = NOW.date().isoformat(), NOW.weekday()

if not DRY and not TOKEN:
    print('THREADS_TOKEN 이 없어 스레드 게시를 건너뜁니다 (설정 전).'); sys.exit(0)


def api(path, params=None, post=False, base=G):
    params = dict(params or {}); params.setdefault('access_token', TOKEN)
    data = urllib.parse.urlencode(params).encode()
    url = f'{base}/{path}' if post else f'{base}/{path}?{data.decode()}'
    req = urllib.request.Request(url, data=data if post else None, method='POST' if post else 'GET')
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{path}: {e.code} {e.read().decode("utf-8", "replace")[:400]}')


def save_token(new):
    global TOKEN
    if not new or new == TOKEN: return
    TOKEN = new
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'THREADS_TOKEN', '--body', new], check=True)
        print('새 스레드 토큰을 THREADS_TOKEN Secret 에 저장했습니다.')
    else:
        print('::warning::스레드 토큰을 새로 받았지만 GH_PAT 가 없어 저장하지 못했습니다.')


def wait_ready(cid):
    for _ in range(30):
        st = api(cid, {'fields': 'status,error_message'})
        if st.get('status') == 'FINISHED': return
        if st.get('status') in ('ERROR', 'EXPIRED'): raise RuntimeError(f'미디어 처리 실패: {cid} {st}')
        time.sleep(5)
    raise RuntimeError(f'미디어 처리 시간 초과: {cid}')


# ── 1. 토큰: 장기 토큰 갱신 (처음 1시간짜리 토큰이면 앱 시크릿으로 장기 토큰 교환)
if not DRY:
    try:
        save_token(api('refresh_access_token', {'grant_type': 'th_refresh_token'}, base='https://graph.threads.net').get('access_token'))
    except Exception as e:
        if SECRET:
            try:
                save_token(api('access_token', {'grant_type': 'th_exchange_token', 'client_secret': SECRET}, base='https://graph.threads.net').get('access_token'))
            except Exception as e2:
                print('토큰 교환 건너뜀:', str(e2)[:200])
        else:
            print('토큰 갱신 건너뜀:', str(e)[:200])

# ── 2. 오늘 게시물 + 블로그 글 링크
try:
    P = json.load(urllib.request.urlopen(f'{SITE}insta/posts.json?t={VER}', timeout=30))
except Exception as e:
    sys.exit(f'posts.json 을 받지 못했습니다: {e}')
if P.get('day') != TODAY:
    print(f"::warning::posts.json 날짜({P.get('day')})가 오늘({TODAY})이 아니라 게시하지 않습니다"); sys.exit(0)


def blog_link(key):
    path, field = {'rt': ('summary.json', 'blog_url'), 'hero': ('summary.json', 'blog_url'), 'fin': ('fin/summary.json', 'blog_url'),
                   'cy': ('cheongyak/summary.json', {0: 'blog_url', 1: 'blog_url_tue', 2: 'blog_url_wed', 3: 'blog_url_thu', 4: 'blog_url_fri'}.get(WD, 'blog_url'))}.get(key, (None, None))
    try:
        return json.load(urllib.request.urlopen(f'{SITE}{path}?t={VER}', timeout=30)).get(field) or BLOG
    except Exception:
        return BLOG


TAG = {'rt': '#아파트실거래가', 'hero': '#신고가', 'cy': '#청약', 'fin': '#기업분석'}


def compose(p, link):
    lines = [x for x in p['caption'].split('\n')]
    head = lines[0].strip()
    rows = [x.strip() for x in lines[1:] if x.strip().startswith(('·', '1.', '2.', '3.', '4.', '5.'))]
    tail = ['', f'👉 전체 보기: {link}', '', f"{TAG.get(p['key'], '#재테크')}"]
    for n in (5, 4, 3, 2, 1, 0):                          # 500자 안으로
        text = '\n'.join([head, ''] + rows[:n] + (['…'] if len(rows) > n else []) + tail)
        if len(text) <= 490: return text
    return '\n'.join([head[:300]] + tail)


def hero_photo_url():                     # PC 가 만든 1위 사진 카드(jpg)가 저장소에 있으면 그 주소 (2026-11-11)
    try:
        d = json.load(urllib.request.urlopen(f'{SITE}cards/hero.json?t={VER}', timeout=30))['day']
        repo = os.environ.get('GITHUB_REPOSITORY') or 'gogokimbiz-spec/sudogwon-rt'
        u = f'https://raw.githubusercontent.com/{repo}/main/cards/rt/{d}_hero.jpg'
        if urllib.request.urlopen(urllib.request.Request(u, method='HEAD'), timeout=30).status == 200:
            return u
    except Exception:
        pass
    return None


# ── 3. 중복 확인용 최근 글 첫 줄
recent = set()
if not DRY:
    try:
        for m in api('me/threads', {'fields': 'text', 'limit': 15}).get('data', []):
            recent.add((m.get('text') or '').split('\n')[0].strip())
    except Exception as e:
        print('최근 게시물 확인 실패 (계속 진행):', str(e)[:200])

# ── 4. 게시
failed = 0
for p in P.get('posts') or []:
    link = blog_link(p['key'])
    text = compose(p, link)
    urls = [SITE + u + f'?v={VER}' for u in p['images']][:20]
    if p['key'] == 'hero' and hero_photo_url():
        urls = [hero_photo_url() + f'?v={VER}']; print('1위 카드: PC 가 만든 사진 카드 사용')
    first = text.split('\n')[0].strip()
    print(f"\n[{p['title']}] 이미지 {len(urls)}장 · {len(text)}자\n{text}")
    if DRY: continue
    if first in recent:
        print('이미 올라간 게시물이라 건너뜁니다.'); continue
    try:
        if len(urls) == 1:
            cid = api('me/threads', {'media_type': 'IMAGE', 'image_url': urls[0], 'text': text}, post=True)['id']
        else:
            kids = []
            for u in urls:
                k = api('me/threads', {'media_type': 'IMAGE', 'image_url': u, 'is_carousel_item': 'true'}, post=True)['id']
                kids.append(k)
            for k in kids: wait_ready(k)
            cid = api('me/threads', {'media_type': 'CAROUSEL', 'children': ','.join(kids), 'text': text}, post=True)['id']
        wait_ready(cid)
        print('게시 완료:', api('me/threads_publish', {'creation_id': cid}, post=True)['id'])
        time.sleep(10)
    except Exception as e:
        failed += 1
        print(f"::warning::스레드 게시 실패 [{p['title']}]:", str(e)[:400])
if failed:
    sys.exit(f'스레드 게시 {failed}건 실패')
