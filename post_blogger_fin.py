"""기업재무 주간 글 (GitHub Actions 용). 입력: site/fin/summary.json
오늘 올릴 글은 build_fin.py 가 summary.json 의 post 에 정해 둡니다.
- 화·금요일: 순위 글 (영업이익률·ROE·매출성장률·부채비율·영업이익증가율·흑자전환 을 돌아가며), 라벨 '기업재무'
- 기업 재무정보만 사용 (주가 자료는 이용 조건상 쓰지 않음)
사용법: python post_blogger_fin.py site/fin/summary.json [--dry]
필요한 환경변수: BLOGGER_BLOG_ID, BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN (실거래 글과 같은 값)
"""
import os, sys, json, datetime, urllib.request, urllib.parse, html

KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
DRY = '--dry' in sys.argv
S = json.load(open(sys.argv[1], encoding='utf-8'))
P = S.get('post')
if not P:
    print('오늘은 기업재무 글이 없습니다 (화·금요일만)'); sys.exit(0)
kind = P['kind']
env = {k: os.environ.get(k, '').strip() for k in ['BLOGGER_BLOG_ID', 'BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN']}
if not DRY and not all(env.values()):
    print('블로거 설정값이 없어 게시를 건너뜁니다.'); sys.exit(0)

SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
esc = html.escape
WD = '월화수목금토일'
FY = S['fy']
mon = today - datetime.timedelta(days=today.weekday())
nth = (mon.day - 1) // 7 + 1


def won(v):
    if v is None: return '-'
    s = '-' if v < 0 else ''; v = abs(v)
    if v >= 1e12:
        j, e = divmod(round(v / 1e8), 10000)
        return f'{s}{j:,}조 {e:,}억' if e else f'{s}{j:,}조'
    return f'{s}{round(v / 1e8):,}억'


fmt = {'opm': lambda v: f'{v:.1f}%', 'roe': lambda v: f'{v:.1f}%', 'dr': lambda v: f'{v:,.0f}%',
       'gr': lambda v: f'{v:+.1f}%', 'opg': lambda v: f'{v:+.1f}%', 'op': won, 'sales': won, 'ni': won}
F = lambda k, v: '-' if v is None else fmt[k](v)
HEAD = {'opm': '영업이익률', 'roe': 'ROE', 'dr': '부채비율', 'gr': '매출 증가율', 'opg': '영업이익 증가율', 'op': '영업이익', 'sales': '매출', 'ni': '순이익'}
T = 'style="border-collapse:collapse;width:100%;font-size:14px"'
TH = 'style="text-align:left;border-bottom:2px solid #ccc;padding:6px 4px"'
THR = 'style="text-align:right;border-bottom:2px solid #ccc;padding:6px 4px"'
TD = 'style="border-bottom:1px solid #eee;padding:6px 4px"'
TDR = 'style="border-bottom:1px solid #eee;padding:6px 4px;text-align:right;white-space:nowrap"'


def table(rows, cols):
    head = f'<tr><th {TH}>#</th><th {TH}>기업</th>' + ''.join(f'<th {THR}>{HEAD[c]}</th>' for c in cols) + (f'<th {THR}>매출</th>' if 'sales' not in cols else '') + '</tr>'
    body = ''.join(f"<tr><td {TD}>{i}</td><td {TD}><b>{esc(x['name'])}</b> <small style=\"color:#888\">{'코스피' if x['market'] == 'KOSPI' else '코스닥'}</small></td>"
                   + ''.join(f'<td {TDR}>{"<b>" if j == 0 else ""}{F(c, x[c])}{"</b>" if j == 0 else ""}</td>' for j, c in enumerate(cols))
                   + (f'<td {TDR}>{won(x["sales"])}</td>' if 'sales' not in cols else '') + '</tr>' for i, x in enumerate(rows, 1))
    return f'<table {T}>{head}{body}</table>'


