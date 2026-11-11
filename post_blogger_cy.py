"""청약 요약(cheongyak/summary.json)으로 구글 블로거에 요일별 청약 글을 올립니다 (GitHub Actions 용).
  --mode=mon 월: 이번 주 청약 일정 / --mode=wed 수: 줍줍·로또 청약 + 결과 / --mode=fri 금: 단지분석
필요한 환경변수: BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN (실거래 글과 같은 값)
선택: SITE_URL (사이트 주소), ADSENSE_CLIENT, ADSENSE_SLOT
사용법: python post_blogger_cy.py site/cheongyak/summary.json --mode=mon|wed|fri [--dry]
"""
import os, sys, json, datetime, urllib.request, urllib.parse, html

env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
DRY = '--dry' in sys.argv
if not DRY and not all(env.values()):
    print('블로거 설정값이 없어 게시를 건너뜁니다.'); sys.exit(0)
SITE = (os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/').rstrip('/') + '/cheongyak/'
S = json.load(open(sys.argv[1], encoding='utf-8'))
MODE = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--mode=')), 'mon')
esc = html.escape

def man(v):
    if v is None: return '-'
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}' if m else f'{e}억') if e else f'{m:,}만'
D = lambda s: datetime.date.fromisoformat(s[:10])
WD = '월화수목금토일'
md = lambda s: f"{D(s).month}.{D(s).day}({WD[D(s).weekday()]})" if s else '-'
w0, w1 = D(S['week'][0]), D(S['week'][1])
nth = (w0.day - 1) // 7 + 1
title = f"[수도권 청약] {w0.month}월 {nth}주차({w0.month}.{w0.day}~{w1.month}.{w1.day}) 청약 일정 · 접수 {len(S['rank1'])}곳"

T = 'style="border-collapse:collapse;width:100%;font-size:14px"'
TH = 'style="text-align:left;border-bottom:2px solid #ccc;padding:6px 4px"'
THR = 'style="text-align:right;border-bottom:2px solid #ccc;padding:6px 4px"'
TD = 'style="border-bottom:1px solid #eee;padding:6px 4px;vertical-align:top"'
TDR = 'style="border-bottom:1px solid #eee;padding:6px 4px;text-align:right;white-space:nowrap;vertical-align:top"'
RED, BLUE = '#d23c3c', '#2a6fd6'
def gap(x):
    g = x.get('gap_new')
    if g is None: return ''
    return f"<br><small style=\"color:{RED if g >= 5 else BLUE if g <= -5 else '#666'}\">주변 신축 대비 {'+' if g > 0 else ''}{g}%</small>"
def name(x):
    sub = ' · '.join(s for s in [x.get('umd'), x.get('builder'), f"{x['units']:,}세대 (일반 {x['general']:,})", '공공' if x.get('kind') == '국민' else ''] if s)
    return f"<a href=\"{esc(x['url'])}\">{esc(x['name'])}</a><br><small>{esc(sub)}</small>"
def rate(x):
    if 'rate' not in x: return '-'
    c = BLUE if x['status'] == '미달' else RED if x['status'] == '1순위 마감' else '#666'
    return f"<b>{x['rate']:.2f} : 1</b><br><small style=\"color:{c}\">{esc(x['status'])}</small>"

RT_SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
def cta(href, icon, title, sub, primary):
    bg = 'background:linear-gradient(135deg,#1f5fbf,#3b82f6);border:2px solid #1f5fbf;box-shadow:0 4px 14px rgba(31,95,191,.35);' if primary \
        else 'background:#ffffff;border:2px solid #1f5fbf;box-shadow:0 3px 10px rgba(31,95,191,.15);'
    fg = '#ffffff' if primary else '#1f5fbf'
    sc = '#e8f0ff' if primary else '#4b5b70'
    return (f'<a href="{href}" style="flex:1 1 260px;display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:14px;text-decoration:none;{bg}">'
            f'<span style="font-size:28px;line-height:1">{icon}</span>'
            f'<span style="flex:1;min-width:0"><span style="display:block;font-size:16.5px;font-weight:800;color:{fg};line-height:1.3">{title}</span>'
            f'<span style="display:block;font-size:12.5px;color:{sc};margin-top:2px">{sub}</span></span>'
            f'<span style="font-size:15px;font-weight:800;color:{fg};white-space:nowrap">보기 ›</span></a>')
