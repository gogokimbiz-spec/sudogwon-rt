"""전세 실거래 카드 (2026-11-25, 매일 · 카톡/인스타/블로그/스레드 – 매매 카드와 별도)
사용법: python make_cards_jeonse.py rt_data.json site/summary.json site/jeonse
  - 같은 폴더의 prev_keys.json.gz(어제 배포된 거래 목록, daily.yml 이 받아 둠)와 비교해 '어제 새로 신고된 전세'를 찾음 (build.py 와 같은 방식).
    어제 자료가 없거나 새 전세가 0건이면 마지막 계약일 거래로 만듦. 날짜 표시(label)는 매매 카드(site/summary.json)와 같게.
결과: OUT/card.png(수도권 전체), OUT/region_1~4.png(서울·경기 북부·인천·경기 남서부·경기 남동부), OUT/caption.txt, OUT/summary.json
카드 구성 (사용자 확정 2026-11-25):
  ① 오늘의 전세 실거래가격 TOP 3 (보증금 높은 순, 같은 단지는 1줄)
  ② 전세 최고가 경신 TOP 3 (같은 단지·같은 전용면적의 최근 6개월 전세 최고가를 넘은 거래, 이전 거래 2건 이상)
  (③ 갱신 인상폭은 11-25 사용자 요청으로 삭제)
  줄은 표: 지역 / 아파트 / 거래일 / 이전가격 → 실거래가격 (이전가격 = 같은 단지·면적 최근 6개월 최고 전세). ① 5 + ② 5 = 10줄, 한쪽이 모자라면 다른 쪽으로 채움.
전세 = 월세 0원 계약. 층·계약구분·종전 보증금은 rt_data.json 의 jeonse_x (fetch.py 2026-11-25~).
"""
import os, sys, json, glob, gzip, hashlib, datetime, statistics, collections
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(KST).date()
PREV_PATH = os.environ.get('PREV_KEYS', 'prev_keys.json.gz')
WD = '월화수목금토일'


# ── 폰트 (make_cards_gap.py 와 같은 방식)
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


def pyeong(area):  # 전용㎡ → 평형(공급 기준 추정, 전용 × 1.33 ÷ 3.3058): 59㎡→24평, 84㎡→34평 (11-25 사용자: 평수도 나오게)
    return int(round(area * 1.33 / 3.3058))


def won_s(v):      # 9.1억 / 8,500만
    return (f'{v / 10000:.2f}'.rstrip('0').rstrip('.') + '억') if v >= 10000 else f'{int(v):,}만'


# ── 어제 새로 신고된 전세 (build.py new_flags 와 같은 규칙)
def rkey(*v): return hashlib.sha1('|'.join(map(str, v)).encode()).hexdigest()[:10]


def new_flags(rows, asof):
    if not os.path.exists(PREV_PATH): return None
    try:
        P = json.load(gzip.open(PREV_PATH, 'rt', encoding='utf-8'))
        if P.get('asof') == asof: P = P.get('prev')        # 같은 날 다시 돌린 경우: 그 전날 자료와 비교
    except Exception as e:
        print('어제 자료를 읽지 못했습니다:', e); return None
    if not P or not P.get('jeonse'): return None
    pk = P['jeonse']; pmax = max(g.split('|')[1] for g in pk); pa = P.get('asof') or '0000'
    cnt = {g: collections.Counter(v) for g, v in pk.items()}
    out = []
    for r in rows:
        g = f'{r[0]}|{r[1][:7]}'; k = rkey(r[1], r[2], r[3], r[4])
        if g in cnt:
            if cnt[g][k] > 0: cnt[g][k] -= 1; out.append(False)
            else: out.append(True)
        elif g.split('|')[1] > pmax: out.append(True)
        else: out.append(r[1] >= pa)
    return out


def load(rt_path, sum_path):
    raw = json.load(open(rt_path, encoding='utf-8'))
    names = json.load(open(os.path.join(HERE, 'names.json'), encoding='utf-8'))
    try: SM = json.load(open(sum_path, encoding='utf-8'))
    except Exception: SM = {}
    J = raw['jeonse']; n = len(J)
    A = raw.get('jeonse_apt') if len(raw.get('jeonse_apt') or []) == n else [''] * n
    X = raw.get('jeonse_x') if len(raw.get('jeonse_x') or []) == n else [[0, '', 0, 0, '', 0]] * n
    rows = []
    for (c, date, umd, area, dep), apt, x in zip(J, A, X):
        if area <= 0 or dep <= 0: continue
        fl, ct, pdep, prent, rr, by = (list(x) + [0, '', 0, 0, '', 0])[:6]
        rows.append({'code': c, 'date': date, 'umd': umd, 'area': area, 'dep': dep, 'apt': apt, 'floor': fl,
                     'ctype': (ct or '').strip(), 'pre': pdep, 'pre_rent': prent, 'rr': (rr or '').strip() == '사용', 'built': by})
    return raw, names, SM, rows


