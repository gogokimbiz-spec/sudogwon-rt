"""상장사 매출 상위 500 재무 순위 페이지 (GitHub Pages /fin/). 기업 재무정보(이용허락 제한 없음)만 사용.
사용법: python build_fin.py fin_data.json site
결과: site/fin/index.html, site/fin/summary.json (post_blogger_fin.py 입력)
"""
import json, sys, os, html, statistics, datetime

raw = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = os.path.join(sys.argv[2], 'fin')
os.makedirs(OUT, exist_ok=True)
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
BLOG = 'https://sudogwon-rt.blogspot.com/'
esc = html.escape
C = raw['companies']

# 금액 단위 자동 맞춤 (원 기준이 아니면 보정)
sales = [x['f']['sales'] for x in C if x['f'] and x['f'].get('sales')]
med = statistics.median(sales) if sales else 1e12
scale = 1_000_000 if med < 1e7 else 1000 if med < 1e10 else 1
if scale != 1:
    print(f'재무 금액 단위 보정 x{scale}')
    for x in C:
        for f in (x['f'], x['fp']):
            if f:
                for k in ('sales', 'op', 'ni', 'assets', 'debt', 'equity'):
                    if f.get(k) is not None: f[k] *= scale


def ratio(a, b):
    return None if a is None or not b else a / b


for x in C:
    f, fp = x['f'] or {}, x['fp'] or {}
    x['opm'] = round(ratio(f.get('op'), f.get('sales')) * 100, 1) if f.get('op') is not None and f.get('sales') and f['sales'] > 0 else None
    x['roe'] = round(f['ni'] / f['equity'] * 100, 1) if f.get('ni') is not None and f.get('equity') and f['equity'] > 0 else None
    x['dr'] = round(f['debt'] / f['equity'] * 100, 1) if f.get('debt') is not None and f.get('equity') and f['equity'] > 0 else None
    x['gr'] = round((f['sales'] / fp['sales'] - 1) * 100, 1) if f.get('sales') and fp.get('sales') and fp['sales'] >= 1e10 else None
    x['opg'] = round((f['op'] / fp['op'] - 1) * 100, 1) if f.get('op') is not None and fp.get('op') and fp['op'] >= 5e9 else None
    x['turn'] = bool(fp.get('op') is not None and f.get('op') is not None and fp['op'] < 0 < f['op'])
    x['sales'], x['op'], x['ni'] = f.get('sales'), f.get('op'), f.get('ni')

# 최신 분기 (DART) – 가장 많은 회사가 낸 보고서 기간으로만 순위
from collections import Counter
qps = Counter(x['q']['period'] for x in C if x.get('q'))
QP = qps.most_common(1)[0][0] if qps else None
QSPAN = next((x['q']['span'] for x in C if x.get('q') and x['q']['period'] == QP), '')
for x in C:
    q = x.get('q') if x.get('q') and x['q']['period'] == QP else {}
    x['q_sales'], x['q_op'] = q.get('sales'), q.get('op')
    x['q_opm'] = round(q['op'] / q['sales'] * 100, 1) if q.get('op') is not None and q.get('sales') and q['sales'] > 0 else None
    x['q_gr'] = round((q['sales'] / q['sales_p'] - 1) * 100, 1) if q.get('sales') and q.get('sales_p') and q['sales_p'] >= 1e10 else None
    x['q_opg'] = round((q['op'] / q['op_p'] - 1) * 100, 1) if q.get('op') is not None and q.get('op_p') and q['op_p'] >= 5e9 else None
    x['q_turn'] = bool(q.get('op_p') is not None and q.get('op') is not None and q['op_p'] < 0 < q['op'])
    x['q_dr'] = round(q['debt'] / q['equity'] * 100, 1) if q.get('debt') is not None and q.get('equity') and q['equity'] > 0 else None
    x['stock'] = x.get('stock')

