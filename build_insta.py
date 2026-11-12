"""인스타그램 게시용 페이지(site/insta/index.html)를 만듭니다 (GitHub Actions 용, 매일).
사용법: python build_insta.py site
- 이미 만들어진 카드 이미지와 게시 문구(caption.txt)를 한 페이지에 모읍니다. 카톡·텔레그램으로는 보내지 않습니다.
- 실거래: 매일 / 청약: 월~금 / 기업재무: 토(오늘 재무 글이 있는 날) / 동네 대표기업: 목
- 검색엔진에 노출되지 않게 noindex. 사이트맵에도 넣지 않습니다.
- 오늘 게시물은 insta/img/*.jpg 와 insta/posts.json 으로도 저장 (post_instagram.py 자동 게시용)
- 해시태그는 5개로 줄입니다: #데이터로보는재테크 + 주제 태그 2개 + 그날 데이터(지역 등) 태그 2개
"""
import sys, os, json, glob, html, datetime

SITE = sys.argv[1]
OUT = os.path.join(SITE, 'insta'); os.makedirs(OUT, exist_ok=True)
KST = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=9)
TODAY = KST.date(); WD = TODAY.weekday()            # 0=월 … 6=일
WDN = '월화수목금토일'[WD]
VER = os.environ.get('GITHUB_RUN_ID') or KST.strftime('%Y%m%d%H%M')
BRAND_TAG = '#데이터로보는재테크'


def load(p):
    try: return json.load(open(os.path.join(SITE, p), encoding='utf-8'))
    except Exception: return None


def read(p):
    try: return open(os.path.join(SITE, p), encoding='utf-8').read().strip()
    except Exception: return ''


def trim_tags(cap, n_fixed, suffix=''):
    """마지막 해시태그 줄을 5개로: 브랜드 + 앞쪽 주제 태그 2 + 데이터 태그(앞에서 n_fixed 개 이후) 2"""
    lines = cap.split('\n')
    if not lines or not lines[-1].lstrip().startswith('#'): return cap + '\n\n' + BRAND_TAG
    tags = [t for t in lines[-1].split() if t.startswith('#')]
    keep = [BRAND_TAG] + tags[:2] + [t if t.endswith(suffix) else t + suffix for t in tags[n_fixed:n_fixed + 2]]
    lines[-1] = ' '.join(dict.fromkeys(keep))
    return '\n'.join(lines)


def imgs(folder, names):
    return [f'{folder}/{n}' for n in names if os.path.exists(os.path.join(SITE, folder, n))]


sections = []

# ── 1. 실거래 (매일)
S = load('summary.json')
if S:
    car = sorted(os.path.basename(p) for p in glob.glob(os.path.join(SITE, 'cards', '[0-9][0-9].png')))
    cap = read('cards/caption.txt')
    if car and cap:
        sections.append(dict(key='rt', title='실거래 신고가', when='매일', today=True,
                             guide=f'사진 {len(car)}장을 순서대로 선택(여러 장) → 캡션 붙여넣기',
                             images=imgs('cards', car), alt=imgs('cards', ['single.png']),
                             caption=trim_tags(cap, 7, '아파트')))

# ── 1-2. 오늘의 신고가 1위 (실거래 캐러셀과 별도 게시물, 있는 날만 – 2026-11-12)
HJ = load('cards/hero.json'); hero_img = imgs('cards', ['hero.png'])
if HJ and hero_img:
    def _man(v):
        v = int(round(v)); e, m = divmod(v, 10000)
        return (f'{e}억 {m:,}만' if m else f'{e}억') if e else f'{m:,}만'
    city = HJ['region'].split(' ')[-1] if HJ['region'].split(' ')[0] in ('서울', '인천') else HJ['region'].split(' ')[0]
    hcap = [f"🏆 오늘의 신고가 1위 | {HJ['apt']} {_man(HJ['price_man'])}", '',
            f"· {HJ['region']} {HJ.get('umd', '')} · 전용 {HJ['area']}㎡ · {HJ.get('floor', '')}층 · {HJ.get('built', '')}년",
            f"· 이전 최고 {_man(HJ['prev_high_man'])} → {_man(HJ['price_man'])} (▲{_man(HJ['price_man'] - HJ['prev_high_man'])})" if HJ.get('prev_high_man') else '',
            '', '※ 그날 수도권 아파트 신고가(같은 단지·같은 면적 최근 6개월 최고가 경신) 중 가장 비싼 거래',
            '자료: 국토교통부 실거래가' + (' · 항공사진 국토교통부 브이월드' if HJ.get('src') not in (None, '그림') else ''),
            '', '전체 실거래·지역별 지도는 프로필 링크에서 👆', '',
            ' '.join(dict.fromkeys([BRAND_TAG, '#신고가', '#아파트실거래가', f'#{city}아파트', '#' + HJ['apt'].replace(' ', '')[:15]]))]
    sections.append(dict(key='hero', title='오늘의 신고가 1위', when='있는 날', today=True,
                         guide='사진 1장 선택 → 캡션 붙여넣기', images=hero_img, alt=[], caption='\n'.join(x for x in hcap if x is not None)))

