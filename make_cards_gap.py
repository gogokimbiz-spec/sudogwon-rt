"""매매·전세 갭 카드 (2026-11-23, 매주 화요일 · 카톡/인스타/블로그/스레드)
사용법: python make_cards_gap.py rt_data.json site/gap [시군구코드]
  - 시군구코드를 안 주면 지역을 자동으로 고름:
    최근 30일 매매+전세 거래가 많은 순으로, 최근 12주 안에 한 번 했던 구는 빼고, 갭 단지가 6곳 이상 나오는 첫 구.
    고른 기록은 저장소 state/gap_used.json ({"YYYY-MM-DD": "코드"}) – daily.yml 이 커밋. 같은 날 다시 돌리면 같은 구를 씀.
결과: OUT/card.png, OUT/caption.txt, OUT/summary.json
계산: 최근 3개월(자료 마지막 계약일 기준 90일) 계약, 같은 단지·같은 전용면적(0.1㎡)에서 매매·전세(월세 0원)가 각각 2건 이상인 곳.
      가격은 중앙값, 갭 = 매매 − 전세. 카드는 갭 큰 3 + 갭 작은 3 (같은 단지는 1줄), 블로그는 전체를 갭 큰 순으로.
전세 단지명: rt_data.json 의 jeonse_apt (fetch.py 2026-11-23~). 없으면(예전 자료) 같은 동·같은 면적에 매매 단지가 1곳뿐일 때만 짝지음.
"""
import os, sys, json, glob, datetime, statistics, collections
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(KST).date()
USED_PATH = os.environ.get('GAP_USED', os.path.join(HERE, 'state', 'gap_used.json'))
DAYS, MIN_N, NEED, SKIP_WEEKS = 90, 2, 6, 12


# ── 폰트 (make_cards_top84.py 와 같은 방식)
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


def won(v):        # 16억 3,000
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억' + (f' {m:,}' if m else '')) if e else f'{m:,}만'


def won_s(v):      # 9.1억 / 8,500만
    return (f'{v / 10000:.1f}억'.replace('.0억', '억')) if v >= 10000 else f'{int(v):,}만'


# ── 계산
def load(rt_path):
    raw = json.load(open(rt_path, encoding='utf-8'))
    names = json.load(open(os.path.join(HERE, 'names.json'), encoding='utf-8'))
    last = max(r[1] for r in raw['trade'])
    d1 = datetime.date.fromisoformat(last); d0 = d1 - datetime.timedelta(days=DAYS - 1)
    return raw, names, d0, d1


def short_name(code, names):
    full = names.get(code, code); last = full.split(' ')[-1]
    dup = sum(1 for v in names.values() if v.split(' ')[-1] == last) > 1      # 서울 중구 / 인천 중구 처럼 겹치면 전체 이름
    return full if dup else last


def gap_rows(raw, code, d0):
    """[[단지, 동, 전용, 준공, 매매건수, 전세건수, 매매중앙값, 전세중앙값], ...] 갭 큰 순"""
    s0 = d0.isoformat()
    T = collections.defaultdict(list); built = {}; who = collections.defaultdict(set)
    for c, date, apt, umd, area, floor, price, by, cd in raw['trade']:
        if c != code or cd == 'O' or area <= 0 or price <= 0: continue
        who[(umd, round(area * 10))].add(apt)
        if date < s0: continue
        k = (apt, umd, round(area * 10)); T[k].append(price); built[k] = by
    J = collections.defaultdict(list)
    ja = raw.get('jeonse_apt')
    if ja and len(ja) == len(raw['jeonse']):
        for (c, date, umd, area, dep), apt in zip(raw['jeonse'], ja):
            if c == code and date >= s0 and dep > 0: J[(apt, umd, round(area * 10))].append(dep)
    else:   # 예전 자료: 같은 동·같은 면적에 매매 단지가 1곳뿐인 경우만
        for c, date, umd, area, dep in raw['jeonse']:
            if c != code or date < s0 or dep <= 0: continue
            a = who.get((umd, round(area * 10)))
            if a and len(a) == 1: J[(next(iter(a)), umd, round(area * 10))].append(dep)
    rows = []
    for k, t in T.items():
        j = J.get(k) or []
        if len(t) < MIN_N or len(j) < MIN_N: continue
        rows.append([k[0], k[1], k[2] / 10, built[k], len(t), len(j), statistics.median(t), statistics.median(j)])
    rows.sort(key=lambda r: r[6] - r[7], reverse=True)
    return rows


