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
_dd = lambda t: datetime.date.fromisoformat(t['date']) if t.get('date') else DAY   # 거래마다 실제 계약일
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
    d.text((64, y + 4), f"{t.get('umd', '')} · 전용 {t['area']}㎡ · {t['floor']}층 · {t['built']}년 · {_dd(t).month}.{_dd(t).day} 계약", font=F(30, 'Medium'), fill=C.INK2)
    y += 70
    d.text((64, y), '거래가', font=F(32, 'Medium'), fill=C.INK2)
    d.text((62, y + 36), man_unit(t['price_man']) + '원', font=F(104, 'Black'), fill=C.ORANGE if t.get('new_high') else C.INK)
    if t.get('new_high'):
        prev = t['prev_high_man']; diff = t['price_man'] - prev; pct = diff / prev * 100
        pd = datetime.date.fromisoformat(t['prev_high_date'])
        bt = f"▲ {man_unit(diff)} · +{pct:.1f}%"; bf = F(34); bw = d.textlength(bt, font=bf)
        by_ = y + 172                                       # 가격 아래 한 줄: 왼쪽 상승 배지, 오른쪽 이전 최고가
        rr(d, (64, by_, 64 + bw + 44, by_ + 60), 30, fill=(255, 255, 255)); d.text((86, by_ + 6), bt, font=bf, fill=C.T['bg'])
        v = f"이전 최고 {man_unit(prev)} ({pd.month}.{pd.day})" if pd.year == _dd(t).year else f"이전 최고 {man_unit(prev)} ({pd.year}.{pd.month})"; d.text((W - 64 - d.textlength(v, font=F(28, 'Medium')), by_ + 14), v, font=F(28, 'Medium'), fill=C.INK2)
        y += 94
    y += 170
    pts = series(t)
    if len(pts) >= 3:
        hl = (_dd(t), t['price_man'])
        if all(not (p == t['price_man'] and dt == _dd(t)) for dt, p in pts): pts = sorted(pts + [hl])
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
        foot = '자료 국토교통부 실거래가 공개시스템'
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
cap += ['', f"※ 신고가: 같은 단지·같은 면적의 {S.get('high_text') or '최근 6개월 최고가'} 경신", ('※ 어제 새로 신고된 거래 기준 (계약일은 며칠 전일 수 있어요)' if S.get('basis') == 'reported' else '※ 계약 후 30일 안에 신고되므로 건수는 늘어날 수 있어요'),
        '자료: 국토교통부 실거래가 공개시스템', '', '지역별 지도·전체 거래는 프로필 링크에서 👆', '', tags]
open(os.path.join(OUT, 'caption.txt'), 'w', encoding='utf-8').write('\n'.join(cap))

