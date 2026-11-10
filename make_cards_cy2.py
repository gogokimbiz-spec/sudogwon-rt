"""수요일(줍줍·로또·결과)·토요일(단지분석) 청약 인스타 캐러셀 카드(1080×1350)를 만듭니다 (GitHub Actions 용).
사용법: python make_cards_cy2.py site/cheongyak/summary.json site/cheongyak/cards_wed --mode=wed
        python make_cards_cy2.py site/cheongyak/summary.json site/cheongyak/cards_sat --mode=sat
결과: <출력폴더>/01.png … NN.png, single.png(=01), latest.png, caption.txt
디자인은 card_style.py(월요일 청약·실거래 카드와 같은 테마)를 씁니다.
"""
import sys, os, glob, json, datetime, shutil, statistics, re
from PIL import ImageFont
import card_style as C

S = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT, '[0-9][0-9].png')): os.remove(f)
MODE = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--mode=')), 'wed')
W, SH = C.W, C.SH
INK, INK2, RED, BLUE = C.INK, C.INK2, C.UP, C.DOWN


def font_path(weight):
    for pat in [f'/usr/share/fonts/**/NotoSansCJK-{weight}.ttc', f'/usr/share/fonts/**/NotoSansCJKkr-{weight}.otf', f'/usr/share/fonts/**/*CJK*{weight}*']:
        hits = glob.glob(pat, recursive=True)
        if hits: return hits[0]
    raise SystemExit('한글 폰트(Noto Sans CJK)를 찾지 못했습니다')
_fc = {}
def F(size, weight='Bold'):
    if (size, weight) in _fc: return _fc[size, weight]
    p = font_path(weight); f = None
    if p.endswith('.ttc'):
        for i in range(10):
            try:
                g = ImageFont.truetype(p, size, index=i)
                if 'KR' in g.getname()[0]: f = g; break
            except Exception: break
    _fc[size, weight] = f or ImageFont.truetype(p, size)
    return _fc[size, weight]
def man(v):
    if v is None: return '-'
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}' if m else f'{e}억') if e else f'{m:,}'
def fit(d, s, font, maxw):
    while d.textlength(s, font=font) > maxw and len(s) > 4: s = s.rstrip('…')[:-1] + '…'
    return s
def city(r):
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' and len(p[0]) > 2 else p[0]
    if p[0] in ('서울', '인천'): return p[1][:-1] if len(p[1]) > 2 else p[1]
    return p[0]
def shortn(n, c):
    n = re.sub(r'^(서울|인천|경기)\s*', '', n)
    return n[len(c):].strip() if n.startswith(c) and len(n) > len(c) + 2 else n
D = lambda s: datetime.date.fromisoformat(s[:10])
WD = '월화수목금토일'
md = lambda s: f"{D(s).month}.{D(s).day}({WD[D(s).weekday()]})"
sg = lambda g: f"{'+' if g > 0 else ''}{g:.0f}%"
pages = []


