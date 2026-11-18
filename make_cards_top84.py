"""국평(전용 84㎡대)·소형(전용 59㎡대) 최고 실거래가 TOP 16 카드 – 서울 / 경기(인천 제외) × 2 = 4장 (2026-11-18, 매월 3일 · 전월 계약분)
사용법: python make_cards_top84.py rt_data.json site/top84 [YYYY-MM]
  - YYYY-MM 을 안 주면 '지난달' (한국 시간 기준)
  - 시험용: python make_cards_top84.py --lists data.json OUT 2026-10   (data.json = {"84": {"seoul": [[지역, 단지, 법정동, 가격(만원), 면적], ...], "gg": [...]}, "59": {...}})
결과: OUT/seoul_84.png, gg_84.png, seoul_59.png, gg_59.png, caption_<지역>_<크기>.txt, summary.json
규칙: 지난달 계약 · 국평 전용 83.5~86㎡ / 소형 57~61㎡ · 해제 거래 제외 · 같은 단지(시군구+단지명)는 가장 비싼 1건 → 가격순 16곳
"""
import os, re, sys, json, glob, datetime
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, SH = 1080, 1350
INK, INK2, RED, LINE, BG = (20, 20, 22), (110, 110, 118), (226, 36, 36), (30, 30, 34), (255, 255, 255)


def font_path(weight):
    for pat in [os.path.join(HERE, 'fonts', f'NotoSansCJKkr-{weight}.otf'), f'/usr/share/fonts/**/NotoSansCJKkr-{weight}.otf',
                f'/usr/share/fonts/**/NotoSansCJK-{weight}.ttc', f'/usr/share/fonts/**/*CJK*{weight}*']:
        hits = glob.glob(pat, recursive=True)
        if hits: return hits[0]
    raise SystemExit('한글 폰트(Noto Sans CJK)를 찾지 못했습니다')
_fc = {}
def F(size, weight='Bold'):
    if (size, weight) not in _fc:
        p = font_path(weight); f = None
        if p.endswith('.ttc'):
            for i in range(10):
                try:
                    g = ImageFont.truetype(p, size, index=i)
                    if 'KR' in g.getname()[0]: f = g; break
                except Exception: break
        _fc[size, weight] = f or ImageFont.truetype(p, size)
    return _fc[size, weight]


def place(region, umd):
    """'서울 서초구','반포동' → '서초·반포' / '성남 분당구','수내동' → '분당·수내' / '과천시','별양동' → '과천·별양'"""
    p = region.split(' ')
    g = p[-1]
    g = g[:-1] if len(g) > 2 and g[-1] in '시군구' else g
    u = umd[:-1] if umd and umd[-1] in '동리가' and len(umd) > 2 else umd
    u = u.rstrip('0123456789')
    return f'{g}·{u}' if u else g


SIZES = {   # 2026-11-18: 국평 + 소형. 종류: (최소 전용㎡, 최대 전용㎡ 미만, 제목 이름, 칩 문구)
    '84': (83.5, 86.0, '국평', '전용 84㎡대'),
    '59': (57.0, 61.0, '소형', '전용 59㎡대'),
}


def compute(rt_path, ym, lo=83.5, hi=86.0):
    raw = json.load(open(rt_path, encoding='utf-8'))
    names = json.load(open(os.path.join(HERE, 'names.json'), encoding='utf-8'))
    best = {}
    for code, date, apt, umd, area, floor, price, by, cd in raw['trade']:
        if cd == 'O' or not date.startswith(ym) or not (lo <= area < hi) or price <= 0: continue
        if not (code.startswith('11') or code.startswith('41')): continue
        k = (code, apt)                                  # 같은 단지가 두 법정동에 걸친 경우(래미안슈르 등)도 1건
        if k not in best or price > best[k][3]:
            best[k] = [names.get(code, code), apt, umd, price, area, code[:2]]
    v = sorted(best.values(), key=lambda x: -x[3])
    return {'seoul': [x[:5] for x in v if x[5] == '11'][:16], 'gg': [x[:5] for x in v if x[5] == '41'][:16]}


def fit_lines(d, text, maxw, sizes):
    """단지명을 1~2줄로: 큰 글씨부터 줄여 가며 맞춤"""
    for s in sizes:
        f = F(s, 'Black')
        if d.textlength(text, font=f) <= maxw: return f, [text]
    f = F(sizes[-1], 'Black')
    # 두 줄로 나누기 (괄호 앞이나 가운데)
    cut = text.find(' ') if 0 < text.find(' ') < len(text) - 1 else text.find('(') if 0 < text.find('(') < len(text) - 1 else len(text) // 2
    a, b = text[:cut].strip(), text[cut:].strip()
    while d.textlength(b, font=f) > maxw and len(b) > 2: b = b[:-2] + '…'
    while d.textlength(a, font=f) > maxw and len(a) > 2: a = a[:-2] + '…'
    return f, [a, b]


