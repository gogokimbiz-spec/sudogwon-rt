"""청약홈 수도권(서울·인천·경기) APT 분양정보·경쟁률 수집 – 공공데이터포털 공식 API 사용 (GitHub Actions 용).
환경변수 DATA_GO_KR_KEY 에 공공데이터포털 일반 인증키(Decoding)를 넣어 실행합니다 (실거래와 같은 키).
공공데이터포털에서 아래 두 API 를 '활용신청' 해야 합니다.
  - 한국부동산원_청약홈 분양정보 조회 서비스 (15098547)
  - 한국부동산원_청약홈 청약접수 경쟁률 및 특별공급 신청현황 조회 서비스 (15098905)
결과: cy_data.json (build_cy.py 입력 형식)
"""
import os, sys, json, time, datetime, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ['DATA_GO_KR_KEY'].strip()
API = 'https://api.odcloud.kr/api/'
KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
BEGIN = (today.replace(day=1) - datetime.timedelta(days=300)).replace(day=1).isoformat()  # 약 10개월 전 1일부터
AREAS = ('서울', '인천', '경기')

def get(path, cond, per=500):
    rows, page = [], 1
    while True:
        q = {'serviceKey': KEY, 'page': page, 'perPage': per, 'returnType': 'JSON'}
        q.update({f'cond[{k}]': v for k, v in cond.items()})
        url = API + path + '?' + urllib.parse.urlencode(q)
        for a in range(6):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    j = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    sys.exit(f'{path}: 인증 실패({e.code}). 공공데이터포털에서 이 API 활용신청이 승인됐는지 확인하세요.')
                err = e
            except Exception as e:
                err = e
            time.sleep(2 + a * 2)
        else:
            raise RuntimeError(f'{path} 실패: {err}')
        data = j.get('data') or []
        rows += data
        if len(rows) >= (j.get('matchCount') or j.get('totalCount') or 0) or not data: return rows
        page += 1

dt = lambda s: (f'{s[:4]}-{s[4:6]}-{s[6:8]}' if s and len(s) == 8 and s.isdigit() else (s or ''))[:10]
def num(v):
    try: return float(str(v).replace(',', '').strip())
    except Exception: return None

# 1) 공고 목록 (전국 → 수도권·분양주택만)
det = get('ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail', {'RCRIT_PBLANC_DE::GTE': BEGIN})
det = [d for d in det if str(d.get('RENT_SECD', '0')) == '0' and
       any((d.get('SUBSCRPT_AREA_CODE_NM') or '').startswith(a) or (d.get('HSSPLY_ADRES') or '').startswith(a) for a in AREAS)]
print('수도권 공고', len(det), BEGIN, '~')
if not det:
    sys.exit('청약홈 API 에서 공고를 받지 못했습니다')

FLAGS = [('SPECLT_RDN_EARTH_AT', '투기과열지구'), ('MDAT_TRGET_AREA_SECD', '청약과열지역'), ('PARCPRC_ULS_AT', '분양가상한제'),
         ('IMPRMN_BSNS_AT', '정비사업'), ('PUBLIC_HOUSE_EARTH_AT', '공공주택지구'), ('LRSCL_BLDLND_AT', '대규모택지개발지구')]

# 특별공급 유형: (이름, 배정 필드, 접수 필드 접미사들)
SPC = [('다자녀', 'MNYCH_HSHLDCO', ['CRSPAREA_MNYCH_CNT', 'CTPRVN_MNYCH_CNT', 'ETC_AREA_MNYCH_CNT']),
       ('신혼부부', 'NWWDS_NMTW_HSHLDCO', ['CRSPAREA_NWWDS_NMTW_CNT', 'CTPRVN_NWWDS_NMTW_CNT', 'ETC_AREA_NWWDS_NMTW_CNT']),
       ('생애최초', 'LFE_FRST_HSHLDCO', ['CRSPAREA_LFE_FRST_CNT', 'CTPRVN_LFE_FRST_CNT', 'ETC_AREA_LFE_FRST_CNT']),
       ('청년', 'YGMN_HSHLDCO', ['CRSPAREA_YGMN_CNT', 'CTPRVN_YGMN_CNT', 'ETC_AREA_YGMN_CNT']),
       ('노부모', 'OLD_PARNTS_SUPORT_HSHLDCO', ['CRSPAREA_OPS_CNT', 'CTPRVN_OPS_CNT', 'ETC_AREA_OPS_CNT']),
       ('신생아', 'NWBB_NWBBSHR_HSHLDCO', ['CRSPAREA_NWBB_NWBBSHR_CNT', 'CTPRVN_NWBB_NWBBSHR_CNT', 'ETC_AREA_NWBB_NWBBSHR_CNT']),
       ('기관추천', 'INSTT_RECOMEND_HSHLDCO', ['INSTT_RECOMEND_DCSN_CNT']),
       ('이전기관', 'TRANSR_INSTT_ENFSN_HSHLDCO', ['TRANSR_INSTT_ENFSN_CNT'])]
