"""부동산 판례 카드 1장 (워터마크 @data_jaetech 3개 – 11-23) (기승전결, 1080×1350, 실거래 카드와 같은 slate 테마) – 2026-11-19
사용법: python make_law_story.py case.json out.png
case.json: date('2026. 9. 10.'), title('…\n…' 2줄), story([['기','…'],['승','…'],['전','…'],['결','…']]), tip, case(사건번호 줄)
글이 길면 글씨를 조금씩 줄여서 넣습니다.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
BG, ROW = (255, 255, 255), (246, 246, 247)
WHITE, GRAY, DIM = (30, 32, 38), (124, 128, 136), (150, 154, 162)
YEL, DARK = (224, 88, 88), (255, 255, 255)
HERE = os.path.dirname(os.path.abspath(__file__))
_cache = {}


def F(size, w='Bold'):
    k = (size, w)
    if k in _cache: return _cache[k]
    for p, idx in ((f'/usr/share/fonts/noto-kr/NotoSansCJKkr-{w}.otf', 0),          # GitHub Actions (저장소 fonts/ 복사본)
                   (os.path.join(HERE, 'fonts', f'NotoSansCJKkr-{w}.otf'), 0),
                   (f'/usr/share/fonts/opentype/noto/NotoSansCJK-{w}.ttc', 1)):
        if os.path.exists(p):
            _cache[k] = ImageFont.truetype(p, size, index=idx); return _cache[k]
    raise SystemExit(f'한글 폰트를 찾지 못했습니다 ({w})')


def tw(d, s, f): return d.textlength(s, font=f)


def wrap(d, text, f, maxw):
    out = []
    for part in str(text).split('\n'):
        cur = ''
        for word in part.split(' '):
            t = (cur + ' ' + word).strip()
            if tw(d, t, f) <= maxw: cur = t
            else:
                if cur: out.append(cur)
                while tw(d, word, f) > maxw:              # 띄어쓰기 없이 너무 긴 낱말
                    n = len(word)
                    while n > 1 and tw(d, word[:n], f) > maxw: n -= 1
                    out.append(word[:n]); word = word[n:]
                cur = word
        if cur: out.append(cur)
    return out


def pill(d, x, y, text, f, bg, fg, padx=18, h=48):
    w = tw(d, text, f) + padx * 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg)
    d.text((x + padx, y + h / 2), text, font=f, fill=fg, anchor='lm')


def watermark(im, d, text='@data_jaetech', alpha=40, size=66):
    """다른 카드(card_style.watermark)와 같은 워터마크: 내용 위에 반투명 아이디 3개를 비스듬히 – 캡처·퍼가기에도 아이디가 남게"""
    f = F(size, 'Black'); w = int(tw(d, text, f)) + 30
    tile = Image.new('RGBA', (w, size + 36), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((15, 6), text, font=f, fill=WHITE + (alpha,))
    tile = tile.rotate(24, expand=True, resample=Image.BICUBIC)
    for cx, cy in ((790, 330), (790, 820), (290, 1080)):
        im.paste(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)), tile)


def draw(c, out, ts=56, bs=30):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    pill(d, 60, 56, c.get('badge') or '이번 주 부동산 판례', F(26), YEL, DARK)
    s = c['date'] + ' 선고'
    d.text((1020 - tw(d, s, F(28, 'Medium')), 80), s, font=F(28, 'Medium'), fill=GRAY, anchor='lm')
    ft = F(ts); y = 136
    for ln in wrap(d, c['title'], ft, 960)[:3]:
        d.text((60, y), ln, font=ft, fill=WHITE); y += int(ts * 1.25)
    y += 26
    lh = int(bs * 1.53)
    for i, (ch, text) in enumerate(c['story']):
        last = i == len(c['story']) - 1
        fb = F(bs, 'Bold' if last else 'Medium')
        lines = wrap(d, text, fb, 850)
        bh = max(124, 44 + lh * len(lines))
        d.rounded_rectangle([60, y, 1020, y + bh], radius=20, fill=(253, 230, 230) if last else ROW)
        cx, cy = 100, y + bh / 2
        d.ellipse([cx - 32, cy - 32, cx + 32, cy + 32], fill=YEL)
        d.text((cx, cy), ch, font=F(38, 'Black'), fill=DARK, anchor='mm')
        yy = y + (bh - lh * len(lines)) / 2 + 2
        for ln in lines:
            d.text((148, yy), ln, font=fb, fill=(150, 36, 36) if last else WHITE); yy += lh
        y += bh + 22
    ty = 1088
    d.rounded_rectangle([60, ty, 1020, ty + 92], radius=18, fill=(255, 244, 244), outline=(232, 226, 226), width=2)
    pill(d, 84, ty + 22, 'TIP', F(24), YEL, DARK, padx=14, h=46)
    ftip = F(29)
    while tw(d, c['tip'], ftip) > 820 and ftip.size > 20: ftip = F(ftip.size - 1)
    d.text((176, ty + 46), c['tip'], font=ftip, fill=WHITE, anchor='lm')
    fc = F(25, 'Medium')
    while tw(d, c['case'], fc) > 960 and fc.size > 18: fc = F(fc.size - 1)
    d.text((60, 1200), c['case'], font=fc, fill=GRAY)
    d.text((60, 1232), '※ 판결 요지를 쉽게 풀어 쓴 것으로 법률 자문이 아닙니다', font=F(21, 'Regular'), fill=DIM)
    watermark(im, d)
    d.line([(60, 1268), (1020, 1268)], fill=(232, 226, 226), width=2)
    d.text((60, 1285), '데이터로 보는 재테크 · 자료 대법원 판례속보·판결문', font=F(24, 'Medium'), fill=GRAY)
    d.text((1020 - tw(d, '@data_jaetech', F(26)), 1283), '@data_jaetech', font=F(26), fill=YEL)
    return im, y


def make(c, out):
    for ts, bs in ((56, 40), (54, 38), (52, 36), (50, 34), (48, 32), (46, 30), (44, 28), (42, 26), (40, 25)):
        im, y = draw(c, out, ts, bs)
        if y <= 1080: break
    else:
        print('::warning::판례 카드 글이 길어 TIP 상자와 겹칠 수 있습니다')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    im.save(out); print('판례 카드 →', out)


if __name__ == '__main__':
    make(json.load(open(sys.argv[1], encoding='utf-8')), sys.argv[2])
