"""summary.json 으로 카카오톡 '나에게 보내기'를 합니다 (GitHub Actions 용).
필요한 Secret: KAKAO_REST_KEY, KAKAO_CLIENT_SECRET, KAKAO_REFRESH_TOKEN
선택 Secret: GH_PAT (카카오가 새 refresh_token 을 주면 KAKAO_REFRESH_TOKEN Secret 을 자동으로 바꿔 둠)
"""
import os, sys, json, datetime, subprocess, urllib.request, urllib.parse

K = {k: os.environ.get(k, '').strip() for k in ['KAKAO_REST_KEY', 'KAKAO_CLIENT_SECRET', 'KAKAO_REFRESH_TOKEN']}
if not all(K.values()):
    print('카카오 설정값이 없어 전송을 건너뜁니다.'); sys.exit(0)
SITE = os.environ.get('SITE_URL', '').strip() or 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
S = json.load(open(sys.argv[1], encoding='utf-8'))

def man(v):
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}' if m else f'{e}억') if e else f'{m:,}만'
def city(r):  # 신고가 줄: '광명시'→'광명', '서울 강남구'→'강남', '용인 기흥구'→'용인'
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' else p[0]
    if p[0] in ('서울', '인천'): return p[1][:-1] if len(p[1]) > 2 else r
    return p[0]
def area_name(r):  # 관심지역 줄: '서울 강남구'→'강남', '성남 분당구'→'성남 분당', '광명시'→'광명'
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' else p[0]
    g = p[1][:-1] if len(p[1]) > 2 else p[1]
    return g if p[0] == '서울' else f'{p[0]} {g}'
cut = lambda s, n=12: s if len(s) <= n else s[:n] + '…'
def man2(v):  # 3.3㎡당 가격: 1억 2,768만 / 7,460만
    v = int(round(v)); e, m = divmod(v, 10000)
    return (f'{e}억 {m:,}만' if m else f'{e}억') if e else f'{m:,}만'
d = datetime.date.fromisoformat(S['day']); wd = '월화수목금토일'[d.weekday()]
link = S.get('blog_url') or SITE
L = [f"🏠 수도권 아파트 실거래 | {d.month}월 {d.day}일({wd})", f"매매 {S['trade_count']}건 · 전세 {S['jeonse_count']}건", '']
if S.get('news'):
    L += [f"📰 {S['news']['title']}", '']
nh = S.get('new_highs') or []
if nh:
    L.append(f"🔺 신고가 {len(nh)}건 (최근 6개월 기준)")
    L += [f"· {city(t['region'])} {cut(t['apt'])} {t['area']}㎡ {man(t['price_man'])}" for t in nh[:3]]
    if len(nh) > 3: L.append(f"  외 {len(nh) - 3}건")
else:
    L.append('💰 거래가 상위 3건')
    L += [f"· {city(t['region'])} {cut(t['apt'])} {t['area']}㎡ {man(t['price_man'])}" for t in (S.get('day_trades') or S.get('top_trades') or [])[:3]]
w = S.get('watch') or []
if w:
    L += ['', '📊 관심지역 30일 (3.3㎡당)']
    L += [f"· {area_name(x['region'])} {man2(x['pp_man'])} {'▲' if x['chg'] >= 0 else '▼'}{abs(x['chg'])}%" for x in w]
L += ['', f'👉 {link}']
text = '\n'.join(L)
print(text)

tok = json.load(urllib.request.urlopen('https://kauth.kakao.com/oauth/token', urllib.parse.urlencode({
    'grant_type': 'refresh_token', 'client_id': K['KAKAO_REST_KEY'], 'client_secret': K['KAKAO_CLIENT_SECRET'],
    'refresh_token': K['KAKAO_REFRESH_TOKEN']}).encode()))
tpl = {'object_type': 'text', 'text': text, 'link': {'web_url': link, 'mobile_web_url': link}, 'button_title': '자세히 보기'}
req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                             data=urllib.parse.urlencode({'template_object': json.dumps(tpl, ensure_ascii=False)}).encode(),
                             headers={'Authorization': 'Bearer ' + tok['access_token']})
res = json.load(urllib.request.urlopen(req))
print('카카오 전송 결과:', res)
if res.get('result_code') != 0:
    sys.exit('카카오 전송 실패')

new_rt = tok.get('refresh_token')
if new_rt:
    open('.kakao_rt', 'w').write(new_rt)  # 같은 작업의 청약 알림이 새 토큰을 쓰도록
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
    else:
        print('::warning::카카오가 새 refresh_token 을 발급했지만 GH_PAT 가 없어 저장하지 못했습니다. 약 1개월 안에 KAKAO_REFRESH_TOKEN 을 다시 발급해 넣어 주세요.')
