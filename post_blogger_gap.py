"""매매·전세 갭 블로그 글 (매주 화요일, GitHub Actions 용). 2026-11-23
사용법: python post_blogger_gap.py site/gap/summary.json [--dry]
- 카드 이미지는 daily.yml 이 저장소 cards/gap/<key>.png 로 보관 → 그 주소를 글에 넣음
- 구 전체 단지를 갭 큰 순으로 표로 (같은 단지라도 전용면적이 다르면 따로)
- 같은 날·같은 구 글이 있으면 고칩니다. 올린 글 주소를 summary.json 의 blog_url 에 적어 둠(카톡·스레드 링크용)
필요한 환경변수: BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN (없으면 건너뜀)
"""
import os, sys, json, datetime, urllib.request, urllib.parse, html

env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
DRY = '--dry' in sys.argv
if not DRY and not all(env.values()):
    print('블로거 설정값이 없어 게시를 건너뜁니다.'); sys.exit(0)
SITE = os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
PATH = [x for x in sys.argv[1:] if not x.startswith('--')][0]
S = json.load(open(PATH, encoding='utf-8'))
TODAY = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date().isoformat()
if S.get('made') != TODAY and not DRY:
    print('오늘은 갭 글이 없는 날입니다'); sys.exit(0)
REPO = os.environ.get('GITHUB_REPOSITORY', 'gogokimbiz-spec/sudogwon-rt'); BR = os.environ.get('GITHUB_REF_NAME') or 'main'
IMG = os.environ.get('GAP_IMG') or f"https://raw.githubusercontent.com/{REPO}/{BR}/cards/gap/{S['key']}.png"
esc = html.escape
d = datetime.date.fromisoformat(S['made']); p0, p1 = (datetime.date.fromisoformat(x) for x in S['period'])
ROWS = sorted(S['rows'], key=lambda r: r[6] - r[7], reverse=True)          # 갭 큰 순
if not ROWS:
    print('갭 자료가 없어 글을 건너뜁니다'); sys.exit(0)
T = 'style="border-collapse:collapse;width:100%;font-size:14px"'
TH = 'style="text-align:left;border-bottom:2px solid #ccc;padding:6px 4px"'
THR = 'style="text-align:right;border-bottom:2px solid #ccc;padding:6px 4px"'
TD = 'style="border-bottom:1px solid #eee;padding:6px 4px;vertical-align:top"'
TDR = 'style="border-bottom:1px solid #eee;padding:6px 4px;text-align:right;white-space:nowrap"'


def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억' + (f' {m:,}' if m else '')) if e else f'{m:,}만'


N = S['name']; R = S['region']; a = S.get('all84')
big, small = ROWS[0], ROWS[-1]
key = f"{N} 아파트 매매·전세 갭 순위 ({d.month}월 {d.day}일)"
title = f"[수도권 실거래] {key} | 갭 가장 큰 곳 {big[0]} {man(big[6] - big[7])}"

parts = []
intro = (f"최근 3개월({p0.month}.{p0.day}~{p1.month}.{p1.day} 계약) 국토교통부 실거래가로 {esc(R)} 아파트의 매매가와 전세가 차이(갭)를 단지별로 계산했습니다. ")
if a: intro += f"{esc(N)} 전용 84㎡대는 매매 {man(a['t'])}, 전세 {man(a['j'])}으로 갭은 약 {man(a['t'] - a['j'])}, 전세가율은 {round(a['j'] / a['t'] * 100)}%입니다. "
intro += (f"갭이 가장 큰 곳은 {esc(big[1])} {esc(big[0])} 전용 {big[2]:g}㎡({man(big[6] - big[7])}), "
          f"가장 작은 곳은 {esc(small[1])} {esc(small[0])} 전용 {small[2]:g}㎡({man(small[6] - small[7])})입니다.")
parts.append(f'<p style="font-size:16px;line-height:1.7">{intro}</p>')
parts.append(f'<div style="margin:0 0 14px;text-align:center"><img src="{IMG}" alt="{esc(N)} 아파트 매매·전세 갭 큰 단지·작은 단지" '
             'style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>')