def uniq(rs):
    seen, out = set(), []
    for r in rs:
        if r[0] in seen: continue
        seen.add(r[0]); out.append(r)
    return out


def pick6(rows):
    big = uniq(rows)[:3]
    small = [r for r in uniq(rows[::-1]) if r[0] not in {b[0] for b in big}][:3]
    return big, small


def summary_stats(raw, code, d0):
    s0 = d0.isoformat()
    t84 = [p for c, d, a, u, ar, f, p, by, cd in raw['trade'] if c == code and cd != 'O' and d >= s0 and 80 <= ar < 86 and p > 0]
    j84 = [dep for c, d, u, ar, dep in raw['jeonse'] if c == code and d >= s0 and 80 <= ar < 86 and dep > 0]
    bands = []
    for lo, hi, nm in ((0, 60, '60㎡ 이하'), (60, 85, '60~85㎡'), (85, 9999, '85㎡ 초과')):
        t = [p / ar for c, d, a, u, ar, f, p, by, cd in raw['trade'] if c == code and cd != 'O' and d >= s0 and lo < ar <= hi and p > 0]
        j = [dep / ar for c, d, u, ar, dep in raw['jeonse'] if c == code and d >= s0 and lo < ar <= hi and dep > 0]
        if len(t) >= 5 and len(j) >= 5: bands.append([nm, round(statistics.median(j) / statistics.median(t) * 100)])
    a84 = {'t': statistics.median(t84), 'nt': len(t84), 'j': statistics.median(j84), 'nj': len(j84)} if len(t84) >= 5 and len(j84) >= 5 else None
    return a84, bands


def choose(raw, names, d0, d1, force=None):
    used = {}
    try: used = json.load(open(USED_PATH, encoding='utf-8'))
    except Exception: pass
    if force: return force, used
    if used.get(TODAY.isoformat()): return used[TODAY.isoformat()], used      # 같은 날 다시 돌림
    cut = (TODAY - datetime.timedelta(weeks=SKIP_WEEKS)).isoformat()
    recent = {c for d, c in used.items() if d >= cut}
    s30 = (d1 - datetime.timedelta(days=29)).isoformat()
    cnt = collections.Counter()
    for r in raw['trade']:
        if r[1] >= s30 and r[8] != 'O': cnt[r[0]] += 1
    for r in raw['jeonse']:
        if r[1] >= s30: cnt[r[0]] += 1
    for code, n in cnt.most_common():
        if code in recent or code not in names: continue
        big, small = pick6(gap_rows(raw, code, d0))
        if len(big) + len(small) >= NEED: return code, used
        print(f'{names[code]}: 갭 단지가 모자라 건너뜀')
    return None, used


