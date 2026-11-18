"""국평(84㎡대)·소형(59㎡대) 최고 실거래가 TOP 16 블로그 글 (매월 3일, GitHub Actions 용).
사용법: python post_blogger_top.py site/top84/summary.json
- 카드 4장(서울·경기 × 국평·소형)은 daily.yml 이 저장소 cards/top/<YYYY-MM>_<카드>.png 로 보관 → 그 주소를 글에 넣음
- 같은 달 글이 이미 있으면 새로 만들지 않고 고칩니다. 올린 글 주소를 summary.json 의 blog_url 에 적어 둠(카톡·스레드 링크용)
필요한 환경변수: BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN (없으면 건너뜀)
"""
import os, re, sys, json, urllib.request, urllib.parse, html

env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
DRY = '--dry' in sys.argv
if not DRY and not all(env.values()):
    print('블로거 설정값이 없어 게시를 건너뜁니다.'); sys.exit(0)
SITE = os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
S = json.load(open(sys.argv[1], encoding='utf-8'))
YM, SHORT = S['month'], S['short']
esc = html.escape
CARDS = [('seoul_84', '서울', '국평', '전용 84㎡대'), ('gg_84', '경기', '국평', '전용 84㎡대'),
         ('seoul_59', '서울', '소형', '전용 59㎡대'), ('gg_59', '경기', '소형', '전용 59㎡대')]
CARDS = [c for c in CARDS if S.get(c[0])]
if not CARDS:
    print('카드 자료가 없어 글을 건너뜁니다'); sys.exit(0)
REPO = os.environ.get('GITHUB_REPOSITORY', 'gogokimbiz-spec/sudogwon-rt'); BR = os.environ.get('GITHUB_REF_NAME') or 'main'
img = lambda k: f'https://raw.githubusercontent.com/{REPO}/{BR}/cards/top/{YM}_{k}.png'
clean = lambda a: re.sub(r'\([^()]*\d+동\)', '', a).strip() or a
eok = lambda v: f'{v / 10000:.2f}억'
def short(r):
    p = r.split(' ')
    g = p[-1]
    return g[:-1] if len(g) > 2 and g[-1] in '시군구' else g

T = 'style="border-collapse:collapse;width:100%;font-size:14px"'
TH = 'style="text-align:left;border-bottom:2px solid #ccc;padding:6px 4px"'
THR = 'style="text-align:right;border-bottom:2px solid #ccc;padding:6px 4px"'
TD = 'style="border-bottom:1px solid #eee;padding:6px 4px"'
TDR = 'style="border-bottom:1px solid #eee;padding:6px 4px;text-align:right;white-space:nowrap"'

first = {k: S[k][0] for k, *_ in CARDS}
s84, g84 = first.get('seoul_84'), first.get('gg_84')
title = (f"[수도권 실거래] {SHORT} 국평·소형 최고 실거래가 TOP 16 | "
         + ' · '.join(x for x in [f"서울 {clean(s84['apt'])} {eok(s84['price_man'])}" if s84 else '', f"경기 {clean(g84['apt'])} {eok(g84['price_man'])}" if g84 else ''] if x))
key = f'{SHORT} 국평·소형 최고 실거래가'

parts = []
intro = [f"{S['label']} 계약된 서울·경기(인천 제외) 아파트 가운데, 국민평형(전용 84㎡대)과 소형(전용 59㎡대)에서 가장 비싸게 거래된 단지 16곳씩을 정리했습니다."]
if s84: intro.append(f"서울 국평 1위는 {esc(short(s84['region']))} {esc(clean(s84['apt']))}({eok(s84['price_man'])}),")
if g84: intro.append(f"경기 국평 1위는 {esc(short(g84['region']))} {esc(clean(g84['apt']))}({eok(g84['price_man'])})입니다.")
parts.append('<p style="font-size:16px;line-height:1.7">' + ' '.join(intro) + '</p>')
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
for i, (k, area, kind, chip) in enumerate(CARDS):
    rows = S[k]
    parts.append(f"<h3>{esc(area)} {kind}({chip}) 최고 실거래가 TOP {len(rows)}</h3>")
    parts.append(f'<div style="margin:0 0 14px;text-align:center"><img src="{img(k)}" alt="{SHORT} {esc(area)} {kind} 최고 실거래가 TOP {len(rows)}" '
                 + ('loading="lazy" ' if i else '') + f'style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>')
    body = ''.join(f"<tr><td {TD}>{j}</td><td {TD}>{esc(r['region'])}<br><small>{esc(r['umd'])}</small></td><td {TD}>{esc(clean(r['apt']))}</td>"
                   f"<td {TDR}>{r['area']:g}㎡</td><td {TDR}><b>{eok(r['price_man'])}</b></td></tr>" for j, r in enumerate(rows, 1))
    parts.append(f"<table {T}><tr><th {TH}>순위</th><th {TH}>지역</th><th {TH}>단지</th><th {THR}>전용</th><th {THR}>최고가</th></tr>{body}</table>")
    if i == 1 and ad_client and ad_slot:                     # 광고 자리 (애드센스 승인 후)
        parts.append(f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                     f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                     '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
parts.append(f'<p style="margin:20px 0"><a href="{SITE}r/" style="display:inline-block;padding:12px 18px;border-radius:12px;background:#1f5fbf;color:#fff;font-weight:bold;text-decoration:none">'
             '🏠 우리 동네 아파트 실거래가 보기 ›</a></p>')
parts.append('<hr><p><small>기준: 해당 달 계약된 아파트 매매 실거래 중 국평은 전용 83.5~86㎡ 미만, 소형은 57~61㎡ 미만. 같은 단지(시군구·단지명)는 그달 가장 비싼 1건만 넣고 가격순으로 16곳을 골랐습니다. '
             '해제 신고된 거래는 뺐습니다. 실거래는 계약 후 30일 안에 신고하므로, 늦게 신고된 거래는 반영되지 않았을 수 있습니다.<br>'
             '자료: 국토교통부 실거래가 공개시스템(공공데이터포털 API). 이 글은 참고용 정보이며 투자 권유가 아닙니다.</small></p>')
content = ''.join(parts)
labels = ['실거래', '국평', '소형 아파트', '최고 실거래가', '수도권 실거래가', '서울 아파트', '경기 아파트']

if DRY:
    open('post_preview_top.html', 'w', encoding='utf-8').write(f'<meta charset="utf-8"><h1>{esc(title)}</h1>' + content)
    print(title); print('라벨:', labels); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': key, 'fetchBodies': 'false'}), headers=H)
items = json.load(urllib.request.urlopen(q)).get('items', [])
same = [p for p in items if key in p.get('title', '') and '[수도권 실거래]' in p.get('title', '')]
body = json.dumps({'title': title, 'content': content, 'labels': labels}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S['blog_url'] = post.get('url')
json.dump(S, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