# 요약
if a:
    parts.append(f"<h3>{esc(N)} 전체 요약</h3>")
    parts.append(f"<table {T}><tr><th {TH}>구분</th><th {THR}>매매</th><th {THR}>전세</th><th {THR}>갭</th><th {THR}>전세가율</th></tr>"
                 f"<tr><td {TD}>전용 84㎡대</td><td {TDR}>{man(a['t'])}<br><small>{a['nt']}건</small></td><td {TDR}>{man(a['j'])}<br><small>{a['nj']}건</small></td>"
                 f"<td {TDR}><b>{man(a['t'] - a['j'])}</b></td><td {TDR}>{round(a['j'] / a['t'] * 100)}%</td></tr></table>")
if S.get('bands'):
    parts.append("<p>평형별 전세가율: " + ' · '.join(f"{esc(n)} <b>{v}%</b>" for n, v in S['bands']) +
                 "<br><small>㎡당 전세 중앙값 ÷ ㎡당 매매 중앙값입니다.</small></p>")
# 광고 자리 (애드센스 승인 후)
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
if ad_client and ad_slot:
    parts.append(f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                 f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                 '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
# 전체 순위 (갭 큰 순)
parts.append(f"<h3>{esc(N)} 단지별 매매·전세 갭 – 갭 큰 순 {len(ROWS)}곳</h3>"
             "<p><small>같은 단지·같은 전용면적에서 최근 3개월 매매와 전세가 각각 2건 이상 있는 곳만 담았습니다. 가격은 중앙값, 갭 = 매매 − 전세입니다. "
             "같은 단지라도 전용면적이 다르면 따로 적었습니다.</small></p>")
body = ''.join(f"<tr><td {TD}><b>{i}</b></td><td {TD}>{esc(apt)}<br><small>{esc(umd)} · {by}년</small></td><td {TDR}>{area:g}㎡</td>"
               f"<td {TDR}>{man(mt)}<br><small>{nt}건</small></td><td {TDR}>{man(mj)}<br><small>{nj}건</small></td>"
               f"<td {TDR}><b>{man(mt - mj)}</b><br><small>전세가율 {round(mj / mt * 100)}%</small></td></tr>"
               for i, (apt, umd, area, by, nt, nj, mt, mj) in enumerate(ROWS, 1))
parts.append(f"<table {T}><tr><th {TH}>순위</th><th {TH}>단지</th><th {THR}>전용</th><th {THR}>매매</th><th {THR}>전세</th><th {THR}>갭</th></tr>{body}</table>")
parts.append(f'<p style="margin:20px 0"><a href="{SITE}r/{S["code"]}.html" style="display:inline-block;padding:12px 18px;border-radius:12px;background:#1f5fbf;color:#fff;font-weight:bold;text-decoration:none">'
             f'🏠 {esc(N)} 아파트 실거래가·신고가 보기 ›</a></p>')
parts.append('<hr><p><small>기준: 최근 3개월 계약된 아파트 매매(해제 거래 제외)와 전세(월세 0원 계약만). 같은 단지·같은 전용면적끼리 비교해 중앙값의 차이를 갭으로 계산했습니다. '
             '실거래는 계약 후 30일 안에 신고하므로 최근 거래는 앞으로 늘어날 수 있고, 실제 갭은 층·향·수리 상태에 따라 다릅니다.<br>'
             '자료: 국토교통부 실거래가 공개시스템(공공데이터포털 API). 이 글은 참고용 정보이며 투자 권유가 아닙니다.</small></p>')
content = ''.join(parts)
labels = ['실거래', '매매전세갭', '전세가율', '갭투자', N, R.split(' ')[0] + ' 아파트']

if DRY:
    open('post_preview_gap.html', 'w', encoding='utf-8').write(f'<meta charset="utf-8"><h1>{esc(title)}</h1>' + content)
    print(title); print('라벨:', labels); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': key, 'fetchBodies': 'false'}), headers=H)
items = json.load(urllib.request.urlopen(q)).get('items', [])
same = [p for p in items if key in p.get('title', '') and '[수도권 실거래]' in p.get('title', '')]
data = json.dumps({'title': title, 'content': content, 'labels': labels}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=data, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=data, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S['blog_url'] = post.get('url')
json.dump(S, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