# ── 1-3. 구별 아파트값 상승률 (매주 월요일 주간 · 매월 첫째 월요일 월간, 2026-11-12)
TR = load('trend/summary.json')
if TR:
    for m, title, when in (('week', '구별 상승률 (주간)', '매주 월요일'), ('month', '구별 상승률 (월간)', '첫째 월요일')):
        im_ = imgs('trend', [f'{m}.png']); c_ = read(f'trend/caption_{m}.txt')
        if im_ and c_ and m in (TR.get('today') or []):
            sections.append(dict(key=f'trend_{m}', title=title, when=when, today=True,
                                 guide='사진 1장 선택 → 캡션 붙여넣기', images=im_, alt=[], caption=c_))

# ── 2. 청약 (월: 이번 주 청약 / 화: 1순위 결과 / 수: 줍줍·로또 / 목: 가점 커트라인 / 금: 단지분석 – 2026-11-11)
CY = load('cheongyak/summary.json')
CYV = {0: ('이번 주 청약', 'cheongyak/cards', ['single.png']),
       1: ('청약 결과', 'cheongyak/cards_tue', None),
       2: ('줍줍·로또 청약', 'cheongyak/cards_wed', None),
       3: ('당첨 가점 커트라인', 'cheongyak/cards_thu', None),
       4: ('청약 단지분석', 'cheongyak/cards_sat', None)}
if CY:
    order = ([WD] if WD in CYV else []) + ([0] if WD != 0 else [])   # 오늘 것, 없으면 월요일 것을 미리보기로
    for wd in order:
        title, folder, names = CYV[wd]
        if names is None:
            names = sorted(os.path.basename(x) for x in glob.glob(os.path.join(SITE, folder, '[0-9][0-9].png')))
        c_ = read(f'{folder}/caption.txt'); im_ = imgs(folder, names)
        if c_ and im_:
            sections.append(dict(key='cy', title=title, when='월~금', today=(wd == WD),
                                 guide=f'사진 {len(im_)}장 선택 → 캡션 붙여넣기', images=im_, alt=[], caption=trim_tags(c_, 7)))
            break

# ── 3. 기업재무 (토, 재무 글이 있는 날)
FN = load('fin/summary.json')
fin_img = imgs('fin/cards', ['single.png'])
if FN and FN.get('post') and fin_img:
    NAME = {'opm': ('영업이익률 TOP', 'opm', '영업이익률'), 'roe': ('ROE TOP', 'roe', 'ROE'),
            'growth': ('매출 성장률 TOP', 'gr', '매출성장'), 'opg': ('영업이익 증가율 TOP', 'opg', '영업이익'),
            'low_debt': ('부채비율 낮은 기업', 'dr', '부채비율'), 'turn': ('흑자전환 기업', 'op', '흑자전환')}
    fmt = {'opm': lambda v: f'{v:.1f}%', 'roe': lambda v: f'{v:.1f}%', 'dr': lambda v: f'{v:,.0f}%',
           'gr': lambda v: f'{v:+.1f}%', 'opg': lambda v: f'{v:+.1f}%',
           'op': lambda v: f'{v / 1e12:,.1f}조' if abs(v) >= 1e12 else f'{v / 1e8:,.0f}억'}
    key = FN['post']['keys'][0]
    q = key.startswith('q_')                      # 분기(누적) 순위: q_opm, q_gr … → 값도 q_ 필드
    t, k, tag = NAME.get(key[2:] if q else key, (key, key, '기업분석'))
    vk = ('q_' + k) if q else k
    rows = (FN.get('rank') or {}).get(key, [])[:10]
    if q:
        L = [f"📊 {FN.get('qp', '')} {t} 10", f"{FN.get('qspan', '')} 기준 · 상장사 매출 상위 500곳", '']
    else:
        L = [f"📊 {t} 10 | {FN.get('fy', '')} 사업연도", '상장사 매출 상위 500곳 기준', '']
    for i, x in enumerate(rows, 1):
        try: L.append(f"{i}. {x['name']} {fmt[k](x[vk])}")
        except Exception: L.append(f"{i}. {x.get('name', '')}")
    L += ['', '※ 금융업은 비율 순위에서 제외', ('자료: 금융감독원 DART 정기보고서' if q else '자료: 금융위원회 기업 재무정보') + ' · 참고용 정보이며 투자 권유가 아닙니다',
          '', '500곳 전체 표는 프로필 링크에서 👆', '',
          ' '.join(dict.fromkeys([BRAND_TAG, '#기업분석', '#재테크', f'#{tag}', '#상장사']))]
    sections.append(dict(key='fin', title='기업재무 순위', when='토', today=WD == 5,
                         guide='사진 1장 선택 → 캡션 붙여넣기', images=fin_img, alt=[], caption='\n'.join(L)))

