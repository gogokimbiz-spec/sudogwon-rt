"""이번 주 수도권 청약 한 장 이미지(1080×1350, 인스타 4:5)를 만듭니다 (GitHub Actions 용).
사용법: python make_cards_cy.py site/cheongyak/summary.json site/cheongyak/cards
결과: <출력폴더>/single.png, latest.png, caption.txt (월)
      + mid.png, caption_mid.txt (수: 이번 주 남은 청약) / next.png, caption_next.txt (금: 다음 주 청약) – 인스타용
필요: Pillow, 한글 폰트(fonts-noto-cjk)
"""
import sys, os, glob, json, datetime, shutil
from PIL import Image, ImageDraw, ImageFont

S = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
W, SH = 1080, 1350
NAVY, WHITE, MUTED, RED, BLUE = (15, 39, 66), (255, 255, 255), (150, 170, 195), (255, 92, 92), (60, 120, 230)
CREAM, INK, INK2 = (247, 248, 251), (20, 30, 45), (95, 108, 125)
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
def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}' if m else f'{e}억') if e else f'{m:,}'
def rr(d, box, r, fill=None): d.rounded_rectangle(box, r, fill=fill)
def fit(d, s, font, maxw):
    while d.textlength(s, font=font) > maxw and len(s) > 4: s = s.rstrip('…')[:-1] + '…'
    return s
def city(r):
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' and len(p[0]) > 2 else p[0]
    if p[0] in ('서울', '인천'): return p[1][:-1] if len(p[1]) > 2 else p[1]
    return p[0]
D = lambda s: datetime.date.fromisoformat(s[:10])
WD = '월화수목금토일'
md = lambda s: f"{D(s).month}.{D(s).day}({WD[D(s).weekday()]})"

w0, w1 = D(S['week'][0]), D(S['week'][1])
r1 = S.get('rank1') or []
done = [x for x in (S.get('last_week') or []) if 'rate' in x]
done.sort(key=lambda x: -x['rate'])

import card_style as C                                 # 공통 디자인 (밝은 화이트·오렌지형)
im, d = C.canvas()
INK, INK2, RED, BLUE = C.INK, C.INK2, C.UP, C.DOWN
C.header(d, F, f'{w0.month}.{w0.day} ~ {w1.month}.{w1.day} 1순위 접수', '이번 주 수도권 청약', f'{len(r1)}곳',
         '분양가 3.3㎡당 · 주변 신축 대비 비싸면 빨강, 싸면 파랑')

