"""수요일(줍줍·로또 청약 + 결과)·금요일(단지분석) 청약 블로그 글 본문. post_blogger_cy.py 가 불러 씁니다.
build(mode, S, h) → (제목, 본문 조각 목록, 라벨)
S: build_cy.py 가 만든 cheongyak/summary.json, h: post_blogger_cy.py 의 표 스타일·도우미 함수
"""
import datetime, statistics, re

BRAND = '데이터로 보는 재테크'
RED, BLUE, GRAY = '#d23c3c', '#2a6fd6', '#666'
WD = '월화수목금토일'
D = lambda s: datetime.date.fromisoformat(s[:10])


def build(mode, S, h):
    return {'tue': tue, 'wed': wed, 'thu': thu}.get(mode, fri)(S, h)


def _common(h):
    T, TH, THR, TD, TDR, man, md, esc = (h[k] for k in ('T', 'TH', 'THR', 'TD', 'TDR', 'man', 'md', 'esc'))
    pc = lambda g: RED if g >= 5 else BLUE if g <= -5 else GRAY
    sg = lambda g: f"{'+' if g > 0 else ''}{g:.0f}%"
    intro = lambda t: f'<p style="background:#f3f6fb;border-radius:8px;padding:10px 12px;font-size:14px;margin:0 0 14px">{t}</p>'
    foot = (f'<hr><p><small><b>{BRAND}</b> · 자료: 한국부동산원 청약홈(분양정보·경쟁률·특별공급 신청현황·잔여세대), 국토교통부 실거래가 공개시스템. '
            '청약 신청 전에는 반드시 입주자모집공고를 확인하세요. 이 글은 참고용 정보이며 투자 권유가 아닙니다.</small></p>')
    return T, TH, THR, TD, TDR, man, md, esc, pc, sg, intro, foot


def _week_label(d):
    mon = d - datetime.timedelta(d.weekday())
    return f"{mon.month}월 {(mon.day - 1) // 7 + 1}주차"


# ───────────────────────── 화요일: 1순위 청약 결과 (2026-11-11 수요일 글에서 분리) ─────────────────────────
def tue(S, h):
    T, TH, THR, TD, TDR, man, md, esc, pc, sg, intro, foot = _common(h)
    W = D(S['tue']); rs = S.get('results') or []; a, b = S['results_range']
    if not rs: raise SystemExit('지난주 결과가 나온 수도권 청약이 없어 화요일 글을 건너뜁니다.')
    title = f"[수도권 청약] {_week_label(W)} 1순위 청약 결과 {len(rs)}곳 ({D(a).month}.{D(a).day}~{D(b).month}.{D(b).day} 접수)"
    P = [intro(f'🏆 <b>화요일 · 1순위 청약 결과</b> · 지난주 1순위 접수한 수도권 단지의 경쟁률을 모았습니다. 월요일 이번 주 청약 일정 · 화요일 청약 결과 · 수요일 줍줍·로또 청약 · 목요일 당첨 가점 커트라인 · 금요일 단지분석이 올라갑니다.'),
         '<div style="display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 24px">'
         + h['cta'](h['SITE'], '🗺️', '청약 지도로 보기', '접수 일정·분양가·주변 신축 대비', True)
         + h['cta'](f"{h['RT_SITE']}r/", '📍', '우리 동네 실거래가', '시군구별 신고가·최근 거래', False) + '</div>']
    # 3) 결과
    rs = S.get('results') or []; a, b = S['results_range']
    P.append(f"<h3>1순위 청약 결과 ({md(a)}~{md(b)} 접수) {len(rs)}곳</h3>")
    if rs:
        rows = ''.join(f"<tr><td {TD}>{esc(x['region'])}</td><td {TD}>{h['name'](x)}</td><td {TDR}>{h['rate'](x)}<br><small>{x.get('apps', 0):,}건</small></td>"
                       f"<td {TDR}>{man(x['pp_man'])}{h['gap'](x)}</td></tr>" for x in rs)
        mi = sum(1 for x in rs if x.get('status') == '미달')
        P.append(f"<p>가장 치열했던 곳은 <b>{esc(rs[0]['name'])}</b>({rs[0]['rate']:.1f} : 1)였고, {len(rs)}곳 중 {mi}곳은 미달이었습니다.</p>"
                 f"<table {T}><tr><th {TH}>지역</th><th {TH}>단지</th><th {THR}>1순위 경쟁률</th><th {THR}>3.3㎡당</th></tr>{rows}</table>"
                 '<p><small>1순위 접수 건수 ÷ 일반공급 세대수(특별공급 제외). 2순위까지 일반공급에 못 미친 주택형이 있으면 미달로 표시합니다.</small></p>')
    else:
        P.append('<p>이 기간에 결과가 나온 수도권 청약이 없습니다.</p>')
    P.append(foot)
    return title, P, ['수도권 청약', '청약 결과', '청약 경쟁률']


