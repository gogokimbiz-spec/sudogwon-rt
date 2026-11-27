"""매매 vs 전세 · 수도권 주간 지도 (2026-11-27, 매주 화요일 13시 rent.yml)
사용법: python make_cards_toheo_rent.py --fetch-only rent_raw.json   (부동산원 자료만 받기 – 표준 라이브러리, PC 실행기 대비)
        python make_cards_toheo_rent.py OUT rent_raw.json             (카드 + special/<기준일>_rent/meta.json – post_special.py 로 게시)
  - 왼쪽: 부동산원 (주) 매매가격지수 T244183132827305, 오른쪽: (주) 전세가격지수 T247713133046872 – 전주 대비
  - 지도 범위 = 토허제 40곳 경계 상자 그대로, 그 안에 보이는 시·구(약 66곳) 모두 색칠
  - rent_raw.json: {'m': {CLS_ID: [[주, 조사일, 지수], ...]}, 'j': {...}}
"""
import os, sys, json, time, datetime, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
KST = datetime.timezone(datetime.timedelta(hours=9)); TODAY_ = datetime.datetime.now(KST).date()
TBL = {'m': 'T244183132827305', 'j': 'T247713133046872'}
# 토허제 40곳 밖 (geo.json 코드: (짧은 이름, R-ONE CLS_ID)) – 2026 인천·화성 개편 반영 (인천 서구 = R-ONE 서해구)
REST = {'28125': ('제물포', 50261), '28155': ('영종', 50262), '28177': ('미추홀', 50254), '28185': ('연수', 50127), '28200': ('남동', 50128),
        '28237': ('부평', 50129), '28245': ('계양', 50130), '28275': ('서구', 50263), '28290': ('검단', 50264), '41113': ('권선', 50085),
        '41150': ('의정부', 50120), '41171': ('만안', 50073), '41192': ('원미', 50094), '41194': ('소사', 50095), '41196': ('오정', 50096),
        '41220': ('평택', 50098), '41250': ('동두천', 50121), '41271': ('상록', 50100), '41273': ('단원', 50101), '41281': ('덕양', 50115),
        '41285': ('일산동', 50116), '41287': ('일산서', 50117), '41360': ('남양주', 50107), '41370': ('오산', 50102), '41390': ('시흥', 50103),
        '41410': ('군포', 50075), '41461': ('처인', 50089), '41480': ('파주', 50253), '41500': ('이천', 50111), '41550': ('안성', 50081),
        '41570': ('김포', 50118), '41591': ('만세', 50256), '41593': ('효행', 50257), '41595': ('병점', 50258), '41610': ('광주', 50109),
        '41630': ('양주', 50122)}
TOHEO_CLS = [50043, 50044, 50045, 50047, 50048, 50049, 50050, 50051, 50052, 50053, 50054, 50056, 50057, 50058, 50060, 50061, 50062, 50063,
             50064, 50065, 50066, 50067, 50068, 50069, 50070, 50071, 50074, 50076, 50078, 50079, 50080, 50084, 50086, 50087, 50090, 50091,
             50097, 50106, 50108, 50259]
ALL_CLS = TOHEO_CLS + [c for _, c in REST.values()] + [50008, 50016]


def wk_id(d):
    y, w, _ = d.isocalendar(); return f'{y}{w:02d}'


def fetch():
    """지역마다 매매·전세 최근 4~5주 (키 없으면 sample 5건이라 기간을 좁혀 한 번씩). 하나씩 천천히, 3번 실패하면 종료(→ PC 실행기)"""
    out = {'m': {}, 'j': {}}
    start, end = wk_id(TODAY_ - datetime.timedelta(days=28)), wk_id(TODAY_)
    for k, tid in TBL.items():
        for c in ALL_CLS:
            q = {'Type': 'json', 'STATBL_ID': tid, 'DTACYCLE_CD': 'WK', 'CLS_ID': c, 'START_WRTTIME': start, 'END_WRTTIME': end}
            if os.environ.get('REB_KEY'): q.update(KEY=os.environ['REB_KEY'], pIndex=1, pSize=100)
            url = 'https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do?' + urllib.parse.urlencode(q)
            for n in range(3):
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as r:
                        j = json.loads(r.read().decode('utf-8'))
                    rows = j['SttsApiTblData'][1].get('row', []) if 'SttsApiTblData' in j else []
                    out[k][str(c)] = sorted([x['WRTTIME_IDTFR_ID'], x['WRTTIME_DESC'], x['DTA_VAL']] for x in rows); break
                except Exception as e:
                    print('  다시 시도', k, c, e); time.sleep(4 + n * 6)
            else:
                raise SystemExit(f'R-ONE 응답 없음 ({k} {c}) – 접속이 막힌 것 같습니다')
            time.sleep(0.3)
    return out


