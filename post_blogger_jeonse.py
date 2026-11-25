"""전세 실거래 블로그 글 (매일, GitHub Actions 용). 2026-11-25
사용법: python post_blogger_jeonse.py site/jeonse/summary.json [--dry]
- 카드 이미지는 daily.yml 이 저장소 cards/jeonse/<key>.png 로 보관 → 그 주소를 글에 넣음
- 전세 실거래가격 TOP 20 / 전세 최고가 경신 전체 / 권역별 (갱신 인상폭은 11-25 사용자 요청으로 삭제)
- 같은 날 글이 있으면 고칩니다. 올린 글 주소를 summary.json 의 blog_url 에 적어 둠(카톡·스레드 링크용)
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
    print('오늘 만든 전세 카드가 없습니다'); sys.exit(0)
REPO = os.environ.get('GITHUB_REPOSITORY', 'gogokimbiz-spec/sudogwon-rt'); BR = os.environ.get('GITHUB_REF_NAME') or 'main'
IMG = os.environ.get('JEONSE_IMG') or f"https://raw.githubusercontent.com/{REPO}/{BR}/cards/jeonse/{S['key']}.png"
esc = html.escape
T = 'style="border-collapse:collapse;width:100%;font-size:14px"'
TH = 'style="text-align:left;border-bottom:2px solid #ccc;padding:6px 4px"'
THR = 'style="text-align:right;border-bottom:2px solid #ccc;padding:6px 4px"'
TD = 'style="border-bottom:1px solid #eee;padding:6px 4px;vertical-align:top"'
TDR = 'style="border-bottom:1px solid #eee;padding:6px 4px;text-align:right;white-space:nowrap"'


def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억' + (f' {m:,}' if m else '')) if e else f'{m:,}만'


def apt_cell(r):
    dd = datetime.date.fromisoformat(r['date'])
    return (f"<td {TD}>{esc(r.get('apt') or '-')}<br><small>{esc(r['region'])} {esc(r['umd'])} · {r['area']:g}㎡ · {r.get('floor', '')}층"
            f" · {dd.month}.{dd.day} 계약</small></td>")


st = S['stats']; L = S['label']; word = '신고' if S['basis'] == 'reported' else '계약'
tops, highs = S['top20'], S['highs_all']
if not tops:
    print('전세 자료가 없어 글을 건너뜁니다'); sys.exit(0)
key = f"전세 실거래 {L} {word}"
t1 = tops[0]
title = f"[수도권 실거래] 오늘의 {key} | 최고 {t1.get('apt') or t1['umd']} {man(t1['dep'])}"

parts = []
intro = (f"{esc(L)} {word}된 수도권 아파트 전세(월세 0원) 실거래는 모두 {st['n']:,}건입니다"
         f" (서울 {st['by_sido'].get('11', 0):,} · 경기 {st['by_sido'].get('41', 0):,} · 인천 {st['by_sido'].get('28', 0):,}). "
         f"가장 비싼 전세는 {esc(t1['region'])} {esc(t1.get('apt') or t1['umd'])} 전용 {t1['area']:g}㎡ {man(t1['dep'])}입니다. ")
if st['n_high']: intro += f"같은 단지·같은 면적의 최근 6개월 최고 전세가를 넘어선 거래는 {st['n_high']:,}건입니다."
parts.append(f'<p style="font-size:16px;line-height:1.7">{intro}</p>')
parts.append(f'<div style="margin:0 0 14px;text-align:center"><img src="{IMG}" alt="오늘의 전세 실거래 {esc(L)}" '
             'style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>')
# 1. 전세 실거래가격 TOP 20
parts.append(f"<h3>💰 전세 실거래가격 TOP {len(tops)}</h3><p><small>보증금 높은 순, 같은 단지는 1건만.</small></p>")
body = ''.join(f"<tr><td {TD}><b>{i}</b></td>{apt_cell(r)}<td {TDR}>{man(r['prev_high']) if r.get('prev_high') else '-'}</td>"
               f"<td {TDR}><b>{man(r['dep'])}</b>{'<br><small style=\"color:#d33\">최고가 경신</small>' if r.get('new_high') else ''}</td></tr>"
               for i, r in enumerate(tops, 1))
parts.append(f"<table {T}><tr><th {TH}>순위</th><th {TH}>단지</th><th {THR}>이전가격</th><th {THR}>실거래가격</th></tr>{body}</table>")
# 광고 자리 (애드센스 승인 후)
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
if ad_client and ad_slot:
    parts.append(f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                 f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                 '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
# 2. 전세 최고가 경신
if highs:
    parts.append(f"<h3>🔺 전세 최고가 경신 {len(highs)}건</h3><p><small>같은 단지·같은 전용면적에서 최근 6개월(이전 거래 2건 이상) 최고 전세보다 비싸게 계약된 거래입니다.</small></p>")
    body = ''.join(f"<tr><td {TD}><b>{i}</b></td>{apt_cell(r)}<td {TDR}><b>{man(r['dep'])}</b><br><small>이전 {man(r['prev_high'])}</small></td>"
                   f"<td {TDR}><span style=\"color:#d33\">+{man(r['dep'] - r['prev_high'])}</span></td></tr>" for i, r in enumerate(highs, 1))
    parts.append(f"<table {T}><tr><th {TH}>순위</th><th {TH}>단지</th><th {THR}>보증금</th><th {THR}>상승</th></tr>{body}</table>")
# 4. 권역별 (매매 실거래 권역 카드와 같은 4개 권역)
if S.get('groups'):
    parts.append("<h3>🗺️ 권역별 전세 실거래</h3><p><small>서울 / 경기 북부: 고양·파주·김포·의정부·양주·동두천·남양주·구리·포천·연천·가평 / "
                 "인천·경기 남서부: 인천·부천·광명·시흥·안산·안양·군포·의왕·과천 / "
                 "경기 남동부: 성남·하남·광주·용인·이천·안성·여주·양평·화성·오산·평택·수원</small></p>")
    for gi, g in enumerate(S['groups'], 1):
        t = (g['cards']['tops'] or [None])[0]
        parts.append(f"<h4>{esc(g['name'])} – {g['n']:,}건 (최고가 경신 {g.get('n_high', 0):,}건)</h4>")
        if t:
            parts.append(f'<div style="margin:0 0 10px;text-align:center"><img src="{IMG[:-4]}_r{gi}.png" alt="{esc(g["name"])} 전세 실거래 {esc(L)}" '
                         'style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>')
            parts.append(f"<p>가장 비싼 전세: {esc(t['region'])} {esc(t.get('apt') or t['umd'])} 전용 {t['area']:g}㎡ <b>{man(t['dep'])}</b></p>")
parts.append(f'<p style="margin:20px 0"><a href="{SITE}" style="display:inline-block;padding:12px 18px;border-radius:12px;background:#1f5fbf;color:#fff;font-weight:bold;text-decoration:none">'
             '🗺️ 수도권 실거래 지도에서 전세 보기 ›</a></p>')
parts.append(f'<hr><p><small>기준: {"어제 새로 신고된" if S["basis"] == "reported" else "마지막 계약일의"} 아파트 전세 계약(월세 0원). 전월세는 계약 후 30일 안에 신고하므로 계약일은 며칠~한 달 전일 수 있습니다. '
             '최고가 경신은 최근 6개월 자료만 비교한 것이라 그 이전 최고가는 반영되지 않습니다.<br>'
             '자료: 국토교통부 실거래가 공개시스템(공공데이터포털 API). 이 글은 참고용 정보입니다.</small></p>')
content = ''.join(parts)
labels = ['실거래', '전세', '전세실거래가', '전세최고가']

if DRY:
    open('post_preview_jeonse.html', 'w', encoding='utf-8').write(f'<meta charset="utf-8"><h1>{esc(title)}</h1>' + content)
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
