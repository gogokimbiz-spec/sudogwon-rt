"""한 번만 올리는 특별 카드 게시 (special.yml) – 2026-11-27
special/<slug>/meta.json 하나 = 게시물 하나. post_at(KST) 이 지났고 special/<slug>/done.txt 가 없으면 올림.
사용법 (special.yml 이 차례로 부름):
  python post_special.py pick [slug]      → 올릴 slug 하나 (GITHUB_OUTPUT slug=…), 없으면 빈 값
  python post_special.py make  <slug>     → meta.make 명령으로 카드 생성 → cards/special/<slug>.png
  python post_special.py blog  <slug>     → 블로그 글 (같은 이미지가 든 글이 있으면 수정) → special/<slug>/state.json blog_url
  python post_special.py insta <slug>     → special_now/insta/posts.json + jpg, special_now/toheo/summary.json(blog_url – 스레드 링크용)
  python post_special.py kakao <slug>     → 카톡 나에게 보내기 (SITE_URL = special_now 공개 주소), special/<slug>/kakao.txt
meta.json: slug, post_at('YYYY-MM-DDTHH:MM' KST), make([명령…], 결과 png 경로 out), title, labels[], blog_html('{IMG}' 자리에 카드),
           kakao_title, kakao_desc, kakao_button, caption(인스타·스레드, 마지막 줄 해시태그)
"""
import os, sys, json, glob, html, shutil, datetime, subprocess, urllib.request, urllib.parse, urllib.error

KST = datetime.timezone(datetime.timedelta(hours=9))
NOW = datetime.datetime.now(KST)
REPO = os.environ.get('GITHUB_REPOSITORY', 'gogokimbiz-spec/sudogwon-rt')
cmd = sys.argv[1]
slug = sys.argv[2] if len(sys.argv) > 2 else ''
D = os.path.join('special', slug)


def meta(s): return json.load(open(os.path.join('special', s, 'meta.json'), encoding='utf-8'))
def state():
    try: return json.load(open(os.path.join(D, 'state.json'), encoding='utf-8'))
    except Exception: return {}
def save_state(st): json.dump(st, open(os.path.join(D, 'state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
def out(k, v):
    if os.environ.get('GITHUB_OUTPUT'): open(os.environ['GITHUB_OUTPUT'], 'a').write(f'{k}={v}\n')
    print(f'{k}={v}')


if cmd == 'pick':
    due = []
    for p in sorted(glob.glob('special/*/meta.json')):
        m = json.load(open(p, encoding='utf-8')); s = m['slug']
        if slug and s != slug: continue
        if os.path.exists(os.path.join('special', s, 'done.txt')): continue
        at = datetime.datetime.fromisoformat(m['post_at']).replace(tzinfo=KST)
        if slug or at <= NOW: due.append((at, s))
    out('slug', sorted(due)[0][1] if due else ''); sys.exit(0)

M = meta(slug)

if cmd == 'make':
    subprocess.run(M['make'], check=True)
    os.makedirs('cards/special', exist_ok=True)
    shutil.copy(M['out'], f'cards/special/{slug}.png'); print('카드 →', f'cards/special/{slug}.png')

elif cmd == 'blog':
    env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
    if not all(env.values()): print('블로거 설정값이 없어 건너뜁니다.'); sys.exit(0)
    img = f'https://raw.githubusercontent.com/{REPO}/main/cards/special/{slug}.png'
    content = M['blog_html'].replace('{IMG}', img)
    ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
    if ad_client and ad_slot and '{AD}' in content:
        content = content.replace('{AD}', f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                                  f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                                  '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
    content = content.replace('{AD}', '')
    tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
        'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
        'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
    H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
    API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"
    items = json.load(urllib.request.urlopen(urllib.request.Request(
        API + '/search?' + urllib.parse.urlencode({'q': M['labels'][0], 'fetchBodies': 'true'}), headers=H))).get('items', [])
    same = [p for p in items if f'cards/special/{slug}.png' in (p.get('content') or '')]
    body = json.dumps({'title': M['title'], 'content': content, 'labels': M['labels']}).encode()
    if same: r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
    else: r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
    url = json.load(r).get('url'); print('블로그 게시:', url)
    st = state(); st['blog_url'] = url; save_state(st)

elif cmd == 'insta':
    from PIL import Image
    link = state().get('blog_url') or 'https://sudogwon-rt.blogspot.com/'
    shutil.rmtree('special_now', ignore_errors=True)
    os.makedirs('special_now/insta/img'); os.makedirs('special_now/toheo')
    Image.open(f'cards/special/{slug}.png').convert('RGB').save(f'special_now/insta/img/{slug}.jpg', 'JPEG', quality=92)
    shutil.copy(f'cards/special/{slug}.png', 'special_now/card.png')
    json.dump({'day': NOW.date().isoformat(), 'posts': [{'key': 'toheo', 'title': M['kakao_title'], 'images': [f'insta/img/{slug}.jpg'],
               'caption': M['caption']}]}, open('special_now/insta/posts.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump({'blog_url': link}, open('special_now/toheo/summary.json', 'w', encoding='utf-8'))   # post_threads.py blog_link('toheo') 가 읽음
    print('posts.json 1건, 링크', link)

elif cmd == 'kakao':
    MARK = os.path.join(D, 'kakao.txt')
    if os.path.exists(MARK): print('이미 보낸 카톡'); sys.exit(0)
    K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
    if not all(K.values()): print('카카오 설정값이 없어 건너뜁니다.'); sys.exit(0)
    SITE = os.environ.get('SITE_URL', '').rstrip('/') + '/'
    link = state().get('blog_url') or 'https://sudogwon-rt.blogspot.com/'
    tpl = {'object_type': 'feed',
           'content': {'title': M['kakao_title'], 'description': M['kakao_desc'],
                       'image_url': f"{SITE}card.png?v={os.environ.get('GITHUB_RUN_ID', '')}", 'image_width': 1080, 'image_height': 1350,
                       'link': {'web_url': link, 'mobile_web_url': link}},
           'buttons': [{'title': M.get('kakao_button') or '자세히 보기', 'link': {'web_url': link, 'mobile_web_url': link}}]}
    tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
        'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
        'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
    try:
        res = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
              data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(),
              headers={'Authorization': 'Bearer ' + tok['access_token']})))
        print('카톡:', res); open(MARK, 'w').write('sent\n')
    except urllib.error.HTTPError as err:
        print('::warning::카톡 실패:', err.read().decode('utf-8', 'replace')[:300])
    new_rt = tok.get('refresh_token')
    if new_rt and os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
