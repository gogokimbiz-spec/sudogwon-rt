"""구별 아파트값 상승률 블로그 글 (GitHub Actions 용).
사용법: python post_blogger_trend.py site/trend/summary.json --mode=week   (매주 월요일: 최근 4주 상승·하락 TOP 10)
        python post_blogger_trend.py site/trend/summary.json --mode=month  (매월 1일: 지난달 구별 순위 + 6개월 추이)
필요한 환경변수: BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN (없으면 건너뜀)
같은 주·같은 달 글이 이미 있으면 새로 만들지 않고 고칩니다.
"""
import os, sys, json, datetime, urllib.request, urllib.parse, html

env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
DRY = '--dry' in sys.argv
if not DRY and not all(env.values()):
    print('블로거 설정값이 없어 게시를 건너뜁니다.'); sys.exit(0)
MODE = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--mode=')), 'week')
SITE = os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
S = json.load(open(sys.argv[1], encoding='utf-8'))
P = S[MODE]
rows = P['rows']
if not rows:
    print('순위를 낼 만큼 거래가 있는 지역이 없어 글을 건너뜁니다'); sys.exit(0)
esc = html.escape
D = datetime.date.fromisoformat
md = lambda s: f'{D(s).month}.{D(s).day}'
pct = lambda v: '-' if v is None else f'{v:+.1f}%'
def man(v):
    if v is None: return '-'
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}만' if m else f'{e}억') if e else f'{m:,}만'
def area_name(r):   # 제목용 짧은 이름: '서울 강남구'→'강남', '성남 분당구'→'성남 분당', '광명시'→'광명'
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' and len(p[0]) > 2 else p[0]
    g = p[1][:-1] if len(p[1]) > 2 else p[1]
    return g if p[0] == '서울' else f'{p[0]} {g}'
def ga(w):
    c = w[-1]
    return w + ('이' if '가' <= c <= '힣' and (ord(c) - 0xAC00) % 28 else '가')

T = 'style="border-collapse:collapse;width:100%;font-size:14px"'
TH = 'style="text-align:left;border-bottom:2px solid #ccc;padding:6px 4px"'
THR = 'style="text-align:right;border-bottom:2px solid #ccc;padding:6px 4px"'
TD = 'style="border-bottom:1px solid #eee;padding:6px 4px"'
TDR = 'style="border-bottom:1px solid #eee;padding:6px 4px;text-align:right;white-space:nowrap"'
UPC, DNC = '#d23c3c', '#2a6fd6'
def reg(r):   # 지역명 → 시군구 페이지 링크
    return f'<a href="{SITE}r/{r["code"]}.html">{esc(r["region"])}</a>'
def table(rs, start=1):
    out = [f"<table {T}><tr><th {TH}>순위</th><th {TH}>지역</th><th {THR}>3.3㎡당</th><th {THR}>직전</th><th {THR}>변동</th><th {THR}>거래</th></tr>"]
    for i, r in enumerate(rs, start):
        col = UPC if r['chg'] > 0 else DNC if r['chg'] < 0 else '#666'
        out.append(f"<tr><td {TD}>{i}</td><td {TD}>{reg(r)}</td><td {TDR}>{man(r['pp_cur'])}</td><td {TDR}>{man(r['pp_prev'])}</td>"
                   f"<td {TDR}><b style=\"color:{col}\">{pct(r['chg'])}</b></td><td {TDR}>{r['n_cur']}건</td></tr>")
    return ''.join(out) + '</table>'
def cta(href, icon, title, sub, primary):
    bg = 'background:linear-gradient(135deg,#1f5fbf,#3b82f6);border:2px solid #1f5fbf;' if primary else 'background:#fff;border:2px solid #1f5fbf;'
    fg, sc = ('#fff', '#dbe8ff') if primary else ('#1f5fbf', '#555')
    return (f'<a href="{href}" style="flex:1 1 240px;display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:14px;text-decoration:none;{bg}">'
            f'<span style="font-size:28px;line-height:1">{icon}</span><span style="flex:1;min-width:0"><span style="display:block;font-size:16px;font-weight:bold;color:{fg}">{title}</span>'
            f'<span style="display:block;font-size:12.5px;color:{sc};margin-top:2px">{sub}</span></span>'
            f'<span style="font-size:15px;font-weight:800;color:{fg};white-space:nowrap">보기 ›</span></a>')

up = [r for r in rows if r['chg'] > 0]; dn = [r for r in rows[::-1] if r['chg'] < 0]
sd = P['sido']
top3 = '·'.join(area_name(r['region']) for r in up[:3])
cur, prev = P['cur'], P['prev']
if MODE == 'week':
    mon = D(P['key'][:10])
    title = f"[수도권 실거래] {mon.year}년 {P['label']} 구별 아파트값 상승률 TOP 10 (최근 4주)" + (f" | {top3}" if top3 else '')
    key = f"{mon.year}년 {P['label']} 구별"
    period = f"최근 4주({md(cur[0])}~{md(cur[1])})를 직전 4주({md(prev[0])}~{md(prev[1])})와 비교"
