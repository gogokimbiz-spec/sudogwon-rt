"""토허제 40곳을 '사는 곳 기준 평균 연봉'으로 3그룹 나눠 본 주간 아파트값 카드 (2026-11-27 시안)
사용법: python make_cards_toheo_income.py OUT raw.json
  - 데이터·색·글꼴은 make_cards_toheo.py 를 그대로 불러 씀 (카드 그리기 직전까지 실행)
  - 소득: 국세청 국세통계 4-2-15 시·군·구별 근로소득 연말정산 신고현황(주소지), 2024년 귀속 – 1인당 평균 총급여(만원)
    경기 일반구는 따로 안 나와 소속 시 값을 씀 (분당·수정·중원=성남, 수지·기흥=용인, 장안·팔달·영통=수원, 동안=안양, 동탄=화성)
"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('TOHEO_MAX_AGE', '9999')
src = open(os.path.join(HERE, 'make_cards_toheo.py'), encoding='utf-8').read()
src = src[:src.index('im, d = C.canvas()')]          # 데이터 + 글꼴·색·지도 함수까지만
__file__ = os.path.join(HERE, 'make_cards_toheo.py')
exec(compile(src, 'make_cards_toheo.py', 'exec'))

INCOME = {   # 만원, 2024년 귀속
    '종로구': 5722, '중구': 5712, '용산구': 8041, '성동구': 5867, '광진구': 4558, '동대문구': 4387, '중랑구': 3673,
    '성북구': 4675, '강북구': 3485, '도봉구': 3705, '노원구': 4367, '은평구': 4135, '서대문구': 4947, '마포구': 5679,
    '양천구': 5496, '강서구': 4514, '구로구': 4179, '금천구': 3632, '영등포구': 5337, '동작구': 4897, '관악구': 3770,
    '서초구': 8960, '강남구': 8925, '송파구': 6109, '강동구': 5095,
    '과천시': 6966, '안양 동안구': 4832, '의왕시': 4883, '성남 수정구': 5944, '성남 중원구': 5944, '성남 분당구': 5944,
    '수원 장안구': 4995, '수원 팔달구': 4995, '수원 영통구': 4995, '용인 기흥구': 5434, '용인 수지구': 5434,
    '광명시': 4771, '구리시': 4163, '하남시': 4897, '화성 동탄구': 5258,
}
CITY = {'성남': '성남시', '수원': '수원시', '용인': '용인시', '안양': '안양시', '화성': '화성시'}
HI, LO = 5400, 4700          # 그룹 경계 (15 · 12 · 13곳)
GROUPS = [('고소득 동네', f'연봉 {HI:,}만 이상', lambda v: v >= HI),
          ('중간 동네', f'연봉 {LO:,}만~{HI:,}만', lambda v: LO <= v < HI),
          ('저소득 동네', f'연봉 {LO:,}만 미만', lambda v: v < LO)]

# 최근 4주 누적
wk_all = sorted(w for w in weeks if w <= last)
w4 = wk_all[-5] if len(wk_all) >= 5 else wk_all[0]
cid_of = {n: cid for _, n, _, cid in REGIONS}
def chg4(n):
    s = ser.get(cid_of[n], {})
    return round((s[last][1] / s[w4][1] - 1) * 100, 2) if last in s and w4 in s else None

for r in rows: r['income'] = INCOME[r['name']]; r['chg4'] = chg4(r['name'])
G = []
for nm, rule, f in GROUPS:
    rs = sorted([r for r in rows if f(r['income'])], key=lambda r: -r['chg'])
    avg = round(sum(r['chg'] for r in rs) / len(rs), 3)
    a4 = [r['chg4'] for r in rs if r['chg4'] is not None]
    G.append(dict(name=nm, rule=rule, rows=rs, avg=avg, avg4=round(sum(a4) / len(a4), 2),
                  inc=round(sum(r['income'] for r in rs) / len(rs))))
pa = lambda v: '0.00%' if abs(v) < 0.005 else f'{v:+.2f}%'

# 한 줄 결론
order = sorted(G, key=lambda g: -g['avg'])
hi_, lo_ = order[0], order[-1]
if [g['name'] for g in order] == [g['name'] for g in G]: head = '연봉 높은 동네일수록 더 올랐다'
elif [g['name'] for g in order] == [g['name'] for g in G[::-1]]: head = '연봉 낮은 동네일수록 더 올랐다'
elif hi_['avg'] > 0 and lo_['avg'] < hi_['avg'] / 3: head = f"{hi_['name']}가 가장 많이 오르고, {lo_['name']}는 주춤"
elif hi_['avg'] > 0: head = f"{hi_['name']}가 가장 많이 올랐다"
else: head = f"{lo_['name']}가 가장 많이 내렸다"
print(head); [print(g['name'], len(g['rows']), pa(g['avg']), '4주', pa(g['avg4'])) for g in G]


# ─────────────────────────── 카드 ───────────────────────────
def header_inc(d):
    ink = C.INK
    d.rectangle((40, 28, W - 40, 34), fill=ink); d.line((40, 40, W - 40, 40), fill=ink, width=2)
    wd = '월화수목금토일'[pub_day.weekday()]
    meta = f'{pub_day.year}년 {pub_day.month}월 {pub_day.day}일 ({wd})  ·  {base_day.month}월 {base_day.day}일 조사 · 한국부동산원 · 전주 대비'
    d.text((44, 50), meta, font=F(21, 'Medium'), fill=C.INK2)
    d.line((40, 86, W - 40, 86), fill=ink, width=1)
    d.text((40, 94), '소득으로 본 토허제 40곳', font=FS(64, 'Black'), fill=ink)
    d.text((42, 172), f'“{head}”', font=FS(34, 'Bold'), fill=C.INK2)
    d.line((40, 228, W - 40, 228), fill=ink, width=2); d.rectangle((40, 234, W - 40, 240), fill=ink)


def band(d, g, box):
    x0, y0, x1, y1 = box
    # 왼쪽: 그룹 이름 · 기준 · 평균
    LW = 300
    d.text((x0, y0 + 8), g['name'], font=FS(40, 'Black'), fill=C.INK)
    d.text((x0 + 2, y0 + 62), f"{g['rule']} · {len(g['rows'])}곳", font=F(20, 'Medium'), fill=C.INK2)
    v = g['avg']; col = C.UP if v > 0.004 else C.DOWN if v < -0.004 else C.INK
    d.text((x0 + 2, y0 + 92), '이번 주 평균', font=FS(22, 'Bold'), fill=C.INK)
    t = pa(v); a_, b_ = t[:-1], '%'
    bf = F(66, 'Black'); d.text((x0, y0 + 118), a_, font=bf, fill=col)
    d.text((x0 + d.textlength(a_, font=bf) + 2, y0 + 150), b_, font=F(34, 'Black'), fill=col)
    v4 = g['avg4']; c4 = C.UP if v4 > 0.004 else C.DOWN if v4 < -0.004 else C.INK
    d.text((x0 + 2, y0 + 214), '최근 4주 누적', font=F(20, 'Medium'), fill=C.INK2)
    t4 = pa(v4); d.text((x0 + 2, y0 + 238), t4, font=F(30, 'Black'), fill=c4)
    d.text((x0 + 2, y0 + 282), f"평균 연봉 {g['inc']:,}만", font=F(20, 'Medium'), fill=C.INK2)
    d.line((x0 + LW - 18, y0 + 8, x0 + LW - 18, y1 - 8), fill=C.T['line'], width=2)
    # 오른쪽: 지역 2열 (이름 · 연봉 · 주간 %)
    rs = g['rows']; half = (len(rs) + 1) // 2; lx = x0 + LW; cw = (x1 - lx - 16) / 2
    rh = min(40, (y1 - y0 - 8) / half)
    nf, inf, vf, pf = FS(25, 'Bold'), F(18, 'Medium'), F(22, 'Black'), F(15, 'Black')
    PW = 86
    for i, r in enumerate(rs):
        cx = lx + (i // half) * (cw + 16); cy = y0 + 6 + (i % half) * rh
        if i % half: d.line((cx, cy, cx + cw, cy), fill=C.T['line'], width=1)
        nm = r['short']; d.text((cx + 2, cy + (rh - 25) / 2 - 7), nm, font=nf, fill=C.INK)
        it = f"{r['income']:,}만"
        if r['name'].split(' ')[0] in CITY: it = '*' + it
        bx = cx + cw - PW
        d.text((bx - 10 - d.textlength(it, font=inf), cy + (rh - 18) / 2 - 4), it, font=inf, fill=C.INK2)
        colb = color(r['chg']); d.rectangle((bx, cy + 5, bx + PW, cy + rh - 5), fill=colb)
        s = pc(r['chg']); a_, b_ = s[:-1], '%'; tw = d.textlength(a_, font=vf) + 1 + d.textlength(b_, font=pf)
        tx = bx + (PW - tw) / 2; ty = cy + (rh - 22) / 2 - 5
        d.text((tx, ty), a_, font=vf, fill=on(colb)); d.text((tx + d.textlength(a_, font=vf) + 1, ty + 6), b_, font=pf, fill=on(colb))


im, d = C.canvas()
header_inc(d)
top, bot = 256, 1236; gap = 14; bh = (bot - top - 2 * gap) / 3
for k, g in enumerate(G):
    y = top + k * (bh + gap)
    if k: d.rectangle((40, y - gap / 2 - 2, W - 40, y - gap / 2 + 1), fill=C.INK)
    band(d, g, (44, y, W - 44, y + bh))
d.line((40, 1244, W - 40, 1244), fill=C.INK, width=2)
d.text((44, 1252), '연봉 = 국세청 2024년 귀속 근로소득 연말정산(사는 곳 기준) 1인당 평균 총급여 · * 경기 일반구는 소속 시 값',
       font=F(17, 'Medium'), fill=C.INK2)
d.line((40, 1290, W - 40, 1290), fill=C.INK, width=2)
C.footer(d, F, '자료 한국부동산원 주간아파트가격동향 · 국세청 국세통계')
import random
random.seed(7); g_ = Image.effect_noise((W // 2, SH // 2), 18).resize((W, SH)).convert('L')
im = Image.composite(im, Image.blend(im, Image.new('RGB', (W, SH), (120, 100, 70)), 0.06), g_.point(lambda v: 255 if v > 120 else 200))
im.save(os.path.join(OUT, 'card_income.png')); print('카드 →', os.path.join(OUT, 'card_income.png'))
