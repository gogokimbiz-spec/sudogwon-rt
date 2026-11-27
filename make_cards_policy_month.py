# -*- coding: utf-8 -*-
"""
이달의 부동산 정책 9가지 카드 (1080×1350, 3×3 칸) – 2026-11-27
  입력: policy_month_inbox/<YYYY-MM>.json  (매월 말 Claude 예약 작업이 정리해 올림)
  출력: <out>/card.png, <out>/caption.txt, <out>/summary.json

  python make_cards_policy_month.py policy_month_inbox/2026-11.json cards/policy_month

inbox JSON
{
 "month": "2026-11",
 "day": "2026-11-30",                       # 게시일(말일)
 "items": [                                  # 9개 (모자라면 있는 만큼, 최소 6)
   {"icon": "house|won|percent|key|doc|building|people|shield|chart|train",
    "title": "공공재개발 수수료",             # 10자 안팎
    "before": "3%", "after": "1%",           # 바뀌는 숫자 (없으면 main 사용)
    "main": "",                              # 숫자 대신 한 줄 (예: '보증금 3분의 1 보장')
    "note": "'27년 말까지 LH 신규 후보지",   # 회색 설명 1~2줄
    "status": "시행|확정|개정안|정부안|추진|예정|모집|논의|결과|전망",
    "date": "2026-11-12", "source": "https://..."}
 ],
 "blog": {"intro": "...", "sections": [["h", "p"], ...]}   # 선택
}
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
NAVY = (23, 32, 51)
BG = (241, 243, 246)
INK = (17, 24, 39)
SUB = (71, 85, 105)
DIM = (100, 116, 139)
RED = (220, 38, 38)
YEL = (255, 196, 0)
HANDLE = "@data_jaetech"

# 상태 칩 색 (배경, 글자)
STATUS = {
    "시행": ((22, 128, 88), (255, 255, 255)), "확정": ((22, 128, 88), (255, 255, 255)),
    "개정안": ((255, 196, 0), (17, 24, 39)), "추진": ((255, 196, 0), (17, 24, 39)),
    "모집": ((255, 196, 0), (17, 24, 39)),
    "정부안": ((37, 99, 235), (255, 255, 255)), "예정": ((37, 99, 235), (255, 255, 255)),
    "논의": ((234, 88, 12), (255, 255, 255)), "국회 논의": ((234, 88, 12), (255, 255, 255)),
    "결과": ((100, 116, 139), (255, 255, 255)), "전망": ((100, 116, 139), (255, 255, 255)),
}
def chip_color(st):
    """'1월 1일 시행', '12.15 마감' 처럼 날짜가 붙어도 끝말로 색을 고름"""
    if st in STATUS:
        return STATUS[st]
    for key, col in (("마감", ((234, 88, 12), (255, 255, 255))), ("종료", ((234, 88, 12), (255, 255, 255))),
                     ("시행", STATUS["시행"]), ("확정", STATUS["확정"]), ("예정", STATUS["예정"]),
                     ("출시", STATUS["예정"]), ("개정안", STATUS["개정안"]), ("추진", STATUS["추진"]),
                     ("논의", STATUS["논의"])):
        if key in st:
            return col
    return ((100, 116, 139), (255, 255, 255))


ICON_BG = {"house": (219, 234, 254), "won": (254, 243, 199), "percent": (254, 226, 226), "key": (209, 250, 229),
           "doc": (237, 233, 254), "building": (224, 231, 255), "people": (252, 231, 243), "shield": (204, 251, 241),
           "chart": (241, 245, 249), "train": (224, 242, 254)}
ICON_FG = {"house": (37, 99, 235), "won": (202, 138, 4), "percent": (220, 38, 38), "key": (5, 150, 105),
           "doc": (124, 58, 237), "building": (67, 56, 202), "people": (219, 39, 119), "shield": (13, 148, 136),
           "chart": (71, 85, 105), "train": (2, 132, 199)}
SUBST = {"全": "전", "α": "a", "⅓": "1/3", "◈": "", "\u00a0": " "}


def _font_path(weight):
    for p in ("/usr/share/fonts/noto-kr/NotoSansCJKkr-%s.otf" % weight,
              os.path.join("fonts", "NotoSansCJKkr-%s.otf" % weight),
              "/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc" % weight,
              "/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc" % ("Bold" if weight == "Black" else "Regular"),
              "C:/Windows/Fonts/malgunbd.ttf" if weight in ("Black", "Bold") else "C:/Windows/Fonts/malgun.ttf"):
        if os.path.exists(p):
            return p
    raise FileNotFoundError(weight)


_FC = {}


def F(w, s):
    if (w, s) not in _FC:
        p = _font_path(w)
        _FC[(w, s)] = ImageFont.truetype(p, s, index=1 if p.endswith(".ttc") else 0)
    return _FC[(w, s)]


def disp(t):
    for a, b in SUBST.items():
        t = t.replace(a, b)
    return t


def tw(d, t, f):
    return d.textlength(t, font=f)


def fit_font(d, text, weight, size, maxw, minsize):
    while size > minsize and tw(d, text, F(weight, size)) > maxw:
        size -= 1
    return F(weight, size)


def wrap(d, text, font, maxw, maxlines):
    lines, cur = [], ""
    for word in text.split(" "):
        t = (cur + " " + word).strip()
        if tw(d, t, font) <= maxw:
            cur = t
            continue
        if cur:
            lines.append(cur)
        cur = word
        while tw(d, cur, font) > maxw:
            k = len(cur)
            while k > 1 and tw(d, cur[:k], font) > maxw:
                k -= 1
            lines.append(cur[:k]); cur = cur[k:]
    if cur:
        lines.append(cur)
    if len(lines) > maxlines:
        lines = lines[:maxlines]
        s = lines[-1]
        while s and tw(d, s + "…", font) > maxw:
            s = s[:-1]
        lines[-1] = s + "…"
    return lines


# ---------- 아이콘 (간단한 도형) ----------
def icon(d, kind, cx, cy, r):
    bg, fg = ICON_BG.get(kind, (241, 245, 249)), ICON_FG.get(kind, (71, 85, 105))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=bg)
    s = r * 0.55
    if kind == "house":
        d.polygon([(cx - s, cy - s * 0.05), (cx, cy - s * 0.95), (cx + s, cy - s * 0.05)], fill=fg)
        d.rectangle((cx - s * 0.72, cy - s * 0.1, cx + s * 0.72, cy + s * 0.8), fill=fg)
        d.rectangle((cx - s * 0.18, cy + s * 0.25, cx + s * 0.18, cy + s * 0.8), fill=bg)
    elif kind == "won":
        d.ellipse((cx - s, cy - s, cx + s, cy + s), fill=fg)
        d.text((cx, cy + 1), "₩", font=F("Black", int(r * 0.85)), fill=bg, anchor="mm")
    elif kind == "percent":
        d.text((cx, cy), "%", font=F("Black", int(r * 1.15)), fill=fg, anchor="mm")
    elif kind == "key":
        d.ellipse((cx - s, cy - s * 0.55, cx - s * 0.1, cy + s * 0.35), outline=fg, width=max(3, int(r * 0.14)))
        d.rectangle((cx - s * 0.15, cy - s * 0.17, cx + s, cy + s * 0.0), fill=fg)
        d.rectangle((cx + s * 0.55, cy, cx + s * 0.72, cy + s * 0.35), fill=fg)
        d.rectangle((cx + s * 0.82, cy, cx + s, cy + s * 0.28), fill=fg)
    elif kind == "doc":
        d.rounded_rectangle((cx - s * 0.7, cy - s, cx + s * 0.7, cy + s), 4, fill=fg)
        for i in range(3):
            y = cy - s * 0.5 + i * s * 0.45
            d.rectangle((cx - s * 0.42, y, cx + s * 0.42, y + s * 0.13), fill=bg)
    elif kind == "building":
        d.rectangle((cx - s * 0.6, cy - s, cx + s * 0.6, cy + s), fill=fg)
        for i in range(3):
            for j in range(2):
                x0 = cx - s * 0.38 + j * s * 0.48; y0 = cy - s * 0.75 + i * s * 0.5
                d.rectangle((x0, y0, x0 + s * 0.28, y0 + s * 0.28), fill=bg)
    elif kind == "people":
        for dx, k in ((-0.42, 0.9), (0.42, 0.9)):
            x = cx + dx * s
            d.ellipse((x - s * 0.3, cy - s * 0.85, x + s * 0.3, cy - s * 0.25), fill=fg)
            d.pieslice((x - s * 0.5, cy - s * 0.15, x + s * 0.5, cy + s * 0.95), 180, 360, fill=fg)
    elif kind == "shield":
        d.polygon([(cx, cy - s), (cx + s * 0.8, cy - s * 0.65), (cx + s * 0.65, cy + s * 0.35), (cx, cy + s),
                   (cx - s * 0.65, cy + s * 0.35), (cx - s * 0.8, cy - s * 0.65)], fill=fg)
        d.line([(cx - s * 0.35, cy), (cx - s * 0.05, cy + s * 0.3), (cx + s * 0.4, cy - s * 0.3)], fill=bg, width=max(3, int(r * 0.12)))
    elif kind == "train":
        d.rounded_rectangle((cx - s * 0.65, cy - s, cx + s * 0.65, cy + s * 0.7), 8, fill=fg)
        d.rectangle((cx - s * 0.45, cy - s * 0.7, cx + s * 0.45, cy - s * 0.1), fill=bg)
        for dx in (-0.35, 0.35):
            d.ellipse((cx + dx * s - s * 0.12, cy + s * 0.25, cx + dx * s + s * 0.12, cy + s * 0.49), fill=bg)
    else:  # chart
        for i, hgt in enumerate((0.6, 1.1, 1.6)):
            x0 = cx - s * 0.8 + i * s * 0.6
            d.rectangle((x0, cy + s * 0.8 - s * hgt, x0 + s * 0.4, cy + s * 0.8), fill=fg)


def tile(img, d, x, y, w, h, it):
    sh = Image.new("RGBA", (int(w) + 20, int(h) + 20), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((10, 12, w + 10, h + 12), 22, fill=(15, 23, 42, 22))
    img.alpha_composite(sh, (int(x) - 10, int(y) - 10))
    d.rounded_rectangle((x, y, x + w, y + h), 22, fill=(255, 255, 255))
    cx, pad = x + w / 2, 18
    inner = w - pad * 2
    icon(d, it.get("icon", "chart"), cx, y + 44, 30)
    t = disp(it["title"])
    d.text((cx, y + 104), t, font=fit_font(d, t, "Black", 33, inner, 24), fill=INK, anchor="mm")
    # 빨간 숫자 줄
    yy = y + 150
    if it.get("before") and it.get("after"):
        b, a = disp(it["before"]), disp(it["after"])
        txt = f"{b} → {a}"
        f = fit_font(d, txt, "Black", 34, inner, 20)
        d.text((cx, yy), txt, font=f, fill=RED, anchor="mm")
    elif it.get("main"):
        m = disp(it["main"])
        f = fit_font(d, m, "Black", 32, inner, 20)
        d.text((cx, yy), m, font=f, fill=RED, anchor="mm")
    # 설명
    nf = F("Medium", 22)
    lines = wrap(d, disp(it.get("note", "")), nf, inner, 2)
    ny = y + 197 if len(lines) == 1 else y + 192
    for ln in lines:
        d.text((cx, ny), ln, font=nf, fill=SUB, anchor="mm")
        ny += 28
    # 상태 칩
    st = it.get("status", "")
    if st:
        bg, fg = chip_color(st)
        cf = F("Bold", 24)
        cw = tw(d, st, cf) + 44
        d.rounded_rectangle((cx - cw / 2, y + h - 52, cx + cw / 2, y + h - 14), 10, fill=bg)
        d.text((cx, y + h - 33), st, font=cf, fill=fg, anchor="mm")


def draw(data, path):
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    y_, m_ = int(data["month"][:4]), int(data["month"][5:7])
    items = data["items"][:9]
    n = len(items)
    # 머리
    d.rectangle((0, 0, W, 292), fill=NAVY)
    d.text((44, 34), "자료: " + data.get("source_line", "국토교통부 등 정부 보도자료"), font=F("Medium", 24), fill=(203, 213, 225))
    d.rounded_rectangle((W - 44 - 210, 26, W - 44, 70), 10, fill=YEL)
    d.text((W - 44 - 105, 48), f"{y_}년 {m_}월", font=F("Black", 26), fill=NAVY, anchor="mm")
    h1 = data.get("head1") or f"{m_}월에 발표된"
    d.text((W / 2, 140), h1, font=fit_font(d, h1, "Black", 74, W - 120, 50), fill=(255, 255, 255), anchor="mm")
    t1, t2 = (data.get("head2") or "부동산 정책") + " ", f"{n}가지"
    f2 = F("Black", 86)
    x0 = W / 2 - (tw(d, t1, f2) + tw(d, t2, f2)) / 2
    d.text((x0, 234), t1, font=f2, fill=(255, 255, 255), anchor="lm")
    d.text((x0 + tw(d, t1, f2), 234), t2, font=f2, fill=YEL, anchor="lm")
    # 3×3
    cols, gap, L = 3, 18, 34
    rows = (n + cols - 1) // cols
    tw_ = (W - L * 2 - gap * (cols - 1)) / cols
    top, bottom = 318, 1262
    th = min(296, (bottom - top - gap * (rows - 1)) / rows)
    y0 = top + ((bottom - top) - (th * rows + gap * (rows - 1))) / 2
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        left = n - r * cols if r == rows - 1 else cols          # 마지막 줄 가운데 정렬
        off = (cols - min(left, cols)) * (tw_ + gap) / 2
        tile(img, d, L + off + c * (tw_ + gap), y0 + r * (th + gap), tw_, th, it)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 1284), "개정안·정부안은 국회 심의·입법 과정에서 바뀔 수 있어요 · 원문은 프로필 링크(블로그)",
           font=F("Medium", 22), fill=DIM, anchor="mm")
    hx = W - 44 - tw(d, HANDLE, F("Black", 32)) - 36
    d.rounded_rectangle((hx, 1302, W - 44, 1340), 8, fill=YEL)
    d.text((hx + 18, 1321), HANDLE, font=F("Black", 32), fill=INK, anchor="lm")
    d.text((44, 1321), "데이터로 보는 재테크", font=F("Bold", 24), fill=DIM, anchor="lm")
    img.convert("RGB").save(path, optimize=True)


def caption(data):
    m_ = int(data["month"][5:7])
    L = [f"🏠 {data.get('head1') or f'{m_}월에 발표된'} {data.get('head2') or '부동산 정책'} {len(data['items'][:9])}가지", ""]
    for i, it in enumerate(data["items"][:9], 1):
        chg = f"{it['before']} → {it['after']}" if it.get("before") and it.get("after") else (it.get("main") or "")
        L.append(f"{i}. {disp(it['title'])}" + (f" | {disp(chg)}" if chg else "") + (f" [{it['status']}]" if it.get("status") else ""))
        if it.get("note"):
            L.append(f"   · {disp(it['note'])}")
    L += ["", "※ 개정안·정부안은 국회 심의·입법 과정에서 바뀔 수 있어요", "자료: " + data.get("source_line", "국토교통부 등 정부 보도자료"), "",
          "원문 링크는 프로필 링크(블로그)에서 👆", "",
          "#데이터로보는재테크 #부동산정책 #이달의정책 #부동산 #내집마련"]
    return "\n".join(L)


def main():
    src, out = sys.argv[1], sys.argv[2]
    data = json.load(open(src, encoding="utf-8"))
    if len(data.get("items") or []) < 6:
        sys.exit("정책이 6개보다 적어 카드를 만들지 않습니다")
    os.makedirs(out, exist_ok=True)
    draw(data, os.path.join(out, "card.png"))
    open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(caption(data))
    json.dump(data, open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("이달의 정책 카드:", data["month"], len(data["items"][:9]), "개 →", out)


if __name__ == "__main__":
    main()