if sys.argv[1] == '--fetch-only':
    R = fetch(); json.dump(R, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
    n = sum(len(v) >= 2 for t in R.values() for v in t.values()); print(f'R-ONE 매매·전세 {n}/{2 * len(ALL_CLS)}곳'); sys.exit(0 if n > len(ALL_CLS) else 1)

RAW = json.load(open(sys.argv[2], encoding='utf-8'))
OUT_ = sys.argv[1]; os.makedirs(OUT_, exist_ok=True)
# make_cards_toheo.py 형식 raw (매매) 로 바꿔 카드 체인(글꼴·색·지도 함수·토허제 rows)을 그대로 씀
tmp_raw = os.path.join(OUT_, 'toheo_raw_from_rent.json')
json.dump([[int(c), '', wk, desc, v] for c, a in RAW['m'].items() for wk, desc, v in a], open(tmp_raw, 'w', encoding='utf-8'))
sys.argv = [sys.argv[0], OUT_, tmp_raw]
os.environ['TOHEO_MAX_AGE'] = os.environ.get('RENT_MAX_AGE') or '10'     # 화요일 기준 최신 조사일(월)은 8일 전
_s = open(os.path.join(HERE, 'make_cards_toheo_incmap.py'), encoding='utf-8').read()
_s = _s[:_s.index('im, d = C.canvas()')]
__file__ = os.path.join(HERE, 'make_cards_toheo_incmap.py')
exec(compile(_s, 'make_cards_toheo_incmap.py', 'exec'))


def wchg(k, c):
    a = {wk: v for wk, _, v in RAW[k].get(str(c), [])}
    return round((a[last] / a[prev] - 1) * 100, 2) if last in a and prev in a else None


cid_of = {c: cid for c, _, _, cid in REGIONS}
for r in rows: r['jchg'] = wchg('j', cid_of[r['code']])
ALL = [dict(code=r['code'], name=r['name'], short=r['short'], chg=r['chg'], jchg=r['jchg'], toheo=True) for r in rows if r['jchg'] is not None] + \
      [dict(code=g, name=nm, short=nm, chg=wchg('m', c), jchg=wchg('j', c), toheo=False) for g, (nm, c) in REST.items()
       if wchg('m', c) is not None and wchg('j', c) is not None]
jx = {'서울': wchg('j', 50008), '경기': wchg('j', 50016)}


def clip(poly, w, h):
    """Sutherland–Hodgman: 다각형을 지도 상자 안으로 자름"""
    for edge in range(4):
        out = []
        inside = [lambda p: p[0] >= 0, lambda p: p[0] <= w, lambda p: p[1] >= 0, lambda p: p[1] <= h][edge]
        def X(a, b):
            if edge < 2:
                x = 0 if edge == 0 else w; t = (x - a[0]) / (b[0] - a[0]); return (x, a[1] + t * (b[1] - a[1]))
            y = 0 if edge == 2 else h; t = (y - a[1]) / (b[1] - a[1]); return (a[0] + t * (b[0] - a[0]), y)
        for i in range(len(poly)):
            a, b = poly[i - 1], poly[i]
            if inside(b):
                if not inside(a): out.append(X(a, b))
                out.append(b)
            elif inside(a): out.append(X(a, b))
        poly = out
        if not poly: return []
    return poly


def area(q): return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(q, q[1:] + q[:1]))) / 2


VIS = set()


