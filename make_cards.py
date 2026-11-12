"""오늘의 신고가 인스타그램 카드 이미지(1080×1350)를 만듭니다 (GitHub Actions 용).
사용법: python make_cards.py site/summary.json site/cards [hist 폴더=hist] [rt_data.json]
결과: <출력폴더>/01.png(표지=요약), 02.png…(신고가 단지별, 최대 8장), 마지막(안내), single.png, caption.txt – 모두 1080×1350, card_style 의 slate 테마. 단지별 카드에 같은 단지·면적 최근 3년 거래 그래프(hist/ + rt_data.json)
필요: Pillow, 한글 폰트(Noto Sans CJK KR – Actions 에서는 apt 로 fonts-noto-cjk 설치)
"""
import sys, os, glob, json, datetime, statistics
from PIL import Image, ImageDraw, ImageFont
os.environ.setdefault('CARD_THEME', 'slate')   # 실거래 카드는 슬레이트(어두운 회청색) + 흰 글씨 (2026-11-11)

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

import card_style as C                                 # 공통 디자인 (재무·청약 카드와 같은 크림색 테마)
W, H = C.W, C.SH                                     # 캐러셀도 1080×1350 (인스타 세로 4:5)
T = C.T


def page_no(d, i):
    t = f'{i} / {total}'; f = F(26, 'Medium')
    d.text((W - 64 - d.textlength(t, font=f), 70), t, font=f, fill=C.INK2)


# ── 1. 표지 = 한 장 요약 이미지(single.png) – 맨 아래에서 만든 뒤 01.png 로 복사

# ── 2. 단지별 카드 + 최근 3년 거래 흐름 그래프 (2026-11-11)
HIST = sys.argv[3] if len(sys.argv) > 3 else 'hist'
RTF = sys.argv[4] if len(sys.argv) > 4 else 'rt_data.json'
try: CODE_OF = {v: k for k, v in json.load(open('names.json', encoding='utf-8')).items()}
except Exception: CODE_OF = {}
try: RT_ROWS = json.load(open(RTF, encoding='utf-8'))['trade']   # [code, date, apt, umd, area, floor, price, built, 해제]
except Exception: RT_ROWS = []
_hist_cache = {}
def hist_rows(code):
    if code not in _hist_cache:
        rows = []
        for f in glob.glob(os.path.join(HIST, code, '*.json')):
            try: rows += json.load(open(f, encoding='utf-8'))   # [date, apt, umd, area, floor, price, 해제]
            except Exception: pass
        _hist_cache[code] = rows
    return _hist_cache[code]
DAY = datetime.date.fromisoformat(S['day'])
def series(t):
    code = CODE_OF.get(t['region'])
    if not code: return []
    apt, umd, ar = t['apt'], t.get('umd', ''), round(t['area'])
    cut = (DAY - datetime.timedelta(365 * 3)).isoformat()
    pts = {(r[1], r[5], r[6]) for r in RT_ROWS if r[0] == code and r[2] == apt and r[3] == umd and round(r[4]) == ar and r[8] != 'O' and r[1] >= cut}
    pts |= {(r[0], r[4], r[5]) for r in hist_rows(code) if r[1] == apt and r[2] == umd and round(r[3]) == ar and r[6] != 'O' and r[0] >= cut}
    return sorted((datetime.date.fromisoformat(dt), p) for dt, fl, p in pts)
def eok(v):
    return (f'{v / 10000:.1f}억'.replace('.0억', '억')) if v >= 10000 else f'{v / 10000:.2f}억'