parts = ['<div style="display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 24px">'
         + cta(SITE, '🗺️', '청약 지도로 보기', '접수 일정·분양가·주변 신축 대비', True)
         + cta(f'{RT_SITE}r/', '📍', '우리 동네 실거래가', '시군구별 신고가·최근 거래', False) + '</div>']
# 청약·분양 뉴스를 맨 위에 (지도 버튼보다 먼저)
news = S.get('news') or []
if news:
    parts.insert(0, '<div style="margin:4px 0 18px;padding:12px 14px;border-left:4px solid #1f5fbf;background:#f3f6fb">'
                    '<div style="font-size:13px;color:#555;margin-bottom:6px">📰 이번 주 청약·분양 뉴스</div><ul style="margin:0;padding-left:18px">' + ''.join(
        f"<li style=\"margin:2px 0\"><a href=\"{esc(n['link'])}\" style=\"font-weight:bold\">{esc(n['title'])}</a> <small>({esc(n.get('source', ''))}{' · ' + n['date'][5:].replace('-', '.') if n.get('date') else ''})</small></li>" for n in news) + '</ul></div>')
r1 = S['rank1']
parts.append(f"<h3>이번 주 청약 접수 {len(r1)}곳</h3>")
if r1:
    rows = ''.join(f"<tr><td {TD}>{md(x['date'])}{'<br><small>특공 ' + md(x['sp_date']) + '</small>' if x.get('sp_date') and x['sp_date'] != x['date'] else ''}</td>"
                   f"<td {TD}>{esc(x['region'])}</td><td {TD}>{name(x)}</td><td {TDR}><b>{man(x['pp_man'])}</b>{gap(x)}</td></tr>" for x in r1)
    parts.append(f"<table {T}><tr><th {TH}>1순위</th><th {TH}>지역</th><th {TH}>단지</th><th {THR}>3.3㎡당 분양가</th></tr>{rows}</table>")
    parts.append('<p><small>3.3㎡당 분양가는 주택형별 최고가를 <b>전용면적</b>으로 나눈 값(세대수 가중)이라 분양 광고의 공급면적 기준 평당가보다 높습니다. '
                 '주변 신축 대비는 분양가를 같은 시군구 최근 10년 내 준공 아파트의 최근 6개월 매매 3.3㎡당 중앙값과 비교한 값입니다. 단지명을 누르면 청약홈 모집공고로 갑니다.</small></p>')
else:
    parts.append('<p>이번 주에는 수도권 청약 접수가 없습니다.</p>')
