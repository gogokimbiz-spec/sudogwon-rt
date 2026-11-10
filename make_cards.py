"""오늘의 신고가 인스타그램 카드 이미지(1080×1080)를 만듭니다 (GitHub Actions 용).
사용법: python make_cards.py site/summary.json site/cards
결과: <출력폴더>/01.png(표지), 02.png…(신고가 단지별, 최대 8장), 마지막(안내), caption.txt(게시 문구)
필요: Pillow, 한글 폰트(Noto Sans CJK KR – Actions 에서는 apt 로 fonts-noto-cjk 설치)
"""
import sys, os, glob, json, datetime
from PIL import Image, ImageDraw, ImageFont

S = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
W = H = 1080
NAVY, NAVY2, WHITE, MUTED, RED, BLUE, LINE = (15, 39, 66), (24, 58, 98), (255, 255, 255), (150, 170, 195), (255, 92, 92), (110, 166, 255), (52, 82, 120)
CREAM, INK, INK2 = (247, 248, 251), (20, 30, 45), (95, 108, 125)

def font_path(weight):
    for pat in [f'/usr/share/fonts/**/NotoSansCJK-{weight}.ttc', f'/usr/share/fonts/**/NotoSansCJKkr-{weight}.otf', f'/usr/share/fonts/**/*CJK*{weight}*']:
        hits = glob.glob(pat, recursive=True)
        if hits: return hits[0]
    raise SystemExit('한글 폰트(Noto Sans CJK)를 찾지 못했습니다')
def F(size, weight='Bold'):
    p = font_path(weight)
    if p.endswith('.ttc'):
        for i in range(10):
            try:
                f = ImageFont.truetype(p, size, index=i)
                if 'KR' in f.getname()[0]: return f
            except Exception: break
    return ImageFont.truetype(p, size)

def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}' if m else f'{e}억') if e else f'{m:,}만'
def man_unit(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}만' if m else f'{e}억') if e else f'{m:,}만'
def wrap(d, text, font, maxw):
    lines, cur = [], ''
    for ch in text:
        if d.textlength(cur + ch, font=font) > maxw and cur:
            lines.append(cur); cur = ch
        else: cur += ch
    if cur: lines.append(cur)
    return lines
def rr(d, box, r, fill=None, outline=None, width=1): d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

day = datetime.date.fromisoformat(S['day']); wd = '월화수목금토일'[day.weekday()]
LB = S.get('label') or f"{day.month}월 {day.day}일({wd})"
LBS = LB.replace('(', ' (')
nh = S.get('new_highs') or []
items = nh[:8]
title_word = '신고가' if nh else '거래가 TOP'
if not nh: items = (S.get('day_trades') or [])[:5]
BRAND = '데이터로 보는 재테크'
total = len(items) + 2

def footer(d, i, dark=True):
    c = MUTED if dark else INK2
    d.text((72, H - 78), BRAND, font=F(28, 'Medium'), fill=c)
    t = f'{i} / {total}'
    d.text((W - 72 - d.textlength(t, font=F(28, 'Medium')), H - 78), t, font=F(28, 'Medium'), fill=c)

# ── 1. 표지
im = Image.new('RGB', (W, H), NAVY); d = ImageDraw.Draw(im)
for k in range(0, H, 6):  # 은은한 대각 그라데이션
    a = k / H; d.line([(0, k), (W, k)], fill=(int(NAVY[0] + (NAVY2[0] - NAVY[0]) * a), int(NAVY[1] + (NAVY2[1] - NAVY[1]) * a), int(NAVY[2] + (NAVY2[2] - NAVY[2]) * a)), width=6)
rr(d, (72, 96, 72 + d.textlength(f'{LBS} 계약', font=F(34)) + 48, 156), 30, fill=RED)
d.text((96, 104), f'{LBS} 계약', font=F(34), fill=WHITE)
d.text((72, 210), '수도권 아파트', font=F(64, 'Medium'), fill=(220, 230, 245))
d.text((72, 290), f'오늘의 {title_word}', font=F(118, 'Black'), fill=WHITE)
d.text((72, 430), f"{len(nh) if nh else len(items)}건", font=F(150, 'Black'), fill=RED)
y = 640
for t in items[:3]:
    nm = t['apt'] if len(t['apt']) <= 14 else t['apt'][:14] + '…'
    d.text((72, y), f"· {t['region'].split(' ')[-1]}  {nm}", font=F(38, 'Medium'), fill=(220, 230, 245))
    d.text((W - 72 - d.textlength(man(t['price_man']), font=F(40)), y), man(t['price_man']), font=F(40), fill=WHITE)
    y += 64