def short_region(code, names):
    full = names.get(code, code); p = full.split(' ')
    return ' '.join(p[1:]) if len(p) > 1 and p[0] in ('서울특별시', '인천광역시', '경기도') else full


def analyze(raw, names, SM, rows):
    asof = raw.get('asof') or TODAY.isoformat()
    flags = new_flags([[r['code'], r['date'], r['umd'], r['area'], r['dep']] for r in rows], asof)
    if flags and any(flags):
        basis = 'reported'; day = [r for r, f in zip(rows, flags) if f]
        label = SM.get('label') if SM.get('basis') == 'reported' else None
        if not label:
            d = datetime.date.fromisoformat(asof) - datetime.timedelta(1); label = f"{d.month}월 {d.day}일({WD[d.weekday()]})"
    else:
        basis = 'contract'; last = max(r['date'] for r in rows); day = [r for r in rows if r['date'] == last]
        d = datetime.date.fromisoformat(last); label = f"{d.month}월 {d.day}일({WD[d.weekday()]})"
        print('어제 자료가 없거나 새 전세가 없어 마지막 계약일 기준으로 만듭니다')
    ids = {id(r) for r in day}
    # 같은 단지·같은 전용면적의 이전 전세 (오늘 신고분 제외, 이번 계약일보다 앞선 계약)
    hist = collections.defaultdict(list)
    for r in rows:
        if id(r) not in ids and r['apt']: hist[(r['code'], r['apt'], r['umd'], round(r['area'] * 10))].append(r)
    for r in day:
        r['region'] = short_region(r['code'], names)
        h = [p for p in hist.get((r['code'], r['apt'], r['umd'], round(r['area'] * 10)), []) if p['date'] <= r['date']]
        r['prev_n'] = len(h)
        if h:                                              # '이전' 칸: 같은 단지·면적의 최근 6개월 최고 전세 (11-25 사용자 표 양식)
            pm = max(h, key=lambda p: p['dep']); r['prev_high'] = pm['dep']; r['prev_high_date'] = pm['date']
            if len(h) >= 2 and r['dep'] > pm['dep']: r['new_high'] = True
    stats = {'n': len(day), 'n_high': sum(1 for r in day if r.get('new_high')),
             'by_sido': {s: sum(1 for r in day if r['code'].startswith(s)) for s in ('11', '28', '41')}}
    return basis, label, day, stats


# ── 4개 권역 – 매매 실거래 권역 카드(build.py group_of)와 똑같이 (2026-11-25 사용자: "지역을 실거래카드와 맞게")
#    서울 · 경기 북부 · 인천·경기 남서부 · 경기 남동부
G_NORTH = {'고양', '파주', '김포', '의정부', '양주', '동두천', '남양주', '구리', '포천', '연천', '가평'}
G_SW = {'부천', '광명', '시흥', '안산', '안양', '군포', '의왕', '과천'}
G_SE = {'성남', '하남', '광주', '용인', '이천', '안성', '여주', '양평', '화성', '오산', '평택', '수원'}
GROUPS = ['서울', '경기 북부', '인천·경기 남서부', '경기 남동부']


def group_of(code, names):
    if code.startswith('11'): return '서울'
    if code.startswith('28'): return '인천·경기 남서부'
    nm = names.get(code, ''); c = nm.split(' ')[0] if ' ' in nm else nm[:-1]   # '수원 영통구' → 수원, '광명시' → 광명
    return '경기 북부' if c in G_NORTH else '인천·경기 남서부' if c in G_SW else '경기 남동부' if c in G_SE else None


def uniq(rs, skip=()):
    seen, out = set(skip), []
    for r in rs:
        k = (r['code'], r['apt'] or r['umd'])
        if k in seen: continue
        seen.add(k); out.append(r)
    return out


EACH, TOTAL = 5, 10


