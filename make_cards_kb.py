"""KB 주간 매수우위지수 / 전세수급지수 TOP 10 카드 (16개 시도) – 2026-11-27 확정
일정(사용자): 수요일 13시 매수우위(buy), 목요일 13시 전세수급(rent) – kb.yml
사용법: python make_cards_kb.py buy|rent OUT kb_wk.json [toheo raw.json]
  - kb_wk.json: {'updated': 'YYYY-MM-DD', 'dates': ['26.11.23', ...16주], 'sido_buy': {지역: [16]}, 'sido_rent': {지역: [16]}}
    (예약 작업 'KB 심리지수 받기'가 수요일 오전 Chrome 으로 KB 데이터허브 표를 읽어 저장소 kb/kb_wk.json 에 올림)
  - 결과: OUT/card_kb_<mode>.png, OUT/slug.txt, special/<조사일>_kb_<mode>/meta.json (post_special.py 로 게시)
  - 최신 조사일이 MAX_AGE(기본 12)일보다 오래되면 종료코드 2 (게시 안 함)
"""
import os, sys, json, datetime, io, contextlib, html as _html
HERE = os.path.dirname(os.path.abspath(__file__))
MODE, OUT_, KBF = sys.argv[1], sys.argv[2], sys.argv[3]
RAWF = sys.argv[4] if len(sys.argv) > 4 else os.path.join(HERE, 'toheo_now', 'toheo', 'raw.json')
os.makedirs(OUT_, exist_ok=True)
K = json.load(open(KBF, encoding='utf-8'))
last = K['dates'][-1]; ld = datetime.date(2000 + int(last[:2]), int(last[3:5]), int(last[6:]))
TODAY_ = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
if (TODAY_ - ld).days > int(os.environ.get('KB_MAX_AGE') or 12):
    print(f'::warning::KB 최신 조사일 {ld} 이 오래되어 게시하지 않습니다'); sys.exit(2)
nth = (ld.day - 1) // 7 + 1; label = f'{ld.month}월 {nth}주'

# 글꼴·색: make_cards_toheo.py 를 카드 그리기 직전까지 실행
os.environ['TOHEO_MAX_AGE'] = '99999'
sys.argv = [sys.argv[0], os.path.join(OUT_, '_toheo_tmp'), RAWF]
_s = open(os.path.join(HERE, 'make_cards_toheo.py'), encoding='utf-8').read()
_s = _s[:_s.index('im, d = C.canvas()')]
__file__ = os.path.join(HERE, 'make_cards_toheo.py')
with contextlib.redirect_stdout(io.StringIO()): exec(compile(_s, 'make_cards_toheo.py', 'exec'))

CFG = {'buy': dict(key='sido_buy', big='이번 주 매수심리 TOP 10', name='매수우위지수', lo='매도우위', hi='매수우위',
                   note='매수우위지수 = 100 + "매수자 많음" 비율 − "매도자 많음" 비율 (0~200)'),
       'rent': dict(key='sido_rent', big='이번 주 전세수요 TOP 10', name='전세수급지수', lo='전세수요적음', hi='전세수요많음',
                    note='전세수급지수 = 100 + "공급 부족" 비율 − "공급 충분" 비율 (0~200) · 높을수록 전세 수요가 많음')}[MODE]


def streak(a):
    sg = 1 if a[-1] > a[-2] else -1 if a[-1] < a[-2] else 0
    if not sg: return 0
    n = 0
    for i in range(len(a) - 1, 0, -1):
        if (a[i] - a[i - 1]) * sg > 0: n += 1
        else: break
    return sg * n


