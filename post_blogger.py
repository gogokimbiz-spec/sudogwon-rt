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
LB = S.get('label') or f"{d.month}월 {d.day}일({wd})"   # 월요일은 '11월 7~8일(주말)'
nh = S.get('new_highs', [])
bs = S['by_sido']
LBF = S.get('label_full') or f'{d.year}년 {LB}'

# 지역 이름 (검색어용): '서울 강남구'→'강남', '성남 분당구'→'성남 분당', '광명시'→'광명', '인천 서구'→'인천 서구'
def area_name(r):
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' and len(p[0]) > 2 else p[0]
    g = p[1][:-1] if len(p[1]) > 2 else p[1]
    return g if p[0] == '서울' else f'{p[0]} {g}'
def label_name(r):  # 블로그 라벨(지역별 모아보기): '강남구 아파트', '인천 서구 아파트', '용인 아파트'
    p = r.split(' ')
    if len(p) == 1: return (p[0][:-1] if p[0][-1] in '시군' and len(p[0]) > 2 else p[0]) + ' 아파트'
    return (p[1] if p[0] == '서울' else f'인천 {p[1]}' if p[0] == '인천' else p[0]) + ' 아파트'
from collections import Counter
def ga(w):  # 받침에 따라 '이/가'
    c = w[-1]
    return w + ('이' if '가' <= c <= '힣' and (ord(c) - 0xAC00) % 28 else '가')
_base = nh or S.get('day_trades') or []
_cnt = Counter(area_name(t['region']) for t in _base)
top_areas = [a for a, _ in sorted(_cnt.items(), key=lambda x: (-x[1], [area_name(t['region']) for t in _base].index(x[0])))][:3]
areas_txt = '·'.join(top_areas)
# 2. 검색어 중심 제목 – 그날 신고가가 많이 나온 지역 이름을 제목에 넣음
title = (f"[수도권 실거래] {LBF} 신고가 {len(nh)}건" if nh else f"[수도권 실거래] {LBF} 매매 {S['trade_count']}건") + \
        (f" | {areas_txt} 아파트 실거래가" if areas_txt else '')
# 4. 지역 라벨 (지역별 모아보기 페이지가 생겨 검색에 걸림)
labels = ['실거래', '수도권 실거래가', '아파트 실거래'] + (['신고가'] if nh else [])
for t in _base:
    ln = label_name(t['region'])
    if ln not in labels and len(labels) < 10: labels.append(ln)

T = 'style="border-collapse:collapse;width:100%;font-size:14px"'
TH = 'style="text-align:left;border-bottom:2px solid #ccc;padding:6px 4px"'
THR = 'style="text-align:right;border-bottom:2px solid #ccc;padding:6px 4px"'
TD = 'style="border-bottom:1px solid #eee;padding:6px 4px;vertical-align:top"'
TDR = 'style="border-bottom:1px solid #eee;padding:6px 4px;text-align:right;white-space:nowrap"'
RED = 'style="color:#d23c3c;font-weight:bold"'

try:
    _NM = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'names.json'), encoding='utf-8'))
    CODE = {v: k for k, v in _NM.items()}
except Exception:
    CODE = {}
def reg(name):  # 지역명에 시군구 페이지 링크
    c = CODE.get(name)
    return f'<a href="{SITE}r/{c}.html">{esc(name)}</a>' if c else esc(name)
def trade_rows(rows, with_prev=False):
    out = []
    for t in rows:
        badge = f' <span {RED}>[신고가]</span>' if t.get('new_high') else ''
        prev = f"<br><small>이전 최고 {man(t['prev_high_man'])} ({t['prev_high_date'][5:].replace('-', '.') if t['prev_high_date'][:4] == (t.get('date') or S['day'])[:4] else t['prev_high_date'][:7].replace('-', '.')})</small>" if with_prev and t.get('new_high') else ''
        out.append(f"<tr><td {TD}>{reg(t['region'])}</td><td {TD}>{esc(t['apt'])}{badge}<br><small>{esc(t['umd'])} · {t['built']}년</small></td>"
                   f"<td {TDR}>{t['area']}㎡ · {t['floor']}층</td><td {TDR}><b>{man(t['price_man'])}</b><br><small>3.3㎡당 {man(t['pp_man'])}</small>{prev}</td></tr>")
    return ''.join(out)