FY = raw.get('fy') or '-'
nonfin = [x for x in C if not x['financial'] and x['sales'] and x['sales'] >= 5e10]


def top(rows, key, rev, n=20):
    rows = [x for x in rows if x.get(key) is not None]
    return sorted(rows, key=lambda x: (-x[key] if rev else x[key], -(x['sales'] or 0)))[:n]


R = {
    'sales': top(C, 'sales', True),
    'opm': top([x for x in nonfin if (x['opm'] or 0) <= 100], 'opm', True),   # 지분법 이익이 큰 지주사(영업이익>매출) 제외
    'roe': top([x for x in nonfin if (x['ni'] or 0) > 0], 'roe', True),
    'growth': top(nonfin, 'gr', True),
    'opg': top(nonfin, 'opg', True),
    'low_debt': top(nonfin, 'dr', False),
    'turn': sorted([x for x in nonfin if x['turn']], key=lambda x: -x['op'])[:20],
}
if QP:
    qn = [x for x in C if not x['financial'] and (x['q_sales'] or 0) >= 2e10]
    R = {'q_gr': top(qn, 'q_gr', True), 'q_opg': top(qn, 'q_opg', True), 'q_opm': top([x for x in qn if (x['q_opm'] or 0) <= 100], 'q_opm', True),
         'q_turn': sorted([x for x in qn if x['q_turn']], key=lambda x: -x['q_op'])[:20], 'q_low_debt': top(qn, 'q_dr', False), **R}
QT = {'q_gr': f'{QP} 누적 매출 증가율 TOP 20', 'q_opg': f'{QP} 누적 영업이익 증가율 TOP 20', 'q_opm': f'{QP} 누적 영업이익률 TOP 20',
      'q_turn': f'{QP} 누적 흑자전환 기업', 'q_low_debt': f'{QP}말 부채비율 낮은 20곳'} if QP else {}
TITLES = {**QT, 'sales': f'{FY}년 매출 TOP 20', 'opm': f'{FY}년 영업이익률 TOP 20', 'roe': f'{FY}년 ROE TOP 20', 'growth': f'{FY}년 매출 성장률 TOP 20',
          'opg': f'{FY}년 영업이익 증가율 TOP 20', 'low_debt': f'{FY}년말 부채비율 낮은 20곳', 'turn': f'{FY}년 영업이익 흑자전환 기업'}


def won(v):
    if v is None: return '-'
    s = '-' if v < 0 else ''; v = abs(v)
    if v >= 1e12:
        j, e = divmod(round(v / 1e8), 10000)
        return f'{s}{j:,}조 {e:,}억' if e else f'{s}{j:,}조'
    return f'{s}{round(v / 1e8):,}억'


fmt = {'opm': lambda v: f'{v:.1f}%', 'roe': lambda v: f'{v:.1f}%', 'dr': lambda v: f'{v:,.0f}%',
       'gr': lambda v: f'{v:+.1f}%', 'opg': lambda v: f'{v:+.1f}%', 'sales': won, 'op': won, 'ni': won}
F = lambda k, v: '-' if v is None else fmt[k.replace('q_', '')](v)
slim = lambda x: {k: x.get(k) for k in ('rank', 'name', 'market', 'stock', 'sales', 'op', 'ni', 'opm', 'roe', 'dr', 'gr', 'opg', 'fy', 'financial', 'q_sales', 'q_op', 'q_opm', 'q_gr', 'q_opg', 'q_dr')}
# 오늘 올릴 글: 화·금요일, 주제를 돌아가며 (수동 실행 FIN_POST=none 이 아니면 오늘 주제로 게시)
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
THEMES = ['q_gr', 'q_opg', 'q_opm', 'q_turn', 'q_low_debt', 'roe'] if QP and sum(1 for x in C if x['q_sales']) >= 300 else ['opm', 'roe', 'growth', 'low_debt', 'opg', 'turn']
fp_env = os.environ.get('FIN_POST', '').strip()
slot = {1: 0, 4: 1}.get(today.weekday())
if slot is None and fp_env and fp_env != 'none': slot = 0
post = None
if slot is not None:
    if sum(1 for x in C if x['f']) < 300:
        print('::warning::재무 데이터가 부족해 오늘 글·카톡은 건너뜁니다')
    else:
        i = (today.isocalendar()[1] * 2 + slot) % len(THEMES)
        key = next((THEMES[(i + k) % len(THEMES)] for k in range(len(THEMES)) if R[THEMES[(i + k) % len(THEMES)]]), None)
        post = {'kind': 'rank', 'keys': [key]} if key else None