def chart(d, box, pts, hl):
    x0, y0, x1, y1 = box
    d.rounded_rectangle((x0 - 28, y0 - 30, x1 + 28, y1 + 56), 16, fill=C.T['card'])
    t0, t1 = pts[0][0], max(pts[-1][0], hl[0])
    ps = [p for _, p in pts] + [hl[1]]; lo, hi = min(ps), max(ps); pad = (hi - lo) * 0.12 or hi * 0.05; lo -= pad; hi += pad
    X = lambda t: x0 + (t - t0).days / max(1, (t1 - t0).days) * (x1 - x0)
    Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    for k in range(4):
        v = lo + (hi - lo) * k / 3; yy = Y(v)
        d.line((x0, yy, x1, yy), fill=C.LINE, width=1)
        d.text((x0 + 4, yy - 30), eok(v), font=F(22, 'Medium'), fill=C.INK2)
    mon = {}
    for t, v in pts: mon.setdefault((t.year, t.month), []).append(v)
    clamp = lambda t: min(max(t, t0), t1)
    line = [(X(clamp(datetime.date(y, m, 15))), Y(statistics.median(v))) for (y, m), v in sorted(mon.items())]
    for t, v in pts: d.ellipse((X(t) - 5, Y(v) - 5, X(t) + 5, Y(v) + 5), fill=(140, 150, 162))
    if len(line) > 1: d.line(line, fill=(255, 255, 255), width=4, joint='curve')
    hx, hy = X(hl[0]), Y(hl[1]); d.ellipse((hx - 13, hy - 13, hx + 13, hy + 13), fill=C.ORANGE, outline=(255, 255, 255), width=3)
    for t, right_ in ((t0, False), (t1, True)):
        s_ = f"{t.year % 100}.{t.month}"; f = F(22, 'Medium'); w_ = d.textlength(s_, font=f)
        d.text((x1 - w_ if right_ else x0, y1 + 14), s_, font=f, fill=C.INK2)
    first, last = statistics.median(mon[min(mon)]), statistics.median(mon[max(mon)])
    nmon = (t1.year - t0.year) * 12 + t1.month - t0.month
    return (last / first - 1) * 100, nmon

for i, t in enumerate(items, start=2):
    im, d = C.canvas()
    d.rectangle((40, 30, W - 40, 36), fill=C.ORANGE)
    cw = C.chip(d, F, 64, 64, t['region'], size=30)
    if t.get('new_high'):
        bf = F(30); bw = d.textlength('신고가', font=bf)
        rr(d, (64 + cw + 14, 64, 64 + cw + 14 + bw + 32, 108), 6, fill=C.ORANGE); d.text((64 + cw + 30, 67), '신고가', font=bf, fill=C.T['pill_t'])
    page_no(d, i)
    y = 138
    for ln in wrap(d, t['apt'], F(64, 'Black'), W - 128)[:2]:
        d.text((62, y), ln, font=F(64, 'Black'), fill=C.INK); y += 80
    d.text((64, y + 4), f"{t.get('umd', '')} · 전용 {t['area']}㎡ · {t['floor']}층 · {t['built']}년 · {DAY.month}.{DAY.day} 계약", font=F(30, 'Medium'), fill=C.INK2)
    y += 70
    d.text((64, y), '거래가', font=F(32, 'Medium'), fill=C.INK2)
    d.text((62, y + 36), man_unit(t['price_man']) + '원', font=F(104, 'Black'), fill=C.ORANGE if t.get('new_high') else C.INK)
    if t.get('new_high'):
        prev = t['prev_high_man']; diff = t['price_man'] - prev; pct = diff / prev * 100
        pd = datetime.date.fromisoformat(t['prev_high_date'])
        bt = f"▲ {man_unit(diff)} · +{pct:.1f}%"; bf = F(34); bw = d.textlength(bt, font=bf)
        by_ = y + 172                                       # 가격 아래 한 줄: 왼쪽 상승 배지, 오른쪽 이전 최고가
        rr(d, (64, by_, 64 + bw + 44, by_ + 60), 30, fill=(255, 255, 255)); d.text((86, by_ + 6), bt, font=bf, fill=C.T['bg'])
        v = f"이전 최고 {man_unit(prev)} ({pd.month}.{pd.day})"; d.text((W - 64 - d.textlength(v, font=F(28, 'Medium')), by_ + 14), v, font=F(28, 'Medium'), fill=C.INK2)
        y += 94
    y += 170
    pts = series(t)
    if len(pts) >= 3:
        hl = (DAY, t['price_man'])
        if all(not (p == t['price_man'] and dt == DAY) for dt, p in pts): pts = sorted(pts + [hl])
        cy0 = y + 70; cy1 = C.SH - 270
        chg, nmon = chart(d, (92, cy0 + 40, W - 92, cy1), pts, hl)
        d.text((64, y), '같은 면적 거래 흐름', font=F(34, 'Black'), fill=C.INK)
        per = f"{round(nmon / 12)}년" if nmon >= 24 else f"{max(1, nmon)}개월"
        s2 = f"{per} {'+' if chg >= 0 else ''}{chg:.0f}% · {len(pts)}건"
        d.text((W - 64 - d.textlength(s2, font=F(30)), y + 4), s2, font=F(30), fill=C.UP if chg >= 0 else C.DOWN)
        foot = '자료 국토교통부 실거래가 · 점=거래, 선=월 중간값, 노란 점=이번 거래'
    else:                                                  # 거래가 너무 적으면 숫자만
        d.line([(40, y), (W - 40, y)], fill=C.LINE, width=2); y += 36
        d.text((64, y), '3.3㎡당', font=F(36, 'Medium'), fill=C.INK2)
        v = f"{man_unit(t['pp_man'])}원"; d.text((W - 64 - d.textlength(v, font=F(40)), y - 2), v, font=F(40), fill=C.INK)
        y += 70
        d.text((64, y), '최근 3년 같은 면적 거래가 적어 그래프는 생략했어요', font=F(28, 'Medium'), fill=C.INK2)
        foot = '자료 국토교통부 실거래가 공개시스템 · 계약일 기준'
    C.cta(d, F, '우리 동네 실거래가 → 프로필 링크')
    C.footer(d, F, foot)
    im.save(os.path.join(OUT, f'{i:02d}.png'))