parts = []
# 3. 맨 위 요약 문장 (검색엔진·독자가 글 내용을 바로 알 수 있게)
HT = S.get('high_text') or '최근 6개월 최고가'                      # 신고가 비교 기준 (역대 최고가 표가 채워지면 '2006년 이후 역대 최고가')
VB = '신고된' if S.get('basis') == 'reported' else '계약된'          # 2026-11-13: 어제 새로 신고된 거래 기준
_s = [f"{LB} {VB} 수도권 아파트 매매는 {S['trade_count']}건(서울 {bs['11']} · 인천 {bs['28']} · 경기 {bs['41']}), 전세는 {S['jeonse_count']}건입니다."]
if nh:
    _a, _k = _cnt.most_common(1)[0]
    _s.append(f"이 가운데 같은 단지·같은 전용면적에서 {HT}를 넘긴 신고가 거래는 {len(nh)}건이며, {_a}에서 {_k}건으로 가장 많았습니다.")
_dt = S.get('day_trades') or []
if _dt:
    t0 = _dt[0]
    _e, _m = divmod(int(round(t0['price_man'])), 10000)
    _won = (f'{_e}억 {_m:,}만 원' if _m else f'{_e}억 원') if _e else f'{_m:,}만 원'
    _s.append(f"가장 비싸게 거래된 아파트는 {t0['region']} {t0['apt']} 전용 {t0['area']}㎡로 {_won}이었습니다.")
_u, _dn = (S.get('up5') or [None])[0], (S.get('down5') or [None])[0]
if _u and _dn:
    _s.append(f"최근 30일 3.3㎡당 매매가는 직전 30일보다 {ga(area_name(_u['region']))} {_u['chg']:+.1f}%로 가장 많이 올랐고, "
              f"{ga(area_name(_dn['region']))} {_dn['chg']:+.1f}%로 가장 많이 내렸습니다.")
summary_html = '<p style="font-size:16px;line-height:1.75;margin:0 0 18px">' + esc(' '.join(_s)) + '</p>'
# 1. 오늘의 부동산 뉴스 (맨 위)
news = S.get('news')
if news:
    parts.append('<div style="margin:4px 0 18px;padding:12px 14px;border-left:4px solid #1f5fbf;background:#f3f6fb">'
                 f"<div style=\"font-size:13px;color:#555;margin-bottom:4px\">📰 오늘의 부동산 뉴스</div>"
                 f"<a href=\"{esc(news['link'])}\" style=\"font-weight:bold;font-size:16px\">{esc(news['title'])}</a> <small>({esc(news.get('source', ''))})</small></div>")
# 2. 지도 버튼
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
# 2. 바로가기 카드 버튼
parts.append('<div style="display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 24px">'
             + cta(SITE, '🗺️', '지역별 지도로 보기', '76개 시군구 가격·변동을 한눈에', True)
             + cta(f'{SITE}r/', '📍', '우리 동네 실거래가', '시군구별 신고가·최근 거래', False) + '</div>')
# 3-0. 오늘의 주요 거래 6건 (2026-11-12 변경): 최고가 3 + 신고가 3.
#      한쪽이 모자라면(신고가가 없는 날 등) 다른 쪽으로 채워 늘 6건. 최고가이면서 신고가인 거래는 최고가 쪽에 한 번만.
_key6 = lambda t: (t['region'], t['apt'], t['area'], t.get('floor'), t['price_man'])
_top_all = sorted(S.get('day_trades') or [], key=lambda t: -t['price_man'])
_nh_all = sorted(nh, key=lambda t: -t['price_man'])
_tp = _top_all[:3]
_seen = {_key6(t) for t in _tp}
_nh6 = [t for t in _nh_all if _key6(t) not in _seen][:3]
_need = 6 - len(_tp) - len(_nh6)
if _need > 0:                                      # 신고가가 모자라면 최고가를 더
    _more = [t for t in _top_all[3:] if _key6(t) not in {_key6(x) for x in _nh6}][:_need]
    _tp += _more; _need -= len(_more)