if len(items) > 3: d.text((72, y + 4), f'외 {len(items) - 3}건 → 넘겨서 보기', font=F(32, 'Medium'), fill=BLUE)
d.line([(72, H - 110), (W - 72, H - 110)], fill=LINE, width=2)
footer(d, 1)
im.save(os.path.join(OUT, '01.png'))

# ── 2. 단지별 카드
for i, t in enumerate(items, start=2):
    im = Image.new('RGB', (W, H), CREAM); d = ImageDraw.Draw(im)
    rr(d, (40, 40, W - 40, H - 130), 36, fill=WHITE)
    reg = t['region']
    pill = F(32); pw = d.textlength(reg, font=pill)
    rr(d, (88, 92, 88 + pw + 44, 148), 28, fill=NAVY); d.text((110, 98), reg, font=pill, fill=WHITE)
    if t.get('new_high'):
        tw = d.textlength('신고가', font=F(32)); rr(d, (W - 88 - tw - 44, 92, W - 88, 148), 28, fill=RED); d.text((W - 88 - tw - 22, 98), '신고가', font=F(32), fill=WHITE)
    lines = wrap(d, t['apt'], F(70, 'Black'), W - 176)[:2]
    y = 186
    for ln in lines: d.text((88, y), ln, font=F(70, 'Black'), fill=INK); y += 88
    d.text((88, y + 6), f"{t.get('umd', '')} · 전용 {t['area']}㎡ · {t['floor']}층 · {t['built']}년", font=F(34, 'Medium'), fill=INK2)
    y += 130
    d.text((88, y), '거래가', font=F(36, 'Medium'), fill=INK2)
    d.text((88, y + 46), man_unit(t['price_man']) + '원', font=F(116, 'Black'), fill=RED if t.get('new_high') else INK)
    y += 228
    d.line([(88, y), (W - 88, y)], fill=(230, 234, 240), width=3)
    y += 30
    if t.get('new_high'):
        prev = t['prev_high_man']; diff = t['price_man'] - prev; pct = diff / prev * 100
        pd = datetime.date.fromisoformat(t['prev_high_date'])
        d.text((88, y), '이전 최고가', font=F(36, 'Medium'), fill=INK2)
        v = f"{man_unit(prev)}원 ({pd.month}.{pd.day})"; d.text((W - 88 - d.textlength(v, font=F(40)), y - 2), v, font=F(40), fill=INK2)
        y += 76
        badge = f"▲ {man_unit(diff)}원 · +{pct:.1f}%"; bw = d.textlength(badge, font=F(44))
        rr(d, (88, y, 88 + bw + 56, y + 76), 38, fill=(255, 235, 235)); d.text((116, y + 10), badge, font=F(44), fill=RED)
        y += 110
    d.text((88, y), '3.3㎡당', font=F(36, 'Medium'), fill=INK2)
    v = f"{man_unit(t['pp_man'])}원"; d.text((W - 88 - d.textlength(v, font=F(40)), y - 2), v, font=F(40), fill=INK)
    d.text((88, H - 186), '출처: 국토교통부 실거래가 공개시스템 · 계약일 기준', font=F(26, 'Regular'), fill=INK2)
    footer(d, i, dark=False)
    im.save(os.path.join(OUT, f'{i:02d}.png'))

# ── 3. 마지막 안내
im = Image.new('RGB', (W, H), NAVY); d = ImageDraw.Draw(im)
d.text((72, 200), '우리 동네', font=F(72, 'Medium'), fill=(220, 230, 245))
d.text((72, 290), '실거래가가', font=F(110, 'Black'), fill=WHITE)
d.text((72, 420), '궁금하다면?', font=F(110, 'Black'), fill=WHITE)
rows = ['🗺  76개 시군구 지도', '📍  지역별 신고가·최근 거래', '📰  매일 아침 부동산 브리핑']
y = 600
for r_ in rows:
    d.text((72, y), r_.replace('🗺', '•').replace('📍', '•').replace('📰', '•'), font=F(42, 'Medium'), fill=(220, 230, 245)); y += 66
