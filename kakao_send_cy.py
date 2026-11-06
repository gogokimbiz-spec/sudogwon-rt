"""청약 주간 요약(cheongyak/summary.json)으로 카카오톡 '나에게 보내기'를 합니다 (GitHub Actions 용).
필요한 Secret: KAKAO_REST_KEY, KAKAO_CLIENT_SECRET, KAKAO_REFRESH_TOKEN (실거래 알림과 같은 값)
선택 Secret: GH_PAT (새 refresh_token 을 Secret 에 자동 저장)
같은 작업에서 kakao_send.py 가 먼저 토큰을 바꿨다면 .kakao_rt 파일의 새 값을 씁니다.
"""
import os, sys, json, datetime, subprocess, urllib.request, urllib.parse

K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if os.path.exists('.kakao_rt'):
    K['KAKAO_REFRESH_TOKEN'] = open('.kakao_rt').read().strip() or K['KAKAO_REFRESH_TOKEN']
DRY = '--dry' in sys.argv
if not DRY and not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)
SITE = (os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/').rstrip('/') + '/cheongyak/'
S = json.load(open(sys.argv[1], encoding='utf-8'))

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
link = S.get('blog_url') or SITE
r1, lw = S['rank1'], S['last_week']
def compose(nshow, with_news, with_last=True):
    L = [f"🏗 수도권 청약 | {w0.month}.{w0.day}~{w1.month}.{w1.day}", f"접수 {len(r1)}곳 · 당첨발표 {len(S['winners'])}곳"]
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
    if with_news and S.get('news'):
        L += ['', f"📰 {cut(S['news'][0]['title'], 28)}"]
    L += ['', f'👉 {link}']
    return '\n'.join(L)
# 카카오 텍스트 메시지는 200자 안팎이 넘으면 잘릴 수 있어 짧아질 때까지 줄입니다
for opt in [(3, True), (2, True), (1, True), (2, True, False), (1, True, False), (2, False), (1, False), (0, False, False)]:
    text = compose(*opt)
    if len(text) <= 200: break
print(text, f'\n({len(text)}자)')
if DRY: sys.exit(0)

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
tpl = {'object_type': 'text', 'text': text, 'link': {'web_url': link, 'mobile_web_url': link}, 'button_title': '청약 일정 보기'}
req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                             data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(),
                             headers={'Authorization': 'Bearer ' + tok['access_token']})
res = json.load(urllib.request.urlopen(req))
print('카카오 전송 결과:', res)
if res.get('result_code') != 0:
    sys.exit('카카오 전송 실패')
new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
