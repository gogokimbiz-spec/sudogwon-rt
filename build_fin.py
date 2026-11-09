"""시총 상위 500 재무·저평가 지표 페이지 (GitHub Pages /fin/).
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
                for k in ('sales', 'op', 'ni', 'pre_tax', 'assets', 'debt', 'equity', 'capital'):
                    if f.get(k) is not None: f[k] *= scale


def ratio(a, b):
    return None if a is None or not b else a / b


for x in C:
    f, fp = x['f'] or {}, x['fp'] or {}
    x['per'] = round(x['cap'] / f['ni'], 1) if f.get('ni') and f['ni'] > 0 else None
    x['pbr'] = round(x['cap'] / f['equity'], 2) if f.get('equity') and f['equity'] > 0 else None
    x['opm'] = round(ratio(f.get('op'), f.get('sales')) * 100, 1) if f.get('op') is not None and f.get('sales') and f['sales'] > 0 else None
    x['dr'] = round(f['debt'] / f['equity'] * 100, 1) if f.get('debt') is not None and f.get('equity') and f['equity'] > 0 else None
    x['gr'] = round((f['sales'] / fp['sales'] - 1) * 100, 1) if f.get('sales') and fp.get('sales') and fp['sales'] >= 1e10 else None
    x['turn'] = bool(fp.get('op') is not None and f.get('op') is not None and fp['op'] < 0 < f['op'])
    x['sales'], x['op'], x['ni'] = f.get('sales'), f.get('op'), f.get('ni')

fys = [x['fy'] for x in C if x['fy']]
FY = max(set(fys), key=fys.count) if fys else '-'
nonfin = [x for x in C if not x['financial'] and x['sales'] and x['sales'] >= 5e10]


def top(rows, key, rev, n=20):
    rows = [x for x in rows if x.get(key) is not None]
    return sorted(rows, key=lambda x: (-x[key] if rev else x[key], -x['cap']))[:n]


R = {
    'low_per': top(C, 'per', False),
    'low_pbr': top(C, 'pbr', False),
    'opm': top(nonfin, 'opm', True),
    'low_debt': top(nonfin, 'dr', False),
    'growth': top(nonfin, 'gr', True),
    'turn': sorted([x for x in nonfin if x['turn']], key=lambda x: -x['op'])[:20],
}
TITLES = {'low_per': 'PER 낮은 20곳', 'low_pbr': 'PBR 낮은 20곳', 'opm': '영업이익률 높은 20곳',
          'low_debt': '부채비율 낮은 20곳', 'growth': '매출 성장률 높은 20곳', 'turn': '영업이익 흑자전환 기업'}


def won(v):
    if v is None: return '-'
    s = '-' if v < 0 else ''; v = abs(v)
    if v >= 1e12:
        j, e = divmod(round(v / 1e8), 10000)
        return f'{s}{j:,}조 {e:,}억' if e else f'{s}{j:,}조'
    return f'{s}{round(v / 1e8):,}억'


fmt = {'per': lambda v: f'{v:,.1f}배', 'pbr': lambda v: f'{v:.2f}배', 'opm': lambda v: f'{v:.1f}%',
       'dr': lambda v: f'{v:,.0f}%', 'gr': lambda v: f'{v:+.1f}%'}
F = lambda k, v: '-' if v is None else fmt[k](v)
slim = lambda x: {k: x[k] for k in ('rank', 'code', 'name', 'market', 'close', 'chg', 'cap', 'per', 'pbr', 'opm', 'dr', 'gr', 'sales', 'op', 'ni', 'fy', 'financial')}
# 오늘 올릴 글 (화요일 순위 글 · 금요일 저평가 지표 글, 수동 실행 시 FIN_POST=rank|value)
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
THEMES = ['opm', 'low_debt', 'growth', 'turn']   # 순위 글은 주마다 돌아가며
fp_env = os.environ.get('FIN_POST', '').strip()
kind = fp_env if fp_env in ('rank', 'value') else {1: 'rank', 4: 'value'}.get(today.weekday())
post = None
if kind and sum(1 for x in C if x['f']) < len(C) * 0.6:
    print('::warning::재무 데이터가 부족해 오늘 글·카톡은 건너뜁니다')
elif kind == 'value':
    post = {'kind': 'value', 'keys': ['low_per', 'low_pbr']}
elif kind == 'rank':
    i = today.isocalendar()[1] % len(THEMES)
    key = next((THEMES[(i + k) % 4] for k in range(4) if R[THEMES[(i + k) % 4]]), None)
    post = {'kind': 'rank', 'keys': [key]} if key else None
summary = {'post': post, 'day': today.isoformat(), 'basDt': raw['basDt'], 'asof': raw['asof'], 'fy': FY, 'count': len(C),
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
COLS = {'low_per': ['per', 'pbr'], 'low_pbr': ['pbr', 'per'], 'opm': ['opm', 'op'], 'low_debt': ['dr', 'opm'], 'growth': ['gr', 'sales'], 'turn': ['op', 'opm']}
HEAD = {'per': 'PER', 'pbr': 'PBR', 'opm': '영업이익률', 'dr': '부채비율', 'gr': '매출 증가', 'op': '영업이익', 'sales': '매출'}
cell = lambda k, x: won(x[k]) if k in ('op', 'sales', 'ni', 'cap') else F(k, x[k])


def rank_table(key):
    rows = R[key]
    if not rows: return '<p class="s">해당 기업이 없습니다.</p>'
    c1, c2 = COLS[key]
    tr = ''.join(f"<tr><td>{i}</td><td>{esc(x['name'])}<span class=m>{'코스피' if x['market'] == 'KOSPI' else '코스닥'}</span></td>"
                 f"<td class=n><b>{cell(c1, x)}</b></td><td class=n>{cell(c2, x)}</td><td class=n>{won(x['cap'])}</td></tr>" for i, x in enumerate(rows, 1))
    return f'<div class=t><table><tr><th>#</th><th>기업</th><th class=n>{HEAD[c1]}</th><th class=n>{HEAD[c2]}</th><th class=n>시가총액</th></tr>{tr}</table></div>'


b = raw['basDt']; bd = datetime.date.fromisoformat(b)
data_js = json.dumps([[x['rank'], x['name'], x['market'][:4], x['close'], x['chg'], x['cap'], x['per'], x['pbr'], x['opm'], x['dr'], x['gr']] for x in C], ensure_ascii=False)
sections = ''.join(f'<section class=p id={k}><h2>{TITLES[k]}</h2>{rank_table(k)}</section>' for k in ('low_per', 'low_pbr', 'opm', 'low_debt', 'growth', 'turn'))
title = f'시가총액 상위 500 PER·PBR·영업이익률·부채비율 ({bd.month}월 {bd.day}일 종가 기준)'
desc = f'코스피·코스닥 시가총액 상위 500개 기업의 PER, PBR, 영업이익률, 부채비율, 매출 성장률을 {FY} 사업연도 재무제표와 {bd.month}월 {bd.day}일 종가로 매일 계산합니다.'
body = f"""<nav><a href="{SITE}">수도권 실거래 지도</a> · <a href="{SITE}cheongyak/">청약 지도</a> · <b>기업 재무</b></nav>
<header><h1>시가총액 상위 500 기업 재무 지표</h1><div class=s>{bd.year}년 {bd.month}월 {bd.day}일 종가 · {FY} 사업연도 재무제표 · 매일 아침 갱신</div></header>
<a class="brief" href="{BLOG}search/label/%EA%B8%B0%EC%97%85%EC%9E%AC%EB%AC%B4"><span><b>블로그에서 주간 순위 글 보기</b><small>영업이익률 · 부채비율 · 흑자전환 · PER·PBR</small></span><span class=bg>보기 ›</span></a>
<section class=p><div class=k><div><span class=s>대상 기업</span><b>{len(C)}곳</b></div><div><span class=s>재무 확인</span><b>{summary['with_fin']}곳</b></div>
<div><span class=s>PER 중앙값</span><b>{F('per', statistics.median([x['per'] for x in C if x['per']]) if any(x['per'] for x in C) else None)}</b></div>
<div><span class=s>PBR 중앙값</span><b>{F('pbr', statistics.median([x['pbr'] for x in C if x['pbr']]) if any(x['pbr'] for x in C) else None)}</b></div></div>
<div class=tabs style="margin-top:12px">{''.join(f'<a href="#{k}">{TITLES[k]}</a>' for k in TITLES)} <a href="#all">전체 500곳</a></div></section>
<div class=g>{sections}</div>
<section class=p id=all><h2>전체 500곳 (제목을 누르면 정렬)</h2><input id=q placeholder="기업명 검색" aria-label="기업명 검색"><div class=t><table id=tb><thead><tr>
<th data-k=0>#</th><th data-k=1>기업</th><th class=n data-k=3>종가</th><th class=n data-k=4>등락</th><th class=n data-k=5>시가총액</th><th class=n data-k=6>PER</th><th class=n data-k=7>PBR</th><th class=n data-k=8>영업이익률</th><th class=n data-k=9>부채비율</th><th class=n data-k=10>매출증가</th>
</tr></thead><tbody></tbody></table></div></section>
<footer>계산 방법: PER = 시가총액 ÷ 당기순이익, PBR = 시가총액 ÷ 자본총계 (연결재무제표 우선, 없으면 별도). 당기순이익·자본총계에 비지배지분이 포함되어 증권사 발표 수치와 다를 수 있습니다.
적자 기업은 PER을 표시하지 않습니다. 은행·보험·증권 등 금융업은 재무 구조가 달라 영업이익률·부채비율·성장률 순위에서 제외했습니다. 보통주 기준이며 스팩은 제외했습니다.<br>
자료: 금융위원회 주식시세정보·KRX상장종목정보·기업 재무정보 (공공데이터포털 API). 참고용 데이터 정리이며 투자 권유가 아닙니다. 투자 판단과 책임은 본인에게 있습니다. · <a href="{SITE}privacy.html">개인정보처리방침</a></footer>"""
script = """<script>
const D=__DATA__;const tb=document.querySelector('#tb tbody'),q=document.getElementById('q');let sk=0,sd=1;
const w=v=>{if(v==null)return'-';const a=Math.abs(v),s=v<0?'-':'';if(a>=1e12){const j=Math.floor(a/1e12),e=Math.round(a%1e12/1e8);return s+j.toLocaleString()+'조'+(e?' '+e.toLocaleString()+'억':'')}return s+Math.round(a/1e8).toLocaleString()+'억'};
const f=(v,d,u)=>v==null?'-':v.toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d})+u;
function draw(){const t=q.value.trim();const r=D.filter(x=>!t||x[1].includes(t)).sort((a,b)=>{const x=a[sk],y=b[sk];if(x==null)return 1;if(y==null)return-1;return(x>y?1:x<y?-1:0)*sd});
tb.innerHTML=r.map(x=>`<tr><td>${x[0]}</td><td>${x[1]}<span class=m>${x[2]=='KOSP'?'코스피':'코스닥'}</span></td><td class=n>${f(x[3],0,'')}</td><td class="n ${x[4]>0?'up':x[4]<0?'down':''}">${x[4]>0?'+':''}${x[4].toFixed(2)}%</td><td class=n>${w(x[5])}</td><td class=n>${f(x[6],1,'배')}</td><td class=n>${f(x[7],2,'배')}</td><td class=n>${f(x[8],1,'%')}</td><td class=n>${f(x[9],0,'%')}</td><td class=n>${x[10]==null?'-':(x[10]>0?'+':'')+x[10].toFixed(1)+'%'}</td></tr>`).join('')}
document.querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{const k=+h.dataset.k;sd=sk===k?-sd:(k>=5&&k!==6&&k!==7&&k!==9?-1:1);sk=k;draw()});q.oninput=draw;draw();
</script>""".replace('__DATA__', data_js)
page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{SITE}fin/">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{SITE}fin/"><meta property="og:type" content="website">
<style>{CSS}</style></head><body><div class="w">{body}</div>{script}</body></html>"""
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(page)
print(f'오늘 글: {post}')
print(f'재무 페이지 생성: {len(C)}개사, 재무 {summary["with_fin"]}개사, 사업연도 {FY}, 순위 ' + ', '.join(f'{k} {len(v)}' for k, v in R.items()))