summary = {'post': post, 'day': today.isoformat(), 'asof': raw['asof'], 'fy': FY, 'qp': QP, 'qspan': QSPAN, 'count': len(C),
           'with_fin': sum(1 for x in C if x['f']), 'rank': {k: [slim(x) for x in v] for k, v in R.items()}}
json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- 페이지 ----
CSS = """
:root{--bg:#f3f5f7;--panel:#fff;--fg:#17202b;--muted:#5d6b7a;--line:#dde3e9;--accent:#1f5fbf;--up:#d23c3c;--down:#2a6fd6}
@media (prefers-color-scheme:dark){:root{--bg:#0f141a;--panel:#171e26;--fg:#e6ecf2;--muted:#93a1b0;--line:#2a3440;--accent:#6ea6ff;--up:#ff6b6b;--down:#6aa3ff;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,"Malgun Gothic",sans-serif;line-height:1.6;word-break:keep-all;padding:20px 16px 48px}
.w{max-width:960px;margin:0 auto;display:grid;gap:16px}a{color:var(--accent)}nav{font-size:.85rem;color:var(--muted)}
h1{font-size:1.6rem;margin:4px 0 2px;line-height:1.3}h2{font-size:1.1rem;margin:0 0 8px}.s{font-size:.8rem;color:var(--muted)}
.p{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;min-width:0}
.k{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.k div{border-top:2px solid var(--line);padding-top:6px}.k b{display:block;font-size:1.2rem}
.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:16px}
.t{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:.85rem}
th,td{text-align:left;padding:6px 4px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500;font-size:.78rem;white-space:nowrap}
td.n,th.n{text-align:right}td.n{white-space:nowrap;font-variant-numeric:tabular-nums}.up{color:var(--up)}.down{color:var(--down)}
th[data-k]{cursor:pointer}th[data-k]:hover{color:var(--accent)}input{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--fg);font-size:.9rem;margin-bottom:8px}
.m{font-size:.7rem;color:var(--muted);margin-left:4px}.tabs{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:.88rem}
.brief{display:flex;align-items:center;gap:14px;padding:16px 18px;border-radius:16px;text-decoration:none;color:#fff;background:linear-gradient(135deg,#0f2742,#1f4f8f)}
.brief b{font-size:17px;color:#fff;display:block}.brief small{font-size:13px;color:#d6e2f2}.brief .bg{margin-left:auto;background:#ff5c5c;color:#fff;font-weight:800;padding:8px 14px;border-radius:999px;white-space:nowrap}
footer{font-size:.78rem;color:var(--muted)}
"""
COLS = {'q_gr': ['q_gr', 'q_sales'], 'q_opg': ['q_opg', 'q_op'], 'q_opm': ['q_opm', 'q_op'], 'q_turn': ['q_op', 'q_opm'], 'q_low_debt': ['q_dr', 'q_opm'],
        'sales': ['sales', 'opm'], 'opm': ['opm', 'op'], 'roe': ['roe', 'ni'], 'growth': ['gr', 'sales'], 'opg': ['opg', 'op'],
        'low_debt': ['dr', 'opm'], 'turn': ['op', 'opm']}
