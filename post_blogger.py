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
def trade_rows(rows, with_prev=False, rank=None):
    out = []
    for t in rows:
        rk = f'<b>{rank[id(t)]}위</b> ' if rank and id(t) in rank else ''
        badge = f' <span {RED}>[신고가]</span>' if t.get('new_high') else ''
        prev = f"<br><small>이전 최고 {man(t['prev_high_man'])} ({t['prev_high_date'][5:].replace('-', '.') if t['prev_high_date'][:4] == (t.get('date') or S['day'])[:4] else t['prev_high_date'][:7].replace('-', '.')})</small>" if with_prev and t.get('new_high') else ''
        out.append(f"<tr><td {TD}>{rk}{reg(t['region'])}</td><td {TD}>{esc(t['apt'])}{badge}<br><small>{esc(t['umd'])} · {t['built']}년</small></td>"
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
# 3-0. 오늘의 주요 거래 (2026-11-18 변경 – 한 장 카드와 같은 규칙): 실거래가격 5 + 신고가 5.
#      가격순 5위마다 1건(1~5위 중 1, 6~10위 중 1 …), 같은 구는 1건만. 건수가 적으면 구간을 좁히고, 한쪽이 모자라면 다른 쪽으로 채워 10건.
_key6 = lambda t: (t['region'], t['apt'], t['area'], t.get('floor'), t['price_man'])
_top_all = sorted(S.get('day_trades_60') or S.get('day_trades') or [], key=lambda t: -t['price_man'])
_nh_all = sorted(nh, key=lambda t: -t['price_man'])
_EACH, _STEP, _used, _RANK = 5, 5, set(), {}
def _stp(pool): return max(1, min(_STEP, len(pool) // _EACH))
def _pick(pool, n, skip=(), start=0):
    out, b, st = [], start, _stp(pool)
    while len(out) < n and b * st < len(pool):
        for i in range(b * st, min((b + 1) * st, len(pool))):
            t = pool[i]
            if t['region'] in _used or _key6(t) in skip: continue
            out.append(t); _used.add(t['region']); _RANK[id(t)] = i + 1; break
        b += 1
    return out
_tp = _pick(_top_all, _EACH)
_nh6 = _pick(_nh_all, _EACH, {_key6(x) for x in _tp})
if len(_tp) + len(_nh6) < _EACH * 2:
    _last = lambda xs, pool: (max(_RANK.get(id(x), 0) for x in xs) - 1) // _stp(pool) + 1 if xs else 0
    if len(_nh6) < _EACH: _tp += _pick(_top_all, _EACH * 2 - len(_tp) - len(_nh6), {_key6(x) for x in _tp + _nh6}, _last(_tp, _top_all))
    else: _nh6 += _pick(_nh_all, _EACH * 2 - len(_tp) - len(_nh6), {_key6(x) for x in _tp + _nh6}, _last(_nh6, _nh_all))
    _tp.sort(key=lambda t: _RANK.get(id(t), 0)); _nh6.sort(key=lambda t: _RANK.get(id(t), 0))
if _tp or _nh6:
    _GH = lambda txt: f'<tr><td colspan="4" style="padding:10px 4px 4px;font-weight:bold;border-bottom:2px solid #ccc">{txt}</td></tr>'
    _rows = (_GH(f'💰 오늘의 실거래가격 {len(_tp)}건') + trade_rows(_tp, True, _RANK) if _tp else '') + \
            (_GH(f'🔺 오늘 신고가 {len(_nh6)}건') + trade_rows(_nh6, True, _RANK) if _nh6 else '')
    parts.append(f"<h3>오늘의 주요 거래 {len(_tp) + len(_nh6)}건</h3><p><small>{LB} {VB} 거래와 신고가를 가격순으로 줄 세워 5위마다 1건씩, 같은 구는 1건만 골랐습니다(앞의 숫자가 순위). "
                 f"신고가는 같은 단지·같은 전용면적의 {HT}보다 비싸게 팔린 거래입니다.</small></p>")
    parts.append(f"<table {T}><tr><th {TH}>지역</th><th {TH}>단지</th><th {THR}>전용·층</th><th {THR}>거래가</th></tr>{_rows}</table>")

# 3-1. 오늘 숫자 읽기 + 알아두면 좋은 점 (2026-11-26 애드센스 '가치가 낮은 콘텐츠' 거절 대응)
#      표·이미지만 있던 글에 그날 숫자로 만든 해설 문단을 넣음. 날마다 숫자·지역·단지가 달라 문장도 매일 달라짐.
def _won(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}만 원' if m else f'{e}억 원') if e else f'{m:,}만 원'
def _jo(w, a, b):  # 받침 있으면 a, 없으면 b
    c = w[-1]
    return w + (a if '가' <= c <= '힣' and (ord(c) - 0xAC00) % 28 else b)
_ins = []
_G = [g for g in (S.get('groups') or []) if g.get('trade_count')]
if _G:
    _r = lambda g: g['nh_count'] / g['trade_count'] * 100
    _gl_txt = ', '.join(f"{g['name']} {g['trade_count']}건" for g in _G)
    _t = f"권역별로 보면 {_gl_txt}이 새로 신고됐어요."
    if nh and len(_G) > 1:
        _gh, _gl = max(_G, key=_r), min(_G, key=_r)
        _t += f" 거래 가운데 신고가 비율은 {_jo(_gh['name'], '이', '가')} {_r(_gh):.0f}%({_gh['nh_count']}/{_gh['trade_count']}건)로 가장 높았고, {_jo(_gl['name'], '은', '는')} {_r(_gl):.0f}%로 가장 낮았어요."
    _ins.append(_t)
_med, _jm = S.get('trade_median_man'), S.get('jeonse_median_man')
if _med and _top_all:
    _t0 = _top_all[0]
    _t = f"이날 신고된 매매의 중간 가격(중앙값)은 {_won(_med)}이에요. 가장 비싼 거래인 {_t0['region']} {_t0['apt']} 전용 {_t0['area']}㎡({_won(_t0['price_man'])})는 중간 가격의 약 {_t0['price_man'] / _med:.0f}배였어요."
    if _jm:
        _t += f" 같은 날 전세의 중간 가격은 {_won(_jm)}으로, 매매 중간 가격의 {_jm / _med * 100:.0f}% 수준이에요. 단지가 서로 달라 정확한 전세가율은 아니고, 시장 분위기를 보는 참고 숫자예요."
    _ins.append(_t)
_nhp = [t for t in nh if t.get('prev_high_man')]
if len(_nhp) >= 3:
    _jump = lambda t: (t['price_man'] / t['prev_high_man'] - 1) * 100
    _js = sorted(_jump(t) for t in _nhp)
    _mj = _js[len(_js) // 2]
    _small = sum(1 for v in _js if v <= 1)
    _t = f"신고가 {len(nh)}건이 이전 최고가보다 얼마나 올랐는지 보면, 중간값은 {_mj:.1f}%예요."
    if _small:
        _t += f" 이전 최고가와 1% 이내 차이로 아슬아슬하게 넘긴 거래가 {_small}건이라, 신고가라도 가격이 크게 뛴 건 아닌 경우가 많아요."
    _cut = (d - datetime.timedelta(days=365 * 3)).isoformat()
    _recent = [t for t in _nhp if (t.get('prev_high_date') or '') >= _cut]
    if _recent:
        _b = max(_recent, key=_jump)
        _t += (f" 최근 3년 안의 기록을 가장 크게 넘어선 곳은 {_b['region']} {_b['apt']} 전용 {_b['area']}㎡로, "
               f"{_b['prev_high_date'][:4]}년 {int(_b['prev_high_date'][5:7])}월 최고가 {_won(_b['prev_high_man'])}보다 {_won(_b['price_man'] - _b['prev_high_man'])} 높은 {_won(_b['price_man'])}에 거래됐어요.")
    _old = len(_nhp) - len(_recent)
    if _old:
        _t += f" 3년 넘게 깨지지 않던 기록을 넘은 거래도 {_old}건 있었어요."
    _ins.append(_t)
if len(nh) >= 3:
    _sm = sum(1 for t in nh if t['area'] <= 60); _md = sum(1 for t in nh if 60 < t['area'] <= 85); _lg = len(nh) - _sm - _md
    _new = sum(1 for t in nh if t.get('built') and t['built'] >= d.year - 10)
    _old30 = sum(1 for t in nh if t.get('built') and t['built'] <= d.year - 30)
    _t = f"신고가를 면적별로 나누면 전용 60㎡ 이하 {_sm}건, 60~85㎡ {_md}건, 85㎡ 초과 {_lg}건이에요. 준공 10년 이내 새 아파트는 {_new}건({_new / len(nh) * 100:.0f}%)이고"
    _t += f", 준공 30년이 넘은 단지도 {_old30}건이에요." if _old30 else ', 준공 30년이 넘은 단지는 없었어요.'
    if _old30:
        _t += " 오래된 단지의 신고가는 집 자체보다 재건축 기대가 가격에 반영된 경우가 많아요."
    _ins.append(_t)
_u, _dn = (S.get('up5') or [None])[0], (S.get('down5') or [None])[0]
if _u and abs(_u['chg']) >= 10:
    _ins.append(f"맨 위 요약의 30일 변동({area_name(_u['region'])} {_u['chg']:+.1f}%)처럼 10%가 넘는 숫자는 조심해서 봐야 해요. 30일 변동은 거래가 적은 지역일수록 비싼 거래 몇 건에 크게 흔들려요. "
                "한 번의 큰 숫자보다 다음 주에도 같은 방향이 이어지는지 함께 보는 게 좋아요.")
_TIPS = [
    ('실거래는 30일 안에 신고해요', '아파트를 사고팔면 계약일로부터 30일 안에 신고해요. 그래서 오늘 올라온 거래 중에는 몇 주 전에 계약한 것도 섞여 있어요. 표의 계약일을 함께 보면 언제 시장 분위기인지 알 수 있어요.'),
    ('신고가 1건만으로 시세를 판단하지 마세요', '신고가는 같은 단지·같은 면적에서 이전보다 비싸게 팔린 한 건의 기록이에요. 층·향·리모델링 여부에 따라 한 건만 튈 수 있어요. 같은 단지에서 비슷한 가격의 거래가 이어지는지가 더 중요해요.'),
    ('해제된 거래는 뺐어요', '실거래로 신고됐다가 나중에 계약이 취소되면 해제 신고가 올라와요. 이 블로그는 해제된 거래를 모두 뺐어요. 가격을 띄우려고 신고만 하고 취소하는 경우도 있어서, 해제 여부는 꼭 확인해야 해요.'),
    ('전용면적과 공급면적은 달라요', '흔히 말하는 34평은 공급면적 기준이고, 실거래 자료의 84㎡는 전용면적이에요. 같은 단지라도 면적이 다르면 가격을 바로 비교할 수 없어서, 신고가도 같은 전용면적끼리만 비교했어요.'),
    ('3.3㎡당 가격으로 비교해요', '3.3㎡당 가격은 거래가를 전용면적으로 나누고 3.3을 곱한 값으로, 흔히 말하는 평당 가격이에요. 크기가 다른 아파트나 지역끼리 비교할 때 써요. 다만 전용면적 기준이라 분양 광고의 평당 가격과는 다를 수 있어요.'),
    ('직거래와 가족 간 거래는 가격이 다를 수 있어요', '중개사를 거치지 않은 직거래나 가족끼리의 거래는 시세보다 훨씬 싸거나 비싸게 신고되기도 해요. 주변 거래와 동떨어진 가격이 보이면 그런 거래인지 의심해 볼 만해요.'),
    ('호가와 실거래가는 달라요', '부동산 앱의 매물 가격은 집주인이 원하는 호가예요. 실거래가는 실제로 계약된 가격이라 호가보다 낮은 경우가 많아요. 집을 알아볼 때는 같은 단지의 최근 실거래가부터 확인하세요.'),
]
_tip = _TIPS[d.weekday()]
if _ins:
    parts.append('<h3>오늘 숫자 읽기</h3>' + ''.join(f'<p style="font-size:15.5px;line-height:1.75">{esc(x)}</p>' for x in _ins))
parts.append(f'<h3>알아두면 좋은 점: {esc(_tip[0])}</h3><p style="font-size:15.5px;line-height:1.75">{esc(_tip[1])}</p>')
# 3. 신고가 표
if nh:
    _nh50 = _nh_all[:50]                           # 2026-11-18: 신고가가 하루 100~200건이라 표는 가격 상위 50건만
    parts.append(f"<h3>신고가 {len(nh)}건" + (f" (가격 상위 {len(_nh50)}건)" if len(nh) > len(_nh50) else '') +
                 f"</h3><p><small>같은 단지·같은 전용면적의 {HT}보다 비싸게 팔린 거래입니다.</small></p>")
    parts.append(f"<table {T}><tr><th {TH}>지역</th><th {TH}>단지</th><th {THR}>전용·층</th><th {THR}>거래가</th></tr>{trade_rows(_nh50, True)}</table>")
    if len(nh) > len(_nh50):
        parts.append(f'<p><small>나머지 신고가 {len(nh) - len(_nh50)}건은 <a href="{SITE}r/">시군구별 실거래가 페이지</a>에서 지역별로 볼 수 있습니다.</small></p>')
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
    _rg = [i for i in range(1, 5) if os.path.exists(f'cards/rt/{_key}_r{i}.png')]   # 권역별 카드 5장 (2026-11-18)
    if _rg:
        _gn = {i + 1: g['name'] for i, g in enumerate(S.get('groups') or [])}
        parts.insert((1 if news else 0) + 1, '<h3>권역별 실거래 (서울 · 경기 북부 · 인천·경기 남서부 · 경기 남동부)</h3>' + ''.join(
            f'<div style="margin:0 0 14px;text-align:center"><img src="{_img[:-4]}_r{i}.png" alt="{esc(_gn.get(i, ""))} 아파트 실거래 {esc(LB)}" loading="lazy" style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>'
            for i in _rg))
    if os.path.exists(f'cards/rt/{_key}_hero.png'):            # 오늘의 신고가 1위 카드 (2026-11-12)
        parts.insert((1 if news else 0) + 1, f'<div style="margin:0 0 18px;text-align:center"><img src="{_img[:-4]}_hero.png" alt="오늘의 신고가 1위" style="width:100%;max-width:540px;height:auto;border-radius:12px"></div>')
# (타로 칸은 2026-11-18 사용자 요청으로 블로그 글에서 뺌)
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