SPREAD = 20                                                # 11-25 사용자: 상위권만 말고 1~20위 안에서 골고루 (다른 지역 전세도 보이게)


def spread(pool, n, used, skip=()):
    """가격순 상위 SPREAD 개를 n 구간으로 나눠 구간마다 1건 – 이미 나온 구(시군구)·단지는 피함. 모자라면 남은 것 중 비싼 순"""
    full = [r for r in pool if (r['code'], r['apt'] or r['umd']) not in skip]
    pool = full[:SPREAD]
    if not pool: return []
    st = max(1, len(pool) // n); out = []
    for b in range(n):
        for r in pool[b * st:(b + 1) * st] if b < n - 1 else pool[b * st:]:
            if r['code'] in used or r in out: continue
            out.append(r); used.add(r['code']); break
    for r in full[:SPREAD * 2]:                            # 빈 구간: 40위 안에서 아직 안 나온 구부터 (11-25 첫 실행 때 강남구 2줄 → 수정)
        if len(out) >= n: break
        if r not in out and r['code'] not in used: out.append(r); used.add(r['code'])
    for r in pool:                                         # 그래도 모자라면(같은 구에 몰린 날) 구가 겹쳐도 채움
        if len(out) >= n: break
        if r not in out: out.append(r)
    out.sort(key=lambda r: -r['dep'])
    for r in out: r['rank'] = full.index(r) + 1
    return out


def pick(day):
    """실거래가격 5 + 최고가 경신 5, 각각 가격순 20위 안에서 고르게. 한쪽이 모자라면 다른 쪽으로 채워 10줄"""
    allp = uniq(sorted(day, key=lambda r: -r['dep']))
    hs = uniq(sorted([r for r in day if r.get('new_high')], key=lambda r: -r['dep']))
    used = set()
    tops = spread(allp, EACH, used)
    highs = spread(hs, EACH, used, {(r['code'], r['apt'] or r['umd']) for r in tops})
    if len(highs) < EACH:
        used = set(); tops = spread(allp, TOTAL - len(highs), used)
        highs = spread(hs, TOTAL - len(tops), used, {(r['code'], r['apt'] or r['umd']) for r in tops})
    return tops, highs


def slim(r):
    keep = ('code', 'region', 'date', 'umd', 'apt', 'area', 'floor', 'dep', 'built', 'ctype', 'new_high', 'prev_high', 'prev_high_date', 'prev_n', 'rank')
    return {k: r[k] for k in keep if k in r}


# 색 조합 (다른 카드와 안 겹치게 – 매매 슬레이트+노랑, 갭 녹회색+노랑, 정책 남색, 청약·재무 크림+빨강, TOP16 검정)
PAL = {
    'navy':   dict(bg=(30, 44, 68), acc=(255, 196, 0), on=(30, 40, 56), line=(64, 80, 108), sub=(196, 206, 222), hi=(255, 120, 110)),
    'purple': dict(bg=(46, 34, 74), acc=(56, 214, 172), on=(24, 40, 40), line=(84, 70, 116), sub=(214, 204, 232), hi=(255, 128, 150)),
    'teal':   dict(bg=(14, 62, 68), acc=(255, 140, 102), on=(40, 24, 18), line=(44, 98, 104), sub=(196, 226, 228), hi=(255, 140, 102)),
    'cocoa':  dict(bg=(58, 40, 32), acc=(120, 200, 255), on=(20, 36, 52), line=(96, 74, 62), sub=(226, 212, 200), hi=(255, 128, 110)),
    # 11-25 사용자 확정: B(틸+코랄)를 밝은 크림 바탕으로 – 머리 띠만 진한 틸, 본문 크림, 강조 코랄
    'cream':  dict(bg=(236, 226, 208), head=(14, 62, 68), head_ink=(255, 255, 255), acc=(255, 128, 90), on=(255, 255, 255),
                   ink=(20, 46, 50), ink2=(106, 116, 114), line=(212, 199, 178), sub=(70, 90, 94), hi=(226, 84, 52),
                   chip=(14, 62, 68), chip_t=(255, 255, 255), mark=(14, 62, 68)),
}
PAL_DEFAULT = 'cream'


# ── 카드 (card_style slate 바탕 + 전세 카드만 남색, 2026-11-25)
# 11-25 3차(사용자): 갱신 인상폭 삭제, 줄을 표로. 4차: 지역 / 아파트 / 거래일 / 이전가격 → 실거래가격
def draw(S, cards, title, out_png):
    os.environ.setdefault('CARD_THEME', 'slate')
    sys.path.insert(0, HERE); import card_style as C
    P = PAL.get(os.environ.get('JEONSE_PAL', ''), PAL[PAL_DEFAULT])
    BG, YEL = P['bg'], P['acc']
    C.T = dict(C.T, bg=BG, head=P.get('head', BG), accent=YEL, pill=YEL, pill_t=P['on'], cta_t=P['on'], big=YEL, line=P['line'],
               ink=P.get('ink', C.T['ink']), ink2=P.get('ink2', C.T['ink2']), chip=P.get('chip', C.T['chip']), chip_t=P.get('chip_t', BG))
    W, WHITE, T = C.W, C.WHITE, C.T
    INK, INK2 = T['ink'], T['ink2']; HINK = P.get('head_ink', INK); MARK = P.get('mark', YEL)
    PRICE = INK                                            # 보통 실거래가격 글씨 (밝은 바탕이면 진한 글씨)
    LINE = T['line']; SUB = P['sub']; UPC = P['hi']
    im, d = C.canvas(); d._image = im
    # 11-26 사용자: "글씨가 너무 작아" → 머리 줄이고, 두 번째 표 머리 생략, 줄 높이·글씨 키움
    hb = 206
    d.rectangle((0, 0, W, hb), fill=T['head'])
    d.rectangle((40, 30, W - 40, 36), fill=HINK)
    pill = f"{S['label']} {'신고' if S['basis'] == 'reported' else '계약'} · 전세"
    pf = F(30); pw = d.textlength(pill, font=pf)
    d.rounded_rectangle((64, 54, 64 + pw + 44, 106), 8, fill=T['pill']); d.text((86, 59), pill, font=pf, fill=T['pill_t'])
    ts = 62
    while ts > 46 and d.textlength(title, font=F(ts, 'Black')) > W - 128: ts -= 2   # '인천·경기 남서부 전세 실거래' 처럼 긴 제목은 글씨를 줄임
    d.text((64, 108 + (62 - ts) * 0.5), title, font=F(ts, 'Black'), fill=HINK)
    tops, highs = cards['tops'], cards['highs']
    secs = [x for x in (('전세 실거래가격', '가격순 20위 안에서 지역별로 고르게', MARK, tops),
                        ('전세 최고가 경신', '최근 6개월 최고보다 비싸게', UPC, highs)) if x[3]]
    X_RG, X_APT, X_AREA_R, X_DATE_R, X_PR_R = 44, 176, 556, 648, W - 44   # 면적(평형·전용) 칸 포함
    y = hb + 16
    SECH, HH, GAPS = 48, 34, 12                            # 섹션 제목 · 표 머리(첫 섹션만) · 섹션 사이
    nrows = sum(len(x[3]) for x in secs)
    RH = max(64, min(96, int((1180 - y - len(secs) * SECH - HH - GAPS * (len(secs) - 1)) / max(nrows, 1))))
    k = min(1.0, RH / 82)
    fa, fr, fp, fd = int(38 * (0.75 + 0.25 * k)), int(25 * (0.8 + 0.2 * k)), int(46 * (0.75 + 0.25 * k)), int(28 * (0.8 + 0.2 * k))

    def rt(x, yy, txt, f, col):                            # 오른쪽 정렬
        d.text((x - d.textlength(txt, font=f), yy), txt, font=f, fill=col)

    def won_p(v):                                          # 이전가격은 짧게: 20.9억 / 8,500만
        return (f'{v / 10000:.1f}'.rstrip('0').rstrip('.') + '억') if v >= 10000 else f'{int(v):,}만'

    for si, (ttl, note, col, rows) in enumerate(secs):
        if si: y += GAPS
        tf = F(34, 'Black')
        d.rectangle((40, y + 6, 50, y + 42), fill=col)
        d.text((62, y), ttl, font=tf, fill=INK)
        d.text((62 + d.textlength(ttl, font=tf) + 14, y + 12), note, font=F(22, 'Medium'), fill=INK2)
        y += SECH
        if si == 0:                                        # 표 머리는 첫 섹션에만
            hf = F(21, 'Medium')
            d.text((X_RG, y + 2), '지역', font=hf, fill=INK2); d.text((X_APT, y + 2), '아파트', font=hf, fill=INK2)
            rt(X_AREA_R, y + 2, '면적', hf, INK2); rt(X_DATE_R, y + 2, '거래일', hf, INK2); rt(X_PR_R, y + 2, '이전가격 → 실거래가격', hf, INK2)
            y += HH
        d.line((40, y - 3, W - 40, y - 3), fill=LINE, width=2)
        for r in rows:
            cy = y + RH / 2 - 4                            # 줄 가운데
            p_ = r['region'].split(' ')
            rg = p_[1] if p_[0] in ('서울', '인천') and len(p_) > 1 else (p_[0] + ' ' + p_[1][:-1]) if len(p_) > 1 else p_[0]
            rf = F(fr, 'Bold'); lim = X_APT - X_RG - 54
            if d.textlength(rg, font=rf) > lim and len(p_) > 1: rg = p_[1][:-1] if p_[1].endswith('구') else p_[1]   # '성남 분당' → '분당'
            while d.textlength(rg, font=rf) > lim and len(rg) > 2: rg = rg[:-1]
            C.chip(d, F, X_RG, cy - (fr + 14) / 2, rg, fr)
            nm = r['apt'] or r['umd']; room = X_AREA_R - 80 - X_APT; fs = fa
            if d.textlength(nm, font=F(fs, 'Black')) > room and '(' in nm: nm = nm.split('(')[0]   # '봇들마을8단지(주공)' → 괄호 빼기
            while fs > fa - 6 and d.textlength(nm, font=F(fs, 'Black')) > room: fs -= 1                # 조금 줄여 보고
            af = F(fs, 'Black')
            while d.textlength(nm, font=af) > room and len(nm) > 3: nm = nm.rstrip('…')[:-1] + '…'   # 그래도 길면 자름
            d.text((X_APT, cy - fs * 0.66), nm, font=af, fill=INK)
            dd = datetime.date.fromisoformat(r['date'])
            rt(X_DATE_R, cy - fd * 0.64, f'{dd.month}.{dd.day}', F(fd, 'Medium'), SUB)
            pf2 = F(int(fd * 1.08), 'Black'); ps = f"{pyeong(r['area'])}평"; rt(X_AREA_R, cy - fd * 1.02, ps, pf2, INK)       # 위: 평형
            af3 = F(max(16, int(fd * 0.72)), 'Medium'); rt(X_AREA_R, cy + fd * 0.36, f"{r['area']:.0f}㎡", af3, INK2)        # 아래: 전용㎡
            prf = F(fp, 'Black'); pr = won(r['dep']); rt(X_PR_R, cy - fp * 0.66, pr, prf, UPC if r.get('new_high') else PRICE)
            if r.get('prev_high'):                         # 이전가격 = 같은 단지·면적 최근 6개월 최고 전세
                xa = X_PR_R - d.textlength(pr, font=prf) - 10; af2 = F(int(fd * 0.92), 'Medium')
                rt(xa, cy - fd * 0.56, '→', af2, INK2); xa -= d.textlength('→', font=af2) + 8
                rt(xa, cy - fd * 0.56, won_p(r['prev_high']), af2, SUB)
            d.line((40, y + RH - 2, W - 40, y + RH - 2), fill=LINE, width=1)
            y += RH
    if not nrows:
        d.text((64, y + 40), '이 권역은 오늘 신고된 전세가 없습니다', font=F(32, 'Bold'), fill=INK2)
    C.cta(d, F, '오늘의 전세 실거래 전체 → 프로필 링크')
    # 반투명 아이디: 왼쪽 위 것만 오른쪽으로 (11-25 사용자) – 전세 카드에서만, card_style 은 그대로
    _wm = C.watermark
    def _wm_j(d_, F_, text=None, alpha=40, size=66):
        im_ = getattr(d_, '_image', None)
        if im_ is None: return
        from PIL import Image as _I, ImageDraw as _D
        text = text or C.IG; f = F_(size, 'Black'); tw = int(d_.textlength(text, font=f)) + 30
        tile = _I.new('RGBA', (tw, size + 36), (0, 0, 0, 0)); col = tuple(C.T['ink'][:3]) + (alpha,)
        _D.Draw(tile).text((15, 6), text, font=f, fill=col)
        tile = tile.rotate(24, expand=True, resample=_I.BICUBIC)
        for cx, cy in ((600, 520), (790, 820), (290, 1080)):
            im_.paste(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)), tile)
    C.watermark = _wm_j
    C.footer(d, F, '자료 국토교통부 전월세 실거래가 · 월세 0원만 · 평형은 추정')
    C.watermark = _wm
    im.save(out_png)


