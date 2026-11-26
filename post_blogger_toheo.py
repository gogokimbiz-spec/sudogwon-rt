"""토허제 40곳 주간 아파트값 블로그 글 (매주 금요일 11시, toheo.yml) – 2026-11-26
사용법: python post_blogger_toheo.py <폴더>/toheo/summary.json   [--dry]
- make_cards_toheo.py 가 만든 summary.json 으로 글을 올림. 같은 주(조사 기준일) 글이 이미 있으면 고칩니다.
- 대표 이미지: 저장소 cards/toheo/<조사 기준일>.png (toheo.yml 이 커밋)
- 올린 글 주소를 summary.json 의 blog_url 에 적어 둠(카톡·스레드 링크용)
필요한 환경변수: BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN (없으면 건너뜀)
"""
import os, sys, json, urllib.request, urllib.parse, html, datetime

env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
DRY = '--dry' in sys.argv
if not DRY and not all(env.values()):
    print('블로거 설정값이 없어 게시를 건너뜁니다.'); sys.exit(0)
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
P = [a for a in sys.argv[1:] if not a.startswith('--')][0]
S = json.load(open(P, encoding='utf-8'))
esc = html.escape
REPO = os.environ.get('GITHUB_REPOSITORY', 'gogokimbiz-spec/sudogwon-rt'); BR = os.environ.get('GITHUB_REF_NAME') or 'main'
img = f"https://raw.githubusercontent.com/{REPO}/{BR}/cards/toheo/{S['base_day']}.png"
rows = S['rows']; bd = datetime.date.fromisoformat(S['base_day'])
pc = lambda v: '0.00%' if abs(v) < 0.005 else f'{v:+.2f}%'
col = lambda v: '#b3261e' if v > 0 else '#1f4e9c' if v < 0 else '#555'
top, bot = rows[0], rows[-1]
ex = S.get('extra') or {}
key = f"토허제 40곳 아파트값 ({S['label']})"
title = f"[토허제 주간] {key} | 1위 {top['name']} {pc(top['chg'])} · 꼴찌 {bot['name']} {pc(bot['chg'])}"


def st(r):
    s = r.get('streak', 0)
    if not s: return '보합'
    return f"{'▲' if s > 0 else '▼'} {abs(s)}주" + (' 연속' if abs(s) > 1 else '째')


ups = sorted([r for r in rows if r.get('streak', 0) > 0], key=lambda r: -r['streak'])[:3]
dns = sorted([r for r in rows if r.get('streak', 0) < 0], key=lambda r: r['streak'])[:3]
sx = ' · '.join(f"{k} {pc(v)}" for k, v in ex.items() if v is not None)

parts = [f'<div style="margin:0 0 16px;text-align:center"><img src="{img}" alt="토허제 40곳 주간 아파트값 지도 – {esc(S["label"])}" '
         'style="width:100%;max-width:540px;height:auto;border-radius:6px"></div>']
parts.append(f'<p style="font-size:16px;line-height:1.8">한국부동산원이 {bd.month}월 {bd.day}일 기준으로 조사한 주간 아파트 매매가격지수를 보면, '
             f'토지거래허가구역(토허제) {len(rows)}곳 가운데 <b>{S["n_up"]}곳이 오르고 {S["n_dn"]}곳이 내렸습니다</b>'
             + (f'(보합 {S["n_eq"]}곳)' if S.get('n_eq') else '') + '. '
             f'가장 많이 오른 곳은 <b style="color:#b3261e">{esc(top["name"])} {pc(top["chg"])}</b>, '
             f'가장 많이 내린 곳은 <b style="color:#1f4e9c">{esc(bot["name"])} {pc(bot["chg"])}</b>입니다.'
             + (f' 같은 주 {esc(sx)}.' if sx else '') + '</p>')
if ups or dns:
    L = []
    if ups: L.append('연속 상승이 가장 긴 곳은 ' + ', '.join(f"{esc(r['name'])} {r['streak']}주" for r in ups))
    if dns: L.append('연속 하락이 가장 긴 곳은 ' + ', '.join(f"{esc(r['name'])} {-r['streak']}주" for r in dns))
    parts.append(f'<p style="font-size:16px;line-height:1.8">{" / ".join(L)}입니다.</p>')

ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
if ad_client and ad_slot:
    parts.append(f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                 f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                 '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')

th = 'style="padding:6px 8px;border-bottom:2px solid #222;text-align:{}"'
td = 'style="padding:6px 8px;border-bottom:1px solid #ddd;text-align:{}"'
tb = [f'<h3>토허제 {len(rows)}곳 주간 변동률 전체 (오른 순)</h3>',
      '<table style="width:100%;border-collapse:collapse;font-size:15px"><tr>'
      + ''.join(f'<th {th.format(a)}>{h}</th>' for h, a in (('순위', 'center'), ('지역', 'left'), ('전주 대비', 'right'), ('연속', 'right'))) + '</tr>']
for r in rows:
    tb.append('<tr>' + f'<td {td.format("center")}>{r["rank"]}</td><td {td.format("left")}>{esc(r["name"])}</td>'
              f'<td {td.format("right")}><b style="color:{col(r["chg"])}">{pc(r["chg"])}</b></td>'
              f'<td {td.format("right")}>{st(r)}</td></tr>')
tb.append('</table>')
parts.append(''.join(tb))
parts.append('<h3>토허제 40곳은 어디?</h3><p style="font-size:15px;line-height:1.8">서울 25개 구 전체와 경기 15곳'
             '(과천, 광명, 하남, 의왕, 구리, 성남 분당·수정·중원, 수원 영통·장안·팔달, 안양 동안, 용인 수지·기흥, 화성 동탄)입니다. '
             '토지거래허가구역에서는 일정 면적 이상 주택을 살 때 관할 구청의 허가를 받아야 하고, 실거주 의무가 붙습니다.</p>')
parts.append(f'<p style="margin:20px 0"><a href="{SITE}" style="display:inline-block;padding:12px 18px;border-radius:8px;background:#1e1914;color:#efe3c8;font-weight:bold;text-decoration:none">'
             '🏠 수도권 아파트 실거래가 지도 보기 ›</a></p>')
parts.append(f'<hr><p><small>자료: 한국부동산원 주간아파트가격동향 – (주) 매매가격지수 ({bd.month}월 {bd.day}일 조사, {S["label"]})<br>'
             '변동률은 이번 주 지수 ÷ 지난주 지수 − 1. 연속 주수는 최근 약 4년 자료로 같은 방향(상승·하락)이 이어진 주 수이며, 보합(0.00%)이면 끊깁니다.<br>'
             '참고용 정보이며 투자 판단의 책임은 본인에게 있습니다.</small></p>')
content = ''.join(parts)
labels = ['토허제', '토지거래허가구역', '주간아파트가격동향', '아파트값', top['name'].split(' ')[-1], bot['name'].split(' ')[-1]]
labels = list(dict.fromkeys(labels))

if DRY:
    open('post_preview_toheo.html', 'w', encoding='utf-8').write(f'<meta charset="utf-8"><h1>{esc(title)}</h1>' + content)
    print(title); print('라벨:', labels); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': '토허제 주간', 'fetchBodies': 'true'}), headers=H)
items = json.load(urllib.request.urlopen(q)).get('items', [])
same = [p for p in items if '[토허제 주간]' in p.get('title', '') and f"cards/toheo/{S['base_day']}.png" in (p.get('content') or '')]   # 같은 조사 기준일 글
body = json.dumps({'title': title, 'content': content, 'labels': labels}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S['blog_url'] = post.get('url')
json.dump(S, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
