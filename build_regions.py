"""시군구별 아파트 실거래가 페이지를 만듭니다 (검색 유입용, GitHub Actions 용).
사용법: python build_regions.py rt_data.json site
결과: site/r/<시군구코드>.html 76개, site/r/index.html (지역 목록), site/sitemap.xml (전체 페이지 목록)
"""
import json, sys, os, html, datetime, statistics, glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
raw = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = sys.argv[2]
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
BLOG = 'https://sudogwon-rt.blogspot.com/'
names = json.load(open(os.path.join(HERE, 'names.json'), encoding='utf-8'))
geo = json.load(open(os.path.join(HERE, 'geo.json'), encoding='utf-8'))
codes = sorted(f['properties']['c'] for f in geo['features'])
esc = html.escape
PY = 3.3058
D = datetime.date.fromisoformat
asof = raw.get('asof') or datetime.date.today().isoformat()

def full(c):  # '서울 강남구' → '서울 강남구', '광명시' → '경기 광명시', '수원 장안구' → '경기 수원시 장안구'
    n = names[c]
    if c.startswith('11') or c.startswith('28'): return n
    p = n.split(' ')
    return f'경기 {n}' if len(p) == 1 else f'경기 {p[0]}시 {p[1]}'
def short(c):
    n = names[c]; p = n.split(' ')
    return p[-1] if len(p) == 1 or p[0] in ('서울', '인천') else f'{p[0]} {p[1]}'
def man(v):
    if v is None: return '-'
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}' if m else f'{e}억') if e else f'{m:,}만'
def manw(v):  # 문장용: 1억 2,768만 원 / 7,460만 원
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}만 원' if m else f'{e}억 원') if e else f'{m:,}만 원'
med = lambda a: statistics.median(a) if a else None

T = [r for r in raw['trade'] if r[8] != 'O' and r[4] > 0 and r[6] > 0 and r[0] in names]
J = [r for r in raw['jeonse'] if r[3] > 0 and r[4] > 0 and r[0] in names]
last = max(D(r[1]) for r in T)
d30, d60 = last - datetime.timedelta(29), last - datetime.timedelta(59)
months = sorted({r[1][:7] for r in T})

byT, byJ = defaultdict(list), defaultdict(list)
for r in T: byT[r[0]].append(r)
for r in J: byJ[r[0]].append(r)
pp = lambda r: r[6] / r[4] * PY

# 신고가: 같은 지역·단지·법정동·전용면적(㎡ 반올림) 이전 거래 최고가 초과
HIGH, _hf = {}, []
for _f in glob.glob(os.path.join(os.environ.get('HIGH_DIR', 'state/high'), '*.json')):
    _h = json.load(open(_f, encoding='utf-8')); HIGH[os.path.basename(_f)[:-5]] = _h.get('max', {}); _hf.append(_h.get('from'))
HIGH_TEXT = (('2006년 이후 역대 최고가' if max(int(v[:4]) for v in _hf) <= 2006 else f"{max(int(v[:4]) for v in _hf)}년 이후 최고가")
             if _hf and all(_hf) and len(_hf) >= 70 else '최근 약 6개월 최고가')
def new_highs(rows):
    hist = defaultdict(list)
    for r in sorted(rows, key=lambda r: r[1]): hist[(r[2], r[3], round(r[4]))].append(r)
    out = []
    for k, a in hist.items():
        for i, r in enumerate(a):
            if D(r[1]) < d30: continue
            prev = [x for x in a[:i] if x[1] < r[1]]
            hh = HIGH.get(r[0], {}).get(f'{r[2]}|{r[3]}|{round(round(r[4] * 10) / 10)}')   # 역대 최고가 표 (build_high.py)
            if hh and hh[1] < r[1]: prev = prev + [[r[0], hh[1], r[2], r[3], r[4], 0, hh[0], 0, '']]
            if prev:
                pm = max(prev, key=lambda x: x[6])
                if r[6] > pm[6]: out.append((r, pm))
    return sorted(out, key=lambda t: (t[0][1], t[0][6]), reverse=True)