# ── 한 장 요약 이미지 (1080×1350) – 오늘의 실거래가격 5 + 신고가 5 (가격순 5위마다 1건, 같은 구는 1건만), 한쪽이 모자라면 다른 쪽으로 채워 10줄
#    (2026-11-12 변경: 고정 11개 '주요 지역' 대신 수도권 전체. 블로그 '오늘의 주요 거래 6건'과 같은 규칙)
def summary_card(TRADES, NHS, TCNT, NHCNT, TITLE, outs):
    """한 장 요약 카드. 수도권 전체(single.png)와 5개 권역 카드(region_*.png)가 같이 씀 (2026-11-18)"""
    _key = lambda t: (t['region'], t['apt'], t['area'], t.get('floor'), t['price_man'])
    # 2026-11-18: 같은 구(시군구)는 카드 전체에서 1건만 → 여러 지역이 보이게. 줄 수는 실거래가격 4 + 신고가 4 = 8줄 (CARD_EACH 로 조정)
    EACH = int(os.environ.get('CARD_EACH', '4') or 4); TOTAL = EACH * 2   # 11-18: 10줄 → 8줄 (폰에서 글씨가 작아서)
    top_all = sorted(TRADES, key=lambda t: -t['price_man'])
    used = set()                                           # 이미 카드에 나온 구
    STEP = int(os.environ.get('CARD_STEP', '5') or 5)      # 2026-11-18: 가격 순위를 5위씩 끊어 구간마다 1건 (1~5위 중 1, 6~10위 중 1, …) → 여러 가격대·지역이 보이게
    RANK = {}                                              # 카드에 'n위'로 표시할 순위
    def stp(pool):                                     # 건수가 적으면 구간을 좁힘 (신고가 9건이면 1위씩) → 적은 날에도 5건 채움
        return max(1, min(STEP, len(pool) // EACH))
    def pick(pool, n, skip=(), start=0):
        out, b, st = [], start, stp(pool)
        while len(out) < n and b * st < len(pool):
            for i in range(b * st, min((b + 1) * st, len(pool))):
                t = pool[i]
                if t['region'] in used or _key(t) in skip: continue
                out.append(t); used.add(t['region']); RANK[id(t)] = i + 1; break
            b += 1
        # 2026-11-23: 거래가 적고 같은 구에 몰린 날(주말·권역 카드)은 구가 겹쳐도 비싼 순으로 채움 → 빈 줄이 안 생기게
        if len(out) < n:
            for i, t in enumerate(pool):
                if len(out) >= n: break
                if id(t) in RANK or _key(t) in skip or t in out: continue
                out.append(t); RANK[id(t)] = i + 1
            out.sort(key=lambda t: RANK[id(t)])
        return out
    mt = pick(top_all, EACH)
    nh_sorted = sorted(NHS, key=lambda t: -t['price_man'])
    nhx = pick(nh_sorted, EACH, {_key(x) for x in mt})
    if len(mt) + len(nhx) < TOTAL:                         # 한쪽이 모자라면 다른 쪽으로 채움 (구 중복 없이, 이어지는 구간에서)
        _last = lambda xs, pool: (max(RANK.get(id(x), 0) for x in xs) - 1) // stp(pool) + 1 if xs else 0
        if len(nhx) < EACH: mt += pick(top_all, TOTAL - len(mt) - len(nhx), {_key(x) for x in mt + nhx}, _last(mt, top_all))
        else: nhx += pick(nh_sorted, TOTAL - len(mt) - len(nhx), {_key(x) for x in mt + nhx}, _last(nhx, nh_sorted))
        mt.sort(key=lambda t: RANK.get(id(t), 0)); nhx.sort(key=lambda t: RANK.get(id(t), 0))
    n_nh, n_top = len(nhx), len(mt)
    _nh_left = [t for t in NHS if _key(t) not in {_key(x) for x in mt + nhx}]
    _st = lambda pool: f'가격순 {stp(pool)}위마다 1건' if stp(pool) > 1 else '가격순'
    secs = [('오늘의 실거래가격', f"{TCNT:,}건 · {_st(top_all)}", mt),
            ('신고가', f'{NHCNT:,}건 · {_st(nh_sorted)}', nhx)]
    secs = [x for x in secs if x[2]]
    if not secs:                                          # 둘 다 없으면 그날 거래가 높은 순
        secs = [('거래가 높은 순', f"{TCNT:,}건 중", top_all[:TOTAL])]
    GAP = 36                                               # 날짜칩과 제목 사이를 좁힘 (2026-11-18)
    im, d = C.canvas(); SH = C.SH
    C.header(d, F, f"{LBS} {'신고' if S.get('basis') == 'reported' else '계약'}", TITLE, '', f"오늘의 실거래가격 · 신고가 (같은 단지·면적 {(S.get('high_text') or '최근 6개월 최고가').replace(' 역대', '')} 경신)", gap=GAP)
    nrows = sum(len(x[2]) for x in secs)
    more = max(0, NHCNT - len(nhx) - sum(1 for x in mt if x.get('new_high')))
    more_tr = max(0, TCNT - len(mt) - len(nhx))
    CTA_TOP = SH - 132                                     # 노란 버튼을 낮게(64px) → 그만큼 위 10줄을 크게 (2026-11-18)
    bottom = CTA_TOP - 14 - (76 if (more > 0 or more_tr > 0) else 0)
    Y0 = 330 - GAP - 8; SECH = 54
    rh = min(118, (bottom - Y0 - SECH * len(secs) - 14 * (len(secs) - 1)) // max(1, nrows))
    k = min(1.0, rh / 118)                                 # 줄이 낮아지면 글씨도 같이 줄임
    Z = lambda v: max(18, int(round(v * (0.55 + 0.45 * k))))
    y = Y0
    for si, (title, sub, rows) in enumerate(secs):
        if si: y += 14
        d.text((64, y + 2), title, font=F(32, 'Black'), fill=C.INK)
        d.text((64 + d.textlength(title, font=F(32, 'Black')) + 16, y + 12), sub, font=F(23, 'Medium'), fill=C.INK2)
        y += SECH
        h = rh - 10                                        # 줄 안쪽 높이 – 글씨 크기를 여기에 맞춤 (10줄이면 약 58px)
        fn, fs, fp = min(40, int(h * 0.52)), min(27, int(h * 0.36)), min(48, int(h * 0.66))
        for t in rows:
            C.row_box(d, y, h)
            p_ = t['region'].split(' ')
            chip = p_[1] if p_[0] in ('서울', '인천') else (p_[0] + ' ' + p_[1][:-1]) if len(p_) > 1 else p_[0][:-1]
            cw = C.chip(d, F, 64, y + 1, chip, size=fs)
            nmf = F(fn, 'Black'); nx = 64 + cw + 12; maxw = W - 64 - nx - 270
            nm = t['apt']
            while d.textlength(nm, font=nmf) > maxw and len(nm) > 4: nm = nm.rstrip('…')[:-1] + '…'
            d.text((nx, y - fn * 0.12), nm, font=nmf, fill=C.INK)
            d.text((64, y + fn * 1.08), (f"{RANK[id(t)]}위 · " if id(t) in RANK else '') + (f"{t.get('umd', '')} · " if title == '오늘의 실거래가격' else '') + f"전용 {t['area']}㎡ · {t['floor']}층 · {t['built']}년",
                   font=F(fs, 'Medium'), fill=C.INK2)
            pr = man(t['price_man']); pf = F(fp, 'Black')
            d.text((W - 64 - d.textlength(pr, font=pf), y - fp * 0.18), pr, font=pf, fill=C.INK)
            if t.get('new_high'):
                diff = t['price_man'] - t['prev_high_man']; pct = diff / t['prev_high_man'] * 100
                s2 = (f"신고가 ▲{man_unit(diff)}" if title == '오늘의 실거래가격' else f"▲{man_unit(diff)} (+{pct:.1f}%)"); sf = F(fs)
                d.text((W - 64 - d.textlength(s2, font=sf), y + fn * 1.08), s2, font=sf, fill=C.UP)
            y += rh
    if more > 0 or more_tr > 0:                             # 2026-11-18: '더 많다'가 한눈에 보이게 큰 안내 상자
        by0 = CTA_TOP - 14 - 66
        d.rounded_rectangle((40, by0, W - 40, by0 + 62), 12, outline=C.ORANGE, width=3)
        segs = [('이 밖에도 ', C.INK, 'Bold')]
        if more > 0: segs += [(f'신고가 {more:,}건', C.ORANGE, 'Black')]
        if more > 0 and more_tr > 0: segs += [(' · ', C.INK2, 'Bold')]
        if more_tr > 0: segs += [(f'실거래 {more_tr:,}건', C.ORANGE, 'Black')]
        segs += [(' 더 있어요', C.INK, 'Bold')]
        fs = 34
        while fs > 24 and sum(d.textlength(t_, font=F(fs, w_)) for t_, _, w_ in segs) > W - 120: fs -= 2
        x_ = (W - sum(d.textlength(t_, font=F(fs, w_)) for t_, _, w_ in segs)) / 2
        for t_, c_, w_ in segs:
            d.text((x_, by0 + 31 - fs * 0.62), t_, font=F(fs, w_), fill=c_); x_ += d.textlength(t_, font=F(fs, w_))
    _cm = '전체 거래·신고가 보기 → 프로필 링크'
    d.rounded_rectangle((40, CTA_TOP, W - 40, CTA_TOP + 64), 10, fill=C.ORANGE)
    d.text(((W - d.textlength(_cm, font=F(32))) / 2, CTA_TOP + 9), _cm, font=F(32), fill=C.T.get('cta_t', C.T.get('pill_t', C.WHITE) if C.T['accent'] == C.T['pill'] else C.WHITE))
    C.footer(d, F, '자료 국토교통부 실거래가 공개시스템 · 가격 단위 만원')
    for o in outs: im.save(os.path.join(OUT, o))
    return len(mt), len(nhx)


n_top, n_nh = summary_card(S.get('day_trades_60') or S.get('day_trades') or [], nh, S.get('trade_count') or 0, len(nh),
                           '수도권 아파트 실거래', ['single.png', '01.png'])   # 01 = 캐러셀 표지
# ── 5개 권역 카드 (서울 · 인천 · 경기 북부 · 경기 남서부 · 경기 남동부) – build.py 의 summary['groups'] (2026-11-18)
for gi, g in enumerate(S.get('groups') or [], 1):
    if not g.get('trades'): continue
    summary_card(g['trades'], g.get('new_highs') or [], g.get('trade_count') or 0, g.get('nh_count') or 0,
                 f"{g['name']} 아파트 실거래", [f'region_{gi}.png'])
    print(f"권역 카드 {gi}: {g['name']} → region_{gi}.png")
print(f'한 장 요약 이미지 → single.png (실거래가격 {n_top} + 신고가 {n_nh}), 캐러셀 {total}장(01=요약) → {OUT}')
