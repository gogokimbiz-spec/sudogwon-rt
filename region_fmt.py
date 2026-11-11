"""동네 대표기업 공통 숫자 표기 (카드·블로그·카톡)"""


def won(v):
    if v is None: return '-'
    s = '-' if v < 0 else ''; v = abs(v)
    if v >= 1e12:
        j, e = divmod(round(v / 1e8), 10000)
        return f'{s}{j:,}조 {e:,}억' if e else f'{s}{j:,}조'
    if v >= 1e8: return f'{s}{round(v / 1e8):,}억'
    return f'{s}{round(v / 1e4):,}만'


def man(v):
    """만원 단위 → '1억 2,300만' / '8,500만'"""
    if not v: return '-'
    e, m = divmod(int(v), 10000)
    return (f'{e}억 {m:,}만' if m else f'{e}억') if e else f'{m:,}만'


def emp(v):
    return f'{v:,}명' if v else '-'


def tenure(v):
    """근속연수: '12.5' → '12.5년', 이미 '년' 이 있으면 그대로"""
    v = (v or '').strip()
    if not v: return '-'
    if '년' in v or '개월' in v: return v.replace(' ', '')
    try: return f'{float(v.replace(",", "")):g}년'
    except ValueError: return v


def short(v):
    """카드용 짧은 금액: 49.0조 / 7,214억 / -350억"""
    if v is None: return '-'
    a = abs(v); s = '-' if v < 0 else ''
    if a >= 1e12: return f'{s}{a / 1e12:,.1f}조'
    if a >= 1e8: return f'{s}{round(a / 1e8):,}억'
    return f'{s}{round(a / 1e4):,}만'