HEAD = {'q_sales': '누적 매출', 'q_op': '누적 영업이익', 'q_opm': '영업이익률', 'q_gr': '매출 증가(전년 동기)', 'q_opg': '영업이익 증가(전년 동기)', 'q_dr': '부채비율',
        'opm': '영업이익률', 'roe': 'ROE', 'dr': '부채비율', 'gr': '매출 증가', 'opg': '영업이익 증가', 'op': '영업이익', 'sales': '매출', 'ni': '순이익'}
MK = lambda m: '코스피' if m == 'KOSPI' else '코스닥'
NAVER = 'https://finance.naver.com/item/main.naver?code='
NM = lambda x: f'<a href="{NAVER}{x["stock"]}" rel="nofollow noopener" target="_blank">{esc(x["name"])}</a>' if x.get('stock') else esc(x['name'])


def rank_table(key):
    rows = R[key]
    if not rows: return '<p class="s">해당 기업이 없습니다.</p>'
    c1, c2 = COLS[key]
    tr = ''.join(f"<tr><td>{i}</td><td>{NM(x)}<span class=m>{MK(x['market'])}</span></td>"
                 f"<td class=n><b>{F(c1, x[c1])}</b></td><td class=n>{F(c2, x[c2])}</td></tr>" for i, x in enumerate(rows, 1))
    return f'<div class=t><table><tr><th>#</th><th>기업</th><th class=n>{HEAD[c1]}</th><th class=n>{HEAD[c2]}</th></tr>{tr}</table></div>'


