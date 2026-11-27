"""국평 한 채 = 연봉 몇 년? – 토허제 40곳 (2026-11-27 시안)
사용법: python make_cards_toheo_years.py OUT raw.json
  - 왼쪽: 아파트 평단가 지도 (make_cards_toheo_ppmap.py 와 같음, pp_4w.json)
  - 오른쪽: 국평(전용 84㎡ = 25.4평) 값 ÷ 평균 연봉 = 몇 년, 높은 순 40곳
"""
import os, json, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
_s = open(os.path.join(HERE, 'make_cards_toheo_ppmap.py'), encoding='utf-8').read()
_s = _s[:_s.index('im, d = C.canvas()')]
__file__ = os.path.join(HERE, 'make_cards_toheo_ppmap.py')
exec(compile(_s, 'make_cards_toheo_ppmap.py', 'exec'))

PY84 = 84 / 3.3058                                   # 전용 84㎡ = 25.4평
RI = json.load(open(os.path.join(HERE, 'rest_inc_pp.json'), encoding='utf-8'))
LIVE = None
if os.environ.get('YEARS_LIVE') == '1':                # 게시 당일 최근 4주 평단가로 갱신 (daily 가 배포한 trend/summary.json)
    try:
        import urllib.request
        LIVE = json.load(urllib.request.urlopen('https://gogokimbiz-spec.github.io/sudogwon-rt/trend/summary.json', timeout=30))['week']
        lp = {r['code']: r['pp_cur'] for r in LIVE['rows']}
        for r in rows:
            if r['code'] in lp: r['pp'] = lp[r['code']]
        for c in RI['pp']:
            if c in lp: RI['pp'][c] = lp[c]
        _pc = [datetime.date.fromisoformat(x) for x in LIVE['cur']]
        print('평단가 갱신:', LIVE['cur'])
    except Exception as e:
        print('::warning::평단가 갱신 실패 – 저장된 값 사용:', e)
for r in rows:
    r['price84'] = r['pp'] * PY84                    # 만원
    r['years'] = r['price84'] / r['income']
RN = {'28125': '제물포', '28155': '영종', '28177': '미추홀', '28185': '연수', '28200': '남동', '28237': '부평', '28245': '계양', '28275': '서구', '28290': '검단',
      '41113': '권선', '41150': '의정부', '41171': '만안', '41192': '원미', '41194': '소사', '41196': '오정', '41220': '평택', '41250': '동두천',
      '41271': '상록', '41273': '단원', '41281': '덕양', '41285': '일산동', '41287': '일산서', '41360': '남양주', '41370': '오산', '41390': '시흥',
      '41410': '군포', '41461': '처인', '41480': '파주', '41500': '이천', '41550': '안성', '41570': '김포', '41591': '만세', '41593': '효행',
      '41595': '병점', '41610': '광주', '41630': '양주'}
for r in rows: r['toheo'] = True
for c in RI['pp']:
    pr = RI['pp'][c] * PY84
    rows.append(dict(code=c, short=RN[c], name=RN[c], pp=RI['pp'][c], income=RI['income'][c], price84=pr, years=pr / RI['income'][c], toheo=False))
yr = sorted(rows, key=lambda r: -r['years'])
YR_EDGES = [10, 13, 16, 20, 24, 28, 34]                # 년 – 오래 걸릴수록 빨강, 짧을수록 파랑
def yr_color(v): return (DNC[::-1] + UPC)[sum(v >= e for e in YR_EDGES)]


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


def draw_map3(im, box, colfn):
    geo = json.load(open(os.path.join(HERE, 'geo.json'), encoding='utf-8'))
    val = {r['code']: r for r in rows}
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
        col = colfn(val[c]) if c in val else OFF
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
        cx, cy = centroid(best); t = r['short']; col = colfn(r)
        f = F(19 if len(t) <= 2 else 15, 'Black') if (a > 3500 or r['toheo']) else F(14, 'Black')
        dx, dy = NUDGE.get(t, (0, 0)) if r['toheo'] else (0, 0)
        tw = d.textlength(t, font=f); tx = min(max(cx + dx * 0.9 - tw / 2, 2), bw - tw - 2); ty = min(max(cy + dy * 0.9 - 11, 2), bh - 24)
        d.text((tx, ty), t, font=f, fill=on(col))
    im.paste(layer, (box[0], box[1]))


