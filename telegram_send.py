"""텔레그램 채널에 오늘의 요약을 올립니다 (GitHub Actions 용).
사용법: python telegram_send.py summary.json          (매일 실거래)
        python telegram_send.py cy_summary.json --cy  (청약 주간)
필요한 Secret: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (예: @sudogwon_rt)  — 없으면 건너뜀
"""
import os, sys, json, html, datetime, urllib.request, urllib.parse, urllib.error

TOKEN, CHAT = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip(), os.environ.get('TELEGRAM_CHAT_ID', '').strip()
DRY = '--dry' in sys.argv
if not DRY and not (TOKEN and CHAT):
    print('텔레그램 설정값이 없어 건너뜁니다.'); sys.exit(0)
S = json.load(open(sys.argv[1], encoding='utf-8'))
CY = '--cy' in sys.argv
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
e = html.escape

def man(v):
    v = int(round(v)); a, m = divmod(v, 10000)
    return (f'{a}억 {m:,}' if m else f'{a}억') if a else f'{m:,}만'
def man2(v):
    v = int(round(v)); a, m = divmod(v, 10000)
    return (f'{a}억 {m:,}만' if m else f'{a}억') if a else f'{m:,}만'
def city(r):
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' else p[0]
    if p[0] in ('서울', '인천'): return p[1][:-1] if len(p[1]) > 2 else r
    return p[0]
def area_name(r):
    p = r.split(' ')
    if len(p) == 1: return p[0][:-1] if p[0][-1] in '시군' else p[0]
    g = p[1][:-1] if len(p[1]) > 2 else p[1]
    return g if p[0] == '서울' else f'{p[0]} {g}'
D = datetime.date.fromisoformat

if not CY:
    d = D(S['day']); wd = '월화수목금토일'[d.weekday()]
    blog = S.get('blog_url') or SITE
    bs = S['by_sido']
    L = [f"<b>🏠 수도권 아파트 실거래 | {d.month}월 {d.day}일({wd})</b>",
         f"매매 {S['trade_count']}건 (서울 {bs['11']} · 인천 {bs['28']} · 경기 {bs['41']}) · 전세 {S['jeonse_count']}건"]
    if S.get('news'):
        n = S['news']; L += ['', f"📰 <a href=\"{e(n['link'])}\">{e(n['title'])}</a> ({e(n.get('source', ''))})"]
    nh = S.get('new_highs') or []
    if nh:
        L += ['', f"<b>🔺 신고가 {len(nh)}건</b> (최근 6개월 기준)"]
        L += [f"· {e(city(t['region']))} {e(t['apt'])} {t['area']}㎡ <b>{man(t['price_man'])}</b> (이전 {man(t['prev_high_man'])})" for t in nh[:5]]
        if len(nh) > 5: L.append(f"  외 {len(nh) - 5}건")
    else:
        L += ['', '<b>💰 거래가 상위</b>'] + [f"· {e(city(t['region']))} {e(t['apt'])} {t['area']}㎡ <b>{man(t['price_man'])}</b>" for t in (S.get('day_trades') or [])[:5]]
    if S.get('watch'):
        L += ['', '<b>📊 관심지역 30일</b> (3.3㎡당)'] + [f"· {e(area_name(x['region']))} {man2(x['pp_man'])} {'▲' if x['chg'] >= 0 else '▼'}{abs(x['chg'])}%" for x in S['watch']]
    up = ' · '.join(f"{e(area_name(x['region']))} +{x['chg']}%" for x in (S.get('up5') or S.get('up3') or [])[:3])
    dn = ' · '.join(f"{e(area_name(x['region']))} {x['chg']}%" for x in (S.get('down5') or S.get('down3') or [])[:3])
    if up or dn: L += ['', f"🔼 {up}", f"🔽 {dn}"]
    L += ['', '<i>※ 실거래는 30일 안에 신고되므로 건수는 더 늘어날 수 있어요</i>']
    buttons = [[{'text': '📝 오늘 브리핑 전체', 'url': blog}], [{'text': '🗺 지도', 'url': SITE}, {'text': '📍 지역별', 'url': SITE + 'r/'}]]
else:
    w0, w1 = D(S['week'][0]), D(S['week'][1])
    blog = S.get('blog_url') or SITE + 'cheongyak/'
    r1 = S.get('rank1') or []
    L = [f"<b>🏗 수도권 청약 | {w0.month}.{w0.day}~{w1.month}.{w1.day}</b>", f"접수 {len(r1)}곳 · 당첨발표 {len(S.get('winners') or [])}곳"]
    news = S.get('news') or []
    if news:
        n = news[0]; L += ['', f"📰 <a href=\"{e(n['link'])}\">{e(n['title'])}</a> ({e(n.get('source', ''))})"]
    if r1:
        L += ['', '<b>📅 이번 주 1순위 접수</b>']
        for x in r1[:8]:
            g = x.get('gap_new'); dd = D(x['date'])
            L.append(f"· {dd.month}.{dd.day} {e(city(x['region']))} <a href=\"{e(x['url'])}\">{e(x['name'])}</a> 3.3㎡당 {man(x['pp_man'])}" + (f" (주변 신축 대비 {'+' if g > 0 else ''}{g}%)" if g is not None else ''))
        if len(r1) > 8: L.append(f"  외 {len(r1) - 8}곳")
    done = [x for x in (S.get('last_week') or []) if 'rate' in x]
    if done:
        L += ['', '<b>🏆 지난주 1순위 결과</b>'] + [f"· {e(city(x['region']))} {e(x['name'])} <b>{x['rate']:.1f}:1</b> {e(x.get('status', ''))}" for x in done[:5]]
    L += ['', '<i>청약 전에는 반드시 입주자모집공고를 확인하세요</i>']
    buttons = [[{'text': '📝 이번 주 청약 정리', 'url': blog}], [{'text': '🗺 청약 지도', 'url': SITE + 'cheongyak/'}]]

text = '\n'.join(L)
print(text, f'\n({len(text)}자)')
if DRY: sys.exit(0)
body = urllib.parse.urlencode({'chat_id': CHAT, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true',
                               'reply_markup': json.dumps({'inline_keyboard': buttons}, ensure_ascii=False)}).encode()
try:
    res = json.load(urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/sendMessage', body, timeout=30))
except urllib.error.HTTPError as err:
    sys.exit('텔레그램 전송 실패: ' + err.read().decode('utf-8', 'replace')[:300])
print('텔레그램 전송 완료' if res.get('ok') else f'텔레그램 전송 실패: {res}')