# ── 카드 (card_style slate, 2026-11-23 사용자 확정 시안)
def draw(S, out_png):
    os.environ.setdefault('CARD_THEME', 'slate')
    sys.path.insert(0, HERE); import card_style as C
    # 갭 카드만 색 바꿈 (2026-11-23 사용자 확정): 짙은 녹회색 바탕 + 강조(칩·버튼·아이디 배지)는 실거래 카드와 같은 노랑, 전세 막대는 진한 초록
    BG, YEL = (50, 64, 60), (255, 196, 0)
    C.T = dict(C.T, bg=BG, head=BG, accent=YEL, pill=YEL, pill_t=(40, 48, 46), big=YEL, line=(84, 100, 95), chip_t=BG)
    W, SH, INK, INK2, WHITE, T = C.W, C.SH, C.INK, C.INK2, C.WHITE, C.T
    LINE = T['line']
    JEON, TRACK = (5, 150, 105), (30, 34, 40)           # 전세 진한 초록 · 매매 막대 (배경보다 어두운 회색, 2026-11-23)
    UPC = T.get('up', (255, 120, 110))
    im, d = C.canvas(); d._image = im
    made = datetime.date.fromisoformat(S['made']); p0, p1 = (datetime.date.fromisoformat(x) for x in S['period'])
    GAP = 34
    C.header(d, F, f"{made.month}월 {made.day}일 ({'월화수목금토일'[made.weekday()]}) 매매·전세", f"{S['name']} 아파트 갭", '',
             '같은 단지·같은 전용면적의 매매가 − 전세가 (최근 3개월 중앙값)', gap=GAP)
    # (2026-11-23 사용자: 위쪽 '구 전체 84㎡대' 요약 칸은 뺌 – 블로그 글에만 넣음)
    y0 = 312 - GAP + 30

    RH = 122; BX0, BX1 = 64, W - 64
    def row(y, n, r):
        apt, umd, area, by, nt, nj, mt, mj = r
        g = mt - mj; rt = round(mj / mt * 100)
        cx = C.chip(d, F, 48, y + 4, umd, 22)
        nm = apt; nf = F(34, 'Black'); room = 600 - cx
        while d.textlength(nm, font=nf) > room and len(nm) > 4: nm = nm[:-1]
        if nm != apt: nm = nm[:-1] + '…'
        d.text((48 + cx + 12, y - 4), nm, font=nf, fill=INK)
        d.text((48, y + 42), f"{n}위 · 전용 {area:g}㎡ · {by}년 · 매매 {nt}·전세 {nj}건", font=F(22, 'Regular'), fill=(200, 206, 214))
        gs = won(g); gf = F(44, 'Black'); gx = W - 64 - d.textlength(gs, font=gf)
        d.text((gx, y - 10), gs, font=gf, fill=WHITE)
        lf2 = F(26, 'Bold'); d.text((gx - 12 - d.textlength('갭', font=lf2), y + 6), '갭', font=lf2, fill=INK2)
        ls = f'전세가율 {rt}%'; lf = F(21, 'Medium')
        d.text((W - 64 - d.textlength(ls, font=lf), y + 42), ls, font=lf, fill=INK2)
        by0 = y + 80; bh = 28; xj = BX0 + (BX1 - BX0) * mj / mt
        d.rounded_rectangle((BX0, by0, BX1, by0 + bh), 6, fill=TRACK)
        d.rounded_rectangle((BX0, by0, xj, by0 + bh), 6, fill=JEON)
        d.rectangle((xj - 6, by0, xj, by0 + bh), fill=JEON)
        sf = F(20, 'Bold'); jt = f'전세 {won_s(mj)}'; tt = f'매매 {won_s(mt)}'
        if d.textlength(jt, font=sf) + 16 < xj - BX0: d.text((BX0 + 10, by0 - 0), jt, font=sf, fill=WHITE)
        d.text((BX1 - 10 - d.textlength(tt, font=sf), by0 - 0), tt, font=sf, fill=WHITE)
        d.line((40, y + RH - 6, W - 40, y + RH - 6), fill=LINE, width=2)

    def section(y, title, col, note, rs):
        tf = F(34, 'Black')
        d.rectangle((40, y + 6, 50, y + 42), fill=col)
        d.text((62, y), title, font=tf, fill=INK)
        d.text((62 + d.textlength(title, font=tf) + 14, y + 12), note, font=F(21, 'Regular'), fill=INK2)
        y += 50
        for n, r in enumerate(rs, 1):
            row(y, n, r); y += RH
        return y

    big, small = pick6(S['rows'])
    ys = section(y0, f'갭 큰 단지 TOP {len(big)}', UPC, '전세 끼고 사도 돈이 많이 드는 곳', big) + 24
    section(ys, f'갭 작은 단지 TOP {len(small)}', JEON, '적은 돈으로 살 수 있는 곳', small)
    C.cta(d, F, f"{S['name']} 단지별 갭 전체 → 프로필 링크")
    C.footer(d, F, '자료 국토교통부 아파트 매매·전월세 실거래가 (전세는 월세 0원 계약만)')
    im.save(out_png)
    return big, small