# ── 3. 마지막 안내
im, d = C.canvas()
C.header(d, F, '데이터로 보는 재테크', '우리 동네 실거래가', '', '궁금하다면 프로필 링크에서 확인하세요')
y = 400
for r_ in ['수도권 76개 시군구 실거래 지도', '지역별 신고가 · 최근 거래', '매일 아침 부동산 브리핑', '월~금 청약 / 토 기업재무']:
    C.row_box(d, y, 110); d.text((64, y + 30), '• ' + r_, font=F(44, 'Medium'), fill=C.INK); y += 130
C.cta(d, F, '프로필 링크에서 확인하세요')
C.footer(d, F, '자료 국토교통부 · 청약홈 · DART')
im.save(os.path.join(OUT, f'{total:02d}.png'))

# ── 게시 문구
tags = ' '.join('#' + x for x in ['아파트실거래가', '신고가', '수도권아파트', '부동산', '아파트', '내집마련', '부동산정보'] +
                list(dict.fromkeys(t['region'].split(' ')[-1] for t in items))[:5])
cap = [f"🔺 {LB} 수도권 아파트 {title_word} {len(nh) if nh else len(items)}건", '']
cap += [f"· {t['region']} {t['apt']} {t['area']}㎡ {man_unit(t['price_man'])}원" + (f" (이전 {man_unit(t['prev_high_man'])})" if t.get('new_high') else '') for t in items]
_mt = sorted(S.get('day_trades') or [], key=lambda t: -t['price_man'])[:3]
if _mt:
    cap += ['', '💰 오늘의 실거래가격'] + [f"· {t['region']} {t['apt']} {t['area']}㎡ {man_unit(t['price_man'])}원" for t in _mt]
cap += ['', '※ 신고가: 같은 단지·같은 면적의 최근 6개월 거래 중 최고가 경신', '※ 계약 후 30일 안에 신고되므로 건수는 늘어날 수 있어요',
        '자료: 국토교통부 실거래가 공개시스템', '', '지역별 지도·전체 거래는 프로필 링크에서 👆', '', tags]
open(os.path.join(OUT, 'caption.txt'), 'w', encoding='utf-8').write('\n'.join(cap))

# ── 한 장 요약 이미지 (1080×1350) – 오늘의 실거래가격 3(지역 무관 비싼 순) + 신고가 3, 한쪽이 모자라면 다른 쪽으로 채워 6줄
#    (2026-11-12 변경: 고정 11개 '주요 지역' 대신 수도권 전체. 블로그 '오늘의 주요 거래 6건'과 같은 규칙)
_key = lambda t: (t['region'], t['apt'], t['area'], t.get('floor'), t['price_man'])
top_all = sorted(S.get('day_trades') or [], key=lambda t: -t['price_man'])
mt = top_all[:3]
nhx = [t for t in nh if _key(t) not in {_key(x) for x in mt}]
n_nh = min(3, len(nhx))
if len(mt) + n_nh < 6:                                # 신고가가 모자라면 실거래가격을 더
    _nk = {_key(x) for x in nhx[:n_nh]}
    mt += [t for t in top_all[3:] if _key(t) not in _nk][:6 - len(mt) - n_nh]