# ───────────────────────── 수요일: 줍줍·로또 청약 ─────────────────────────
def wed(S, h):
    T, TH, THR, TD, TDR, man, md, esc, pc, sg, intro, foot = _common(h)
    W = D(S['wed']); z0, z1 = S['zz_range']; zz = S.get('zz') or []
    title = f"[수도권 청약] {_week_label(W)} 줍줍 {len(zz)}곳 · 시세보다 싼 분양 TOP 5"
    P = [intro(f'🔥 <b>수요일 · 줍줍·로또 청약</b> · {md(z0)}~{md(z1)} 접수하는 무순위·임의공급과 시세보다 싸게 나온 분양을 모았습니다. 월요일 이번 주 청약 일정 · 화요일 청약 결과 · 수요일 줍줍·로또 청약 · 목요일 당첨 가점 커트라인 · 금요일 단지분석이 올라갑니다.'),
         '<div style="display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 24px">'
         + h['cta'](h['SITE'], '🗺️', '청약 지도로 보기', '접수 일정·분양가·주변 신축 대비', True)
         + h['cta'](f"{h['RT_SITE']}r/", '📍', '우리 동네 실거래가', '시군구별 신고가·최근 거래', False) + '</div>']
    # 1) 줍줍
    P.append(f"<h3>줍줍 일정 {md(z0)}~{md(z1)} · {len(zz)}곳 (무순위·임의공급)</h3>")
    if zz:
        rows = ''
        for x in zz:
            if x.get('p_min'):
                pr = f"<b>{man(x['p_min'])}{'~' + man(x['p_max']) if x['p_max'] != x['p_min'] else ''}</b>" + \
                     (f"<br><small>{', '.join(str(a) + '㎡' for a in x['areas'])}</small>" if x.get('areas') else '')
            elif x.get('orig_pp'):
                pr = f"<small>원 공고 3.3㎡</small><br><b>{man(x['orig_pp'])}</b>" + \
                     (f"<br><small style=\"color:{pc(x['orig_gap'])}\">주변 신축 {sg(x['orig_gap'])}</small>" if x.get('orig_gap') is not None else '')
            else:
                pr = '<small>모집공고 확인</small>'
            when = md(x['r0']) + ('' if x['r0'] == x['r1'] else '~' + md(x['r1'])[-5:])
            nm = f"<a href=\"{esc(x['url'])}\">{esc(x['name'])}</a>" if x.get('url') else esc(x['name'])
            rows += (f"<tr><td {TD}>{when}</td><td {TD}>{esc(x['region'])}</td>"
                     f"<td {TD}>{nm}<br><small>{esc(x['kind'])} · {x['units']}세대{' · 발표 ' + md(x['win']) if x.get('win') else ''}</small></td><td {TDR}>{pr}</td></tr>")
        P.append(f"<table {T}><tr><th {TH}>접수</th><th {TH}>지역</th><th {TH}>단지</th><th {THR}>분양가</th></tr>{rows}</table>"
                 '<p><small>당첨자 계약 포기·부적격으로 남은 물량을 다시 공급하는 청약입니다. 가점과 관계없이 추첨이지만 무주택·거주지 등 자격 요건은 '
                 '공고마다 다르니 반드시 모집공고를 확인하세요. 무순위는 분양가가 목록에 없어 원래 공고의 3.3㎡당 분양가를 함께 적었습니다.</small></p>')
    else:
        P.append('<p>이 기간에 접수하는 수도권 무순위·임의공급이 없습니다.</p>')
    # 2) 로또 TOP 5
    c5 = S.get('cheap5') or []
    if c5:
        def rt(x):
            if 'rate' not in x: return '<small>접수 전·결과 없음</small>'
            return f"<b>{x['rate']:.1f} : 1</b><br><small style=\"color:{BLUE if x['status'] == '미달' else RED}\">{esc(x['status'])}</small>"
        rows = ''.join(f"<tr><td {TD}><b>{i}</b></td><td {TD}><a href=\"{esc(x['url'])}\">{esc(x['name'])}</a><br><small>{esc(x['region'])} · 공고 {md(x['ann'])}</small></td>"
                       f"<td {TDR}>{man(x['pp_man'])}<br><small style=\"color:{BLUE}\">주변 신축 {sg(x['gap_new'])}</small></td><td {TDR}>{rt(x)}</td></tr>" for i, x in enumerate(c5, 1))
        hot = [x for x in c5 if x.get('status') == '미달']
        note = (f" 시세보다 싸게 나와도 {len(hot)}곳은 미달이었어요. 입지·교통·입주 시점이 가격만큼 중요하다는 뜻이에요." if hot else '')
        P.append(f"<h3>시세보다 싸게 나온 분양 TOP 5 (최근 6개월 · 민영)</h3><table {T}><tr><th {TH}>#</th><th {TH}>단지</th><th {THR}>3.3㎡당 분양가</th><th {THR}>1순위</th></tr>{rows}</table>"
                 f"<p><small>같은 시군구 최근 10년 내 준공 아파트 매매 3.3㎡당 중앙값과 비교(전용면적 기준)한 단순 비교입니다.{note}</small></p>")
    P.append(foot)
    return title, P, ['수도권 청약', '줍줍', '무순위 청약', '로또 청약']