R = S['rank']
THEMES = [('opm', ['opm', 'op'], '영업이익률 높은 기업 TOP 20', '매출 대비 영업이익 비율이 높은 순서입니다. 매출 500억 원 이상, 금융업 제외.'),
          ('roe', ['roe', 'ni'], 'ROE 높은 기업 TOP 20', 'ROE(자기자본이익률) = 당기순이익 ÷ 자본총계. 자기 돈으로 얼마나 이익을 냈는지 보여 줍니다. 매출 500억 원 이상, 금융업 제외.'),
          ('growth', ['gr', 'sales'], '매출 성장률 높은 기업 TOP 20', f'{FY}년 매출을 직전 연도와 비교했습니다. 직전 연도 매출 100억 원 이상, 금융업 제외.'),
          ('low_debt', ['dr', 'opm'], '부채비율 낮은 기업 TOP 20', '부채총계 ÷ 자본총계. 낮을수록 재무구조가 안정적입니다. 매출 500억 원 이상, 금융업 제외.'),
          ('opg', ['opg', 'op'], '영업이익 증가율 높은 기업 TOP 20', f'{FY}년 영업이익을 직전 연도와 비교했습니다. 직전 연도 영업이익 50억 원 이상, 금융업 제외.'),
          ('turn', ['op', 'opm'], '영업이익 흑자전환 기업', f'직전 연도 영업적자에서 {FY}년 영업흑자로 돌아선 기업입니다. 금융업 제외.')]
parts = []
key, cols, name, note = next(t for t in THEMES if t[0] == P['keys'][0])
title = f'[기업재무] {name} – 상장사 매출 상위 500 ({FY} 사업연도)'
label = '기업재무'
rows = R[key]
parts.append(f'<p>코스피·코스닥 상장사 중 {FY} 사업연도 매출 상위 500개 기업의 재무제표로 정리한 <b>{name}</b>입니다. {note}</p>')
if rows:
    x = rows[0]
    parts.append(f"<p>1위는 <b>{esc(x['name'])}</b>({F(cols[0], x[cols[0]])})이고, 상위 {len(rows)}곳 중 코스피 {sum(r['market'] == 'KOSPI' for r in rows)}곳, 코스닥 {sum(r['market'] != 'KOSPI' for r in rows)}곳입니다.</p>")
parts.append(table(rows, cols))
key_title = f'[기업재무] {name}'

parts.insert(0, f'<div style="margin:8px 0 20px"><a href="{SITE}fin/" style="display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:14px;text-decoration:none;'
                'background:linear-gradient(135deg,#1f5fbf,#3b82f6);color:#fff"><span style="font-size:26px">📊</span><span style="flex:1"><b style="display:block;font-size:16px">상장사 매출 상위 500 전체 표 보기</b>'
                '<small style="color:#e8f0ff">영업이익률·ROE·부채비율·성장률 · 검색·정렬</small></span><b>보기 ›</b></a></div>')
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
if ad_client and ad_slot:
    parts.insert(3, f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                    f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                    '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
parts.append('<hr><p><small>계산: 연결재무제표 우선(없으면 별도), 당기순이익·자본총계에 비지배지분 포함이라 증권사 발표 수치와 다를 수 있습니다. 대상은 코스피·코스닥 상장사 중 매출 상위 500곳. '
             '자료: 금융위원회 기업 재무정보·기업기본정보(공공데이터포털). '
             '이 글은 공개 데이터를 정리한 참고 자료이며 특정 종목의 매수·매도를 권유하지 않습니다. 투자 판단과 책임은 본인에게 있습니다.</small></p>')
# 대표 이미지 (daily.yml 이 저장소 cards/fin/ 에 보관한 카드)
if os.path.exists(f"cards/fin/{S['day']}.png") and os.environ.get('GITHUB_REPOSITORY'):
    _img = f"https://raw.githubusercontent.com/{os.environ['GITHUB_REPOSITORY']}/{os.environ.get('GITHUB_REF_NAME') or 'main'}/cards/fin/{S['day']}.png"
    parts.insert(0, f'<div style="margin:0 0 18px;text-align:center"><img src="{_img}" alt="{esc(title)}" style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>')
content = ''.join(parts)

if DRY:
    open('post_preview_fin.html', 'w', encoding='utf-8').write(f'<meta charset="utf-8"><h1>{esc(title)}</h1>' + content)
    print('미리보기:', title); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': label, 'fetchBodies': 'false'}), headers=H)
items = json.load(urllib.request.urlopen(q)).get('items', [])
# 같은 주 같은 글이 있으면 수정 (재실행해도 중복 글 없음)
same = [p for p in items if p.get('title', '').startswith(key_title) and p.get('published', '')[:10] >= (today - datetime.timedelta(days=2)).isoformat()]
body = json.dumps({'title': title, 'content': content, 'labels': [label, '재테크', '기업분석']}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S['blog_url'] = post.get('url'); S['title'] = title
json.dump(S, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