if _need > 0:                                      # 최고가가 모자라면 신고가를 더
    _seen = {_key6(t) for t in _tp + _nh6}
    _nh6 += [t for t in _nh_all if _key6(t) not in _seen][:_need]
if _tp or _nh6:
    _GH = lambda txt: f'<tr><td colspan="4" style="padding:10px 4px 4px;font-weight:bold;border-bottom:2px solid #ccc">{txt}</td></tr>'
    _rows = (_GH(f'💰 오늘의 실거래가격 {len(_tp)}건') + trade_rows(_tp, True) if _tp else '') + \
            (_GH(f'🔺 오늘 신고가 {len(_nh6)}건') + trade_rows(_nh6, True) if _nh6 else '')
    parts.append(f"<h3>오늘의 주요 거래 {len(_tp) + len(_nh6)}건</h3><p><small>{LB} {VB} 거래 중 가장 비싸게 거래된 아파트와 신고가 거래입니다. "
                 f"신고가는 같은 단지·같은 전용면적의 {HT}보다 비싸게 팔린 거래입니다.</small></p>")
    parts.append(f"<table {T}><tr><th {TH}>지역</th><th {TH}>단지</th><th {THR}>전용·층</th><th {THR}>거래가</th></tr>{_rows}</table>")
# 3. 신고가 표
if nh:
    parts.append(f"<h3>신고가 {len(nh)}건</h3><p><small>같은 단지·같은 전용면적의 {HT}보다 비싸게 팔린 거래입니다.</small></p>")
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
             f"<p><small>{LB} {VB} 매매 {S['trade_count']}건(서울 {bs['11']} · 인천 {bs['28']} · 경기 {bs['41']}), 전세 {S['jeonse_count']}건. "
             + ("계약일이 며칠 전이어도 이 날 새로 신고된 거래를 모두 담았습니다.</small></p>" if S.get('basis') == 'reported' else "실거래는 계약 후 30일 안에 신고하므로 건수는 앞으로 늘어납니다.</small></p>"))
parts.append(f"<table {T}><tr><th {TH}>지역</th><th {TH}>단지</th><th {THR}>전용·층</th><th {THR}>거래가</th></tr>{trade_rows(S['day_trades'])}</table>")
# 6. 최근 30일 상승·하락 5곳
up = ' · '.join(f"{esc(short(x['region']))} <span style=\"color:#d23c3c\">+{x['chg']}%</span>" for x in S.get('up5', []))
dn = ' · '.join(f"{esc(short(x['region']))} <span style=\"color:#2a6fd6\">{x['chg']}%</span>" for x in S.get('down5', []))
parts.append(f"<h3>최근 30일 3.3㎡당 매매가 변동 (직전 30일 대비)</h3><p>상승: {up or '-'}<br>하락: {dn or '-'}</p>"
             "<p><small>시군구별 3.3㎡당 매매가 중앙값 비교이며, 두 기간 모두 거래 10건 이상인 지역만 집계했습니다.</small></p>"
             f'<p>👉 <a href="{SITE}r/">우리 동네 시군구별 아파트 실거래가·신고가 보기</a></p>')
# 8. 출처·고지
parts.append('<hr><p><small>자료: 국토교통부 실거래가 공개시스템(공공데이터포털 API). 해제 신고된 거래는 제외했습니다. '
             '이 글은 참고용 정보이며 투자 권유가 아닙니다.</small></p>')
# 대표 이미지 (블로그 목록 썸네일·공유 미리보기용) – daily.yml 이 저장소 cards/ 에 보관한 날짜별 이미지
_key = S['day']
if os.path.exists(f'cards/rt/{_key}.png') and os.environ.get('GITHUB_REPOSITORY'):
    _img = f"https://raw.githubusercontent.com/{os.environ['GITHUB_REPOSITORY']}/{os.environ.get('GITHUB_REF_NAME') or 'main'}/cards/rt/{_key}.png"
    _has_img = True
    parts.insert(1 if news else 0, f'<div style="margin:0 0 18px;text-align:center"><img src="{_img}" alt="{esc(title)}" style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>')
    if os.path.exists(f'cards/rt/{_key}_hero.png'):            # 오늘의 신고가 1위 카드 (2026-11-12)
        parts.insert((1 if news else 0) + 1, f'<div style="margin:0 0 18px;text-align:center"><img src="{_img[:-4]}_hero.png" alt="오늘의 신고가 1위" style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>')