S = K[CFG['key']]; ranked = sorted(S.items(), key=lambda kv: -kv[1][-1]); top = ranked[:10]
im, d = C.canvas(); ink = C.INK
d.rectangle((40, 28, W - 40, 34), fill=ink); d.line((40, 40, W - 40, 40), fill=ink, width=2)
d.text((44, 50), f'{ld.year}년 {ld.month}월 {ld.day}일 조사 ({label}) · KB부동산 · 공인중개사 설문 · 16개 시도', font=F(21, 'Medium'), fill=C.INK2)
d.line((40, 86, W - 40, 86), fill=ink, width=1)
d.text((40, 96), CFG['big'], font=FS(70, 'Black'), fill=ink)
d.line((40, 206, W - 40, 206), fill=ink, width=2); d.rectangle((40, 212, W - 40, 218), fill=ink)
y0 = 238
d.text((40, y0), CFG['name'], font=FS(42, 'Black'), fill=ink)
tf = FS(24, 'Bold'); t = f"{CFG['lo']}  —  100  —  {CFG['hi']}"
d.text((W - 40 - d.textlength(t, font=tf), y0 + 14), t, font=tf, fill=C.INK2)
d.line((40, y0 + 62, W - 40, y0 + 62), fill=ink, width=2)
RX, NX, BX0, BX1, VX, CX, SX0, SX1 = 44, 96, 236, 486, 632, 760, 800, W - 44
hy = y0 + 72; hf = F(16, 'Medium')
d.text((BX0, hy), '0', font=hf, fill=C.INK2); d.text(((BX0 + BX1) / 2 - 13, hy), '100', font=hf, fill=C.INK2)
d.text((BX1 - 28, hy), '200', font=hf, fill=C.INK2); d.text((CX - 64, hy), '전주 대비', font=hf, fill=C.INK2)
d.text((SX0, hy), f"최근 16주 ({K['dates'][0][3:].replace('.', '/')}~)", font=hf, fill=C.INK2)
rh = 88; y = y0 + 100
for i, (reg, a) in enumerate(top):
    v, dv = a[-1], a[-1] - a[-2]; col = C.UP if v >= 100 else C.DOWN
    if i: d.line((40, y - 6, W - 40, y - 6), fill=C.T['line'], width=1)
    cy = y + rh / 2 - 6
    rf = F(28, 'Black'); d.text((RX + 32 - d.textlength(str(i + 1), font=rf), cy - 20), str(i + 1), font=rf, fill=C.INK2)
    d.text((NX, cy - 24), reg, font=FS(34, 'Black'), fill=ink)
    mx = (BX0 + BX1) / 2; px = BX0 + (BX1 - BX0) * min(max(v, 0), 200) / 200
    d.rectangle((BX0, cy - 14, BX1, cy + 14), fill=C.T['card'])
    d.rectangle((min(mx, px), cy - 14, max(mx, px), cy + 14), fill=col)
    d.line((mx, cy - 22, mx, cy + 22), fill=ink, width=2)
    vf = F(40, 'Black'); vt = f'{v:.1f}'
    d.text((VX - d.textlength(vt, font=vf), cy - 28), vt, font=vf, fill=col)
    ct = f'{dv:+.1f}'; cf = F(25, 'Black')
    d.text((CX - d.textlength(ct, font=cf), cy - 20), ct, font=cf, fill=C.UP if dv > 0.05 else C.DOWN if dv < -0.05 else ink)
    st = streak(a)
    if abs(st) >= 3:
        s2 = f"{abs(st)}주 연속 {'↑' if st > 0 else '↓'}"; sf = F(15, 'Medium')
        d.text((CX - d.textlength(s2, font=sf), cy + 12), s2, font=sf, fill=C.INK2)
    lo_, hi_ = min(a), max(a); pad_ = (hi_ - lo_) * 0.15 + 0.5; lo_, hi_ = lo_ - pad_, hi_ + pad_
    pts = [(SX0 + (SX1 - SX0) * k / (len(a) - 1), cy + 24 - 50 * (x - lo_) / (hi_ - lo_)) for k, x in enumerate(a)]
    d.line(pts, fill=col, width=4); ex, ey = pts[-1]; d.ellipse((ex - 6, ey - 6, ex + 6, ey + 6), fill=col)
    y += rh
