"""주간 부동산 판례 블로그 글 (매주 목요일, daily.yml) – 2026-11-19
사용법: python post_blogger_law.py site/law/summary.json   [--dry]
- law.yml(수 저녁)이 만든 cards/law/<게시일>.json·png 를 daily.yml 이 site/law/ 로 복사 → 이 글을 올림
- 같은 사건 글이 이미 있으면 고칩니다. 올린 글 주소를 summary.json 의 blog_url 에 적어 둠(카톡·스레드 링크용)
필요한 환경변수: BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN (없으면 건너뜀)
"""
import os, sys, json, urllib.request, urllib.parse, html

env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
DRY = '--dry' in sys.argv
if not DRY and not all(env.values()):
    print('블로거 설정값이 없어 게시를 건너뜁니다.'); sys.exit(0)
SITE = os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
P = [a for a in sys.argv[1:] if not a.startswith('--')][0]
S = json.load(open(P, encoding='utf-8'))
esc = html.escape
REPO = os.environ.get('GITHUB_REPOSITORY', 'gogokimbiz-spec/sudogwon-rt'); BR = os.environ.get('GITHUB_REF_NAME') or 'main'
img = f"https://raw.githubusercontent.com/{REPO}/{BR}/cards/law/{S['day']}.png"
B = S.get('blog') or {}
m, d = int(S['day'][5:7]), int(S['day'][8:10])
key = S['case_no']
title = f"[부동산 판례] {m}월 {d}일 | {B.get('title') or S['title'].replace(chr(10), ' ')}"

parts = [f'<div style="margin:0 0 16px;text-align:center"><img src="{img}" alt="{esc(S["title"].replace(chr(10), " "))} – {esc(key)} 기승전결 요약" '
         f'style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>']
if B.get('intro'): parts.append(f'<p style="font-size:16px;line-height:1.7">{esc(B["intro"])}</p>')
parts.append('<div style="background:#f6f7f9;border-radius:12px;padding:14px 16px;margin:16px 0;font-size:15px;line-height:1.7">'
             + ''.join(f'<p style="margin:4px 0"><b style="color:#c99700">{esc(k)}</b> &nbsp;{esc(v)}</p>' for k, v in S['story']) + '</div>')
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
for i, sec in enumerate(B.get('sections') or []):
    h, body = (sec[0], sec[1]) if isinstance(sec, (list, tuple)) else (sec.get('h', ''), sec.get('p', ''))
    parts.append(f'<h3>{esc(h)}</h3><p style="font-size:16px;line-height:1.7">{esc(body)}</p>')
    if i == 1 and ad_client and ad_slot:                       # 광고 자리 (애드센스 승인 후)
        parts.append(f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                     f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                     '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
parts.append(f'<p style="border:2px solid #ffc400;border-radius:12px;padding:12px 16px;font-size:16px"><b>💡 TIP</b> {esc(S["tip"])}</p>')
parts.append(f'<p style="margin:20px 0"><a href="{SITE}" style="display:inline-block;padding:12px 18px;border-radius:12px;background:#1f5fbf;color:#fff;font-weight:bold;text-decoration:none">'
             '🏠 수도권 아파트 실거래가 지도 보기 ›</a></p>')
parts.append(f'<hr><p><small>사건: {esc(S["case"])}<br>자료: <a href="{esc(S.get("source_url", ""))}">대법원 판례속보 「{esc(S.get("post_title", ""))}」</a><br>'
             '판결 요지를 쉽게 풀어 쓴 글로, 법률 자문이 아닙니다. 실제 사안은 사실관계에 따라 결론이 달라질 수 있으니 전문가와 상담하세요.</small></p>')
content = ''.join(parts)
labels = list(dict.fromkeys(['부동산 판례', '대법원 판례'] + [k for k in (B.get('keywords') or []) if k][:4]))

if DRY:
    open('post_preview_law.html', 'w', encoding='utf-8').write(f'<meta charset="utf-8"><h1>{esc(title)}</h1>' + content)
    print(title); print('라벨:', labels); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': key, 'fetchBodies': 'true'}), headers=H)
items = json.load(urllib.request.urlopen(q)).get('items', [])
same = [p for p in items if '[부동산 판례]' in p.get('title', '') and key in (p.get('content') or '')]
body = json.dumps({'title': title, 'content': content, 'labels': labels}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S['blog_url'] = post.get('url')
json.dump(S, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
