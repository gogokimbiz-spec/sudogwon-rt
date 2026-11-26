"""이번 주 부동산 정책 블로그 글 (매주 금요일, policy.yml) – 2026-11-20
사용법: python post_blogger_policy.py policy_now/policy/summary.json   [--dry]
- make_cards_policy.py 가 만든 card.json(정책 2건 + 나머지 목록)으로 글을 씀. 카드 이미지는 cards/policy/<게시일>.png
- 같은 주 글이 이미 있으면 고칩니다. 올린 글 주소를 summary.json 의 blog_url 에 적어 둠(카톡·스레드 링크용)
필요한 환경변수: BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN (없으면 건너뜀)
"""
import os, sys, json, urllib.request, urllib.parse, html, datetime

env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
DRY = '--dry' in sys.argv
if not DRY and not all(env.values()):
    print('블로거 설정값이 없어 게시를 건너뜁니다.'); sys.exit(0)
P = [a for a in sys.argv[1:] if not a.startswith('--')][0]
S = json.load(open(P, encoding='utf-8'))
esc = html.escape
REPO = os.environ.get('GITHUB_REPOSITORY', 'gogokimbiz-spec/sudogwon-rt'); BR = os.environ.get('GITHUB_REF_NAME') or 'main'
img = f"https://raw.githubusercontent.com/{REPO}/{BR}/cards/policy/{S['day']}.png"
MAP = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
PAGE = MAP + 'policy/'
WD = '월화수목금토일'


def md(d):
    x = datetime.date.fromisoformat(d)
    return f'{x.month}.{x.day}({WD[x.weekday()]})'


rows = S['rows']
heads = ' · '.join(r['short'] for r in rows)
title = f"[부동산 정책] {S['label']} | {heads}"
if len(title) > 70:
    title = f"[부동산 정책] {S['label']} | {rows[0]['short']}" + (f" 외 {len(rows) - 1}건" if len(rows) > 1 else '')
key = f"cards/policy/{S['day']}.png"

parts = [f'<div style="margin:0 0 16px;text-align:center"><img src="{img}" alt="{esc(S["label"])} 꼭 알아둘 부동산 정책 – {esc(heads)}" '
         f'style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>',
         f'<p style="font-size:16px;line-height:1.7">{esc(S["label"])}({esc(S["range"])}) 국토교통부가 발표한 부동산·주택 정책 '
         f'{S["total"]}건 가운데 꼭 알아둘 {len(rows)}가지를 정리했어요.</p>']
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
for i, r in enumerate(rows, 1):
    lis = ''.join(f'<li style="margin:4px 0">{esc(s)}</li>' for s in r.get('summary') or [])
    links = f'<a href="{esc(r["url"])}">보도자료 원문</a>' + (f' · <a href="{esc(r["pdf"])}">PDF</a>' if r.get('pdf') else '')
    parts.append(f'<h3>{i}. {esc(r["short"])}</h3>'
                 f'<p style="margin:0 0 6px;color:#64748b;font-size:14px">[{esc(r["tag"])}] {md(r["date"])} 발표'
                 + (f' · {esc(r["dept"])}' if r.get('dept') else '') + '</p>'
                 + (f'<ul style="font-size:16px;line-height:1.7;padding-left:20px">{lis}</ul>' if lis else '')
                 + f'<p style="font-size:14px">{links}</p>')
    if i == 1 and ad_client and ad_slot:                       # 광고 자리 (애드센스 승인 후)
        parts.append(f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                     f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                     '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
others = [o for o in S.get('others') or [] if '동정' not in (o.get('tags') or [])]
if others:
    parts.append('<h3>이번 주 다른 발표</h3><ul style="font-size:15px;line-height:1.7;padding-left:20px">'
                 + ''.join(f'<li>{md(o["date"])} <a href="{esc(o["url"])}">{esc(o["title"])}</a></li>' for o in others) + '</ul>')
parts.append(f'<p style="margin:20px 0"><a href="{PAGE}" style="display:inline-block;padding:12px 18px;border-radius:12px;background:#172033;color:#fff;font-weight:bold;text-decoration:none;margin:0 8px 8px 0">'
             '📋 부동산 정책 모아보기 ›</a>'
             f'<a href="{MAP}" style="display:inline-block;padding:12px 18px;border-radius:12px;background:#1f5fbf;color:#fff;font-weight:bold;text-decoration:none">'
             '🏠 수도권 아파트 실거래가 지도 ›</a></p>')
parts.append('<hr><p><small>자료: 국토교통부 보도자료(공공누리 제1유형). 보도자료의 제목·요약을 옮긴 글로, '
             '자세한 내용과 시행 시기는 원문을 확인하세요.</small></p>')
# 해설 문단·알아두면 좋은 점 (2026-11-26 애드센스 '가치가 낮은 콘텐츠' 대응, blog_extra.py)
import sys as _sx, os as _ox; _sx.path.insert(0, _ox.path.dirname(_ox.path.abspath(__file__))); import blog_extra
parts = blog_extra.add(parts, 'policy')
content = ''.join(parts)
labels = list(dict.fromkeys(['부동산 정책', '주택공급'] + [r['tag'] for r in rows]))

if DRY:
    open('post_preview_policy.html', 'w', encoding='utf-8').write(f'<meta charset="utf-8"><h1>{esc(title)}</h1>' + content)
    print(title); print('라벨:', labels); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': '부동산 정책 ' + S['label'], 'fetchBodies': 'true'}), headers=H)
items = json.load(urllib.request.urlopen(q)).get('items', [])
same = [p for p in items if p.get('title', '').startswith('[부동산 정책]') and key in (p.get('content') or '')]
body = json.dumps({'title': title, 'content': content, 'labels': labels}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S['blog_url'] = post.get('url')
json.dump(S, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