d.line((40, 1244, W - 40, 1244), fill=ink, width=2)
d.text((44, 1252), CFG['note'], font=F(17, 'Medium'), fill=C.INK2)
d.line((40, 1290, W - 40, 1290), fill=ink, width=2)
C.footer(d, F, '자료 KB부동산 주간 아파트시장동향')
import random
random.seed(7); g_ = Image.effect_noise((W // 2, SH // 2), 18).resize((W, SH)).convert('L')
im = Image.composite(im, Image.blend(im, Image.new('RGB', (W, SH), (120, 100, 70)), 0.06), g_.point(lambda v: 255 if v > 120 else 200))
png = os.path.join(OUT_, f'card_kb_{MODE}.png'); im.save(png); print('카드 →', png)

# ── 게시용 meta.json
slug = f'{ld.isoformat()}_kb_{MODE}'
f1 = lambda v: f'{v:.1f}'
th = 'style="padding:6px 8px;border-bottom:2px solid #222;text-align:{}"'; td = 'style="padding:6px 8px;border-bottom:1px solid #ddd;text-align:{}"'
tb = ('<table style="width:100%;border-collapse:collapse;font-size:15px"><tr>'
      + ''.join(f'<th {th.format(a)}>{h}</th>' for h, a in (('순위', 'center'), ('지역', 'left'), (CFG['name'], 'right'), ('전주 대비', 'right'))) + '</tr>'
      + ''.join(f'<tr><td {td.format("center")}>{i}</td><td {td.format("left")}>{r}</td><td {td.format("right")}><b>{f1(a[-1])}</b></td>'
                f'<td {td.format("right")}>{a[-1] - a[-2]:+.1f}</td></tr>' for i, (r, a) in enumerate(ranked, 1)) + '</table>')
above = [r for r, a in ranked if a[-1] > 100]
if MODE == 'buy':
    lead = (f'KB부동산 {ld.month}월 {ld.day}일 조사({label}) 주간 매수우위지수 1위는 <b>{top[0][0]} {f1(top[0][1][-1])}</b>입니다. '
            + (f'100을 넘어 매수자가 더 많은 곳은 {", ".join(above)}입니다.' if above else '16개 시도 모두 100 아래로, 집을 사려는 사람보다 팔려는 사람이 많은 \'매도우위\' 시장입니다.'))
    tag2 = '#매수심리'
else:
    lead = (f'KB부동산 {ld.month}월 {ld.day}일 조사({label}) 주간 전세수급지수 1위는 <b>{top[0][0]} {f1(top[0][1][-1])}</b>입니다. '
            + (f'16개 시도 가운데 {len(above)}곳이 100을 넘어 전세 수요가 공급보다 많습니다.' if above else '16개 시도 모두 100 아래로 전세 공급이 충분한 편입니다.'))
    tag2 = '#전세수요'
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
body = (f'<div style="margin:0 0 16px;text-align:center"><img src="{{IMG}}" alt="KB {CFG["name"]} TOP 10 – {label}" style="width:100%;max-width:540px;height:auto;border-radius:6px"></div>'
        f'<p style="font-size:16px;line-height:1.8">{lead} 2~3위는 {top[1][0]} {f1(top[1][1][-1])}, {top[2][0]} {f1(top[2][1][-1])}입니다. '
        f'{CFG["name"]}는 0~200 사이 값으로, 100보다 낮으면 {CFG["lo"]}, 높으면 {CFG["hi"]}을 뜻합니다.</p>'
        '{AD}' f'<h3>16개 시도 {CFG["name"]} 전체 ({label})</h3>' + tb
        + f'<p style="margin:20px 0"><a href="{SITE}" style="display:inline-block;padding:12px 18px;border-radius:8px;background:#1e1914;color:#efe3c8;font-weight:bold;text-decoration:none">🏠 수도권 아파트 실거래가 지도 보기 ›</a></p>'
        f'<hr><p><small>자료: KB부동산 데이터허브 주간 아파트시장동향 ({ld.month}월 {ld.day}일 조사). {CFG["note"]}. 표본 공인중개사무소 설문 결과입니다.<br>참고용 정보이며 투자 판단의 책임은 본인에게 있습니다.</small></p>')
cap = '\n'.join([f"📊 {CFG['big']} | KB {CFG['name']} {label}", '', f"({CFG['lo']} ← 100 → {CFG['hi']})", ''] +
                [f"· {i}위 {r} {f1(a[-1])} ({a[-1] - a[-2]:+.1f})" for i, (r, a) in enumerate(top[:5], 1)] + ['',
                f'자료: KB부동산 주간 아파트시장동향({ld.month}/{ld.day} 조사) · 참고용 정보', '', '10위까지 전체 표는 프로필 링크에서 👆', '',
                f"#데이터로보는재테크 {tag2} #KB부동산 #{top[0][0]} #{top[1][0]}"])
meta = dict(slug=slug, post_at=TODAY_.isoformat() + 'T00:00', make=['python', '-c', 'pass'], out=png,
            title=f"[KB {CFG['name']}] {CFG['big']} ({label}) | 1위 {top[0][0]} {f1(top[0][1][-1])} · 2위 {top[1][0]} · 3위 {top[2][0]}",
            labels=[f"KB {CFG['name']}", 'KB부동산', tag2[1:], '아파트시장동향'], blog_html=body,
            kakao_title=f"📊 {CFG['big']} ({label})",
            kakao_desc=f"1위 {top[0][0]} {f1(top[0][1][-1])} · 2위 {top[1][0]} {f1(top[1][1][-1])} · 3위 {top[2][0]} {f1(top[2][1][-1])}\n({CFG['lo']} ← 100 → {CFG['hi']})",
            kakao_button='16개 시도 전체 보기', caption=cap)
os.makedirs(os.path.join('special', slug), exist_ok=True)
json.dump(meta, open(os.path.join('special', slug, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(os.path.join(OUT_, 'slug.txt'), 'w').write(slug)
print('게시 준비 →', slug); print(cap)