def caption(S, big, small):
    p0, p1 = (datetime.date.fromisoformat(x) for x in S['period'])
    L = [f"🏠 {S['name']} 아파트 매매·전세 갭 | 갭 큰 단지 vs 작은 단지", '']
    a = S.get('all84')
    if a: L += [f"· {S['name']} 전용 84㎡대: 매매 {won_s(a['t'])} · 전세 {won_s(a['j'])} → 갭 {won_s(a['t'] - a['j'])} (전세가율 {round(a['j'] / a['t'] * 100)}%)", '']
    # 줄마다 '· ' 로 시작해야 스레드(post_threads.py)가 목록으로 가져감 → 묶음 제목 대신 🔺(갭 큰)·🔹(갭 작은) 표시
    L += [f"· 🔺 갭 큰 {i}위 {r[1]} {r[0]} {r[2]:g}㎡ 갭 {won(r[6] - r[7])} (전세가율 {round(r[7] / r[6] * 100)}%)" for i, r in enumerate(big, 1)]
    L += [f"· 🔹 갭 작은 {i}위 {r[1]} {r[0]} {r[2]:g}㎡ 갭 {won(r[6] - r[7])} (전세가율 {round(r[7] / r[6] * 100)}%)" for i, r in enumerate(small, 1)]
    L += ['', f"※ {p0.month}.{p0.day}~{p1.month}.{p1.day} 계약 · 같은 단지·같은 전용면적 매매·전세 각 2건 이상 · 중앙값 · 전세는 월세 0원 계약만",
          '자료: 국토교통부 실거래가 공개시스템', '', f"{S['name']} 단지별 갭 전체 순위는 프로필 링크에서 👆", '',
          ' '.join(dict.fromkeys(['#갭투자', '#전세가율', '#아파트실거래가', f"#{S['name'].replace(' ', '')}아파트", f"#{S['name'].replace(' ', '')}"]))]
    return '\n'.join(L)


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    raw, names, d0, d1 = load(a[0])
    OUT = a[1]; os.makedirs(OUT, exist_ok=True)
    force = (a[2] if len(a) > 2 else '') or os.environ.get('GAP_REGION', '').strip() or None
    code, used = choose(raw, names, d0, d1, force)
    if not code: sys.exit('갭 카드를 만들 지역이 없습니다')
    rows = gap_rows(raw, code, d0)
    a84, bands = summary_stats(raw, code, d0)
    S = {'made': TODAY.isoformat(), 'key': f'{TODAY.isoformat()}_{code}', 'code': code, 'region': names.get(code, code),
         'name': short_name(code, names), 'period': [d0.isoformat(), d1.isoformat()], 'all84': a84, 'bands': bands, 'rows': rows,
         'exact': bool(raw.get('jeonse_apt'))}
    big, small = draw(S, os.path.join(OUT, 'card.png'))
    open(os.path.join(OUT, 'caption.txt'), 'w', encoding='utf-8').write(caption(S, big, small))
    json.dump(S, open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    used[TODAY.isoformat()] = code
    os.makedirs(os.path.dirname(USED_PATH), exist_ok=True)
    json.dump(dict(sorted(used.items())[-60:]), open(USED_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"갭 카드: {S['region']} ({code}) · 단지·면적 {len(rows)}곳 · 단지명 매칭 {'정확' if S['exact'] else '추정(예전 자료)'}")