CSS = """
:root{--bg:#f3f5f7;--panel:#fff;--fg:#17202b;--muted:#5d6b7a;--line:#dde3e9;--accent:#1f5fbf;--up:#d23c3c;--down:#2a6fd6}
@media (prefers-color-scheme:dark){:root{--bg:#0f141a;--panel:#171e26;--fg:#e6ecf2;--muted:#93a1b0;--line:#2a3440;--accent:#6ea6ff;--up:#ff6b6b;--down:#6aa3ff;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:"IBM Plex Sans KR",system-ui,-apple-system,"Malgun Gothic",sans-serif;line-height:1.6;word-break:keep-all;padding:20px max(16px,env(safe-area-inset-left,0px)) 48px}
.w{max-width:960px;margin:0 auto;display:grid;gap:16px}a{color:var(--accent)}
nav{font-size:.85rem;color:var(--muted)}h1{font-size:1.7rem;margin:4px 0 2px;line-height:1.3}h2{font-size:1.1rem;margin:0 0 8px}
.p{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;min-width:0}
.k{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.k div{border-top:2px solid var(--line);padding-top:6px}
.k b{display:block;font-size:1.25rem;font-variant-numeric:tabular-nums}.s{font-size:.8rem;color:var(--muted)}
.up{color:var(--up)}.down{color:var(--down)}.t{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:.85rem}
th,td{text-align:left;padding:6px 4px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:500;font-size:.78rem}
td.n,th.n{text-align:right}td.n{white-space:nowrap;font-variant-numeric:tabular-nums}.nh{background:var(--up);color:#fff;font-size:.7rem;padding:1px 5px;border-radius:4px;margin-left:4px}
.ctas{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}.cta{flex:1 1 240px;display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:14px;text-decoration:none;border:2px solid #1f5fbf;background:var(--panel);color:#1f5fbf;box-shadow:0 3px 10px rgba(31,95,191,.15)}
.cta.pri{background:linear-gradient(135deg,#1f5fbf,#3b82f6);color:#fff;box-shadow:0 4px 14px rgba(31,95,191,.35)}.cta .i{font-size:28px;line-height:1}.cta .tx{flex:1;min-width:0}.cta b{display:block;font-size:16px;line-height:1.3}
.cta small{display:block;font-size:12.5px;opacity:.85;margin-top:2px}.cta .go{font-weight:800;white-space:nowrap}.cta:focus-visible{outline:3px solid #f0b44c;outline-offset:2px}
.brief{display:flex;align-items:center;gap:14px;padding:16px 18px;border-radius:16px;text-decoration:none;color:#fff;background:linear-gradient(135deg,#0f2742,#1f4f8f);box-shadow:0 6px 18px rgba(15,39,66,.28)}
.brief:hover{filter:brightness(1.08)}.brief:focus-visible{outline:3px solid #f0b44c;outline-offset:2px}
.brief .bi{font-size:30px;line-height:1}.brief .bt{flex:1;min-width:0;display:grid;gap:3px}
.brief .bp{justify-self:start;background:#ff5c5c;color:#fff;font-size:12px;font-weight:700;padding:2px 10px;border-radius:999px}
.brief b{font-size:18px;line-height:1.3;color:#fff}.brief small{font-size:13px;color:#d6e2f2}
.brief .bg{background:#ff5c5c;color:#fff;font-weight:800;padding:10px 16px;border-radius:999px;white-space:nowrap}
@media (max-width:520px){.brief{padding:14px}.brief .bi{display:none}.brief b{font-size:16px}.brief .bg{padding:8px 12px}}
.regs{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:.88rem}footer{font-size:.78rem;color:var(--muted)}
"""
def page(title, desc, canon, body):
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canon}"><meta property="og:type" content="website">
<style>{CSS}</style></head><body><div class="w">{body}
<script>(async()=>{{try{{const s=await(await fetch('../summary.json?t='+Date.now())).json();const d=new Date(s.day+'T00:00:00'),w='일월화수목금토'[d.getDay()],n=(s.new_highs||[]).length;for(const a of document.querySelectorAll('a.brief')){{if(s.blog_url)a.href=s.blog_url;a.querySelector('b').textContent=`${{d.getMonth()+1}}월 ${{d.getDate()}}일(${{w}}) 실거래 브리핑 보기`;a.querySelector('small').textContent=(n?`신고가 ${{n}}건 · `:'')+`매매 ${{s.trade_count}}건 · 거래가 TOP 20`+(s.news?' · 오늘의 뉴스':'');}}}}catch(e){{}}}})();</script>
<footer>자료: 국토교통부 실거래가 공개시스템(공공데이터포털 API). 해제 신고 거래 제외, 계약일 기준. 실거래는 계약 후 30일 안에 신고되므로 최근 거래는 더 늘어날 수 있습니다. 참고용 정보이며 투자 권유가 아닙니다. · <a href="{SITE}privacy.html">개인정보처리방침</a></footer>
</div></body></html>"""

def region_links(cur=None):
    groups = [('서울', '11'), ('인천', '28'), ('경기', '41')]
    out = []
    for g, p in groups:
        links = ' '.join(f'<a href="{c}.html">{esc(short(c))}</a>' if c != cur else f'<b>{esc(short(c))}</b>' for c in codes if c.startswith(p))
        out.append(f'<p><b>{g}</b> <span class="regs">{links}</span></p>')
    return ''.join(out)

os.makedirs(os.path.join(OUT, 'r'), exist_ok=True)
index_rows = []
for c in codes:
    rows, jrows = byT.get(c, []), byJ.get(c, [])
    nm, fn = names[c], full(c)
    cur = [pp(r) for r in rows if D(r[1]) >= d30]; prv = [pp(r) for r in rows if d60 <= D(r[1]) < d30]
    m1, m0 = med(cur), med(prv)
    chg = (m1 / m0 - 1) * 100 if m1 and m0 and len(cur) >= 10 and len(prv) >= 10 else None
    jcur = [r[4] / r[3] * PY for r in jrows if D(r[1]) >= d30]; jm = med(jcur)
    ratio = jm / m1 * 100 if jm and m1 and len(jcur) >= 10 else None
    # 단지별 30일
    cx = defaultdict(list)
    for r in rows:
        if D(r[1]) >= d30: cx[(r[2], r[3])].append(r)
    top = sorted(cx.items(), key=lambda kv: (-len(kv[1]), -med([x[6] for x in kv[1]])))[:10]
    nh = new_highs(rows)
    recent = sorted(rows, key=lambda r: (r[1], r[6]), reverse=True)[:50]
    # 월별
    mrows = ''
    for m in months:
        a = [pp(r) for r in rows if r[1].startswith(m)]; b = [r[4] / r[3] * PY for r in jrows if r[1].startswith(m)]
        mrows += f'<tr><td>{int(m[:4])}년 {int(m[5:])}월</td><td class="n">{len(a):,}</td><td class="n">{man(med(a))}</td><td class="n">{len(b):,}</td><td class="n">{man(med(b))}</td></tr>'
    # 자동 해설 문장 (페이지마다 다른 본문)
    s = [f'최근 30일({d30.month}.{d30.day}~{last.month}.{last.day}) {fn} 아파트 매매는 {len(cur):,}건 신고됐습니다.']
    if m1: s.append(f'3.3㎡당 매매가 중앙값은 {manw(m1)}' + (f'으로 직전 30일보다 {abs(chg):.1f}% {"올랐" if chg > 0 else "내렸"}습니다.' if chg is not None and abs(chg) >= 1 else '으로 직전 30일과 비슷한 수준입니다.' if chg is not None else '입니다.'))
    if top: s.append(f'거래가 가장 많은 단지는 {top[0][0][1]} {top[0][0][0]}({len(top[0][1])}건)입니다.')
    if nh: s.append(f'같은 기간 신고가 거래는 {len(nh)}건으로, 가장 최근은 {nh[0][0][2]} 전용 {round(nh[0][0][4])}㎡ {manw(nh[0][0][6])}입니다.')
    if ratio: s.append(f'전세가율(3.3㎡당 전세 ÷ 매매)은 약 {ratio:.0f}%입니다.')
    chg_html = '' if chg is None else f'<span class="{"up" if chg > 0 else "down"}">{"▲" if chg > 0 else "▼"} {abs(chg):.1f}%</span>'
    nh_html = ''.join(f'<tr><td>{r[1][5:].replace("-", ".")}</td><td>{esc(r[2])}<span class="nh">신고가</span><br><span class="s">{esc(r[3])} · {r[7]}년</span></td><td class="n">{round(r[4])}㎡ · {r[5]}층</td>'
                      f'<td class="n"><b>{man(r[6])}</b><br><span class="s">이전 {man(pm[6])} ({pm[1][2:].replace("-", ".")})</span></td></tr>' for r, pm in nh[:20])
    top_html = ''.join(f'<tr><td>{esc(a)}<br><span class="s">{esc(u)}</span></td><td class="n">{len(v)}건</td><td class="n">{man(med([x[6] for x in v]))}</td><td class="n">{man(med([pp(x) for x in v]))}</td></tr>' for (a, u), v in top)
    rec_html = ''.join(f'<tr><td>{r[1][5:].replace("-", ".")}</td><td>{esc(r[2])}<br><span class="s">{esc(r[3])} · {r[7]}년</span></td><td class="n">{round(r[4])}㎡ · {r[5]}층</td><td class="n"><b>{man(r[6])}</b></td></tr>' for r in recent)
    title = f'{short(c)} 아파트 실거래가 · 신고가 ({last.month}월 {last.day}일 기준) | 수도권 실거래 지도'
    desc = ' '.join(s)[:150]
    body = f"""<nav><a href="{SITE}">수도권 실거래 지도</a> › <a href="index.html">지역별</a> › {esc(nm)}</nav>