def eok(v):                                          # 만원 → '31.9억'
    return f'{v / 10000:.1f}억'


im, d = C.canvas(); ink = C.INK
d.rectangle((40, 28, W - 40, 34), fill=ink); d.line((40, 40, W - 40, 40), fill=ink, width=2)
d.text((44, 50), f'{TODAY.year}년 {TODAY.month}월 {TODAY.day}일  ·  실거래 {_pc[0].month}/{_pc[0].day}~{_pc[1].month}/{_pc[1].day} · 국토교통부 · 국세청',
       font=F(21, 'Medium'), fill=C.INK2)
d.line((40, 86, W - 40, 86), fill=ink, width=1)
d.text((40, 96), '이 동네 연봉으로 이 동네 집 사려면?', font=FS(58, 'Black'), fill=ink)
d.line((40, 206, W - 40, 206), fill=ink, width=2); d.rectangle((40, 212, W - 40, 218), fill=ink)

mid = W // 2; GW = 5; L0 = 12
MW = mid - GW - L0; MH = int(MW * 1.345) + 12
MT = 316; MB_ = MT + MH
d.text((40, 230), '몇 년 걸릴까', font=FS(40, 'Black'), fill=ink)
d.text((42, 276), '국평(84㎡) 값 ÷ 그 동네 평균 연봉', font=F(19, 'Medium'), fill=C.INK2)
d.text((mid + 16, 230), '오래 걸리는 순', font=FS(40, 'Black'), fill=ink)
draw_map3(im, (L0, MT, mid - GW, MB_), lambda r: yr_color(r['years']))
yr = [r for r in yr if r['code'] in VIS]
d = ImageDraw.Draw(im)
d.text((mid + 18, 276), f'단위: 년 · 지도 속 {len(yr)}곳 · 한 푼도 안 쓸 때', font=F(19, 'Medium'), fill=C.INK2)
d = ImageDraw.Draw(im)
d.line((mid, 232, mid, 1230), fill=C.T['line'], width=2)
legend2(d, 50, MB_ + 12, DNC[::-1] + UPC, '10년 미만', '34년 이상', '20년')
# 평단가 아래: 한 줄 요약
d.text((50, MB_ + 74), '가장 오래 걸리는 곳', font=F(19, 'Medium'), fill=C.INK2)
d.text((50, MB_ + 100), f"{yr[0]['short']} {yr[0]['years']:.1f}년", font=FS(40, 'Black'), fill=C.UP)
d.text((50, MB_ + 156), f"가장 짧은 곳 {yr[-1]['short']} {yr[-1]['years']:.1f}년", font=FS(26, 'Bold'), fill=C.DOWN)