def page(pill, title, big, sub, rows, draw_row, cta, foot, rh_max=150, extra_top=0, reserve=0):
    im, d = C.canvas()
    C.header(d, F, pill, title, big, sub)
    top, bottom = 340 + extra_top, SH - 175 - reserve
    n = max(1, len(rows)); rh = min(rh_max, (bottom - top) // n)
    y = top
    for i, x in enumerate(rows):
        C.row_box(d, y, rh - 14); draw_row(d, x, i, y, y + (rh - 14) // 2, rh); y += rh
    C.cta(d, F, cta); C.footer(d, F, foot)
    pages.append(im)
    return d, y


def right(d, s, font, y, col=None):
    d.text((W - 64 - d.textlength(s, font=font), y), s, font=font, fill=col or INK)


def name_row(d, x0, cy, chip_txt, name, sub, maxw_right):
    cw = C.chip(d, F, x0, cy - 52, chip_txt)
    nf = F(38, 'Black'); nx = x0 + cw + 14
    d.text((nx, cy - 57), fit(d, name, nf, W - 64 - nx - maxw_right), font=nf, fill=INK)
    d.text((x0, cy + 2), sub, font=F(27, 'Medium'), fill=INK2)


# ───────────────────────── 수요일 ─────────────────────────
def wed():
    zz = S.get('zz') or []; z0, z1 = S['zz_range']
    rng = f"{D(z0).month}.{D(z0).day} ~ {D(z1).month}.{D(z1).day} 접수"
    foot = '자료 청약홈 · 분양가 단위 만원 · 청약 전 모집공고 확인'
    # 1) 줍줍
    rows = (zz[:6] if len(zz) > 7 else zz[:7]) or [None]
    def zrow(d, x, i, y, cy, rh):
        if x is None:
            d.text((64, cy - 30), '이 기간 수도권 줍줍이 없어요', font=F(42, 'Black'), fill=INK); return
        c = city(x['region'])
        when = md(x['r0']) + ('' if x['r0'] == x['r1'] else '~' + md(x['r1'])[-5:])
        name_row(d, 64, cy, c, shortn(x['name'], c), f"{when} · {x['kind']} {x['units']}세대", 280)
        if x.get('p_min'):
            right(d, man(x['p_min']) + ('~' if x['p_max'] != x['p_min'] else ''), F(44, 'Black'), cy - 58)
            right(d, '분양가(만원)', F(26, 'Medium'), cy + 4, INK2)
        elif x.get('orig_pp'):
            right(d, man(x['orig_pp']) + '만', F(44, 'Black'), cy - 58)
            right(d, '원 공고 3.3㎡당', F(26, 'Medium'), cy + 4, INK2)
        else:
            right(d, '공고 확인', F(34, 'Black'), cy - 50, INK2)
    d, y = page(rng, '이번 주 줍줍', f'{len(zz)}곳', '무순위·임의공급 · 가점 없이 추첨 (자격은 공고마다 다름)', rows, zrow,
                '줍줍 일정·모집공고 → 프로필 링크', foot, rh_max=128, reserve=44 if len(zz) > 7 else 0)
    if len(zz) > 7: d.text((64, y + 2), f'외 {len(zz) - 6}곳은 프로필 링크에서', font=F(28, 'Medium'), fill=INK2)
    # 2) 로또 TOP 5
    c5 = S.get('cheap5') or []
    if c5:
        def crow(d, x, i, y, cy, rh):
            C.badge(d, F, 60, cy, i + 1, 30, i == 0)
            c = city(x['region'])
            st = f" · {x['rate']:.1f}:1 {x['status']}" if 'rate' in x else ''
            nf = F(38, 'Black'); d.text((136, cy - 57), fit(d, shortn(x['name'], c), nf, W - 64 - 136 - 260), font=nf, fill=INK)
            d.text((136, cy + 2), f"{x['region']}{st}", font=F(27, 'Medium'), fill=INK2)
            right(d, sg(x['gap_new']), F(48, 'Black'), cy - 62, BLUE)
            right(d, f"3.3㎡ {man(x['pp_man'])}만", F(26, 'Medium'), cy + 4, INK2)
        page('최근 6개월 · 민영', '시세보다 싼 분양', 'TOP5', '분양가 vs 같은 시군구 신축(10년 내) 매매 시세', c5, crow,
             '전체 순위·지도 → 프로필 링크', '주변 신축 매매 3.3㎡당 중앙값 비교 · 전용면적 기준')
    # 3) 결과
    rs = [x for x in (S.get('results') or []) if 'rate' in x][:6]
    if rs:
        a, b = S['results_range']
        def rrow(d, x, i, y, cy, rh):
            c = city(x['region'])
            name_row(d, 64, cy, c, shortn(x['name'], c), f"{md(x['date'])} 1순위 · 일반 {x['general']}세대 · {x.get('apps', 0):,}건", 250)
            right(d, f"{x['rate']:.1f} : 1", F(46, 'Black'), cy - 60, BLUE if x['status'] == '미달' else RED)
            right(d, x['status'], F(26, 'Medium'), cy + 4, INK2)
        page(f"{D(a).month}.{D(a).day} ~ {D(b).month}.{D(b).day} 접수", '1순위 청약 결과', f'{len(S["results"])}곳',
             '1순위 접수 ÷ 일반공급 · 미달은 파랑', rs, rrow, '전체 결과 → 프로필 링크', foot, rh_max=150)
    # 4) 가점 커트라인
    cl = S.get('cutline') or {}
    areas = [a for a in ('서울', '인천', '경기') if a in cl]
    if areas:
        def lrow(d, a, i, y, cy, rh):
            d.text((64, cy - 34), a, font=F(52, 'Black'), fill=INK)
            for j, bnd in enumerate(['60㎡ 이하', '60~85㎡']):
                v = cl[a].get(bnd); x = 330 + j * 360
                d.text((x, cy - 70), bnd, font=F(26, 'Medium'), fill=INK2)
                d.text((x, cy - 36), f"{v['min_med']}점" if v else '-', font=F(56, 'Black'), fill=RED if v and v['min_med'] >= 60 else INK)
                if v: d.text((x, cy + 30), f"평균 {v['avg']}점 · {v['n']}개 주택형", font=F(24, 'Medium'), fill=INK2)
        page('최근 6개월 · 민영 · 해당지역', '당첨 가점 커트라인', '', '주택형별 최저 당첨 가점의 중앙값 (미달·추첨 제외)', areas, lrow,
             '단지별 가점 → 프로필 링크', '이 점수면 절반 정도의 주택형에서 당첨됐다는 뜻', rh_max=230)
    # 캡션
    cap = [f"🔥 이번 주 수도권 줍줍 {len(zz)}곳 ({D(z0).month}.{D(z0).day}~{D(z1).month}.{D(z1).day} 접수)", '']
    for x in zz[:8]:
        pr = f" {man(x['p_min'])}만~" if x.get('p_min') else ''
        cap.append(f"· {md(x['r0'])} {x['region']} {x['name']} ({x['kind']} {x['units']}세대){pr}")
    if c5:
        cap += ['', '💰 시세보다 싸게 나온 분양 TOP 5 (최근 6개월)'] + [f"{i}. {x['name']} 주변 신축 대비 {sg(x['gap_new'])}" for i, x in enumerate(c5, 1)]
    if rs:
        cap += ['', '🏆 1순위 결과'] + [f"· {x['name']} {x['rate']:.1f}:1 {x['status']}" for x in rs[:3]]
    tags = ['줍줍', '무순위청약', '수도권청약', '청약', '아파트청약', '내집마련', '부동산'] + list(dict.fromkeys(city(x['region']) + '줍줍' for x in zz))[:4]
    cap += ['', '※ 무순위·임의공급도 자격 요건이 있어요. 반드시 입주자모집공고를 확인하세요', '자료: 청약홈 · 참고용 정보이며 투자 권유가 아닙니다',
            '', '줍줍 일정·청약 지도는 프로필 링크에서 👆', '', ' '.join('#' + t for t in tags)]
    return cap


# ───────────────────────── 토요일: 단지분석 ─────────────────────────
def sat():
    p = S.get('pick')
    if not p: raise SystemExit('단지분석 대상이 없어 토요일 카드를 만들지 않습니다')
    ex = lambda t: float(t[0][:7]) if re.match(r'\d{3}\.', t[0]) else None
    ty = [t for t in p['types'] if ex(t)]
    gp = [t[7] for t in ty if t[7] and t[7][0]]
    c = city(p['region']); nm = shortn(p['name'], c)
    foot = '자료 청약홈·국토부 실거래가 · 분양가 단위 만원'
    # 1) 표지: KPI 4칸
    im, d = C.canvas()
    tf = F(76, 'Black'); title = nm
    while d.textlength(title, font=tf) > W - 130 and len(title) > 4: title = title[:-2] + '…'
    C.header(d, F, f"{p['region']} {p.get('umd') or ''} · 단지분석".replace('  ', ' '), title, '', f"시공 {p.get('builder') or '-'} · 총 {p['units']:,}세대 · 일반 {p['general']:,}세대")
    kp = [('1순위 경쟁률', f"{p['rate']:.1f}:1" if 'rate' in p else '-', p.get('status', ''), RED),
          ('당첨 가점', f"{min(x[0] for x in gp):.0f}점~" if gp else '발표 전', f"평균 {statistics.mean(x[2] for x in gp):.1f}점" if gp else '', INK),
          ('3.3㎡당 분양가', f"{man(p['pp_man'])}만" if p.get('pp_man') else '-', '전용면적 기준', INK),
          ('주변 신축 대비', sg(p['gap_new']) if p.get('gap_new') is not None else '-', f"신축 {man(p['ref_new'])}만" if p.get('ref_new') else '',
           RED if (p.get('gap_new') or 0) > 0 else BLUE)]
    bw, bh = (W - 80 - 24) // 2, 330
    for i, (lb, v, sub, col) in enumerate(kp):
        x = 40 + (i % 2) * (bw + 24); y = 350 + (i // 2) * (bh + 24)
        C.row_box(d, y, bh) if False else d.rounded_rectangle((x, y, x + bw, y + bh), 18, outline=C.LINE, width=3, fill=C.T.get('card', C.T['bg']))
        d.text((x + 32, y + 36), lb, font=F(30, 'Medium'), fill=INK2)
        vf = F(84, 'Black')
        while d.textlength(v, font=vf) > bw - 64: vf = F(vf.size - 6, 'Black')
        d.text((x + 32, y + 110), v, font=vf, fill=col)
        d.text((x + 32, y + 240), sub, font=F(30, 'Medium'), fill=INK2)
    C.cta(d, F, '넘겨서 주택형·특공·주변 시세 보기 →'); C.footer(d, F, foot)
    pages.append(im)
    # 2) 면적대별
    bands = []
    for bn, lo, hi in [('60㎡ 이하', 0, 60), ('60~75㎡', 60, 80), ('84㎡ 안팎', 80, 90), ('85㎡ 초과', 90, 999)]:
        ts = [t for t in ty if lo <= ex(t) < hi and t[2] and t[4]]
        if ts: bands.append((bn, ts))
    if bands:
        def brow(d, b, i, y, cy, rh):
            bn, ts = b; gg, aa = sum(t[2] for t in ts), sum(t[5] for t in ts); pr = [t[4] for t in ts]
            mins = [t[7][0] for t in ts if t[7] and t[7][0]]
            d.text((64, cy - 60), bn, font=F(44, 'Black'), fill=INK)
            d.text((64, cy + 2), f"분양가 {man(min(pr))}{'~' + man(max(pr)) if max(pr) != min(pr) else ''}만 · {len(ts)}개 타입", font=F(28, 'Medium'), fill=INK2)
            right(d, f"{aa / gg:.1f} : 1", F(48, 'Black'), cy - 64, RED if aa >= gg else BLUE)
            right(d, f"가점 최저 {min(mins):.0f}점" if mins else '가점 -', F(28, 'Medium'), cy + 2, INK2)
        page(f"{c} · {nm[:12]}", '면적대별 결과', '', '분양가(최고가 기준) · 1순위 경쟁률 · 당첨 가점(해당지역)', bands, brow,
             '주택형별 전체 표 → 프로필 링크', foot, rh_max=200)
    # 3) 특공
    sp = [x for x in (p.get('sp_stat') or []) if x[1]]
    if sp:
        def srow(d, x, i, y, cy, rh):
            k, a, n = x
            d.text((64, cy - 30), k, font=F(40, 'Black'), fill=INK)
            d.text((330, cy - 22), f"배정 {a} · 접수 {n:,}", font=F(30, 'Medium'), fill=INK2)
            right(d, f"{n / a:.1f} : 1", F(44, 'Black'), cy - 32, RED if n > a else BLUE)
        page(f"{c} · {nm[:12]}", '특별공급 신청현황', '', f"특공 {sum(x[1] for x in sp):,}세대에 {sum(x[2] for x in sp):,}건 접수", sp, srow,
             '청약 지도 → 프로필 링크', foot, rh_max=120)
    # 4) 주변 시세
    near = [n for n in (p.get('near') or []) if n.get('m59') or n.get('m84')][:4]
    if near:
        u59 = [t[4] for t in ty if 57 <= ex(t) < 61 and t[4]]; u84 = [t[4] for t in ty if 82 <= ex(t) < 86 and t[4]]
        rows = near + [{'apt': f"{nm} (분양가)", 'built': None, 'm59': min(u59) if u59 else None, 'm84': min(u84) if u84 else None, 'me': True}]
        def nrow(d, n, i, y, cy, rh):
            nf = F(36, 'Black'); col = RED if n.get('me') else INK
            d.text((64, cy - 52), fit(d, n['apt'], nf, 470), font=nf, fill=col)
            d.text((64, cy + 2), f"{n['built']}년 준공 · 최근 6개월 {n['n']}건" if n.get('built') else '최저 분양가', font=F(26, 'Medium'), fill=INK2)
            for j, k in enumerate(['m59', 'm84']):
                s = f"{man(n[k])}" if n.get(k) else '-'; xr = 790 + j * 226
                ff = F(32, 'Black'); d.text((xr - d.textlength(s, font=ff), cy - 30), s, font=ff, fill=col)
        d, _ = page(f"{p.get('umd') or c} 신축 아파트", '주변 시세와 비교', '', '최근 10년 내 준공 · 최근 6개월 매매 중앙값 (만원)', rows, nrow,
                    '단지분석 전체 글 → 프로필 링크', foot, rh_max=150, extra_top=40)
        for j, k in enumerate(['59㎡', '84㎡']):
            ff = F(30); xr = 790 + j * 226; d.text((xr - d.textlength(k, font=ff), 336), k, font=ff, fill=INK2)
    cap = [f"📌 단지분석 | {p['name']} ({p['region']})", '']
    if 'rate' in p: cap.append(f"· 1순위 {p['rate']:.1f}:1 ({p.get('apps', 0):,}건 / 일반 {p['general']}세대) {p['status']}")
    if gp: cap.append(f"· 당첨 가점 최저 {min(x[0] for x in gp):.0f}점, 평균 {statistics.mean(x[2] for x in gp):.1f}점 (해당지역)")
    if p.get('pp_man'): cap.append(f"· 3.3㎡당 분양가 {man(p['pp_man'])}만" + (f" (주변 신축 대비 {sg(p['gap_new'])})" if p.get('gap_new') is not None else ''))
    if sp:
        b = max(sp, key=lambda x: x[2] / x[1]); cap.append(f"· 특공 최고 경쟁률 {b[0]} {b[2] / b[1]:.1f}:1")
    tags = ['청약', '청약분석', '수도권청약', '아파트분양', '당첨가점', '내집마련', '부동산', c + '청약', re.sub(r'[^가-힣A-Za-z0-9]', '', nm)[:15]]
    cap += ['', '주택형별 분양가·경쟁률·가점 전체 표는 블로그에 👆 (프로필 링크)', '자료: 청약홈·국토부 실거래가 · 참고용 정보이며 투자 권유가 아닙니다',
            '', ' '.join('#' + t for t in tags)]
    return cap


cap = wed() if MODE == 'wed' else sat()
for i, im in enumerate(pages, 1):
    im.save(os.path.join(OUT, f'{i:02d}.png'))
shutil.copy(os.path.join(OUT, '01.png'), os.path.join(OUT, 'single.png'))
shutil.copy(os.path.join(OUT, '01.png'), os.path.join(OUT, 'latest.png'))
open(os.path.join(OUT, 'caption.txt'), 'w', encoding='utf-8').write('\n'.join(cap))
print(f'청약 {MODE} 카드 {len(pages)}장 → {OUT}')
