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
Fm = lambda k, v: '-' if v is None else fmt[k.replace('q_', '')](v)
LAB = {'q_sales': '누적 매출', 'q_op': '누적 영업이익', 'q_opm': '영업이익률', 'q_dr': '부채비율',
       'opm': '영업이익률', 'roe': 'ROE', 'dr': '부채비율', 'gr': '매출', 'opg': '영업이익', 'op': '영업이익', 'sales': '매출', 'ni': '순이익'}
QP, QS = S.get('qp') or '', S.get('qspan') or ''
THEME = {'q_gr': ('매출 증가율 TOP', 'q_gr', 'q_sales', f'{QS} · 전년 동기 대비'),
         'q_opg': ('영업이익 증가율', 'q_opg', 'q_op', f'{QS} · 전년 동기 대비'),
         'q_opm': ('영업이익률 TOP', 'q_opm', 'q_op', f'{QS} 매출 대비 영업이익'),
         'q_turn': ('흑자전환 기업', 'q_op', 'q_opm', f'{QS} · 전년 동기 영업적자 → 흑자'),
         'q_low_debt': ('부채비율 낮은 기업', 'q_dr', 'q_opm', f'{QP}말 부채총계 ÷ 자본총계'),
         'opm': ('영업이익률 TOP', 'opm', 'op', '매출 대비 영업이익 비율'),
         'roe': ('ROE TOP', 'roe', 'ni', '자기자본 대비 순이익 비율'),
         'growth': ('매출 성장률 TOP', 'gr', 'sales', '직전 연도 대비 매출 증가율'),
         'opg': ('영업이익 증가율 TOP', 'opg', 'op', '직전 연도 대비 영업이익 증가율'),
         'low_debt': ('부채비율 낮은 기업', 'dr', 'opm', '부채총계 ÷ 자본총계'),
         'turn': ('흑자전환 기업', 'op', 'opm', '영업적자 → 영업흑자')}

R = S['rank']

import card_style as C                                 # 공통 디자인 (밝은 화이트·오렌지형)
im, d = C.canvas()
INK, INK2, RED, BLUE = C.INK, C.INK2, C.UP, C.DOWN
bd = datetime.date.fromisoformat(S['basDt'][:10]) if S.get('basDt') else datetime.date.today()
if P['kind'] == 'rank':
    key = P['keys'][0]; t, k1, k2, sub = THEME[key]
    pill = (f"{QP} 실적" if key.startswith('q_') else f"{S['fy']} 사업연도") + " · 상장사 매출 상위 500"
    head, big = t, '' if key == 'turn' else str(min(10, len(R[key])))
    if len(head) > 10: big = ''
else:
    pill = f'{bd.month}.{bd.day} 종가 · 시총 상위 500'
    head, big, sub = '저평가 지표', 'PER·PBR', '숫자가 낮을수록 이익·자산 대비 주가가 낮음'
C.header(d, F, pill, head, big, sub + (' · 금융업 제외' if P['kind'] == 'rank' else ''))


def row(y, rh, i, x, k1, k2):
    z = min(1.0, rh / 116)                      # 줄이 많으면 글자를 조금 작게
    C.row_box(d, y, rh - 10)
    cy = y + (rh - 10) // 2
    bs = int(28 * z) + 4
    C.badge(d, F, 60, cy, i, bs, i <= 3)
    v1 = Fm(k1, x[k1]); vf = F(int(46 * z), 'Black'); vw = d.textlength(v1, font=vf)
    d.text((W - 64 - vw, cy - int(32 * z)), v1, font=vf, fill=RED if k1.replace('q_', '') in ('opm', 'gr', 'op', 'opg', 'roe') else BLUE)
    mk = '코스피' if x['market'] == 'KOSPI' else '코스닥'
    nx = 60 + 2 * bs + 22; nf = F(int(40 * z), 'Black')
    d.text((nx, cy - int(42 * z)), fit(d, x['name'], nf, W - 64 - vw - 40 - nx), font=nf, fill=INK)
    d.text((nx, cy + int(6 * z)), f"{mk} · " + (f"{LAB[k2]} {Fm(k2, x[k2])}" if k2.endswith('sales') else f"매출 {won(x.get('q_sales') or x['sales'])} · {LAB[k2]} {Fm(k2, x[k2])}"), font=F(int(26 * z), 'Medium'), fill=INK2)


top, bottom = 340, SH - 170
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
C.cta(d, F, '500곳 전체 순위 → 프로필 링크')
C.footer(d, F, '자료 DART·금융위원회 · 참고용 데이터이며 투자 권유가 아닙니다')
im.save(os.path.join(OUT, 'single.png'))
shutil.copy(os.path.join(OUT, 'single.png'), os.path.join(OUT, 'latest.png'))
print('기업재무 카드 →', os.path.join(OUT, 'single.png'))