# ── 4. 동네 대표기업 (목, 인스타·스레드 전용 – 블로그·카톡 없음, 2026-11-11)
DG = load('dong/summary.json')
dong_img = imgs('dong/cards', ['single.png'])
if DG and DG.get('post') and dong_img:
    from region_fmt import short, man, emp, tenure
    P = DG['post']; area = P['name'].split()[-1]
    rng = 'TOP 10' if P['start'] == 1 else f"{P['start']}~{P['end']}위"
    L = [f"🏢 {area} 대표기업 {rng} | {P['name']} 본사", f"{DG['fy']}년 매출 기준 · 비상장 포함", '']
    for x in P['rows']:
        L.append(f"{x['rank']}. {x['n']} 매출 {short(x['sales'])} · 영업이익 {short(x.get('op'))}")
        sub = ' · '.join(t for t in [f"직원 {emp(x['emp'])}" if x.get('emp') else '', f"근속 {tenure(x['tenure'])}" if x.get('tenure') else '',
                                     f"평균연봉 {man(x['sal'])}" if x.get('sal') else ''] if t)
        if sub: L.append('   ' + sub)
    L += ['', '※ 본사 주소 기준 · 직원·근속·연봉은 공시한 회사만 표시',
          '자료: 금융위원회 기업 재무정보·기업기본정보 · 참고용 정보', '',
          f'{area} 아파트 실거래가는 프로필 링크에서 👆', '',
          ' '.join(dict.fromkeys([BRAND_TAG, '#동네대표기업', f'#{area}', f'#{area}회사', '#연봉']))]
    sections.append(dict(key='dong', title='동네 대표기업', when='목', today=True,
                         guide='사진 1장 선택 → 캡션 붙여넣기', images=dong_img, alt=[], caption='\n'.join(L)))