# 오른쪽: 보이는 지역 전체 3열 (순위 · 이름 · 년)
X0, X1 = mid + 14, W - 36; GAP = 10; NC = 3; colw = (X1 - X0 - GAP * (NC - 1)) / NC
top, bot = 316, 1234; per = -(-len(yr) // NC); rh = (bot - top) / per
vmax = yr[0]['years']
for i, r in enumerate(yr):
    c = i // per; cx = X0 + c * (colw + GAP); cy = top + (i % per) * rh
    if i % per: d.line((cx, cy, cx + colw, cy), fill=C.T['line'], width=1)
    col = yr_color(r['years'])
    d.rectangle((cx, cy + 4, cx + (colw - 2) * r['years'] / vmax, cy + rh - 4), fill=C.T['card'])
    rf = F(14, 'Medium'); rs = str(i + 1)
    d.text((cx + 22 - d.textlength(rs, font=rf), cy + (rh - 14) / 2 - 3), rs, font=rf, fill=C.INK2)
    d.rectangle((cx + 26, cy + rh / 2 - 5, cx + 35, cy + rh / 2 + 4), fill=col)
    d.text((cx + 39, cy + (rh - 18) / 2 - 5), r['short'], font=FS(18, 'Bold'), fill=ink)
    t = f"{r['years']:.1f}"; tf = F(18, 'Black')
    d.text((cx + colw - 2 - d.textlength(t, font=tf), cy + (rh - 18) / 2 - 5), t, font=tf, fill=C.UP if i < 10 else ink)
d.line((40, 1244, W - 40, 1244), fill=ink, width=2)
d.text((44, 1252), '84㎡ 값 = 최근 4주 실거래 평단가 × 25.4평 · 연봉 = 국세청 1인당 평균 총급여(사는 곳, 2024년 귀속 · 인천은 2023년, 경기 일반구는 시 값)',
       font=F(16, 'Medium'), fill=C.INK2)
d.line((40, 1290, W - 40, 1290), fill=ink, width=2)
C.footer(d, F, '자료 국토교통부 실거래가 · 국세청 국세통계')
import random
random.seed(7); g_ = Image.effect_noise((W // 2, SH // 2), 18).resize((W, SH)).convert('L')
im = Image.composite(im, Image.blend(im, Image.new('RGB', (W, SH), (120, 100, 70)), 0.06), g_.point(lambda v: 255 if v > 120 else 200))
im.save(os.path.join(OUT, 'card_years.png')); print('카드 →', os.path.join(OUT, 'card_years.png'))
print([(r['short'], round(r['years'], 1), eok(r['price84'])) for r in yr])


# ─────────────────────────── 게시용 meta.json (YEARS_SLUG 가 있으면 – special.yml 의 make 단계에서 실행) ───────────────────────────
SLUG = os.environ.get('YEARS_SLUG')
if SLUG:
    import html as _h
    mp = os.path.join('special', SLUG, 'meta.json'); M = json.load(open(mp, encoding='utf-8'))
    th = 'style="padding:6px 8px;border-bottom:2px solid #222;text-align:{}"'; td = 'style="padding:6px 8px;border-bottom:1px solid #ddd;text-align:{}"'
    tb = ('<table style="width:100%;border-collapse:collapse;font-size:15px"><tr>' + ''.join(f'<th {th.format(a)}>{h}</th>' for h, a in
          (('순위', 'center'), ('지역', 'left'), ('국평(84㎡) 값', 'right'), ('평균 연봉', 'right'), ('걸리는 시간', 'right'), ('토허제', 'center'))) + '</tr>'
          + ''.join(f'<tr><td {td.format("center")}>{i}</td><td {td.format("left")}>{_h.escape(r["name"])}</td><td {td.format("right")}>{eok(r["price84"])}</td>'
                    f'<td {td.format("right")}>{r["income"]:,}만</td><td {td.format("right")}><b>{r["years"]:.1f}년</b></td>'
                    f'<td {td.format("center")}>{"●" if r["toheo"] else ""}</td></tr>' for i, r in enumerate(yr, 1)) + '</table>')
    t3 = ', '.join(f"{r['name']} {r['years']:.1f}년" for r in yr[:3]); b3 = ', '.join(f"{r['name']} {r['years']:.1f}년" for r in yr[-3:][::-1])
    SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
    M['title'] = f"[이 동네 연봉으로 이 동네 집 사려면?] 국평 한 채 = 연봉 몇 년 | 1위 {yr[0]['name']} {yr[0]['years']:.1f}년 · 가장 짧은 {yr[-1]['name']} {yr[-1]['years']:.1f}년"
    M['blog_html'] = ('<div style="margin:0 0 16px;text-align:center"><img src="{IMG}" alt="이 동네 연봉으로 이 동네 집 사려면 몇 년 걸릴까 지도" style="width:100%;max-width:540px;height:auto;border-radius:6px"></div>'
        f'<p style="font-size:16px;line-height:1.8">그 동네에 사는 직장인의 평균 연봉을 한 푼도 쓰지 않고 모으면, 같은 동네 국평(전용 84㎡) 아파트 한 채를 사는 데 몇 년이 걸릴까요? '
        f'수도권 {len(yr)}개 시·구를 계산해 보니 가장 오래 걸리는 곳은 <b style="color:#b3261e">{t3}</b>, 가장 짧은 곳은 <b style="color:#1f4e9c">{b3}</b>였습니다.</p>'
        f'<p style="font-size:16px;line-height:1.8">국평 값은 최근 4주({_pc[0].month}/{_pc[0].day}~{_pc[1].month}/{_pc[1].day}) 아파트 매매 실거래의 3.3㎡당 중앙값에 25.4평(84㎡)을 곱했고, '
        '연봉은 국세청이 공개한 사는 곳 기준 1인당 평균 총급여입니다.</p>{AD}'
        f'<h3>수도권 {len(yr)}개 시·구 – 국평 한 채에 연봉 몇 년? (오래 걸리는 순)</h3>' + tb +
        f'<p style="margin:20px 0"><a href="{SITE}" style="display:inline-block;padding:12px 18px;border-radius:8px;background:#1e1914;color:#efe3c8;font-weight:bold;text-decoration:none">🏠 수도권 아파트 실거래가 지도 보기 ›</a></p>'
        '<hr><p><small>국평 값 = 국토교통부 아파트 매매 실거래(해제 제외) 3.3㎡당 중앙값 × 25.4평. 거래가 적은 곳은 값이 크게 움직일 수 있습니다.<br>'
        '연봉 = 국세청 국세통계 「시·군·구별 근로소득 연말정산 신고현황(주소지)」 1인당 평균 총급여. 서울·경기는 2024년 귀속, 인천은 2023년 귀속(2026년 개편 구는 옛 구 값). '
        '경기 일반구는 따로 나오지 않아 소속 시 값을 씀. 세금·생활비를 빼지 않은 단순 계산입니다.<br>참고용 정보이며 투자 판단의 책임은 본인에게 있습니다.</small></p>')
    M['kakao_title'] = '🏠 이 동네 연봉으로 이 동네 집 사려면?'
    M['kakao_desc'] = f"국평 한 채 = 연봉 몇 년\n1위 {yr[0]['short']} {yr[0]['years']:.1f}년 · 가장 짧은 {yr[-1]['short']} {yr[-1]['years']:.1f}년"
    M['kakao_button'] = f'{len(yr)}곳 전체 보기'
    M['caption'] = '\n'.join(['🏠 이 동네 연봉으로 이 동네 집 사려면? | 국평 한 채 = 연봉 몇 년', '',
                               '⏳ 오래 걸리는 곳'] + [f"· {r['short']} {r['years']:.1f}년 ({eok(r['price84'])})" for r in yr[:5]] + ['',
                               '⚡ 짧은 곳'] + [f"· {r['short']} {r['years']:.1f}년 ({eok(r['price84'])})" for r in yr[-3:][::-1]] + ['',
                               '국평(84㎡) 값 ÷ 그 동네 평균 연봉, 한 푼도 안 쓸 때', '',
                               '자료: 국토교통부 실거래가(최근 4주) · 국세청 근로소득 연말정산(사는 곳) · 참고용 정보', '',
                               f'{len(yr)}곳 전체 표는 프로필 링크에서 👆', '',
                               f"#데이터로보는재테크 #내집마련 #연봉 #{yr[0]['short']} #{yr[-1]['short']}"])
    M['labels'] = ['내집마련', '연봉', '평단가', '아파트값', '토허제']
    json.dump(M, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('meta.json 갱신 →', mp)
