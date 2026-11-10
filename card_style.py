"""카드 이미지 공통 디자인. make_cards.py / make_cards_cy.py / make_cards_fin.py 가 함께 씁니다.
THEME 값만 바꾸면 세 카드 색이 함께 바뀝니다. (환경변수 CARD_THEME 로도 바꿀 수 있음)
"""
import os
from PIL import Image, ImageDraw

W, SH = 1080, 1350
THEMES = {
    # 이름: 배경, 머리배경, 장식, 포인트, 칩글씨, 날짜칩, 칩배경, 글씨, 보조글씨, 테두리, 머리글씨, 머리보조, 큰숫자
    'orange':   dict(bg=(255, 255, 255), head=(255, 245, 236), deco=(255, 228, 205), accent=(255, 122, 26), chip_t=(226, 98, 8),
                     pill=(18, 184, 166), chip=(255, 239, 225), ink=(25, 31, 40), ink2=(139, 149, 161), line=(240, 230, 220),
                     h_ink=(25, 31, 40), h_ink2=(139, 149, 161), big=(255, 122, 26)),
    'mint':     dict(bg=(246, 250, 249), head=(14, 165, 145), deco=(52, 196, 176), accent=(14, 165, 145), chip_t=(10, 120, 106),
                     pill=(255, 255, 255), chip=(224, 245, 241), ink=(22, 34, 46), ink2=(128, 142, 152), line=(222, 236, 233),
                     h_ink=(255, 255, 255), h_ink2=(214, 246, 240), big=(255, 236, 140), pill_t=(10, 120, 106)),
    'lavender': dict(bg=(250, 249, 255), head=(238, 234, 255), deco=(221, 213, 255), accent=(108, 76, 230), chip_t=(96, 64, 214),
                     pill=(255, 168, 76), chip=(236, 231, 255), ink=(30, 27, 52), ink2=(140, 136, 160), line=(229, 225, 245),
                     h_ink=(30, 27, 52), h_ink2=(140, 136, 160), big=(108, 76, 230)),
    'paper':    dict(bg=(246, 241, 232), head=(246, 241, 232), deco=None, accent=(214, 69, 36), chip_t=(246, 241, 232),
                     pill=(28, 26, 23), chip=(28, 26, 23), ink=(28, 26, 23), ink2=(120, 112, 100), line=(28, 26, 23),
                     h_ink=(28, 26, 23), h_ink2=(120, 112, 100), big=(214, 69, 36), flat=True),
    'dark':     dict(bg=(17, 17, 17), head=(17, 17, 17), deco=(32, 32, 32), accent=(198, 244, 50), chip_t=(198, 244, 50),
                     pill=(198, 244, 50), chip=(38, 44, 22), ink=(245, 245, 245), ink2=(150, 150, 150), line=(48, 48, 48),
                     h_ink=(255, 255, 255), h_ink2=(150, 150, 150), big=(198, 244, 50), pill_t=(17, 17, 17), card=(28, 28, 28),
                     up=(255, 90, 95), down=(77, 163, 255)),
}
THEME = os.environ.get('CARD_THEME') or 'paper'   # orange / mint / lavender / paper / dark
T = THEMES.get(THEME, THEMES['orange'])
WHITE = (255, 255, 255)
INK, INK2, LINE, ORANGE = T['ink'], T['ink2'], T['line'], T['accent']
UP, DOWN = T.get('up', (240, 68, 82)), T.get('down', (49, 130, 246))
BRAND = '데이터로 보는 재테크'


def canvas():
    im = Image.new('RGB', (W, SH), T['bg'])
    return im, ImageDraw.Draw(im)


def header(d, F, pill, title, big='', sub=''):
    d.rectangle((0, 0, W, 312), fill=T['head'])
    if T.get('deco'): d.ellipse((W - 350, -160, W + 110, 300), fill=T['deco'])
    if T.get('flat'):
        d.rectangle((40, 30, W - 40, 36), fill=T['ink']); d.rectangle((40, 302, W - 40, 312), fill=T['ink'])
    else:
        d.rectangle((0, 308, W, 312), fill=T['accent'])
    pf = F(30); pw = d.textlength(pill, font=pf)
    d.rounded_rectangle((64, 58, 64 + pw + 44, 110), 8 if T.get('flat') else 26, fill=T['pill'])
    d.text((86, 63), pill, font=pf, fill=T.get('pill_t', WHITE))
    tf = F(76, 'Black'); d.text((62, 134), title, font=tf, fill=T['h_ink'])
    if big:
        room = W - 76 - (62 + d.textlength(title, font=tf) + 28)
        size = 120 if len(big) <= 3 else 72
        while size > 56 and d.textlength(big, font=F(size, 'Black')) > room: size -= 4
        bf = F(size, 'Black')
        d.text((W - 76 - d.textlength(big, font=bf), 112 + (120 - size) * 0.45), big, font=bf, fill=T['big'])
    if sub:
        d.text((64, 244), sub, font=F(28, 'Medium'), fill=T['h_ink2'])


def row_box(d, y, h):
    if T.get('flat'):
        d.line((40, y + h + 4, W - 40, y + h + 4), fill=T['line'], width=2)
    else:
        d.rounded_rectangle((40, y, W - 40, y + h), 24, fill=T.get('card', WHITE), outline=T['line'], width=3)


def chip(d, F, x, y, text, size=26):
    f = F(size); w = d.textlength(text, font=f)
    d.rounded_rectangle((x, y, x + w + 28, y + size + 14), 6 if T.get('flat') else (size + 14) // 2, fill=T['chip'])
    d.text((x + 14, y + 3), text, font=f, fill=T['chip_t'])
    return w + 28


def badge(d, F, x, cy, n, size, hot):
    col = T['accent'] if hot else T['pill'] if T['pill'] != WHITE else T['ink2']
    d.ellipse((x, cy - size, x + 2 * size, cy + size), fill=col)
    nf = F(int(size * 1.15), 'Black'); s = str(n)
    d.text((x + size - d.textlength(s, font=nf) / 2, cy - size * 0.9), s, font=nf, fill=T.get('pill_t', WHITE) if col == T['pill'] else WHITE)


def cta(d, F, msg):
    d.rounded_rectangle((40, SH - 150, W - 40, SH - 60), 10 if T.get('flat') else 45, fill=T['accent'])
    d.text(((W - d.textlength(msg, font=F(38))) / 2, SH - 136), msg, font=F(38), fill=T.get('cta_t', T.get('pill_t', WHITE) if T['accent'] == T['pill'] else WHITE))


def footer(d, F, text):
    d.text((64, SH - 46), f'{BRAND} · {text}', font=F(22, 'Regular'), fill=T['ink2'])