def draw(rows, area_name, ym, out_png, size='84'):
    """실거래·신고가 카드와 같은 디자인(card_style slate): 머리말 + 4×4 칸 + 노란 버튼 + 아래 출처·아이디 (2026-11-18)"""
    os.environ.setdefault('CARD_THEME', 'slate')
    sys.path.insert(0, HERE); import card_style as C
    y_, m_ = int(ym[:4]), int(ym[5:7])
    im, d = C.canvas(); W_, SH_ = C.W, C.SH
    GAP = 36
    lo, hi, kind, chip = SIZES[size]
    C.header(d, F, f'{y_}년 {m_}월 계약분 · {chip}', f'{y_ % 100}년 {m_}월 {area_name} {kind}', f'TOP {len(rows)}',
             '단지별 최고 실거래가 · 같은 단지는 1건 · 단위 억 원', gap=GAP)
    gx0, gy0, gx1 = 40, 312 - GAP + 22, W_ - 40
    CTA_TOP = SH_ - 132
    gy1 = CTA_TOP - 18
    gp = 10
    cw, ch = (gx1 - gx0 - gp * 3) / 4, (gy1 - gy0 - gp * 3) / 4
    for i, (region, apt, umd, price, area) in enumerate(rows):
        cx, cy = gx0 + (cw + gp) * (i % 4), gy0 + (ch + gp) * (i // 4)
        hot = i < 3
        d.rounded_rectangle((cx, cy, cx + cw, cy + ch), 12, fill=C.T.get('card', C.T['bg']), outline=C.ORANGE if hot else C.LINE, width=3 if hot else 2)
        pad = 14
        rk = f'{i + 1:02d}'; fr = F(34, 'Black')
        d.text((cx + pad, cy + 8), rk, font=fr, fill=C.ORANGE if hot else C.INK)
        C.chip(d, F, cx + pad + d.textlength(rk, font=fr) + 10, cy + 14, place(region, umd), size=21)
        nm = re.sub(r'\([^()]*\d+동\)', '', apt).strip() or apt     # '현대14차(203,204,205,206동)' → '현대14차'
        fn, lines = fit_lines(d, nm, cw - pad * 2, [32, 30, 28, 26])
        ny = cy + 64 if len(lines) == 1 else cy + 56
        for ln in lines:
            d.text((cx + pad, ny), ln, font=fn, fill=C.INK); ny += fn.size + 4
        pt = f'{price / 10000:.2f}억'; pf = F(50, 'Black')
        while d.textlength(pt, font=pf) > cw - pad * 2 - 8 and pf.size > 36: pf = F(pf.size - 2, 'Black')
        d.text((cx + cw - pad - d.textlength(pt, font=pf), cy + ch - pf.size - 24), pt, font=pf, fill=C.ORANGE if hot else C.INK)
    cm = '우리 동네 실거래가 → 프로필 링크'
    d.rounded_rectangle((40, CTA_TOP, W_ - 40, CTA_TOP + 64), 10, fill=C.ORANGE)
    d.text(((W_ - d.textlength(cm, font=F(32))) / 2, CTA_TOP + 9), cm, font=F(32),
           fill=C.T.get('cta_t', C.T.get('pill_t', C.WHITE) if C.T['accent'] == C.T['pill'] else C.WHITE))
    C.footer(d, F, f'자료 국토교통부 실거래가 · 전용 {lo:g}~{hi:g}㎡ 미만 · 해제 거래 제외')
    im.save(out_png)


def caption(rows, area_name, ym, size='84'):
    lo, hi, kind, chip = SIZES[size]
    y_, m_ = int(ym[:4]), int(ym[5:7])
    L = [f'🏆 {y_ % 100}년 {m_}월 {area_name} {kind}({chip}) 최고 실거래가 TOP {len(rows)}', '']
    L += [f"{i + 1}. {place(r, u)} {re.sub(r'\([^()]*\d+동\)', '', a).strip() or a} {p / 10000:.2f}억" for i, (r, a, u, p, _) in enumerate(rows)]
    L += ['', f'※ 전용 {lo:g}~{hi:g}㎡ 미만, 같은 단지는 그달 가장 비싼 1건 · 해제 거래 제외', '자료: 국토교통부 실거래가 공개시스템',
          '', '우리 동네 실거래가는 프로필 링크에서 👆', '',
          ' '.join([f'#{kind}', f'#{size}제곱미터', '#아파트실거래가', f"#{area_name.replace(' ', '')}아파트", '#신고가', '#부동산', '#내집마련'])]
    return '\n'.join(L)


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    KST = datetime.timezone(datetime.timedelta(hours=9))
    if len(a) > 2: ym = a[2]
    else:
        t = datetime.datetime.now(KST).date().replace(day=1) - datetime.timedelta(days=1); ym = f'{t.year}-{t.month:02d}'
    OUT = a[1]; os.makedirs(OUT, exist_ok=True)
    S = {'month': ym, 'label': f'{int(ym[:4])}년 {int(ym[5:7])}월', 'short': f'{int(ym[2:4])}년 {int(ym[5:7])}월', 'key': f'{ym}_top',
         'made': datetime.datetime.now(KST).date().isoformat(),   # 만든 날 – 카톡·인스타는 이 날짜가 오늘일 때만 보냄
         'cards': [f'{k}_{z}' for z in SIZES for k in ('seoul', 'gg')]}
    LISTS = json.load(open(a[0], encoding='utf-8')) if '--lists' in sys.argv else None   # 시험용: {"84": {"seoul": [...], "gg": [...]}, "59": {...}}
    for size, (lo, hi, kind, chip) in SIZES.items():
        L = LISTS.get(size, {}) if LISTS is not None else compute(a[0], ym, lo, hi)
        for key, nm in (('seoul', '서울'), ('gg', '경기')):
            rows = L.get(key) or []
            if not rows: print(nm, kind, '자료 없음'); continue
            draw(rows, nm, ym, os.path.join(OUT, f'{key}_{size}.png'), size)
            open(os.path.join(OUT, f'caption_{key}_{size}.txt'), 'w', encoding='utf-8').write(caption(rows, nm, ym, size))
            S[f'{key}_{size}'] = [{'region': r, 'apt': ap, 'umd': u, 'price_man': p, 'area': ar} for r, ap, u, p, ar in rows]
            print(f'{nm} {kind} TOP {len(rows)} → {key}_{size}.png')
    json.dump(S, open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