if S['winners']:
    parts.append(f"<h3>이번 주 당첨자 발표 {len(S['winners'])}곳</h3><ul>" +
                 ''.join(f"<li>{md(x['date'])} · {esc(x['region'])} <a href=\"{esc(x['url'])}\">{esc(x['name'])}</a>{' — ' + rate(x).replace('<br>', ' ') if 'rate' in x else ''}</li>" for x in S['winners']) + '</ul>')
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
if ad_client and ad_slot:
    parts.append(f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                 f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                 '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
lw = S['last_week']
if lw and MODE == 'mon' and os.environ.get('CY_MON_LASTWEEK'):  # 결과는 수요일 글로 옮김
    rows = ''.join(f"<tr><td {TD}>{esc(x['region'])}</td><td {TD}>{name(x)}</td><td {TDR}>{rate(x)}<br><small>{x.get('apps', 0):,}건</small></td><td {TDR}>{man(x['pp_man'])}{gap(x)}</td></tr>" for x in lw)
    parts.append(f"<h3>지난주 1순위 결과 {len(lw)}곳</h3><table {T}><tr><th {TH}>지역</th><th {TH}>단지</th><th {THR}>1순위 경쟁률</th><th {THR}>3.3㎡당</th></tr>{rows}</table>"
                 '<p><small>1순위 접수 건수 ÷ 일반공급 세대수(특별공급 제외). 2순위까지 일반공급에 못 미친 주택형이 있으면 미달로 표시합니다.</small></p>')
parts.append('<p style="background:#f3f6fb;border-radius:8px;padding:10px 12px;font-size:14px">📅 이번 주 청약 시리즈 · <b>수요일</b> 줍줍·로또 청약과 결과 · <b>금요일</b> 단지분석이 이어서 올라옵니다.</p>')
parts.append('<hr><p><small>자료: 한국부동산원 청약홈 APT 분양정보·경쟁률, 국토교통부 실거래가 공개시스템. '
             '청약 신청 전에는 반드시 입주자모집공고를 확인하세요. 이 글은 참고용 정보이며 투자 권유가 아닙니다.</small></p>')
LABELS = ['수도권 청약', '아파트 분양', '청약 경쟁률']
if MODE in ('tue', 'wed', 'thu', 'fri'):
    import cy_posts                                          # 수·금 글 본문 (같은 폴더)
    title, parts, LABELS = cy_posts.build(MODE, S, dict(T=T, TH=TH, THR=THR, TD=TD, TDR=TDR, man=man, md=md, esc=esc, name=name, rate=rate, gap=gap, cta=cta,
                                                        SITE=SITE, RT_SITE=RT_SITE))
    if ad_client and ad_slot:                                 # 광고는 본문 중간(두 번째 표 앞)
        parts.insert(min(4, len(parts) - 1), f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                     f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                     '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
    news = []
# 대표 이미지 (블로그 목록 썸네일·공유 미리보기용) – daily.yml 이 저장소 cards/ 에 보관한 날짜별 이미지
_key = {'mon': S['week'][0], 'tue': f"{S.get('tue')}_tue", 'wed': f"{S.get('wed')}_wed", 'thu': f"{S.get('thu')}_thu", 'fri': f"{S.get('fri')}_fri"}[MODE]
if os.path.exists(f'cards/cy/{_key}.png') and os.environ.get('GITHUB_REPOSITORY'):
    _img = f"https://raw.githubusercontent.com/{os.environ['GITHUB_REPOSITORY']}/{os.environ.get('GITHUB_REF_NAME') or 'main'}/cards/cy/{_key}.png"
    _has_img = True
    parts.insert(1 if news else 0, f'<div style="margin:0 0 18px;text-align:center"><img src="{_img}" alt="{esc(title)}" style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>')
# 이번 주 청약 당첨운 타로 (대표 이미지 바로 아래, 월요일 글만)
try:
    if MODE != 'mon': raise RuntimeError('월요일 글에만 넣음')
    from tarot import today_card, blog_html
    _t = today_card(w0, 'cy')
    parts.insert((1 if news else 0) + (1 if '_has_img' in globals() else 0),
                 blog_html(_t, f'{w0.month}.{w0.day}~{w1.month}.{w1.day} 이번 주 청약 당첨운 타로'))
except Exception as _e:
    print('타로 칸 건너뜀:', _e)
content = ''.join(parts)

if DRY:
    open(f'post_preview_cy_{MODE}.html', 'w', encoding='utf-8').write(f'<meta charset="utf-8"><h1>{esc(title)}</h1>' + content); print(title); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"
# 같은 글이 이미 있으면 새로 만들지 않고 고칩니다 (월: 주간 날짜 / 수: '줍줍' + 주차 / 금: 단지명)
if MODE == 'mon':
    key, tag = f"({w0.month}.{w0.day}~", '청약 일정'
elif MODE == 'tue':
    key, tag = title.split(' 1순위')[0], '청약 결과'
elif MODE == 'wed':
    key, tag = title.split(' 줍줍')[0], '줍줍'
elif MODE == 'thu':
    key, tag = title.split(' 당첨')[0], '커트라인'
else:
    key, tag = (S.get('pick') or {}).get('name', title), '단지분석'
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': '수도권 청약', 'fetchBodies': 'false'}), headers=H)
items = json.load(urllib.request.urlopen(q)).get('items', [])
same = [p for p in items if key in p.get('title', '') and tag in p.get('title', '') and '[수도권 청약' in p.get('title', '') and p.get('published', '')[:4] == str(w0.year)]
body = json.dumps({'title': title, 'content': content, 'labels': LABELS}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S[{'mon': 'blog_url', 'tue': 'blog_url_tue', 'wed': 'blog_url_wed', 'thu': 'blog_url_thu', 'fri': 'blog_url_fri'}[MODE]] = post.get('url')
json.dump(S, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
