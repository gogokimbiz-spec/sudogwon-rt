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
def sh(r):
    n = r.split(' ')[-1]
    return n[:-1] if len(n) > 2 and n[-1] in '구시' else n
d = datetime.date.fromisoformat(S['day']); wd = '월화수목금토일'[d.weekday()]
link = S.get('blog_url') or SITE
L = [f"[수도권 실거래] {d.month}월 {d.day}일 ({wd})",
     f"매매 {S['trade_count']}건 (서울 {S['by_sido']['11']} · 인천 {S['by_sido']['28']} · 경기 {S['by_sido']['41']}) · 전세 {S['jeonse_count']}건"]
nh = S.get('new_highs') or []
if nh:
    L.append(f"신고가 {len(nh)}건: " + ' · '.join(f"{sh(t['region'])} {t['apt']}" for t in nh[:2]) + (' 외' if len(nh) > 2 else ''))
for i, t in enumerate((S.get('top_trades') or [])[:2]):
    L.append(f"{'최고가:' if i == 0 else '　　　'} {sh(t['region'])} {t['apt']} {t['area']}㎡ {man(t['price_man'])}")
L.append('30일 상승: ' + ' · '.join(f"{sh(x['region'])} +{x['chg']}%" for x in S.get('up3', [])))
L.append('30일 하락: ' + ' · '.join(f"{sh(x['region'])} {x['chg']}%" for x in S.get('down3', [])))
if S.get('news'):
    L.append(f"📰 {S['news']['title']}")
L.append('※ 아직 신고 중이라 건수는 늘어날 수 있어요')
L.append(f'자세히 보기: {link}')
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
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--body', new_rt], check=True)
        print('새 refresh_token 을 Secret 에 저장했습니다.')
    else:
        print('::warning::카카오가 새 refresh_token 을 발급했지만 GH_PAT 가 없어 저장하지 못했습니다. 약 1개월 안에 KAKAO_REFRESH_TOKEN 을 다시 발급해 넣어 주세요.')