def draw_map3(im, box, key):
    """보이는 지역 모두 색칠 + 이름 (토허제 40곳 경계 상자 그대로)"""
    geo = json.load(open(os.path.join(HERE, 'geo.json'), encoding='utf-8'))
    val = {r['code']: r for r in ALL}
    polys = {}
    for f in geo['features']:
        g = f['geometry']; polys[f['properties']['c']] = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    pts = [p for c in val if val[c]['toheo'] for pl in polys.get(c, []) for p in pl[0]]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts); y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    kx = math.cos(math.radians((y0 + y1) / 2)); bw, bh = box[2] - box[0], box[3] - box[1]; pad = 6
    s_ = min((bw - 2 * pad) / ((x1 - x0) * kx), (bh - 2 * pad) / (y1 - y0))
    ox = (bw - (x1 - x0) * kx * s_) / 2; oy = (bh - (y1 - y0) * s_) / 2
    P = lambda p: (ox + (p[0] - x0) * kx * s_, oy + (y1 - p[1]) * s_)
    layer = Image.new('RGB', (bw, bh), C.T['bg']); d = ImageDraw.Draw(layer)
    for c, pl in polys.items():
        col = color(val[c][key]) if c in val else OFF
        for poly in pl: d.polygon([P(p) for p in poly[0]], fill=col)
    for c, pl in polys.items():
        for poly in pl:
            q = [P(p) for p in poly[0]]; d.line(q + [q[0]], fill=C.T['bg'], width=2)
    for c, r in val.items():
        if c not in polys: continue
        best = max((clip([P(p) for p in poly[0]], bw, bh) for poly in polys[c]), key=lambda q: area(q) if len(q) > 2 else 0)
        if len(best) < 3: continue
        a = area(best)
        if a > 200: VIS.add(c)
        if a < 1400: continue
        cx, cy = centroid(best); t = r['short']; col = color(r[key])
        f = F(19 if len(t) <= 2 else 15, 'Black') if (a > 3500 or r['toheo']) else F(14, 'Black')
        dx, dy = NUDGE.get(t, (0, 0)) if r['toheo'] else (0, 0)
        tw = d.textlength(t, font=f); tx = min(max(cx + dx * 0.9 - tw / 2, 2), bw - tw - 2); ty = min(max(cy + dy * 0.9 - 11, 2), bh - 24)
        d.text((tx, ty), t, font=f, fill=on(col))
    im.paste(layer, (box[0], box[1]))



im, d = C.canvas()
ink = C.INK
d.rectangle((40, 28, W - 40, 34), fill=ink); d.line((40, 40, W - 40, 40), fill=ink, width=2)
wd = '월화수목금토일'[pub_day.weekday()]
d.text((44, 50), f'{pub_day.year}년 {pub_day.month}월 {pub_day.day}일 ({wd})  ·  {base_day.month}월 {base_day.day}일 조사 · 한국부동산원 · 전주 대비',
       font=F(21, 'Medium'), fill=C.INK2)
d.line((40, 86, W - 40, 86), fill=ink, width=1)
d.text((40, 96), '매매 vs 전세 · 수도권 주간', font=FS(70, 'Black'), fill=ink)
d.line((40, 206, W - 40, 206), fill=ink, width=2); d.rectangle((40, 212, W - 40, 218), fill=ink)

mid = W // 2; GW = 5; L0, R1 = 12, W - 12
MW = mid - GW - L0; MH = int(MW * 1.345) + 12
MT = 316; MB_ = MT + MH
titles = ['매매 상승률', '전세 상승률']
subs = [f"{label} · 서울 {pc(extra['서울'])} · 경기 {pc(extra['경기'])}", f"{label} · 서울 {pc(jx['서울'])} · 경기 {pc(jx['경기'])}"]
for k in range(2):
    x0 = 40 if k == 0 else mid + 16
    d.text((x0, 230), titles[k], font=FS(40, 'Black'), fill=ink)
    d.text((x0 + 2, 276), subs[k], font=F(19, 'Medium'), fill=C.INK2)
draw_map3(im, (L0, MT, mid - GW, MB_), 'chg')
draw_map3(im, (mid + GW, MT, R1, MB_), 'jchg')
d = ImageDraw.Draw(im)
d.line((mid, 232, mid, MB_ + 150), fill=C.T['line'], width=2)
for x in (50, mid + 30): legend2(d, x, MB_ + 12, DNC[::-1] + [FLAT] + UPC, '하락', '상승', '보합')
for k, (t1, key) in enumerate((('매매 많이 오른 곳', 'chg'), ('전세 많이 오른 곳', 'jchg'))):
    x = 50 if k == 0 else mid + 30; xr = mid - 30 if k == 0 else W - 50
    d.text((x, MB_ + 72), t1, font=F(19, 'Medium'), fill=C.INK2)
    for i, r in enumerate(sorted([r for r in ALL if r['code'] in VIS], key=lambda r: -r[key])[:3]):
        y = MB_ + 102 + i * 35
        d.text((x, y), f'{i + 1}', font=F(22, 'Black'), fill=C.INK2)
        d.text((x + 30, y - 4), r['short'], font=FS(26, 'Black'), fill=ink)
        t = pc(r[key]); tf = F(25, 'Black')
        d.text((xr - d.textlength(t, font=tf), y - 2), t, font=tf, fill=C.UP if r[key] > 0 else C.DOWN)