# ── 자동 게시용: JPEG 복사본 + posts.json (Instagram API 는 공개 주소의 JPEG 만 받음 → post_instagram.py 가 사용)
try:
    from PIL import Image
    IMG = os.path.join(OUT, 'img'); os.makedirs(IMG, exist_ok=True)
    posts = []
    for s in sections:
        if not s['today']: continue
        urls = []
        for i, p in enumerate(s['images'][:10], 1):          # 캐러셀은 최대 10장
            name = f"{s['key']}_{i:02d}.jpg"
            Image.open(os.path.join(SITE, p)).convert('RGB').save(os.path.join(IMG, name), 'JPEG', quality=92)
            urls.append(f'insta/img/{name}')
        posts.append({'key': s['key'], 'title': s['title'], 'images': urls, 'caption': s['caption']})
    json.dump({'day': TODAY.isoformat(), 'posts': posts}, open(os.path.join(OUT, 'posts.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'자동 게시용 posts.json: {len(posts)}건')
except Exception as e:
    print('::warning::자동 게시용 JPEG/posts.json 생성 실패:', e)

# ── 페이지
todo = [s for s in sections if s['today']]
later = [s for s in sections if not s['today']]
E = html.escape


def card(s, idx):
    ims = ''.join(f'<a class="im" href="../{p}?v={VER}" download="{s["key"]}_{TODAY:%m%d}_{i:02d}.png">'
                  f'<img src="../{p}?v={VER}" loading="lazy" alt=""><span>{i}</span></a>'
                  for i, p in enumerate(s['images'], 1))
    alt = ''
    if s['alt']:
        p = s['alt'][0]
        alt = (f'<details><summary>한 장짜리 요약 이미지로 올리기</summary>'
               f'<a class="im one" href="../{p}?v={VER}" download="{s["key"]}_{TODAY:%m%d}_single.png">'
               f'<img src="../{p}?v={VER}" loading="lazy" alt=""></a></details>')
    return f'''
<section class="card{' dim' if not s['today'] else ''}">
  <div class="hd"><b>{E(s['title'])}</b><em>{E(s['when'])}</em></div>
  <p class="guide">{E(s['guide'])}</p>
  <div class="ims">{ims}</div>
  <p class="tip">이미지를 길게 눌러 '사진에 저장' (PC는 클릭하면 저장)</p>
  {alt}
  <textarea id="c{idx}" readonly>{E(s['caption'])}</textarea>
  <button onclick="cp('c{idx}', this)">캡션 복사</button>
</section>'''


body = ''.join(card(s, i) for i, s in enumerate(todo)) or '<p class="none">오늘 올릴 게시물이 없어요.</p>'
if later:
    body += '<h2>다른 요일 게시물 (미리보기)</h2>' + ''.join(card(s, i + 100) for i, s in enumerate(later))

page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>인스타 게시용 | 데이터로 보는 재테크</title>
<style>
:root{{--navy:#13233F;--red:#FF4D4F;--bg:#F4F6FA;--ink:#18202C;--ink2:#6B7685}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif}}
header{{background:var(--navy);color:#fff;padding:20px 16px}}header small{{opacity:.7}}header h1{{margin:4px 0 0;font-size:22px}}
main{{max-width:640px;margin:0 auto;padding:12px 16px 40px}}
.todo{{background:#fff;border-radius:14px;padding:12px 16px;margin:4px 0 12px;font-size:15px}}
.card{{background:#fff;border-radius:16px;padding:16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}.dim{{opacity:.75}}
.hd{{display:flex;justify-content:space-between;align-items:center}}.hd b{{font-size:19px}}
.hd em{{font-style:normal;font-size:13px;background:var(--navy);color:#fff;border-radius:20px;padding:3px 10px}}
.guide{{margin:6px 0 10px;color:var(--ink2);font-size:14px}}.tip{{margin:6px 0;color:var(--ink2);font-size:12px}}
.ims{{display:flex;gap:8px;overflow-x:auto;padding-bottom:4px}}
.im{{position:relative;flex:0 0 46%;display:block}}.im img{{width:100%;border-radius:10px;display:block;border:1px solid #e3e7ee}}
.im span{{position:absolute;left:6px;top:6px;background:rgba(0,0,0,.6);color:#fff;font-size:12px;border-radius:10px;padding:1px 7px}}
.im.one{{width:60%;margin-top:8px}}details{{margin:6px 0;font-size:14px;color:var(--ink2)}}
textarea{{width:100%;height:180px;margin-top:8px;border:1px solid #dfe3ea;border-radius:10px;padding:10px;font-size:14px;line-height:1.5;font-family:inherit;resize:vertical}}
button{{width:100%;margin-top:8px;padding:14px;border:0;border-radius:12px;background:var(--red);color:#fff;font-size:16px;font-weight:700}}
h2{{font-size:15px;color:var(--ink2);margin:28px 0 4px}}.none{{text-align:center;color:var(--ink2);padding:40px 0}}
footer{{text-align:center;color:var(--ink2);font-size:12px;padding:16px}}footer a{{color:inherit}}
</style></head><body>
<header><small>데이터로 보는 재테크 · 인스타 게시용</small><h1>{TODAY.month}월 {TODAY.day}일({WDN}) 올릴 게시물</h1></header>
<main>
<div class="todo">오늘 할 일: {' · '.join(E(s['title']) for s in todo) or '없음'}<br>
<span style="color:var(--ink2);font-size:13px">① 이미지 저장 → ② 캡션 복사 → ③ 인스타에서 새 게시물</span></div>
{body}
</main>
<footer>데이터로 보는 재테크 · <a href="https://sudogwon-rt.blogspot.com">블로그</a> · 이 페이지는 검색에 노출되지 않습니다</footer>
<script>
function cp(id,b){{var t=document.getElementById(id);
 function ok(){{b.textContent='복사됐어요 ✓';setTimeout(function(){{b.textContent='캡션 복사'}},1500)}}
 if(navigator.clipboard&&window.isSecureContext){{navigator.clipboard.writeText(t.value).then(ok,function(){{t.select();document.execCommand('copy');ok()}})}}
 else{{t.select();document.execCommand('copy');ok()}}}}
</script></body></html>'''
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(page)
print(f'인스타 페이지 → {OUT}/index.html (오늘 {len(todo)}건: {", ".join(s["title"] for s in todo) or "없음"})')
