"""summary.json 으로 구글 블로거에 그날 글을 올립니다 (GitHub Actions 용).
필요한 환경변수: BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN
선택: SITE_URL (지도 사이트 주소)
값이 없으면 아무것도 하지 않고 끝납니다.
"""
import os, sys, json, datetime, urllib.request, urllib.parse, html

env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
if not all(env.values()):
    print('블로거 설정값이 없어 게시를 건너뜁니다.'); sys.exit(0)
SITE = os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
S = json.load(open(sys.argv[1], encoding='utf-8'))
DRY = '--dry' in sys.argv

def man(v):
    if v is None: return '-'
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}' if m else f'{e}억') if e else f'{m:,}만'
short = lambda r: r.split(' ')[-1]
esc = html.escape
d = datetime.date.fromisoformat(S['day']); wd = '월화수목금토일'[d.weekday()]
nh = S.get('new_highs', [])
bs = S['by_sido']
title = f"[수도권 아파트 실거래] {d.year}년 {d.month}월 {d.day}일({wd}) 매매 {S['trade_count']}건" + (f" · 신고가 {len(nh)}건" if nh else '')

T = 'style="border-collapse:collapse;width:100%;font-size:14px"'
TH = 'style="text-align:left;border-bottom:2px solid #ccc;padding:6px 4px"'
THR = 'style="text-align:right;border-bottom:2px solid #ccc;padding:6px 4px"'
TD = 'style="border-bottom:1px solid #eee;padding:6px 4px;vertical-align:top"'
TDR = 'style="border-bottom:1px solid #eee;padding:6px 4px;text-align:right;white-space:nowrap"'
RED = 'style="color:#d23c3c;font-weight:bold"'

def trade_rows(rows, with_prev=False):
    out = []
    for t in rows:
        badge = f' <span {RED}>[신고가]</span>' if t.get('new_high') else ''
        prev = f"<br><small>이전 최고 {man(t['prev_high_man'])} ({t['prev_high_date'][5:].replace('-', '.')})</small>" if with_prev and t.get('new_high') else ''
        out.append(f"<tr><td {TD}>{esc(t['region'])}</td><td {TD}>{esc(t['apt'])}{badge}<br><small>{esc(t['umd'])} · {t['built']}년</small></td>"
                   f"<td {TDR}>{t['area']}㎡ · {t['floor']}층</td><td {TDR}><b>{man(t['price_man'])}</b><br><small>3.3㎡당 {man(t['pp_man'])}</small>{prev}</td></tr>")
    return ''.join(out)

parts = []
# 2. 지도 버튼
parts.append(f'<p style="margin:8px 0 20px"><a href="{SITE}" style="display:inline-block;padding:10px 16px;background:#1f5fbf;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">▶ 지역별 지도로 자세히 보기</a></p>')
# 3. 신고가 표
if nh:
    parts.append(f"<h3>신고가 {len(nh)}건</h3><p><small>같은 단지·같은 전용면적에서 최근 약 6개월 거래보다 비싸게 팔린 거래입니다.</small></p>")
    parts.append(f"<table {T}><tr><th {TH}>지역</th><th {TH}>단지</th><th {THR}>전용·층</th><th {THR}>거래가</th></tr>{trade_rows(nh, True)}</table>")
else:
    parts.append('<h3>신고가</h3><p>이 날 신고된 거래 중 신고가는 아직 없습니다.</p>')
# 4. 광고 (애드센스 승인 후 ADSENSE_CLIENT, ADSENSE_SLOT 값을 넣으면 이 자리에 광고가 들어갑니다)
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
if ad_client and ad_slot:
    parts.append(f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                 f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                 '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
# 5. 전날 거래가 높은 순 20건
parts.append(f"<h3>전날 거래가 높은 순 {min(20, len(S['day_trades']))}건</h3>"
             f"<p><small>{d.month}월 {d.day}일 계약 매매 {S['trade_count']}건(서울 {bs['11']} · 인천 {bs['28']} · 경기 {bs['41']}), 전세 {S['jeonse_count']}건. "
             "실거래는 계약 후 30일 안에 신고하므로 건수는 앞으로 늘어납니다.</small></p>")
parts.append(f"<table {T}><tr><th {TH}>지역</th><th {TH}>단지</th><th {THR}>전용·층</th><th {THR}>거래가</th></tr>{trade_rows(S['day_trades'])}</table>")
# 6. 최근 30일 상승·하락 5곳
up = ' · '.join(f"{esc(short(x['region']))} <span style=\"color:#d23c3c\">+{x['chg']}%</span>" for x in S.get('up5', []))
dn = ' · '.join(f"{esc(short(x['region']))} <span style=\"color:#2a6fd6\">{x['chg']}%</span>" for x in S.get('down5', []))
parts.append(f"<h3>최근 30일 3.3㎡당 매매가 변동 (직전 30일 대비)</h3><p>상승: {up or '-'}<br>하락: {dn or '-'}</p>"
             "<p><small>시군구별 3.3㎡당 매매가 중앙값 비교이며, 두 기간 모두 거래 10건 이상인 지역만 집계했습니다.</small></p>")
# 7. 오늘의 부동산 뉴스
news = S.get('news')
if news:
    parts.append(f"<h3>오늘의 부동산 뉴스</h3><p><a href=\"{esc(news['link'])}\">{esc(news['title'])}</a> <small>({esc(news.get('source', ''))})</small></p>")
# 8. 출처·고지
parts.append('<hr><p><small>자료: 국토교통부 실거래가 공개시스템(공공데이터포털 API). 해제 신고된 거래는 제외했습니다. '
             '이 글은 참고용 정보이며 투자 권유가 아닙니다.</small></p>')
content = ''.join(parts)

if DRY:
    open('post_preview.html', 'w', encoding='utf-8').write(f'<h1>{esc(title)}</h1>' + content); print(title); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"

# 같은 날짜 글이 이미 있으면 새로 만들지 않고 고칩니다
key = f"{d.year}년 {d.month}월 {d.day}일"
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': key, 'fetchBodies': 'false'}), headers=H)
items = json.load(urllib.request.urlopen(q)).get('items', [])
same = [p for p in items if key in p.get('title', '') and '수도권 아파트 실거래' in p.get('title', '')]
body = json.dumps({'title': title, 'content': content, 'labels': ['수도권 실거래가', '아파트 실거래', '신고가']}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S['blog_url'] = post.get('url')
json.dump(S, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