def sp_stat(rows):
    """특별공급 유형별 [이름, 배정 세대, 접수 건수] (단지 합계)"""
    if not rows: return None
    out = []
    for n, fa, fc in SPC:
        al = sum(num(r.get(fa)) or 0 for r in rows); ap = sum(num(r.get(f)) or 0 for r in rows for f in fc)
        out.append([n, int(al), int(ap)])
    return out if any(x[1] for x in out) else None

def one(d):
    hm, pb = str(d['HOUSE_MANAGE_NO']), str(d['PBLANC_NO'])
    c = {'HOUSE_MANAGE_NO::EQ': hm, 'PBLANC_NO::EQ': pb}
    mdl = get('ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancMdl', c)
    r1 = dt(d.get('GNRL_RNK1_CRSPAREA_RCPTDE')) or dt(d.get('RCEPT_BGNDE'))
    started = bool(r1) and r1 <= today.isoformat()
    cmp = get('ApplyhomeInfoCmpetRtSvc/v1/getAPTLttotPblancCmpet', c) if started else []
    sco = get('ApplyhomeInfoCmpetRtSvc/v1/getAptLttotPblancScore', c) if started else []
    try:
        spr = get('ApplyhomeInfoCmpetRtSvc/v1/getAPTSpsplyReqstStus', c) if started else []
    except Exception as e:
        print('특별공급 신청현황 실패', hm, e); spr = []
    area = next((a for a in AREAS if (d.get('SUBSCRPT_AREA_CODE_NM') or '').startswith(a)), None) or \
           next(a for a in AREAS if (d.get('HSSPLY_ADRES') or '').startswith(a))
    ty = []
    for m in sorted(mdl, key=lambda m: str(m.get('MODEL_NO'))):
        t = str(m.get('HOUSE_TY') or '').strip()
        rows = [x for x in cmp if str(x.get('HOUSE_TY') or '').strip() == t]
        rank = lambda x: str(x.get('SUBSCRPT_RANK_CODE') or '').strip()
        a1 = sum(num(x.get('REQ_CNT')) or 0 for x in rows if rank(x) in ('1', '1순위'))
        a2 = sum(num(x.get('REQ_CNT')) or 0 for x in rows if rank(x) in ('2', '2순위'))
        sc = [x for x in sco if str(x.get('HOUSE_TY') or '').strip() == t and num(x.get('LWET_SCORE'))]
        s0 = next((x for x in sc if str(x.get('RESIDE_SECD')) == '01'), sc[0] if sc else None)
        ty.append([t, num(m.get('SUPLY_AR')), int(num(m.get('SUPLY_HSHLDCO')) or 0), int(num(m.get('SPSPLY_HSHLDCO')) or 0),
                   num(m.get('LTTOT_TOP_AMOUNT')), int(a1), int(a2),
                   [num(s0.get('LWET_SCORE')), num(s0.get('TOP_SCORE')), num(s0.get('AVRG_SCORE'))] if s0 else None,
                   '' if started else '청약 접수일 미도래'])
    ct = dt(d.get('CNTRCT_CNCLS_BGNDE')); ct2 = dt(d.get('CNTRCT_CNCLS_ENDDE'))
    sp0, sp1 = dt(d.get('SPSPLY_RCEPT_BGNDE')), dt(d.get('SPSPLY_RCEPT_ENDDE'))
    return {'pb': pb, 'hm': hm, 'nm': d.get('HOUSE_NM', ''), 'area': area, 'kind': d.get('HOUSE_DTL_SECD_NM') or '',
            'builder': d.get('CNSTRCT_ENTRPS_NM') or '', 'con': d.get('CNSTRCT_ENTRPS_NM') or '',
            'ann': dt(d.get('RCRIT_PBLANC_DE')), 'rcpt': f"{dt(d.get('RCEPT_BGNDE'))} ~ {dt(d.get('RCEPT_ENDDE'))}",
            'win': dt(d.get('PRZWNER_PRESNATN_DE')), 'addr': d.get('HSSPLY_ADRES'), 'size': str(d.get('TOT_SUPLY_HSHLDCO') or ''),
            'sc': {k: v for k, v in {'sp': sp0 if sp0 == sp1 or not sp1 else f'{sp0} ~ {sp1}', 'r1': r1,
                                     'r2': dt(d.get('GNRL_RNK2_CRSPAREA_RCPTDE')), 'ct': f'{ct} ~ {ct2}' if ct2 and ct2 != ct else ct}.items() if v},
            'move': (lambda s: f'{s[:4]}.{s[4:6]}' if len(s) == 6 else s)(str(d.get('MVN_PREARNGE_YM') or '')),
            'note': ', '.join(n for k, n in FLAGS if str(d.get(k) or '').upper() == 'Y') or None,
            'url': d.get('PBLANC_URL'), 'ty': ty, 'hasc': bool(cmp), 'sp_stat': sp_stat(spr)}