SH_ = [r for r in ALL if r['code'] in VIS]; n_j = sum(r['jchg'] > 0 for r in SH_); n_m = sum(r['chg'] > 0 for r in SH_)
d.line((40, 1244, W - 40, 1244), fill=ink, width=2)
d.text((44, 1252), f"지도 속 {len(SH_)}개 시·구 중 전세 오른 곳 {n_j}곳 · 매매 오른 곳 {n_m}곳 · 한국부동산원 (주) 매매·전세가격지수",
       font=F(17, 'Medium'), fill=C.INK2)
d.line((40, 1290, W - 40, 1290), fill=ink, width=2)
C.footer(d, F, '자료 한국부동산원 주간아파트가격동향')
import random
random.seed(7); g_ = Image.effect_noise((W // 2, SH // 2), 18).resize((W, SH)).convert('L')
im = Image.composite(im, Image.blend(im, Image.new('RGB', (W, SH), (120, 100, 70)), 0.06), g_.point(lambda v: 255 if v > 120 else 200))
im.save(os.path.join(OUT, 'card_rent.png')); print('카드 →', os.path.join(OUT, 'card_rent.png'))


# ─────────────────────────── 게시용 meta.json (post_special.py 가 블로그·카톡·인스타·스레드에 올림) ───────────────────────────
import html as _html
SHOWN = [r for r in ALL if r['code'] in VIS]
slug = f'{base_day.isoformat()}_rent'
tm = sorted(SHOWN, key=lambda r: -r['chg']); tj = sorted(SHOWN, key=lambda r: -r['jchg'])
nm_ = lambda r: r['name'] if r['toheo'] else r['short']
col_ = lambda v: '#b3261e' if v > 0 else '#1f4e9c' if v < 0 else '#555'
th = 'style="padding:6px 8px;border-bottom:2px solid #222;text-align:{}"'; td = 'style="padding:6px 8px;border-bottom:1px solid #ddd;text-align:{}"'
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
tb = ('<table style="width:100%;border-collapse:collapse;font-size:15px"><tr>'
      + ''.join(f'<th {th.format(a)}>{h}</th>' for h, a in (('순위', 'center'), ('지역', 'left'), ('전세', 'right'), ('매매', 'right'), ('토허제', 'center'))) + '</tr>'
      + ''.join(f'<tr><td {td.format("center")}>{i}</td><td {td.format("left")}>{_html.escape(nm_(r))}</td>'
                f'<td {td.format("right")}><b style="color:{col_(r["jchg"])}">{pc(r["jchg"])}</b></td>'
                f'<td {td.format("right")}><span style="color:{col_(r["chg"])}">{pc(r["chg"])}</span></td>'
                f'<td {td.format("center")}>{"●" if r["toheo"] else ""}</td></tr>' for i, r in enumerate(tj, 1)) + '</table>')
body = (f'<div style="margin:0 0 16px;text-align:center"><img src="{{IMG}}" alt="수도권 아파트 매매·전세 주간 변동률 지도 – {label}" style="width:100%;max-width:540px;height:auto;border-radius:6px"></div>'
        f'<p style="font-size:16px;line-height:1.8">한국부동산원 {base_day.month}월 {base_day.day}일 조사({label}) 주간 아파트 가격을 보면, 지도 속 수도권 {len(SHOWN)}개 시·구 가운데 '
        f'<b>전세는 {n_j}곳, 매매는 {n_m}곳</b>이 올랐습니다. 서울은 매매 {pc(extra["서울"])} · 전세 {pc(jx["서울"])}, 경기는 매매 {pc(extra["경기"])} · 전세 {pc(jx["경기"])}입니다.</p>'
        f'<p style="font-size:16px;line-height:1.8">전세가 가장 많이 오른 곳은 <b style="color:#b3261e">{_html.escape(nm_(tj[0]))} {pc(tj[0]["jchg"])}</b>, '
        f'{_html.escape(nm_(tj[1]))} {pc(tj[1]["jchg"])}, {_html.escape(nm_(tj[2]))} {pc(tj[2]["jchg"])}이고, 매매는 <b style="color:#b3261e">{_html.escape(nm_(tm[0]))} {pc(tm[0]["chg"])}</b>, '
        f'{_html.escape(nm_(tm[1]))} {pc(tm[1]["chg"])}, {_html.escape(nm_(tm[2]))} {pc(tm[2]["chg"])} 순입니다. 매매가 가장 많이 내린 곳은 {_html.escape(nm_(tm[-1]))} {pc(tm[-1]["chg"])}입니다.</p>'
        '{AD}' f'<h3>수도권 {len(SHOWN)}개 시·구 전세·매매 주간 변동률 (전세 오른 순)</h3>' + tb
        + f'<p style="margin:20px 0"><a href="{SITE}" style="display:inline-block;padding:12px 18px;border-radius:8px;background:#1e1914;color:#efe3c8;font-weight:bold;text-decoration:none">🏠 수도권 아파트 실거래가 지도 보기 ›</a></p>'
        f'<hr><p><small>자료: 한국부동산원 주간아파트가격동향 (주) 매매·전세가격지수 ({base_day.month}월 {base_day.day}일 조사, {pub_day.month}월 {pub_day.day}일 발표). '
        '변동률 = 이번 주 지수 ÷ 지난주 지수 − 1. 지도 범위는 토지거래허가구역(토허제) 40곳이 들어가는 상자이며, ● 표시가 토허제 지역입니다.<br>참고용 정보이며 투자 판단의 책임은 본인에게 있습니다.</small></p>')
cap = '\n'.join([f'🗺️ 매매 vs 전세 · 수도권 주간 아파트값 | {label}', '',
                 f'· 서울 매매 {pc(extra["서울"])} · 전세 {pc(jx["서울"])}', f'· 경기 매매 {pc(extra["경기"])} · 전세 {pc(jx["경기"])}', '',
                 '🏠 전세 많이 오른 곳'] + [f"· {r['short']} {pc(r['jchg'])}" for r in tj[:3]] + ['',
                 '📈 매매 많이 오른 곳'] + [f"· {r['short']} {pc(r['chg'])}" for r in tm[:3]] + ['',
                 f'지도 속 {len(SHOWN)}곳 중 전세 오른 곳 {n_j} · 매매 오른 곳 {n_m}', '',
                 f'자료: 한국부동산원 주간아파트가격동향({base_day.month}/{base_day.day} 조사) · 참고용 정보', '', '전체 표는 프로필 링크에서 👆', '',
                 f"#데이터로보는재테크 #전세 #아파트값 #{tj[0]['short']} #{tm[0]['short']}"])
meta = dict(slug=slug, post_at=TODAY_.isoformat() + 'T00:00', make=['python', '-c', 'pass'], out=os.path.join(OUT_, 'card_rent.png'),
            title=f"[매매·전세 주간] 수도권 아파트값 ({label}) | 전세 1위 {nm_(tj[0])} {pc(tj[0]['jchg'])} · 매매 1위 {nm_(tm[0])} {pc(tm[0]['chg'])}",
            labels=['매매·전세 주간', '전세', '아파트값', '주간아파트가격동향', '토허제'], blog_html=body,
            kakao_title=f'🗺️ 매매 vs 전세 · 수도권 주간 ({label})',
            kakao_desc=f"서울 매매 {pc(extra['서울'])} · 전세 {pc(jx['서울'])}\n전세 1위 {tj[0]['short']} {pc(tj[0]['jchg'])} · 매매 1위 {tm[0]['short']} {pc(tm[0]['chg'])}",
            kakao_button='전체 표 보기', caption=cap)
os.makedirs(os.path.join('special', slug), exist_ok=True)
json.dump(meta, open(os.path.join('special', slug, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(os.path.join(OUT_, 'slug.txt'), 'w').write(slug)
print('게시 준비 →', os.path.join('special', slug, 'meta.json')); print(cap)