# ───────────────────────── 목요일: 당첨 가점 커트라인 ─────────────────────────
def thu(S, h):
    T, TH, THR, TD, TDR, man, md, esc, pc, sg, intro, foot = _common(h)
    W = D(S['thu'])
    if not (S.get('cutline') or {}): raise SystemExit('가점 자료가 없어 목요일 글을 건너뜁니다.')
    title = f"[수도권 청약] {_week_label(W)} 당첨 가점 커트라인 (서울·인천·경기 · 최근 6개월)"
    P = [intro(f'📊 <b>목요일 · 당첨 가점 커트라인</b> · 최근 6개월 수도권 민영 청약에서 몇 점이면 당첨됐는지 정리했습니다. 월요일 이번 주 청약 일정 · 화요일 청약 결과 · 수요일 줍줍·로또 청약 · 목요일 당첨 가점 커트라인 · 금요일 단지분석이 올라갑니다.'),
         '<div style="display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 24px">'
         + h['cta'](h['SITE'], '🗺️', '청약 지도로 보기', '접수 일정·분양가·주변 신축 대비', True)
         + h['cta'](f"{h['RT_SITE']}r/", '📍', '우리 동네 실거래가', '시군구별 신고가·최근 거래', False) + '</div>']
    # 4) 가점 커트라인
    cl = S.get('cutline') or {}
    if cl:
        cell = lambda v: (f"<td {TDR}><b>{v['min_med']}점</b><br><small>평균 {v['avg']}점 · {v['n']}개 주택형</small></td>" if v else f"<td {TDR}>-</td>")
        rows = ''.join(f"<tr><td {TD}><b>{a}</b></td>{cell(cl.get(a, {}).get('60㎡ 이하'))}{cell(cl.get(a, {}).get('60~85㎡'))}</tr>" for a in ('서울', '인천', '경기') if a in cl)
        P.append(f"<h3>최근 6개월 당첨 가점 커트라인</h3><table {T}><tr><th {TH}>지역</th><th {THR}>60㎡ 이하</th><th {THR}>60~85㎡</th></tr>{rows}</table>"
                 '<p><small>민영주택 주택형별 최저 당첨 가점의 중앙값(해당지역 기준, 미달·추첨 주택형 제외)입니다. '
                 '"이 점수면 절반 정도의 주택형에서 당첨됐다"는 뜻이에요.</small></p>')
    if not (S.get('cutline') or {}):
        P.append('<p>최근 6개월 가점이 공개된 수도권 민영 단지가 없습니다.</p>')
    P.append(foot)
    return title, P, ['수도권 청약', '청약 가점', '당첨 가점']


