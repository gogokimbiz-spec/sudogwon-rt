"""기업재무 한 장 이미지(1080×1350)를 만듭니다 (GitHub Actions 용, 화·금요일).
사용법: python make_cards_fin.py site/fin/summary.json site/fin/cards
결과: <출력폴더>/single.png, latest.png
필요: Pillow, 한글 폰트(fonts-noto-cjk)
"""
import sys, os, glob, json, datetime, shutil
from PIL import Image, ImageDraw, ImageFont

S = json.load(open(sys.argv[1], encoding='utf-8'))
P = S.get('post')
if not P:
    print('오늘은 기업재무 카드가 없습니다'); sys.exit(0)
OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
W, SH = 1080, 1350
NAVY, WHITE, MUTED, RED, BLUE = (15, 39, 66), (255, 255, 255), (150, 170, 195), (255, 92, 92), (60, 120, 230)
CREAM, INK, INK2, GOLD = (247, 248, 251), (20, 30, 45), (95, 108, 125), (240, 180, 76)
BRAND = '데이터로 보는 재테크'


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
def rr(d, box, r, fill=None): d.rounded_rectangle(box, r, fill=fill)
def fit(d, s, font, maxw):
    while d.textlength(s, font=font) > maxw and len(s) > 3: s = s.rstrip('…')[:-1] + '…'
    return s


def won(v):
    if v is None: return '-'
    s = '-' if v < 0 else ''; v = abs(v)
    if v >= 1e12:
        j, e = divmod(round(v / 1e8), 10000)
        return f'{s}{j:,}조 {e:,}억' if e else f'{s}{j:,}조'
    return f'{s}{round(v / 1e8):,}억'
fmt = {'opm': lambda v: f'{v:.1f}%', 'roe': lambda v: f'{v:.1f}%', 'dr': lambda v: f'{v:,.0f}%',
       'gr': lambda v: f'{v:+.1f}%', 'opg': lambda v: f'{v:+.1f}%', 'op': won, 'sales': won, 'ni': won}
Fm = lambda k, v: '-' if v is None else fmt[k](v)
LAB = {'opm': '영업이익률', 'roe': 'ROE', 'dr': '부채비율', 'gr': '매출', 'opg': '영업이익', 'op': '영업이익', 'sales': '매출', 'ni': '순이익'}
THEME = {'opm': ('영업이익률 TOP', 'opm', 'op', '매출 대비 영업이익 비율'),
         'roe': ('ROE TOP', 'roe', 'ni', '자기자본 대비 순이익 비율'),
         'growth': ('매출 성장률 TOP', 'gr', 'sales', '직전 연도 대비 매출 증가율'),
         'opg': ('영업이익 증가율 TOP', 'opg', 'op', '직전 연도 대비 영업이익 증가율'),
         'low_debt': ('부채비율 낮은 기업', 'dr', 'opm', '부채총계 ÷ 자본총계'),
         'turn': ('흑자전환 기업', 'op', 'opm', '영업적자 → 영업흑자')}

R = S['rank']

im = Image.new('RGB', (W, SH), CREAM); d = ImageDraw.Draw(im)
d.rectangle((0, 0, W, 300), fill=NAVY)
if P['kind'] == 'rank':
    key = P['keys'][0]; t, k1, k2, sub = THEME[key]
    pill = f"{S['fy']} 사업연도 · 상장사 매출 상위 500"
    head, big = t, '' if key == 'turn' else str(min(10, len(R[key])))
    if len(head) > 10: big = ''
else:
    pill = f'{bd.month}.{bd.day} 종가 · 시총 상위 500'
    head, big, sub = '저평가 지표', 'PER·PBR', '숫자가 낮을수록 이익·자산 대비 주가가 낮음'
lw = d.textlength(pill, font=F(32))
rr(d, (64, 56, 64 + lw + 44, 110), 27, fill=RED); d.text((86, 62), pill, font=F(32), fill=WHITE)
d.text((64, 136), head, font=F(78, 'Black'), fill=WHITE)
if big:
    bf = F(110 if len(big) <= 3 else 72, 'Black')
    d.text((W - 64 - d.textlength(big, font=bf), 128 if len(big) <= 3 else 150), big, font=bf, fill=GOLD)
d.text((64, 248), sub + (' · 금융업 제외' if P['kind'] == 'rank' else ''), font=F(28, 'Medium'), fill=MUTED)


def row(y, rh, i, x, k1, k2):
    z = min(1.0, rh / 116)                      # 줄이 많으면 글자를 조금 작게
    rr(d, (40, y, W - 40, y + rh - 10), 20, fill=WHITE)
    cy = y + (rh - 10) // 2
    n = str(i); bs = int(28 * z) + 4
    rr(d, (60, cy - bs, 60 + 2 * bs, cy + bs), 14, fill=NAVY if i > 3 else RED)
    nf2 = F(int(32 * z), 'Black')
    d.text((60 + bs - d.textlength(n, font=nf2) / 2, cy - int(24 * z)), n, font=nf2, fill=WHITE)
    v1 = Fm(k1, x[k1]); vf = F(int(46 * z), 'Black'); vw = d.textlength(v1, font=vf)
    d.text((W - 64 - vw, cy - int(32 * z)), v1, font=vf, fill=RED if k1 in ('opm', 'gr', 'op') else BLUE)
    mk = '코스피' if x['market'] == 'KOSPI' else '코스닥'
    nx = 60 + 2 * bs + 22; nf = F(int(40 * z), 'Black')
    d.text((nx, cy - int(42 * z)), fit(d, x['name'], nf, W - 64 - vw - 40 - nx), font=nf, fill=INK)
    d.text((nx, cy + int(6 * z)), f"{mk} · 매출 {won(x['sales'])}" + ('' if k2 == 'sales' else f" · {LAB[k2]} {Fm(k2, x[k2])}"), font=F(int(26 * z), 'Medium'), fill=INK2)


top, bottom = 330, SH - 170
if P['kind'] == 'rank':
    rows = R[key][:10]
    rh = (bottom - top) // max(7, len(rows))
    y = top
    for i, x in enumerate(rows, 1):
        row(y, rh, i, x, k1, k2); y += rh
else:
    rh = (bottom - top - 116) // 10
    y = top
    for key in P['keys']:
        t, k1, k2, _ = THEME[key]
        d.text((64, y), t, font=F(34, 'Black'), fill=INK); y += 58
        for i, x in enumerate(R[key][:5], 1):
            row(y, rh, i, x, k1, k2); y += rh
rr(d, (40, SH - 150, W - 40, SH - 60), 45, fill=NAVY)
msg = '500곳 전체 순위 → 프로필 링크'
d.text(((W - d.textlength(msg, font=F(38))) / 2, SH - 136), msg, font=F(38), fill=WHITE)
d.text((64, SH - 46), f'{BRAND} · 자료 금융위원회 · 참고용 데이터이며 투자 권유가 아닙니다', font=F(22, 'Regular'), fill=INK2)
im.save(os.path.join(OUT, 'single.png'))
shutil.copy(os.path.join(OUT, 'single.png'), os.path.join(OUT, 'latest.png'))
print('기업재무 카드 →', os.path.join(OUT, 'single.png'))