n_nh = min(len(nhx), 6 - len(mt)); n_top = len(mt)   # 실거래가격이 모자라면 신고가를 더
secs = [('오늘의 실거래가격', f"{S.get('trade_count', 0)}건 중 비싼 순", mt),
        ('신고가', f'{len(nh)}건 중', nhx[:n_nh])]
secs = [x for x in secs if x[2]]
if not secs:                                          # 둘 다 없으면 그날 거래가 높은 순
    secs = [('거래가 높은 순', f"{S.get('trade_count', 0)}건 중", (S.get('day_trades') or [])[:6])]
im, d = C.canvas(); SH = C.SH
C.header(d, F, f'{LBS} 계약', '수도권 아파트 실거래', '', '오늘의 실거래가격 · 신고가 (같은 단지·면적 최근 6개월 최고가 경신)')
nrows = sum(len(x[2]) for x in secs)
more = len(nhx) - (len(secs[-1][2]) if secs[-1][0] == '신고가' else 0)
bottom = SH - 170 - (40 if more > 0 else 0)
rh = min(118, (bottom - 330 - 62 * len(secs) - 18 * (len(secs) - 1)) // max(1, nrows))
y = 330
for si, (title, sub, rows) in enumerate(secs):
    if si: y += 18
    d.text((64, y + 6), title, font=F(34, 'Black'), fill=C.INK)
    d.text((64 + d.textlength(title, font=F(34, 'Black')) + 16, y + 18), sub, font=F(24, 'Medium'), fill=C.INK2)
    y += 62
    for t in rows:
        C.row_box(d, y, rh - 12); cy = y + (rh - 12) // 2
        p_ = t['region'].split(' ')
        chip = p_[1] if p_[0] in ('서울', '인천') else (p_[0] + ' ' + p_[1][:-1]) if len(p_) > 1 else p_[0][:-1]
        cw = C.chip(d, F, 64, cy - 48, chip)
        nmf = F(36, 'Black'); nx = 64 + cw + 14; maxw = W - 64 - nx - 290
        nm = t['apt']
        while d.textlength(nm, font=nmf) > maxw and len(nm) > 4: nm = nm.rstrip('…')[:-1] + '…'
        d.text((nx, cy - 52), nm, font=nmf, fill=C.INK)
        d.text((64, cy + 2), (f"{t.get('umd', '')} · " if title == '오늘의 실거래가격' else '') + f"전용 {t['area']}㎡ · {t['floor']}층 · {t['built']}년",
               font=F(25, 'Medium'), fill=C.INK2)
        pr = man(t['price_man']); pf = F(44, 'Black')
        d.text((W - 64 - d.textlength(pr, font=pf), cy - 54), pr, font=pf, fill=C.INK)
        if t.get('new_high'):
            diff = t['price_man'] - t['prev_high_man']; pct = diff / t['prev_high_man'] * 100
            s2 = (f"신고가 ▲{man_unit(diff)}" if title == '오늘의 실거래가격' else f"▲{man_unit(diff)} (+{pct:.1f}%)"); sf = F(25)
            d.text((W - 64 - d.textlength(s2, font=sf), cy + 6), s2, font=sf, fill=C.UP)
        y += rh
if more > 0: d.text((64, y + 2), f'신고가 외 {more}건은 프로필 링크에서', font=F(26, 'Medium'), fill=C.INK2)
C.cta(d, F, '우리 동네 실거래가 → 프로필 링크')
C.footer(d, F, '자료 국토교통부 실거래가 공개시스템 · 가격 단위 만원')
im.save(os.path.join(OUT, 'single.png'))
im.save(os.path.join(OUT, '01.png'))   # 캐러셀 표지 = 한 장 요약
print(f'한 장 요약 이미지 → single.png (실거래가격 {n_top} + 신고가 {n_nh}), 캐러셀 {total}장(01=요약) → {OUT}')