with ThreadPoolExecutor(3) as ex:
    OUT = list(ex.map(one, det))
# ── 줍줍: 무순위·재공급(잔여세대) + 임의공급, 최근 40일 공고 중 수도권
R0 = (today - datetime.timedelta(days=40)).isoformat()
REM = []
for kind, dpath, mpath in [('무순위', 'getRemndrLttotPblancDetail', 'getRemndrLttotPblancMdl'),
                           ('임의공급', 'getOPTLttotPblancDetail', 'getOPTLttotPblancMdl')]:
    try:
        rows = get('ApplyhomeInfoDetailSvc/v1/' + dpath, {'RCRIT_PBLANC_DE::GTE': R0})
    except Exception as e:
        print(f'{kind} 목록 실패: {e}'); continue
    for d in rows:
        area = next((a for a in AREAS if (d.get('SUBSCRPT_AREA_CODE_NM') or '').startswith(a) or (d.get('HSSPLY_ADRES') or '').startswith(a)), None)
        if not area: continue
        b0 = dt(d.get('SUBSCRPT_RCEPT_BGNDE') or d.get('GNRL_RCEPT_BGNDE')); b1 = dt(d.get('SUBSCRPT_RCEPT_ENDDE') or d.get('GNRL_RCEPT_ENDDE')) or b0
        if not b0 or b1 < (today - datetime.timedelta(days=7)).isoformat(): continue      # 이미 끝난 지 오래된 것은 뺌
        hm, pb = str(d['HOUSE_MANAGE_NO']), str(d['PBLANC_NO'])
        try: mdl = get('ApplyhomeInfoDetailSvc/v1/' + mpath, {'HOUSE_MANAGE_NO::EQ': hm, 'PBLANC_NO::EQ': pb})
        except Exception: mdl = []
        sec = str(d.get('HOUSE_SECD') or '')
        REM.append({'pb': pb, 'nm': d.get('HOUSE_NM', ''), 'area': area, 'addr': d.get('HSSPLY_ADRES'),
                    'kind': '임의공급' if kind == '임의공급' else ('불법행위 재공급' if sec == '06' else '무순위'),
                    'ann': dt(d.get('RCRIT_PBLANC_DE')), 'r0': b0, 'r1': b1, 'win': dt(d.get('PRZWNER_PRESNATN_DE')),
                    'size': int(num(d.get('TOT_SUPLY_HSHLDCO')) or 0), 'url': d.get('PBLANC_URL'),
                    'ty': [[str(m.get('HOUSE_TY') or '').strip(), int(num(m.get('SUPLY_HSHLDCO')) or 0), num(m.get('LTTOT_TOP_AMOUNT'))] for m in mdl]})
print('줍줍(무순위·임의공급) 수도권', len(REM), '건')
json.dump({'asof': today.isoformat(), 'range': [BEGIN, ''], 'items': OUT, 'remndr': REM}, open('cy_data.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('저장', len(OUT), '건 · 경쟁률 있는 곳', sum(o['hasc'] for o in OUT))
