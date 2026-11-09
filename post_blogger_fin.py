"""기업재무 주간 글 (GitHub Actions 용). 입력: site/fin/summary.json
오늘 올릴 글은 build_fin.py 가 summary.json 의 post 에 정해 둡니다.
- 화요일: 순위 글 (영업이익률 → 부채비율 → 매출성장률 → 흑자전환 을 주마다 돌아가며), 라벨 '기업재무'
- 금요일: 저평가 지표 글 (PER·PBR 낮은 20곳), 라벨 '저평가 지표'
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
bd = datetime.date.fromisoformat(S['basDt'])
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


fmt = {'per': lambda v: f'{v:,.1f}배', 'pbr': lambda v: f'{v:.2f}배', 'opm': lambda v: f'{v:.1f}%',
       'dr': lambda v: f'{v:,.0f}%', 'gr': lambda v: f'{v:+.1f}%', 'op': won, 'sales': won, 'cap': won}
F = lambda k, v: '-' if v is None else fmt[k](v)
HEAD = {'per': 'PER', 'pbr': 'PBR', 'opm': '영업이익률', 'dr': '부채비율', 'gr': '매출 증가율', 'op': '영업이익', 'sales': '매출'}
T = 'style="border-collapse:collapse;width:100%;font-size:14px"'
TH = 'style="text-align:left;border-bottom:2px solid #ccc;padding:6px 4px"'
THR = 'style="text-align:right;border-bottom:2px solid #ccc;padding:6px 4px"'
TD = 'style="border-bottom:1px solid #eee;padding:6px 4px"'
TDR = 'style="border-bottom:1px solid #eee;padding:6px 4px;text-align:right;white-space:nowrap"'


def table(rows, cols):
    head = f'<tr><th {TH}>#</th><th {TH}>기업</th>' + ''.join(f'<th {THR}>{HEAD[c]}</th>' for c in cols) + f'<th {THR}>시가총액</th></tr>'
    body = ''.join(f"<tr><td {TD}>{i}</td><td {TD}><b>{esc(x['name'])}</b> <small style=\"color:#888\">{'코스피' if x['market'] == 'KOSPI' else '코스닥'}</small></td>"
                   + ''.join(f'<td {TDR}>{"<b>" if j == 0 else ""}{F(c, x[c])}{"</b>" if j == 0 else ""}</td>' for j, c in enumerate(cols))
                   + f'<td {TDR}>{won(x["cap"])}</td></tr>' for i, x in enumerate(rows, 1))
    return f'<table {T}>{head}{body}</table>'


R = S['rank']
THEMES = [('opm', ['opm', 'op'], '영업이익률 높은 기업 TOP 20', '매출 대비 영업이익 비율이 높은 순서입니다. 매출 500억 원 이상, 금융업 제외.'),
          ('low_debt', ['dr', 'opm'], '부채비율 낮은 기업 TOP 20', '부채총계 ÷ 자본총계. 낮을수록 재무구조가 안정적입니다. 매출 500억 원 이상, 금융업 제외.'),
          ('growth', ['gr', 'sales'], '매출 성장률 높은 기업 TOP 20', f'{FY}년 매출을 직전 연도와 비교했습니다. 직전 연도 매출 100억 원 이상, 금융업 제외.'),
          ('turn', ['op', 'opm'], '영업이익 흑자전환 기업', f'직전 연도 영업적자에서 {FY}년 영업흑자로 돌아선 기업입니다. 금융업 제외.')]
parts = []
if kind == 'rank':
    key, cols, name, note = next(t for t in THEMES if t[0] == P['keys'][0])
    title = f'[기업재무] {name} – 시가총액 상위 500 기준 ({FY} 사업연도)'
    label = '기업재무'
    rows = R[key]
    parts.append(f'<p>코스피·코스닥 시가총액 상위 500개 기업의 {FY} 사업연도 재무제표로 정리한 <b>{name}</b>입니다. {note}</p>')
    if rows:
        x = rows[0]
        parts.append(f"<p>1위는 <b>{esc(x['name'])}</b>({F(cols[0], x[cols[0]])})이고, 상위 {len(rows)}곳 중 코스피 {sum(r['market'] == 'KOSPI' for r in rows)}곳, 코스닥 {sum(r['market'] != 'KOSPI' for r in rows)}곳입니다.</p>")
    parts.append(table(rows, cols))
    key_title = f'[기업재무] {name}'
else:
    title = f'[저평가 지표] {mon.month}월 {nth}주차 PER·PBR 낮은 기업 20곳 ({bd.month}.{bd.day} 종가 기준)'
    label = '저평가 지표'
    parts.append(f'<p>시가총액 상위 500개 기업의 PER(주가수익비율)과 PBR(주가순자산비율)을 {bd.month}월 {bd.day}일({WD[bd.weekday()]}) 종가와 {FY} 사업연도 재무제표로 계산했습니다. '
                 '수치가 낮다고 해서 반드시 저평가라는 뜻은 아니며, 업종 특성과 일회성 이익을 함께 봐야 합니다.</p>')
    parts.append(f'<h3>PER 낮은 20곳</h3>{table(R["low_per"], ["per", "pbr"])}')
    parts.append('<p><small>PER = 시가총액 ÷ 당기순이익. 적자 기업은 제외됩니다.</small></p>')
    parts.append(f'<h3>PBR 낮은 20곳</h3>{table(R["low_pbr"], ["pbr", "per"])}')
    parts.append('<p><small>PBR = 시가총액 ÷ 자본총계. 1배 미만이면 장부상 순자산보다 시가총액이 작다는 뜻입니다.</small></p>')
    key_title = f'[저평가 지표] {mon.month}월 {nth}주차'

parts.insert(0, f'<div style="margin:8px 0 20px"><a href="{SITE}fin/" style="display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:14px;text-decoration:none;'
                'background:linear-gradient(135deg,#1f5fbf,#3b82f6);color:#fff"><span style="font-size:26px">📊</span><span style="flex:1"><b style="display:block;font-size:16px">시가총액 상위 500 전체 표 보기</b>'
                '<small style="color:#e8f0ff">PER·PBR·영업이익률·부채비율 매일 갱신 · 검색·정렬</small></span><b>보기 ›</b></a></div>')
ad_client, ad_slot = os.environ.get('ADSENSE_CLIENT', '').strip(), os.environ.get('ADSENSE_SLOT', '').strip()
if ad_client and ad_slot:
    parts.insert(3, f'<div style="margin:24px 0"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_client}" crossorigin="anonymous"></script>'
                    f'<ins class="adsbygoogle" style="display:block" data-ad-client="{ad_client}" data-ad-slot="{ad_slot}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
                    '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
parts.append('<hr><p><small>계산: 연결재무제표 우선(없으면 별도), 당기순이익·자본총계에 비지배지분 포함이라 증권사 발표 수치와 다를 수 있습니다. 보통주 기준, 스팩 제외. '
             '자료: 금융위원회 주식시세정보·KRX상장종목정보·기업 재무정보(공공데이터포털). '
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
same = [p for p in items if p.get('title', '').startswith(key_title) and p.get('published', '')[:10] >= mon.isoformat()]
body = json.dumps({'title': title, 'content': content, 'labels': [label, '재테크', '주식']}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S['blog_url'] = post.get('url'); S['title'] = title
json.dump(S, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