<header><h1>{esc(fn)} 아파트 실거래가</h1><div class="s">{last.year}년 {last.month}월 {last.day}일 계약분까지 · 매일 아침 갱신</div></header>
<a class="brief" href="https://sudogwon-rt.blogspot.com/"><span class="bi">📝</span><span class="bt"><span class="bp">매일 아침 업데이트</span><b>오늘 블로그 브리핑 보기</b><small>전날 신고가 · 거래가 TOP 20 · 오늘의 부동산 뉴스</small></span><span class="bg">보기 ›</span></a>
<section class="p"><div class="k">
<div><span class="s">최근 30일 매매</span><b>{len(cur):,}건</b></div>
<div><span class="s">3.3㎡당 매매 중앙값</span><b>{man(m1)}</b><span class="s">직전 30일 대비 {chg_html or '-'}</span></div>
<div><span class="s">3.3㎡당 전세 중앙값</span><b>{man(jm)}</b><span class="s">전세 {len(jcur):,}건</span></div>
<div><span class="s">전세가율</span><b>{f'{ratio:.0f}%' if ratio else '-'}</b></div>
<div><span class="s">신고가 (30일)</span><b>{len(nh)}건</b></div></div>
<p>{esc(' '.join(s))}</p>
<div class="ctas"><a class="cta pri" href="{SITE}"><span class="i">🗺️</span><span class="tx"><b>지역별 지도로 보기</b><small>76개 시군구 가격·변동을 한눈에</small></span><span class="go">보기 ›</span></a><a class="cta" href="{SITE}cheongyak/"><span class="i">🏗️</span><span class="tx"><b>이번 주 청약 일정</b><small>수도권 1순위 접수·분양가 비교</small></span><span class="go">보기 ›</span></a></div></section>
{f'<section class="p"><h2>최근 30일 신고가 {len(nh)}건</h2><p class="s">같은 단지·같은 전용면적의 {HIGH_TEXT}보다 비싸게 팔린 거래</p><div class="t"><table><tr><th>계약일</th><th>단지</th><th class="n">전용·층</th><th class="n">거래가</th></tr>{nh_html}</table></div></section>' if nh else ''}
{f'<section class="p"><h2>최근 30일 거래 많은 단지</h2><div class="t"><table><tr><th>단지</th><th class="n">거래</th><th class="n">거래가 중앙값</th><th class="n">3.3㎡당</th></tr>{top_html}</table></div></section>' if top else ''}
<section class="p"><h2>월별 추이</h2><div class="t"><table><tr><th>월</th><th class="n">매매</th><th class="n">3.3㎡당 매매</th><th class="n">전세</th><th class="n">3.3㎡당 전세</th></tr>{mrows}</table></div><p class="s">이번 달은 아직 신고 중이라 건수가 적게 보입니다.</p></section>
<section class="p"><h2>최근 거래 {len(recent)}건</h2><div class="t"><table><tr><th>계약일</th><th>단지</th><th class="n">전용·층</th><th class="n">거래가</th></tr>{rec_html}</table></div></section>
<a class="brief" href="https://sudogwon-rt.blogspot.com/"><span class="bi">📝</span><span class="bt"><span class="bp">놓치지 마세요</span><b>오늘 블로그 브리핑 보기</b><small>전날 신고가 · 거래가 TOP 20 · 오늘의 부동산 뉴스</small></span><span class="bg">보기 ›</span></a>
<section class="p"><h2>다른 지역 실거래가</h2>{region_links(c)}</section>"""
    open(os.path.join(OUT, 'r', f'{c}.html'), 'w', encoding='utf-8').write(page(title, desc, f'{SITE}r/{c}.html', body))
    index_rows.append(f'<tr><td><a href="{c}.html">{esc(nm)}</a></td><td class="n">{len(cur):,}</td><td class="n">{man(m1)}</td><td class="n">{"" if chg is None else f"<span class=\"{"up" if chg > 0 else "down"}\">{chg:+.1f}%</span>"}</td><td class="n">{len(nh)}</td></tr>')

body = f"""<nav><a href="{SITE}">수도권 실거래 지도</a> › 지역별</nav>
<header><h1>수도권 시군구별 아파트 실거래가</h1><div class="s">{last.year}년 {last.month}월 {last.day}일 계약분까지 · 매일 아침 갱신</div></header>
<a class="brief" href="https://sudogwon-rt.blogspot.com/"><span class="bi">📝</span><span class="bt"><span class="bp">매일 아침 업데이트</span><b>오늘 블로그 브리핑 보기</b><small>전날 신고가 · 거래가 TOP 20 · 오늘의 부동산 뉴스</small></span><span class="bg">보기 ›</span></a>
<section class="p">{region_links()}</section>
<section class="p"><h2>최근 30일 한눈에 보기</h2><div class="t"><table><tr><th>지역</th><th class="n">매매</th><th class="n">3.3㎡당</th><th class="n">직전 30일 대비</th><th class="n">신고가</th></tr>{''.join(index_rows)}</table></div></section>"""
open(os.path.join(OUT, 'r', 'index.html'), 'w', encoding='utf-8').write(
    page(f'수도권 시군구별 아파트 실거래가 ({last.month}월 {last.day}일 기준) | 수도권 실거래 지도',
         '서울·인천·경기 76개 시군구의 아파트 매매·전세 실거래가, 신고가, 최근 30일 변동을 매일 정리합니다.', f'{SITE}r/', body))

urls = [(SITE, 'daily', '1.0'), (SITE + 'r/', 'daily', '0.9'), (SITE + 'cheongyak/', 'daily', '0.8'), (SITE + 'fin/', 'daily', '0.8'), (SITE + 'unse/', 'weekly', '0.6')] + \
       [(f'{SITE}r/{c}.html', 'daily', '0.7') for c in codes] + [(SITE + 'privacy.html', 'monthly', '0.2')]
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + \
     ''.join(f'  <url><loc>{u}</loc><lastmod>{asof}</lastmod><changefreq>{f}</changefreq><priority>{p}</priority></url>\n' for u, f, p in urls) + '</urlset>\n'
open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8').write(sm)
print(f'지역 페이지 {len(codes)}개 + 목록 + 사이트맵({len(urls)}개 주소) 생성, 기준일 {last}')