# ───────────────────────── 금요일: 단지분석 ─────────────────────────
def fri(S, h):
    T, TH, THR, TD, TDR, man, md, esc, pc, sg, intro, foot = _common(h)
    p = S.get('pick')
    if not p: raise SystemExit('이번 주 단지분석 대상이 없어 금요일 글을 건너뜁니다.')
    ex = lambda t: float(t[0][:7]) if re.match(r'\d{3}\.', t[0]) else None
    ty = [t for t in p['types'] if ex(t)]
    gp = [t[7] for t in ty if t[7] and t[7][0]]
    m = re.search(r'([가-힣]+[시군구])\s*([가-힣0-9]+[동읍면가])?', (p.get('addr') or '').replace('특별시', '').replace('광역시', ''))
    place = f"{p['region']} {p.get('umd') or ''}".strip()
    title = f"[수도권 청약 단지분석] {p['name']} 분양가·경쟁률·당첨 가점 총정리 ({place})"
    g, a1 = p['general'], p.get('apps', 0)
    P = [intro('📌 <b>금요일 단지분석</b> · 최근 당첨자 발표가 난 수도권 민영 단지 중 1순위 접수가 가장 많았던 곳을 골라 깊게 들여다봅니다.')]
    lead = f"{esc(p.get('addr') or place)}에 들어서는 <b>{esc(p['name'])}</b>(시공 {esc(p.get('builder') or '-')}, 총 {p['units']:,}세대)의 청약 결과를 데이터로 정리했습니다. "
    if 'rate' in p:
        lead += f"일반공급 {g:,}세대에 1순위 {a1:,}건이 접수돼 평균 <b>{p['rate']:.1f} : 1</b>({esc(p['status'])})"
        lead += f"이었고, 당첨 가점은 최저 {min(x[0] for x in gp):.0f}점이었습니다." if gp else "이었습니다."
    P.append(f'<p>{lead}</p>')
    card = lambda label, val, sub='', col='#222': (f'<div style="flex:1 1 150px;border:1px solid #e3e3e3;border-radius:10px;padding:10px 12px">'
                                                   f'<div style="font-size:12px;color:#777">{label}</div><div style="font-size:20px;font-weight:bold;color:{col}">{val}</div>'
                                                   f'<div style="font-size:12px;color:#777">{sub}</div></div>')
    gn = p.get('gap_new')
    P.append('<div style="display:flex;flex-wrap:wrap;gap:8px;margin:14px 0">'
             + card('1순위 평균 경쟁률', f"{p['rate']:.1f} : 1" if 'rate' in p else '-', f'접수 {a1:,}건 / 일반 {g}세대', RED)
             + card('당첨 가점', f"{min(x[0] for x in gp):.0f}점~" if gp else '발표 전', f"평균 {statistics.mean(x[2] for x in gp):.1f}점 (해당지역)" if gp else '')
             + card('3.3㎡당 분양가', man(p['pp_man']) if p.get('pp_man') else '-', '전용면적 기준')
             + card(f"{p['region'].split(' ')[-1]} 신축 시세 대비", sg(gn) if gn is not None else '-', f"신축 3.3㎡ {man(p['ref_new'])}" if p.get('ref_new') else '', pc(gn) if gn is not None else '#222')
             + '</div>')
    P.append('<div style="display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 24px">'
             + h['cta'](p['url'], '📄', '청약홈 모집공고', '공급위치·일정·주택형 원문', True)
             + h['cta'](h['SITE'], '🗺️', '청약 지도로 보기', f"{p['region']} 다른 분양 보기", False) + '</div>')
    # 일정
    fmt = lambda s: s.replace(f"{D(s[:10]).year}-", '').replace('-', '.') if s else '-'
    sched = [('모집공고', md(p['ann'])), ('특별공급', md(p['sp']) if p.get('sp') and len(p['sp']) == 10 else fmt(p.get('sp'))),
             ('1순위', md(p['r1'])), ('2순위', md(p['r2']) if p.get('r2') else '-'), ('당첨자 발표', md(p['win'])), ('계약', fmt(p.get('ct')))]
    if p.get('move'): sched.append(('입주 예정', p['move'].replace('.', '년 ') + '월'))
    if p.get('note'): sched.append(('규제·특징', p['note']))
    P.append(f"<h3>청약 일정</h3><table {T}>" + ''.join(f'<tr><td {TD}>{k}</td><td {TD}>{esc(v)}</td></tr>' for k, v in sched) + '</table>')
    # 주택형별
    rows = ''
    for t in ty:
        r = t[5] / t[2] if t[2] else 0; e = ex(t)
        rows += (f"<tr><td {TD}><b>{esc(t[0])}</b><br><small>전용 {int(e)}㎡</small></td><td {TDR}>{t[2]} / {t[3]}</td>"
                 f"<td {TDR}><b>{man(t[4])}</b><br><small>3.3㎡ {man(t[4] / e * 3.3058) if t[4] else '-'}</small></td>"
                 f"<td {TDR}><b>{r:.1f} : 1</b><br><small>{t[5]:,}건{' · 2순위 ' + format(t[6], ',') + '건' if t[6] else ''}</small></td>"
                 f"<td {TDR}>{f'{t[7][0]:.0f} / {t[7][2]:.1f}' if t[7] and t[7][0] else '-'}</td></tr>")
    P.append(f"<h3>주택형별 분양가·경쟁률·당첨 가점</h3><table {T}><tr><th {TH}>주택형</th><th {THR}>일반 / 특공</th><th {THR}>분양가(최고)</th>"
             f"<th {THR}>1순위</th><th {THR}>가점 최저/평균</th></tr>{rows}</table>"
             '<p><small>분양가는 주택형별 최고가(발코니 확장·옵션 제외). 가점은 해당지역 당첨자 기준입니다.</small></p>')
    # 면적대 요약
    bl = []
    for nm_, lo, hi in [('60㎡ 이하', 0, 60), ('60~75㎡', 60, 80), ('84㎡ 안팎', 80, 90), ('85㎡ 초과', 90, 999)]:
        ts = [t for t in ty if lo <= ex(t) < hi and t[2]]
        if not ts: continue
        gg, aa = sum(t[2] for t in ts), sum(t[5] for t in ts); pr = [t[4] for t in ts if t[4]]
        mins = [t[7][0] for t in ts if t[7] and t[7][0]]
        bl.append(f"<li><b>{nm_}</b>: 분양가 {man(min(pr))}{'~' + man(max(pr)) if pr and max(pr) != min(pr) else ''}, 경쟁률 {aa / gg:.1f} : 1"
                  + (f", 가점 최저 {min(mins):.0f}점" if mins else '') + '</li>' if pr else '')
    if len(bl) > 1: P.append('<h3>면적대별로 보면</h3><ul>' + ''.join(bl) + '</ul>')
    # 특공
    sp = [x for x in (p.get('sp_stat') or []) if x[1]]
    if sp:
        tot_a, tot_p = sum(x[1] for x in sp), sum(x[2] for x in sp)
        best = max(sp, key=lambda x: x[2] / x[1])
        rows = ''.join(f"<tr><td {TD}>{k}</td><td {TDR}>{a}</td><td {TDR}>{c:,}</td><td {TDR}><b style=\"color:{RED if c > a else BLUE}\">{c / a:.1f} : 1</b></td></tr>" for k, a, c in sp)
        P.append(f"<h3>특별공급 신청현황</h3><p>특별공급 {tot_a:,}세대에 {tot_p:,}건이 접수됐습니다. 가장 치열한 유형은 <b>{best[0]}</b>({best[2] / best[1]:.1f} : 1)였어요.</p>"
                 f"<table {T}><tr><th {TH}>유형</th><th {THR}>배정</th><th {THR}>접수</th><th {THR}>경쟁률</th></tr>{rows}</table>"
                 '<p><small>특별공급에서 남은 물량은 일반공급으로 넘어갑니다.</small></p>')
    # 주변 시세
    near = [n for n in (p.get('near') or []) if n.get('m59') or n.get('m84')][:4]
    if near:
        u59 = [t[4] for t in ty if 57 <= ex(t) < 61 and t[4]]; u84 = [t[4] for t in ty if 82 <= ex(t) < 86 and t[4]]
        r59 = [n['m59'] for n in near if n.get('m59')]; r84 = [n['m84'] for n in near if n.get('m84')]
        cmp_ = []
        if u59 and r59: cmp_.append(f"59㎡ 분양가(최저 {man(min(u59))})는 주변 59㎡ 시세 중앙값 대비 <b style=\"color:{pc((min(u59) / statistics.median(r59) - 1) * 100)}\">{sg((min(u59) / statistics.median(r59) - 1) * 100)}</b>")
        if u84 and r84: cmp_.append(f"84㎡ 분양가(최저 {man(min(u84))})는 주변 84㎡ 시세 중앙값 대비 <b style=\"color:{pc((min(u84) / statistics.median(r84) - 1) * 100)}\">{sg((min(u84) / statistics.median(r84) - 1) * 100)}</b>")
        rows = ''.join(f"<tr><td {TD}>{esc(n['apt'])}<br><small>{n['built']}년 준공 · 최근 6개월 {n['n']}건</small></td>"
                       f"<td {TDR}>{man(n['m59']) + '<br><small>' + str(n['n59']) + '건</small>' if n.get('m59') else '-'}</td>"
                       f"<td {TDR}>{man(n['m84']) + '<br><small>' + str(n['n84']) + '건</small>' if n.get('m84') else '-'}</td></tr>" for n in near)
        rows += (f"<tr><td {TD}><b>{esc(p['name'])} (분양가)</b>{'<br><small>' + p['move'][:4] + '년 입주 예정</small>' if p.get('move') else ''}</td>"
                 f"<td {TDR}><b>{man(min(u59)) + '~' if u59 else '-'}</b></td><td {TDR}><b>{man(min(u84)) + '~' if u84 else '-'}</b></td></tr>")
        P.append(f"<h3>주변 신축 아파트 실거래와 비교</h3><p>같은 {esc(p.get('umd') or '동네')}의 최근 10년 내 준공 아파트 매매 실거래(최근 6개월, 중앙값)입니다. "
                 + (', '.join(cmp_) + '입니다.' if cmp_ else '') + '</p>'
                 f"<table {T}><tr><th {TH}>단지</th><th {THR}>59㎡</th><th {THR}>84㎡</th></tr>{rows}</table>"
                 '<p><small>새 아파트는 입주까지 몇 년이 남아 있어 지금 시세와 단순 비교하기는 어렵습니다. 참고용으로 봐 주세요.</small></p>')
    P.append(foot)
    return title, P, ['수도권 청약', '청약 단지분석', '청약 경쟁률', '당첨 가점']