top, bottom = 340, SH - 170
n_last = min(3, len(done)) if len(r1) <= 4 else 0       # 접수 단지가 적으면 지난주 결과도 같이
rows_ = r1[:7 - n_last] if r1 else []
if len(r1) > len(rows_): bottom -= 40                 # '외 N곳' 안내 자리
slots = len(rows_) + n_last
rh = min(128, (bottom - top - (70 if n_last else 0)) // max(1, slots))
y = top
if not rows_:
    d.text((64, y + 20), '이번 주 1순위 접수 단지가 없어요', font=F(44, 'Black'), fill=INK); y += 110
for x in rows_:
    C.row_box(d, y, rh - 14)
    cy = y + (rh - 14) // 2
    cw = C.chip(d, F, 64, cy - 52, city(x['region']))
    nmf = F(38, 'Black'); nx = 64 + cw + 14
    d.text((nx, cy - 57), fit(d, x['name'], nmf, W - 64 - nx - 280), font=nmf, fill=INK)
    sub = f"{md(x['date'])} 접수 · 일반 {x.get('general') or x.get('units') or '-'}세대" + (f" · {x['kind']}" if x.get('kind') else '')
    d.text((64, cy + 2), sub, font=F(27, 'Medium'), fill=INK2)
    pr = man(x['pp_man']) + '만'; pfnt = F(46, 'Black')
    d.text((W - 64 - d.textlength(pr, font=pfnt), cy - 58), pr, font=pfnt, fill=INK)
    g = x.get('gap_new')
    if g is not None:
        s2 = f"주변 신축 대비 {'+' if g > 0 else ''}{g}%"; sf = F(28)
        d.text((W - 64 - d.textlength(s2, font=sf), cy + 4), s2, font=sf, fill=RED if g > 0 else BLUE if g < 0 else INK2)
    y += rh
if n_last:
    d.text((64, y + 6), '지난주 1순위 경쟁률', font=F(34, 'Black'), fill=INK)
    y += 70
    for x in done[:n_last]:
        C.row_box(d, y, rh - 14)
        cy = y + (rh - 14) // 2
        cw = C.chip(d, F, 64, cy - 20, city(x['region']))
        rt = f"{x['rate']:.1f} : 1"; rf = F(44, 'Black'); rw = d.textlength(rt, font=rf)
        st = x.get('status', ''); sf = F(26, 'Medium'); sw = d.textlength(st, font=sf)
        nx = 64 + cw + 14
        d.text((nx, cy - 26), fit(d, x['name'], F(34, 'Black'), W - 64 - nx - rw - sw - 40), font=F(34, 'Black'), fill=INK)
        d.text((W - 64 - rw, cy - 32), rt, font=rf, fill=BLUE if st == '미달' else RED)
        d.text((W - 64 - rw - 20 - sw, cy - 14), st, font=sf, fill=INK2)
        y += rh
more = len(r1) - len(rows_)
if more > 0: d.text((64, y + 2), f'외 {more}곳은 프로필 링크에서', font=F(28, 'Medium'), fill=INK2)
C.cta(d, F, '청약 일정·지도 → 프로필 링크')
C.footer(d, F, '자료 청약홈 · 분양가 단위 만원 · 청약 전 모집공고 확인')
im.save(os.path.join(OUT, 'single.png'))
shutil.copy(os.path.join(OUT, 'single.png'), os.path.join(OUT, 'latest.png'))

# 게시 문구
cap = [f"🏗 이번 주 수도권 청약 {len(r1)}곳 ({w0.month}.{w0.day}~{w1.month}.{w1.day} 1순위 접수)", '']
for x in r1[:10]:
    g = x.get('gap_new')
    cap.append(f"· {md(x['date'])} {x['region']} {x['name']} 3.3㎡당 {man(x['pp_man'])}만" + (f" (주변 신축 대비 {'+' if g > 0 else ''}{g}%)" if g is not None else ''))
if done:
    cap += ['', '🏆 지난주 1순위 경쟁률'] + [f"· {x['region']} {x['name']} {x['rate']:.1f}:1 {x.get('status', '')}" for x in done[:3]]
tags = ['청약', '아파트청약', '수도권청약', '분양', '청약일정', '내집마련', '부동산'] + list(dict.fromkeys(city(x['region']) + '청약' for x in r1))[:4]
cap += ['', '※ 청약 전에는 반드시 입주자모집공고를 확인하세요', '자료: 청약홈 · 참고용 정보이며 투자 권유가 아닙니다',
        '', '청약 지도·전체 일정은 프로필 링크에서 👆', '', ' '.join('#' + t for t in tags)]
open(os.path.join(OUT, 'caption.txt'), 'w', encoding='utf-8').write('\n'.join(cap))
print('청약 한 장 이미지 → single.png / latest.png, caption.txt')


# ── 인스타 수·금요일용 카드 (수: 이번 주 남은 청약 / 금: 다음 주 청약) ─────────────────
def list_card(rows, pill, title, sub, cta, fname, capname, cap_head, empty_msg):
    if not rows:
        for f in (fname, capname):
            if os.path.exists(os.path.join(OUT, f)): os.remove(os.path.join(OUT, f))
        print(f'{fname}: {empty_msg} – 만들지 않음'); return
    im, d = C.canvas()
    C.header(d, F, pill, title, f'{len(rows)}곳', sub)
    top, bottom = 340, SH - 170
    show = rows[:7]
    if len(rows) > len(show): bottom -= 40
    rh = min(128, (bottom - top) // max(1, len(show)))
    y = top
    for x in show:
        C.row_box(d, y, rh - 14)
        cy = y + (rh - 14) // 2
        cw = C.chip(d, F, 64, cy - 52, city(x['region']))
        nmf = F(38, 'Black'); nx = 64 + cw + 14
        d.text((nx, cy - 57), fit(d, x['name'], nmf, W - 64 - nx - 280), font=nmf, fill=INK)
        sub2 = f"{md(x['date'])} 접수 · 일반 {x.get('general') or x.get('units') or '-'}세대" + (f" · {x['kind']}" if x.get('kind') else '')
        d.text((64, cy + 2), sub2, font=F(27, 'Medium'), fill=INK2)
        if x.get('pp_man'):
            pr = man(x['pp_man']) + '만'; pfnt = F(46, 'Black')
            d.text((W - 64 - d.textlength(pr, font=pfnt), cy - 58), pr, font=pfnt, fill=INK)
        g = x.get('gap_new')
        if g is not None:
            s2 = f"주변 신축 대비 {'+' if g > 0 else ''}{g}%"; sf = F(28)
            d.text((W - 64 - d.textlength(s2, font=sf), cy + 4), s2, font=sf, fill=RED if g > 0 else BLUE if g < 0 else INK2)
        y += rh
    if len(rows) > len(show): d.text((64, y + 2), f'외 {len(rows) - len(show)}곳은 프로필 링크에서', font=F(28, 'Medium'), fill=INK2)
    C.cta(d, F, cta)
    C.footer(d, F, '자료 청약홈 · 분양가 단위 만원 · 청약 전 모집공고 확인')
    im.save(os.path.join(OUT, fname))
    cp_ = [cap_head, '']
    for x in rows[:10]:
        g = x.get('gap_new')
        cp_.append(f"· {md(x['date'])} {x['region']} {x['name']}" + (f" 3.3㎡당 {man(x['pp_man'])}만" if x.get('pp_man') else '') +
                   (f" (주변 신축 대비 {'+' if g > 0 else ''}{g}%)" if g is not None else ''))
    tg = ['청약', '아파트청약', '수도권청약', '분양', '청약일정', '내집마련', '부동산'] + list(dict.fromkeys(city(x['region']) + '청약' for x in rows))[:4]
    cp_ += ['', '※ 청약 전에는 반드시 입주자모집공고를 확인하세요', '자료: 청약홈 · 참고용 정보이며 투자 권유가 아닙니다',
            '', '청약 지도·전체 일정은 프로필 링크에서 👆', '', ' '.join('#' + t for t in tg)]
    open(os.path.join(OUT, capname), 'w', encoding='utf-8').write('\n'.join(cp_))
    print(f'{fname} / {capname} ({len(rows)}곳)')


TD = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).date()
rest = [x for x in r1 if x.get('date') and D(x['date']) >= TD]
list_card(rest, f'{TD.month}.{TD.day} ~ {w1.month}.{w1.day} 1순위 접수', '이번 주 남은 청약', '아직 접수할 수 있는 수도권 단지',
          '청약 일정·지도 → 프로필 링크', 'mid.png', 'caption_mid.txt',
          f"📌 이번 주 남은 수도권 청약 {len(rest)}곳 ({TD.month}.{TD.day}~{w1.month}.{w1.day} 1순위 접수)", '이번 주 남은 접수 단지 없음')
nx_ = S.get('next_week') or []
if S.get('next_range'):
    n0_, n1_ = D(S['next_range'][0]), D(S['next_range'][1])
    list_card(nx_, f'{n0_.month}.{n0_.day} ~ {n1_.month}.{n1_.day} 1순위 접수', '다음 주 수도권 청약', '미리 보고 청약 통장 준비하세요',
              '청약 일정·지도 → 프로필 링크', 'next.png', 'caption_next.txt',
              f"🗓 다음 주 수도권 청약 {len(nx_)}곳 ({n0_.month}.{n0_.day}~{n1_.month}.{n1_.day} 1순위 접수)", '다음 주 접수 단지 없음')
