"""청약 주간 요약(cheongyak/summary.json)으로 카카오톡 '나에게 보내기'를 합니다 (GitHub Actions 용).
필요한 Secret: KAKAO_REST_KEY, KAKAO_CLIENT_SECRET, KAKAO_REFRESH_TOKEN (실거래 알림과 같은 값)
선택 Secret: GH_PAT (새 refresh_token 을 Secret 에 자동 저장)
같은 작업에서 kakao_send.py 가 먼저 토큰을 바꿨다면 .kakao_rt 파일의 새 값을 씁니다.
"""
import os, sys, json, datetime, subprocess, urllib.request, urllib.parse, urllib.error

K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if os.path.exists('.kakao_rt'):
    K['KAKAO_REFRESH_TOKEN'] = open('.kakao_rt').read().strip() or K['KAKAO_REFRESH_TOKEN']
DRY = '--dry' in sys.argv
if not DRY and not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)
SITE = (os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/').rstrip('/') + '/cheongyak/'
VER = f"{os.environ.get('GITHUB_RUN_ID', '')}{os.environ.get('GITHUB_RUN_ATTEMPT', '')}" or str(int(__import__('time').time()))  # 카카오가 같은 주소의 이미지를 캐시하므로 실행마다 다른 주소
S = json.load(open(sys.argv[1], encoding='utf-8'))
MODE = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--mode=')), 'mon')   # mon: 이번 주 청약 / tue: 청약 결과 / wed: 줍줍·로또 / thu: 당첨 가점 커트라인 / fri: 단지분석 (2026-11-11)

D = lambda s: datetime.date.fromisoformat(s[:10])
WD = '월화수목금토일'
md = lambda s: f"{D(s).month}.{D(s).day}({WD[D(s).weekday()]})"
def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억{m:,}' if m else f'{e}억') if e else f'{m:,}만'
def city(r):
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' else p[0]
    if p[0] in ('서울', '인천'): return p[1][:-1] if len(p[1]) > 2 else r
    return p[0]
cut = lambda s, n=11: s if len(s) <= n else s[:n] + '…'
w0, w1 = D(S['week'][0]), D(S['week'][1])
link = S.get({'tue': 'blog_url_tue', 'wed': 'blog_url_wed', 'thu': 'blog_url_thu', 'fri': 'blog_url_fri'}.get(MODE, 'blog_url')) or SITE
FOLDER = {'tue': 'cards_tue/', 'wed': 'cards_wed/', 'thu': 'cards_thu/', 'fri': 'cards_sat/'}.get(MODE, 'cards/')
RS = [x for x in (S.get('results') or []) if 'rate' in x]; CL = S.get('cutline') or {}
if (MODE == 'tue' and not RS) or (MODE == 'thu' and not CL):
    print(f'{MODE}: 보낼 청약 자료가 없어 카톡을 건너뜁니다'); sys.exit(0)
PK = S.get('pick') or {}
if MODE == 'fri' and not PK:
    print('이번 주 단지분석 대상이 없어 금요일 청약 카톡은 건너뜁니다'); sys.exit(0)
r1, lw = S['rank1'], S['last_week']
def compose(nshow, with_news, with_last=True):
    L = [f"🏗 수도권 청약 | {w0.month}.{w0.day}~{w1.month}.{w1.day}", f"접수 {len(r1)}곳 · 당첨발표 {len(S['winners'])}곳"]
    if with_news and S.get('news'):
        L += ['', f"📰 {cut(S['news'][0]['title'], 28)}"]
    if r1:
        L.append('')
        for x in r1[:nshow]:
            g = x.get('gap_new'); c = city(x['region']); n = x['name'][len(c):].strip() if x['name'].startswith(c) else x['name']
            L.append(f"· {md(x['date'])[:-3]} {c} {cut(n, 10)}" + (f" {'+' if g > 0 else ''}{g}%" if g is not None else ''))
        if len(r1) > nshow: L.append(f"  외 {len(r1) - nshow}곳")
    done = [x for x in lw if 'rate' in x]
    if with_last and done:
        top = done[0]; mi = sum(1 for x in done if x['status'] == '미달')
        L += ['', f"🏆 지난주 최고 {city(top['region'])} {cut(top['name'], 9)} {top['rate']:.1f}:1" + (f" · 미달 {mi}곳" if mi else '')]
    L += ['', f'👉 {link}']
    return '\n'.join(L)
def shortn(n, c):
    import re as _r
    n = _r.sub(r'^(서울|인천|경기)\s*', '', n)
    return n[len(c):].strip() if n.startswith(c) else n
def compose_wed(nshow, with_cheap=True, with_res=True):
    zz, z0, z1 = S.get('zz') or [], *[D(x) for x in S['zz_range']]
    L = [f"🔥 수도권 줍줍 | {z0.month}.{z0.day}~{z1.month}.{z1.day}", f"무순위·임의공급 {len(zz)}곳"]
    if zz:
        L.append('')
        for x in zz[:nshow]:
            c = city(x['region']); n = shortn(x['name'], c)
            L.append(f"· {md(x['r0'])[:-3]} {c} {cut(n, 10)} {x['units']}세대")
        if len(zz) > nshow: L.append(f"  외 {len(zz) - nshow}곳")
    c5 = S.get('cheap5') or []
    if with_cheap and c5:
        L += ['', f"💰 시세보다 싼 분양 1위 {city(c5[0]['region'])} {cut(shortn(c5[0]['name'], city(c5[0]['region'])), 9)} {c5[0]['gap_new']}%"]
    rs = S.get('results') or []
    if with_res and rs:
        mi = sum(1 for x in rs if x.get('status') == '미달')
        L += ['', f"🏆 최고 경쟁률 {city(rs[0]['region'])} {cut(shortn(rs[0]['name'], city(rs[0]['region'])), 9)} {rs[0]['rate']:.1f}:1" + (f" · 미달 {mi}곳" if mi else '')]
    L += ['', f'👉 {link}']
    return '\n'.join(L)
def compose_fri(*_):
    c = city(PK.get('region', '')); L = [f"📌 청약 단지분석 | {cut(PK.get('name', ''), 16)}", PK.get('region', '')]
    if 'rate' in PK: L.append(f"1순위 {PK['rate']:.1f}:1 {PK.get('status', '')}")
    if PK.get('pp_man'): L.append(f"3.3㎡당 {man(PK['pp_man'])}" + ('' if man(PK['pp_man'])[-1] in '만억' else '만') + (f" (주변 신축 {'+' if PK['gap_new'] > 0 else ''}{PK['gap_new']}%)" if PK.get('gap_new') is not None else ''))
    L += ['', f'👉 {link}']
    return '\n'.join(L)
def compose_tue(*_):
    a, b = S['results_range']
    L = [f"🏆 1순위 청약 결과 | {D(a).month}.{D(a).day}~{D(b).month}.{D(b).day} 접수", '']
    L += [f"· {city(x['region'])} {cut(x['name'], 10)} {x['rate']:.1f}:1 {x['status']}" for x in RS[:4]]
    L += ['', f'👉 {link}']
    return '\n'.join(L)
def compose_thu(*_):
    L = ['📊 당첨 가점 커트라인 | 최근 6개월', '']
    for a in ('서울', '인천', '경기'):
        if a in CL: L.append(f"· {a} " + ' / '.join(f"{k} {v['min_med']}점" for k, v in CL[a].items()))
    L += ['', f'👉 {link}']
    return '\n'.join(L)
if MODE in ('tue', 'thu'):
    compose = compose_tue if MODE == 'tue' else compose_thu
    OPTS = [()]
elif MODE == 'fri':
    compose = compose_fri
    OPTS = [()]
elif MODE == 'wed':
    compose = compose_wed
    OPTS = [(3, True, False), (2, True, False), (1, True, False), (1, False, False), (0, False, False)]   # 결과는 화요일로 옮김
else:
    OPTS = [(3, True), (2, True), (1, True), (2, True, False), (1, True, False), (2, False), (1, False), (0, False, False)]
# 카카오 텍스트 메시지는 200자 안팎이 넘으면 잘릴 수 있어 짧아질 때까지 줄입니다
for opt in OPTS:
    text = compose(*opt)
    if len(text) <= 200: break
print(text, f'\n({len(text)}자)')
if DRY: sys.exit(0)

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
BTN = {'tue': '청약 결과 보기', 'wed': '줍줍 일정 보기', 'thu': '가점 커트라인 보기', 'fri': '단지분석 보기'}.get(MODE, '청약 일정 보기')
tpl = {'object_type': 'text', 'text': text, 'link': {'web_url': link, 'mobile_web_url': link}, 'button_title': BTN}
req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                             data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(),
                             headers={'Authorization': 'Bearer ' + tok['access_token']})