data_js = json.dumps([[x['rank'], x['name'], x['market'][:4], x['q_sales'], x['q_op'], x['q_opm'], x['q_gr'], x['q_opg'], x['q_dr'], x['roe'], x.get('stock') or ''] for x in C], ensure_ascii=False)
sections = ''.join(f'<section class=p id={k}><h2>{TITLES[k]}</h2>{rank_table(k)}</section>' for k in TITLES)
med = lambda k: statistics.median([x[k] for x in C if x[k] is not None]) if any(x[k] is not None for x in C) else None
title = f'상장사 매출 상위 500 실적 순위 ({QP or FY} 기준) – 매출·영업이익 증가율, 영업이익률, 부채비율'
desc = f'코스피·코스닥 상장사 중 매출 상위 500곳의 {FY} 사업연도 영업이익률, ROE, 부채비율, 매출 성장률, 흑자전환 기업을 금융위원회 재무 데이터로 정리합니다.'
body = f"""<nav><a href="{SITE}">수도권 실거래 지도</a> · <a href="{SITE}cheongyak/">청약 지도</a> · <b>기업 재무</b></nav>
<header><h1>상장사 매출 상위 500 재무 순위</h1><div class=s>{('최신 실적 ' + QP + ' (' + QSPAN + ', DART) · ') if QP else ''}{FY} 사업연도 재무제표 · {raw['asof']} 갱신</div></header>
<a class="brief" href="{BLOG}search/label/%EA%B8%B0%EC%97%85%EC%9E%AC%EB%AC%B4"><span><b>블로그에서 주간 순위 글 보기</b><small>영업이익률 · ROE · 매출 성장률 · 부채비율 · 흑자전환</small></span><span class=bg>보기 ›</span></a>
<section class=p><div class=k><div><span class=s>대상 기업</span><b>{len(C)}곳</b></div>
<div><span class=s>영업이익률 중앙값</span><b>{F('opm', med('opm'))}</b></div><div><span class=s>ROE 중앙값</span><b>{F('roe', med('roe'))}</b></div>
<div><span class=s>부채비율 중앙값</span><b>{F('dr', med('dr'))}</b></div></div>
<div class=tabs style="margin-top:12px">{''.join(f'<a href="#{k}">{TITLES[k]}</a>' for k in TITLES)} <a href="#all">전체 500곳</a></div></section>
<div class=g>{sections}</div>
<section class=p id=all><h2>전체 500곳 – {QP or FY} {QSPAN} 기준 (제목을 누르면 정렬, 기업명을 누르면 네이버 증권)</h2><input id=q placeholder="기업명 검색" aria-label="기업명 검색"><div class=t><table id=tb><thead><tr>
<th data-k=0>#</th><th data-k=1>기업</th><th class=n data-k=3>매출</th><th class=n data-k=4>영업이익</th><th class=n data-k=5>영업이익률</th><th class=n data-k=6>매출증가</th><th class=n data-k=7>영업이익증가</th><th class=n data-k=8>부채비율</th><th class=n data-k=9>ROE({FY})</th>
</tr></thead><tbody></tbody></table></div></section>
<footer>계산 방법: 영업이익률 = 영업이익 ÷ 매출, ROE = 당기순이익 ÷ 자본총계, 부채비율 = 부채총계 ÷ 자본총계 (연결재무제표 우선, 없으면 별도). 비지배지분이 포함되어 증권사 발표 수치와 다를 수 있습니다.
대상은 코스피·코스닥 상장사 중 {FY} 사업연도 매출 상위 500곳입니다. 금융업은 재무 구조가 달라 비율 순위에서 제외했습니다.<br>
자료: 금융감독원 DART 오픈API(분기 실적), 금융위원회 기업 재무정보·기업기본정보(공공데이터포털). 분기 실적은 누적 기준이며 전년 동기와 비교합니다. 참고용 데이터 정리이며 투자 권유가 아닙니다. · <a href="{SITE}privacy.html">개인정보처리방침</a></footer>"""
script = """<script>
const D=__DATA__;const tb=document.querySelector('#tb tbody'),q=document.getElementById('q');let sk=0,sd=1;
const w=v=>{if(v==null)return'-';const a=Math.abs(v),s=v<0?'-':'';if(a>=1e12){const j=Math.floor(a/1e12),e=Math.round(a%1e12/1e8);return s+j.toLocaleString()+'조'+(e?' '+e.toLocaleString()+'억':'')}return s+Math.round(a/1e8).toLocaleString()+'억'};
const p=(v,d)=>v==null?'-':v.toFixed(d)+'%';const g=v=>v==null?'-':(v>0?'+':'')+v.toFixed(1)+'%';
function draw(){const t=q.value.trim();const r=D.filter(x=>!t||x[1].includes(t)).sort((a,b)=>{const x=a[sk],y=b[sk];if(x==null)return 1;if(y==null)return-1;return(x>y?1:x<y?-1:0)*sd});
tb.innerHTML=r.map(x=>`<tr><td>${x[0]}</td><td>${x[10]?`<a href="https://finance.naver.com/item/main.naver?code=${x[10]}" rel="nofollow noopener" target="_blank">${x[1]}</a>`:x[1]}<span class=m>${x[2]=='KOSP'?'코스피':'코스닥'}</span></td><td class=n>${w(x[3])}</td><td class="n ${x[4]<0?'down':''}">${w(x[4])}</td><td class=n>${p(x[5],1)}</td><td class=n>${g(x[6])}</td><td class=n>${g(x[7])}</td><td class=n>${p(x[8],0)}</td><td class=n>${p(x[9],1)}</td></tr>`).join('')}
document.querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{const k=+h.dataset.k;sd=sk===k?-sd:(k>=3&&k!==8?-1:1);sk=k;draw()});q.oninput=draw;draw();
</script>""".replace('__DATA__', data_js)
page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{SITE}fin/">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{SITE}fin/"><meta property="og:type" content="website">
<style>{CSS}</style></head><body><div class="w">{body}</div>{script}</body></html>"""
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(page)
print(f'오늘 글: {post}')
print(f'재무 페이지 생성: {len(C)}개사, 재무 {summary["with_fin"]}개사, 사업연도 {FY}, 순위 ' + ', '.join(f'{k} {len(v)}' for k, v in R.items()))