rr(d, (72, 830, W - 72, 920), 46, fill=RED)
msg = '프로필 링크에서 확인하세요'; d.text(((W - d.textlength(msg, font=F(44))) / 2, 846), msg, font=F(44), fill=WHITE)
footer(d, total)
im.save(os.path.join(OUT, f'{total:02d}.png'))

# ── 게시 문구
tags = ' '.join('#' + x for x in ['아파트실거래가', '신고가', '수도권아파트', '부동산', '아파트', '내집마련', '부동산정보'] +
                list(dict.fromkeys(t['region'].split(' ')[-1] for t in items))[:5])
cap = [f"🔺 {LB} 수도권 아파트 {title_word} {len(nh) if nh else len(items)}건", '']
cap += [f"· {t['region']} {t['apt']} {t['area']}㎡ {man_unit(t['price_man'])}원" + (f" (이전 {man_unit(t['prev_high_man'])})" if t.get('new_high') else '') for t in items]
cap += ['', '※ 신고가: 같은 단지·같은 면적의 최근 6개월 거래 중 최고가 경신', '※ 계약 후 30일 안에 신고되므로 건수는 늘어날 수 있어요',
        '자료: 국토교통부 실거래가 공개시스템', '', '지역별 지도·전체 거래는 프로필 링크에서 👆', '', tags]
open(os.path.join(OUT, 'caption.txt'), 'w', encoding='utf-8').write('\n'.join(cap))
print(f'카드 {total}장 생성 → {OUT}')

# ── 한 장 요약 이미지 (1080×1350, 인스타 세로 4:5) – card_style.py 공통 디자인 ─────────────────
import card_style as C
im, d = C.canvas(); SH = C.SH
cnt = f"{len(nh) if nh else len(items)}건"
C.header(d, F, f'{LBS} 계약', f'수도권 아파트 {title_word}', cnt,
         '같은 단지·같은 면적 최근 6개월 최고가 경신' if nh else '이 날 거래가 높은 순')
rows_ = items[:7]
top, bottom = 340, SH - 170
if nh and len(nh) > len(rows_): bottom -= 40          # '외 N건' 안내 자리
rh = min(128, (bottom - top) // max(1, len(rows_)))
y = top
for k, t in enumerate(rows_):
    C.row_box(d, y, rh - 14)
    cy = y + (rh - 14) // 2
    reg = t['region'].split(' ')[-1] if t['region'].split(' ')[0] in ('서울', '인천') else t['region'].split(' ')[0]
    cw = C.chip(d, F, 64, cy - 52, reg)
    nmf = F(40, 'Black'); nx = 64 + cw + 14; maxw = W - 64 - nx - 300   # 가격과 겹치지 않도록
    nm = t['apt']
    while d.textlength(nm, font=nmf) > maxw and len(nm) > 4: nm = nm.rstrip('…')[:-1] + '…'
    d.text((nx, cy - 58), nm, font=nmf, fill=C.INK)
    d.text((64, cy + 4), f"전용 {t['area']}㎡ · {t['floor']}층 · {t['built']}년", font=F(27, 'Medium'), fill=C.INK2)
    pr = man(t['price_man']); pfnt = F(50, 'Black')
    d.text((W - 64 - d.textlength(pr, font=pfnt), cy - 60), pr, font=pfnt, fill=C.INK)
    if t.get('new_high'):
        diff = t['price_man'] - t['prev_high_man']; pct = diff / t['prev_high_man'] * 100
        sub = f"▲{man_unit(diff)} (+{pct:.1f}%)"; sf = F(28)
        d.text((W - 64 - d.textlength(sub, font=sf), cy + 4), sub, font=sf, fill=C.UP)
    y += rh
more = (len(nh) - len(rows_)) if nh else 0
if more > 0: d.text((64, y + 2), f'외 {more}건은 프로필 링크에서', font=F(28, 'Medium'), fill=C.INK2)
C.cta(d, F, '우리 동네 실거래가 → 프로필 링크')
C.footer(d, F, '자료 국토교통부 실거래가 공개시스템 · 가격 단위 만원')
im.save(os.path.join(OUT, 'single.png'))
print('한 장 요약 이미지 → single.png')