# 이미지가 있으면 글 메시지는 보내지 않고 이미지만 보냅니다 (이미지를 못 만든 날만 글로 대신 보냄)
_card = SITE + FOLDER + 'latest.png'
try: _has_card = urllib.request.urlopen(urllib.request.Request(_card, method='HEAD'), timeout=20).status == 200
except Exception: _has_card = False
if not _has_card:
    res = json.load(urllib.request.urlopen(req))
    print('카카오 전송 결과:', res)
    if res.get('result_code') != 0:
        sys.exit('카카오 전송 실패')
else:
    print('카드 이미지가 있어 글 메시지는 생략합니다')
# 이번 주 청약 카드 이미지 (인스타그램용) 도 같이 보냅니다
card = SITE + FOLDER + 'latest.png'
try: ok_img = urllib.request.urlopen(urllib.request.Request(card, method='HEAD'), timeout=20).status == 200
except Exception: ok_img = False
if ok_img:
    feed = {'object_type': 'feed', 'content': {'title': (f"수도권 1순위 청약 결과 {len(RS)}곳" if MODE == 'tue' else '수도권 당첨 가점 커트라인 (최근 6개월)' if MODE == 'thu' else f"이번 주 수도권 줍줍 {len(S.get('zz') or [])}곳" if MODE == 'wed' else f"단지분석 | {PK.get('name', '')}" if MODE == 'fri' else f"이번 주 수도권 청약 {len(r1)}곳 ({w0.month}.{w0.day}~{w1.month}.{w1.day})"),
            'description': '이미지를 눌러 크게 보기',
            'image_url': f"{card}?v={VER}", 'image_width': 1080, 'image_height': 1350,
            'link': {'web_url': link, 'mobile_web_url': link}},
            'buttons': [{'title': BTN, 'link': {'web_url': link, 'mobile_web_url': link}}]}
    try:
        r2 = json.load(urllib.request.urlopen(urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
             data=urllib.parse.urlencode({'template_object': json.dumps(feed, ensure_ascii=False)}).encode(),
             headers={'Authorization': 'Bearer ' + tok['access_token']})))
        print('청약 이미지 전송 결과:', r2)
    except urllib.error.HTTPError as err:
        print('::warning::청약 이미지 전송 실패:', err.read().decode('utf-8', 'replace')[:300])
else:
    print('청약 카드 이미지가 없어 이미지 메시지는 건너뜁니다')
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
