"""동네 대표기업 카드(1080×1350): '○○구 대표기업 TOP 10 / 11~20위 …'.
사용법: python make_cards_region.py site/dong/summary.json site/dong/cards
"""
import sys, os, glob, json, shutil
from PIL import ImageFont
import card_style as C
from region_fmt import won, man, emp, tenure, short

S = json.load(open(sys.argv[1], encoding='utf-8'))
P = S.get('post')
if not P:
    print('오늘은 동네 대표기업 카드가 없습니다'); sys.exit(0)
OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
W, SH = C.W, C.SH


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
def fit(d, s, font, maxw):
    while d.textlength(s, font=font) > maxw and len(s) > 2: s = s.rstrip('…')[:-1] + '…'
    return s


im, d = C.canvas()
area = P['name'].split()[-1]
big = 'TOP 10' if P['start'] == 1 else f"{P['start']}~{P['end']}위"
C.header(d, F, f"{S['fy']}년 매출 기준 · 동네 대표기업", f'{area} 대표기업', big, f"{P['name']} 본사 기업 · 비상장 포함")
rows = P['rows'][:10]
top, bottom = 340, SH - 170
rh = (bottom - top) // 10
z = rh / 105
y = top
for i, x in enumerate(rows, P['start']):
    C.row_box(d, y, rh - 8)
    cy = y + (rh - 8) // 2
    bs = int(26 * z)
    C.badge(d, F, 56, cy, i, bs, i <= 3)
    # 첫 줄: 회사명(+동) …… 매출 / 영업이익   둘째 줄: 직원 · 근속 · 평균연봉
    vf, lf = F(int(34 * z), 'Black'), F(int(24 * z), 'Medium')
    parts = [('매출 ', lf, C.INK2), (short(x['sales']), vf, C.ORANGE)]
    if x.get('op') is not None:
        parts += [('  영업이익 ', lf, C.INK2), (short(x['op']), vf, C.INK if x['op'] >= 0 else C.DOWN)]
    vw = sum(d.textlength(t, font=f) for t, f, _ in parts)
    vx = W - 64 - vw
    for t, f, col in parts:
        d.text((vx, cy - int(40 * z) + (int(10 * z) if f is lf else 0)), t, font=f, fill=col); vx += d.textlength(t, font=f)
    nx = 56 + 2 * bs + 20; nf = F(int(34 * z), 'Black')
    room = W - 64 - vw - 24 - nx
    has_chip = bool(x.get('dong'))
    nm = fit(d, x['n'], nf, room - (110 if has_chip else 0))
    d.text((nx, cy - int(42 * z)), nm, font=nf, fill=C.INK)
    if has_chip and d.textlength(nm, font=nf) + 100 < room:
        C.chip(d, F, int(nx + d.textlength(nm, font=nf) + 12), cy - int(37 * z), x['dong'], int(20 * z))
    sub = '   ·   '.join(t for t in [f"직원 {emp(x['emp'])}" if x.get('emp') else '', f"근속 {tenure(x['tenure'])}" if x.get('tenure') else '',
                                     f"평균연봉 {man(x['sal'])}" if x.get('sal') else ''] if t) or '직원·근속·연봉 미공시'
    d.text((nx, cy + int(8 * z)), fit(d, sub, F(int(26 * z), 'Medium'), W - 64 - nx), font=F(int(26 * z), 'Medium'), fill=C.INK2)
    y += rh
C.cta(d, F, '직원 수·평균연봉 전체 → 블로그')
C.footer(d, F, '자료 금융위원회 기업 재무·기본정보 · 본사 주소 기준')
im.save(os.path.join(OUT, 'single.png'))
shutil.copy(os.path.join(OUT, 'single.png'), os.path.join(OUT, 'latest.png'))
print('동네 대표기업 카드 →', os.path.join(OUT, 'single.png'))