else:
    title = f"[수도권 실거래] {P['label']} 구별 아파트값 상승률 순위 (전월 대비)" + (f" | {top3}" if top3 else '')
    key = f"{P['label']} 구별 아파트값"
    period = f"{P['label']} 한 달({md(cur[0])}~{md(cur[1])})을 그 전달({md(prev[0])}~{md(prev[1])})과 비교"

# 요약 문장
s = [f"{period}한 수도권 시군구별 아파트 3.3㎡당 매매가(중앙값) 변동입니다."]
if sd['수도권']['chg'] is not None:
    s.append(f"수도권 전체는 {pct(sd['수도권']['chg'])}(서울 {pct(sd['서울']['chg'])} · 인천 {pct(sd['인천']['chg'])} · 경기 {pct(sd['경기']['chg'])})였습니다.")
if up: s.append(f"가장 많이 오른 곳은 {area_name(up[0]['region'])}({pct(up[0]['chg'])})" + (f", 이어서 {area_name(up[1]['region'])}({pct(up[1]['chg'])})" if len(up) > 1 else '') + "입니다.")
if dn: s.append(f"가장 많이 내린 곳은 {area_name(dn[0]['region'])}({pct(dn[0]['chg'])})입니다.")
s.append(f"두 기간 모두 거래가 {S['min_n']}건 이상인 {len(rows)}개 시군구만 집계했습니다.")
parts = [f'<p style="font-size:16px;line-height:1.75;margin:0 0 18px">{esc(" ".join(s))}</p>']
# 카드 이미지 (daily.yml 이 저장소 cards/trend/<key>.png 에 보관)
if os.path.exists(f"cards/trend/{P['key']}.png") and os.environ.get('GITHUB_REPOSITORY'):
    img = f"https://raw.githubusercontent.com/{os.environ['GITHUB_REPOSITORY']}/{os.environ.get('GITHUB_REF_NAME') or 'main'}/cards/trend/{P['key']}.png"
    parts.append(f'<div style="margin:0 0 18px;text-align:center"><img src="{img}" alt="{esc(title)}" style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>')
parts.append('<div style="display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 24px">'
             + cta(SITE, '🗺️', '지역별 지도로 보기', '기간을 골라 시군구 변동을 색으로 확인', True)
             + cta(f'{SITE}r/', '📍', '우리 동네 실거래가', '시군구별 신고가·최근 거래', False) + '</div>')
if MODE == 'week':
    parts.append(f"<h3>상승 TOP {min(10, len(up))}</h3>" + table(up[:10]) if up else '')
    parts.append(f"<h3>하락 TOP {min(10, len(dn))}</h3>" + table(dn[:10]) if dn else '')
else:
    parts.append(f"<h3>{P['label']} 시군구별 상승률 순위 ({len(rows)}곳)</h3>" + table(rows))
    ser = P.get('series') or {}
    if ser.get('수도권'):
        ms = [x['month'] for x in ser['수도권']]
        head = ''.join(f"<th {THR}>{int(m[5:])}월</th>" for m in ms)
        body = ''.join(f"<tr><td {TD}>{nm}</td>" + ''.join(f"<td {TDR}>{man(x['pp'])}</td>" for x in ser[nm]) + '</tr>' for nm in ('수도권', '서울', '인천', '경기'))
        parts.append(f"<h3>최근 {len(ms)}개월 3.3㎡당 매매가 추이</h3><table {T}><tr><th {TH}>지역</th>{head}</tr>{body}</table>")
# 광고 자리 (애드센스 승인 후)
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
if ad_client and ad_slot:
    parts.insert(2, f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                    f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                    '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
parts.append('<hr><p><small>계산 방법: 시군구마다 기간 안 아파트 매매 실거래의 3.3㎡당 가격(거래가 ÷ 전용면적 × 3.3058) 중앙값을 구해 비교했습니다. '
             '비싼 단지가 많이 팔린 기간은 실제 시세보다 오른 것처럼 보일 수 있습니다. 실거래는 계약 후 30일 안에 신고하므로 최근 기간 숫자는 앞으로 바뀔 수 있는 잠정치입니다.<br>'
             '자료: 국토교통부 실거래가 공개시스템(공공데이터포털 API), 해제 신고 거래 제외. 이 글은 참고용 정보이며 투자 권유가 아닙니다.</small></p>')
content = ''.join(parts)
labels = ['실거래', '구별 상승률', '아파트값 순위', '수도권 실거래가'] + list(dict.fromkeys(area_name(r['region']) + ' 아파트' for r in up[:3] + dn[:2]))

if DRY:
    open(f'post_preview_trend_{MODE}.html', 'w', encoding='utf-8').write(f'<meta charset="utf-8"><h1>{esc(title)}</h1>' + content)
    print(title); print('라벨:', labels); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': key, 'fetchBodies': 'false'}), headers=H)
items = json.load(urllib.request.urlopen(q)).get('items', [])
same = [p for p in items if key in p.get('title', '') and '[수도권 실거래]' in p.get('title', '')]
body = json.dumps({'title': title, 'content': content, 'labels': labels[:10]}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
P['blog_url'] = post.get('url')
json.dump(S, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