# 오늘의 부동산 타로 (대표 이미지 바로 아래 – 대표 이미지가 블로그 썸네일이 되도록 타로는 그 뒤에 둠)
try:
    from tarot import today_card
    _t = today_card()
    parts.insert((1 if news else 0) + (1 if '_has_img' in globals() else 0),
        '<div id="tarot" style="margin:0 0 22px;padding:16px;border-radius:16px;background:linear-gradient(135deg,#0f2742,#1f4f8f);color:#fff;text-align:center">'
        f'<div style="font-size:13px;color:#e8b94a;font-weight:bold;letter-spacing:.02em">🔮 {_t["label"]} 오늘의 부동산 타로</div>'
        f'<img src="{_t["image"]}" alt="오늘의 부동산 타로 카드 {esc(_t["n"])}" style="width:180px;max-width:60%;height:auto;margin:10px auto 6px;display:block;border-radius:10px">'
        f'<div style="font-size:20px;font-weight:bold;color:#fff">{esc(_t["n"])} <span style="color:#e8b94a;font-size:16px">{_t["stars"]}</span></div>'
        f'<div style="font-size:12.5px;color:#b9c8dc;margin:2px 0 8px">{esc(_t["kw"])}</div>'
        f'<div style="font-size:15px;line-height:1.6;color:#fff;margin:0 auto 10px;max-width:440px">{esc(_t["msg"])}</div>'
        f'<div style="font-size:13px;color:#d6e2f2;margin-bottom:12px">행운의 층 <b style="color:#fff">{_t["luck"]["floor"]}층</b> · 행운의 방향 <b style="color:#fff">{_t["dir"]}</b> · 오늘 해보면 좋은 일 <b style="color:#fff">{esc(_t["act"])}</b></div>'
        f'<a href="{_t["url"]}" style="display:inline-block;background:#ff5c5c;color:#fff;font-weight:bold;font-size:16px;padding:11px 22px;border-radius:999px;text-decoration:none">🔮 나도 카드 뽑기 ›</a>'
        '<div style="font-size:11px;color:#93a6bf;margin-top:10px">재미로 보는 운세이며 투자 판단의 근거가 아닙니다</div></div>')
except Exception as _e:
    print('타로 칸 건너뜀:', _e)
parts.insert(1 if news else 0, summary_html)
content = ''.join(parts)

if DRY:
    open('post_preview.html', 'w', encoding='utf-8').write(f'<h1>{esc(title)}</h1>' + content); print(title); print('라벨:', labels); sys.exit(0)

tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
    'client_id': env['BLOGGER_CLIENT_ID'], 'client_secret': env['BLOGGER_CLIENT_SECRET'],
    'refresh_token': env['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()))['access_token']
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'}
API = f"https://www.googleapis.com/blogger/v3/blogs/{env['BLOGGER_BLOG_ID']}/posts"

# 같은 날짜 글이 이미 있으면 새로 만들지 않고 고칩니다
key = (S.get('label_full') or f"{d.year}년 {d.month}월 {d.day}일").split('(')[0]
q = urllib.request.Request(API + '/search?' + urllib.parse.urlencode({'q': key, 'fetchBodies': 'false'}), headers=H)
items = json.load(urllib.request.urlopen(q)).get('items', [])
same = [p for p in items if key in p.get('title', '') and ('수도권 아파트 실거래' in p.get('title', '') or '[수도권 실거래]' in p.get('title', ''))]
body = json.dumps({'title': title, 'content': content, 'labels': labels}).encode()
if same:
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/{same[0]['id']}", data=body, headers=H, method='PUT'))
else:
    r = urllib.request.urlopen(urllib.request.Request(API, data=body, headers=H, method='POST'))
post = json.load(r)
print('게시 완료:', post.get('url'))
S['blog_url'] = post.get('url')
json.dump(S, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
