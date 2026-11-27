"""다음 달부터 달라지는 부동산 9가지 – 블로그 글 (매월 말일 15시, policy_month.yml) – 2026-11-27
사용법: python post_blogger_policy_month.py <폴더>/policy_month/summary.json   [--dry]
- 카드 이미지: cards/policy_month/<month>.png (저장소 raw 주소)
- 같은 달 글이 있으면 고칩니다. 올린 글 주소를 summary.json 의 blog_url 에 적어 둠(카톡·스레드 링크용)
필요한 환경변수: BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN (없으면 건너뜀)
"""
import os, sys, json, urllib.request, urllib.parse, html

env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
DRY = '--dry' in sys.argv
if not DRY and not all(env.values()):
    print('블로거 설정값이 없어 게시를 건너뜁니다.'); sys.exit(0)
P = [a for a in sys.argv[1:] if not a.startswith('--')][0]
S = json.load(open(P, encoding='utf-8'))
esc = html.escape
REPO = os.environ.get('GITHUB_REPOSITORY', 'gogokimbiz-spec/sudogwon-rt'); BR = os.environ.get('GITHUB_REF_NAME') or 'main'
img = f"https://raw.githubusercontent.com/{REPO}/{BR}/cards/policy_month/{S['month']}.png"
MAP = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
y, m = int(S['month'][:4]), int(S['month'][5:7])
items = S['items'][:9]
head = f"{S.get('head1') or f'{m}월부터 달라지는'} {S.get('head2') or '부동산'} {len(items)}가지"
title = f"[부동산 정책] {head} ({y}년 {m}월)"
key = f"cards/policy_month/{S['month']}.png"


def chg(it):
    if it.get('before') and it.get('after'):
        return f"{it['before']} → {it['after']}"
    return it.get('main') or ''


B = S.get('blog') or {}
parts = [f'<div style="margin:0 0 16px;text-align:center"><img src="{img}" alt="{esc(head)} – {y}년 {m}월" '
         f'style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>',
         f'<p style="font-size:16px;line-height:1.7">{esc(B.get("intro") or f"{m}월에 시행되거나 마감되는 부동산 제도와 곧 바뀌는 대출·세금·청약 규정을 한 장으로 정리했어요. 날짜를 확인하고 미리 챙기세요.")}</p>']
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
for i, it in enumerate(items, 1):
    c = chg(it)
    src = f' · <a href="{esc(it["source"])}">자료 보기</a>' if it.get('source') else ''
    parts.append(f'<h3>{i}. {esc(it["title"])}' + (f' – {esc(c)}' if c else '') + '</h3>'
                 f'<p style="font-size:16px;line-height:1.7;margin:4px 0">{esc(it.get("detail") or it.get("note", ""))}</p>'
                 f'<p style="font-size:14px;color:#64748b;margin:0 0 12px"><b style="color:#c2410c">{esc(it.get("status", ""))}</b>{src}</p>')
    if i == 3 and ad_client and ad_slot:
        parts.append(f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                     f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                     '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
parts.append(f'<p style="margin:20px 0"><a href="{MAP}policy/" style="display:inline-block;padding:12px 18px;border-radius:12px;background:#172033;color:#fff;font-weight:bold;text-decoration:none;margin:0 8px 8px 0">'
             '📋 부동산 정책 모아보기 ›</a>'
             f'<a href="{MAP}" style="display:inline-block;padding:12px 18px;border-radius:12px;background:#1f5fbf;color:#fff;font-weight:bold;text-decoration:none">'
             '🏠 수도권 아파트 실거래가 지도 ›</a></p>')
parts.append(f'<hr><p><small>자료: {esc(S.get("source_line") or "정부 보도자료")}. 개정안·정부안·예정 항목은 국회 심의나 기관 사정에 따라 바뀔 수 있어요. '
             '실제 적용 여부는 각 기관 안내와 원문을 확인하세요. 참고용 정보이며 법률·세무 자문이 아닙니다.</small></p>')
content = ''.join(parts)
labels = ['부동산 정책', '달라지는 제도', f'{y}년 {m}월']

if DRY:
    open('post_preview_policy_month.html', 'w', encoding='utf-8').write(f'<meta charset="utf-8"><h1>{esc(title)}</h1>' + content)
    print(title); print('라벨:', labels); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': f'부동산 정책 {y}년 {m}월', 'fetchBodies': 'true'}), headers=H)
found = json.load(urllib.request.urlopen(q)).get('items', [])
same = [p for p in found if p.get('title', '').startswith('[부동산 정책]') and key in (p.get('content') or '')]
body = json.dumps({'title': title, 'content': content, 'labels': labels}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S['blog_url'] = post.get('url')
json.dump(S, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