def caption(S):
    st = S['stats']; tops, highs = S['cards']['tops'], S['cards']['highs']
    L = [f"🔑 오늘의 전세 실거래 | {S['label']} {'신고' if S['basis'] == 'reported' else '계약'} {st['n']:,}건", '']
    # 줄마다 '· ' 로 시작해야 스레드(post_threads.py)가 목록으로 가져감
    L += [f"· 💰 {i}위 {r['region']} {r['apt']} {r['area']:g}㎡({pyeong(r['area'])}평) {won(r['dep'])}" for i, r in enumerate(tops[:3], 1)]
    L += [f"· 🔺 최고가 경신 {r['region']} {r['apt']} {r['area']:g}㎡({pyeong(r['area'])}평) {won(r['dep'])} (이전 {won_s(r["prev_high"])})" for r in highs[:3]]
    for g in S.get('groups') or []:
        t = (g['cards']['tops'] or [None])[0]
        if t: L.append(f"· 🗺️ {g['name']} 최고 {t['apt']} {t['area']:g}㎡({pyeong(t['area'])}평) {won(t['dep'])} ({g['n']:,}건)")
    city = [n for n, k in (('서울', '11'), ('경기', '41'), ('인천', '28')) if st['by_sido'].get(k)][:2]
    L += ['', '※ 전세 = 월세 0원 계약 · 평형은 전용면적으로 추정 · 최고가 경신은 같은 단지·같은 전용면적 최근 6개월 기준',
          '자료: 국토교통부 실거래가 공개시스템', '', '전세 실거래 전체는 프로필 링크에서 👆', '',
          ' '.join(dict.fromkeys(['#전세', '#전세실거래가', '#아파트전세'] + [f'#{c}전세' for c in city]))]
    return '\n'.join(L)


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    raw, names, SM, rows = load(a[0], a[1])
    OUT = a[2]; os.makedirs(OUT, exist_ok=True)
    if not raw.get('jeonse_x'): print('::warning::rt_data.json 에 jeonse_x 가 없습니다 (fetch.py 가 예전 것) – 층 없이 만듭니다')
    basis, label, day, stats = analyze(raw, names, SM, rows)
    if not day: sys.exit('전세 거래가 없어 카드를 건너뜁니다')
    tops, highs = pick(day)
    key = SM.get('day') if basis == 'reported' and SM.get('basis') == 'reported' else (raw.get('asof') or TODAY.isoformat())
    S = {'made': TODAY.isoformat(), 'key': key, 'basis': basis, 'label': label, 'stats': stats,
         'cards': {'tops': [slim(r) for r in tops], 'highs': [slim(r) for r in highs]},
         'top20': [slim(r) for r in uniq(sorted(day, key=lambda r: -r['dep']))[:20]],
         'highs_all': [slim(r) for r in sorted([r for r in day if r.get('new_high')], key=lambda r: -r['dep'])[:40]]}
    draw(S, S['cards'], '수도권 전세 실거래', os.path.join(OUT, 'card.png'))
    # 4개 권역 카드 region_1~4.png (서울·경기 북부·인천·경기 남서부·경기 남동부 – 매매 권역 카드와 같음)
    S['groups'] = []
    for gi, g in enumerate(GROUPS, 1):
        gd = [r for r in day if group_of(r['code'], names) == g]
        t_, h_ = pick(gd)
        cards = {'tops': [slim(r) for r in t_], 'highs': [slim(r) for r in h_]}
        S['groups'].append({'name': g, 'n': len(gd), 'n_high': sum(1 for r in gd if r.get('new_high')), 'cards': cards})
        draw(S, cards, f'{g} 전세 실거래', os.path.join(OUT, f'region_{gi}.png'))
        print(f'권역 카드 {gi}: {g} {len(gd)}건 → region_{gi}.png')
    open(os.path.join(OUT, 'caption.txt'), 'w', encoding='utf-8').write(caption(S))
    json.dump(S, open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"전세 카드: {label} · {'신고' if basis == 'reported' else '계약'} {stats['n']}건 · 최고가 경신 {stats['n_high']} · 카드 {len(tops)}/{len(highs)}")
