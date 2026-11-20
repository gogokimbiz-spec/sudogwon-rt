# -*- coding: utf-8 -*-
"""
부동산 정책 한 장 카드 (1080×1350, 실거래 카드와 같은 모양)
  입력: site/policy/policy.json (fetch_policy.py 결과)
  출력: site/policy/week.png, site/policy/caption_week.txt, site/policy/card.json

  python make_cards_policy.py              # 지난주(월~일) – 월요일 게시용
  python make_cards_policy.py --week this  # 이번 주(오늘까지)
"""
import argparse
import datetime as dt
import json
import os
import re

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.environ.get("POLICY_DIR") or os.path.join("site", "policy")
KST = dt.timezone(dt.timedelta(hours=9))
W, H = 1080, 1350
BG = (52, 58, 66)
WHITE = (255, 255, 255)
SUB = (196, 201, 207)
DIM = (150, 157, 165)
LINE = (84, 92, 102)
YEL = (255, 196, 0)
CHIP = (232, 234, 236)
HANDLE = "@data_jaetech"
N_ROWS = 2  # 카드에 올릴 정책 수 (1~2)

# 카드에 올릴 우선순위 (동정은 제외)
SCORE = {"공급": 6, "규제·금융": 6, "청약·분양": 5, "정비사업": 5, "전월세": 5,
         "법령·제도": 4, "해명": 3, "통계·동향": 2, "기타": 1}
TAG_COLOR = {"공급": (37, 99, 235), "청약·분양": (124, 58, 237), "전월세": (13, 148, 136),
             "정비사업": (194, 65, 12), "규제·금융": (220, 38, 38), "통계·동향": (75, 85, 99),
             "법령·제도": (3, 105, 161), "해명": (161, 98, 7), "기타": (100, 116, 139)}


# ---------- 폰트 (make_cards.py 와 같은 위치 우선) ----------
def _font_path(weight):
    cands = [
        "/usr/share/fonts/noto-kr/NotoSansCJKkr-%s.otf" % weight,
        os.path.join("fonts", "NotoSansCJKkr-%s.otf" % weight),
        "/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc" % weight,
        "/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc" % ("Bold" if weight == "Black" else "Regular"),
        "C:/Windows/Fonts/malgunbd.ttf" if weight in ("Black", "Bold") else "C:/Windows/Fonts/malgun.ttf",
    ]
    for p in cands:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("한글 폰트 없음: " + weight)


_FC = {}


def F(weight, size):
    key = (weight, size)
    if key not in _FC:
        p = _font_path(weight)
        _FC[key] = ImageFont.truetype(p, size, index=1 if p.endswith(".ttc") else 0)  # ttc 1 = KR
    return _FC[key]


def tw(d, text, font):
    return d.textlength(text, font=font)


def fit(d, text, font, maxw):
    """maxw 안에 들어가게 자르고 … 붙임"""
    if tw(d, text, font) <= maxw:
        return text
    while text and tw(d, text + "…", font) > maxw:
        text = text[:-1]
    return text.rstrip(" ,·…") + "…"


# ---------- 문장 다듬기 ----------
# 저장소 폰트(서브셋)에 없는 글자 바꾸기 (2026-11-20 확인: α 全 ◈ 없음)
SUBST = {"全": "전", "α": "a", "β": "b", "◈": "", "◆": "", "■": "", "□": "", "▲": "↑", "▼": "↓", "\u00a0": " "}


def disp(t):
    for a, b in SUBST.items():
        t = t.replace(a, b)
    return t


def short_title(t):
    t = disp(t)
    t = re.sub(r"^\s*\[[^\]]*\]\s*", "", t)               # [장관동정] 등 머리말
    t = re.sub(r"^\s*<[^>]*>\s*", "", t)                   # <주택 신속공급 방안(8.13) 후속조치>
    t = t.replace("「", "").replace("」", "").replace("“", "").replace("”", "").replace('"', "")
    t = re.sub(r"\s*·{2,}\s*", " · ", t)
    t = re.sub(r"\s*…\s*", " · ", t)
    return re.sub(r"\s+", " ", t).strip(" .")


def best_sub(subs):
    good = [s for s in subs if not re.match(r"\s*[【◈※]", s)]
    good = [re.sub(r"^\s*[-·◦○●▶▷]\s*", "", s).replace("「", "").replace("」", "").strip() for s in good]
    good = [s for s in good if len(s) >= 6]
    if not good:
        return ""
    return good[0]


def headline(d, title, font, maxw):
    """제목이 한 줄에 안 들어가면 · , 사이 앞부분만(뜻이 남는 길이일 때)"""
    t = short_title(title)
    if tw(d, t, font) <= maxw:
        return t, ""
    parts = [p for p in re.split(r"\s*(?:,|…)\s+|\s+·\s*|\s*·\s+", t) if p]
    if len(parts) > 1:
        ok = [p for p in parts if len(p) >= 6 and tw(d, p, font) <= maxw]
        if parts[0] in ok:
            best = parts[0]
        elif ok:  # 앞부분이 길면 숫자 있는 쪽(핵심 결과)을 제목으로
            best = ([p for p in ok if re.search(r"\d", p)] or ok)[0]
        else:
            best = None
        if best:
            return best, " · ".join(p for p in parts if p != best)
    return fit(d, t, font, maxw), ""


def pick(items, start, end):
    cand = [x for x in items if start.isoformat() <= x["date"] <= end.isoformat() and "동정" not in x.get("tags", [])]
    for x in cand:
        tags = x.get("tags") or ["기타"]
        x["_score"] = max(SCORE.get(t, 1) for t in tags) + (1 if re.search(r"\d", " ".join(x.get("subs", []))) else 0) \
            + (2 if len(x.get("subs", [])) >= 2 else 0) \
            - (2 if x.get("section") not in ("주택토지", "일반", "") else 0)
    cand.sort(key=lambda x: x["date"], reverse=True)
    cand.sort(key=lambda x: -x["_score"])
    return cand


# ---------- 그리기 ----------
# ---------- 색 테마 ----------
THEMES = {
    # 밝은 배경 + 흰 패널 (기본)
    "light": dict(bg=(241, 243, 246), head_bg=(23, 32, 51), head_fg=(255, 255, 255), head_sub=(203, 213, 225),
                  panel=(255, 255, 255), panel_line=(226, 232, 240), title=(17, 24, 39), text=(51, 65, 85),
                  dim=(100, 116, 139), accent=(255, 196, 0), accent_fg=(17, 24, 39), bullet=(234, 88, 12),
                  chip=(241, 245, 249), wm=(15, 23, 42, 10), box_line=(23, 32, 51), box_fg=(17, 24, 39),
                  box_hi=(234, 88, 12), foot=(100, 116, 139)),
    # 네이비 배경 + 흰 패널
    "navy": dict(bg=(23, 37, 84), head_bg=(23, 37, 84), head_fg=(255, 255, 255), head_sub=(191, 219, 254),
                 panel=(255, 255, 255), panel_line=(255, 255, 255), title=(15, 23, 42), text=(51, 65, 85),
                 dim=(100, 116, 139), accent=(255, 196, 0), accent_fg=(15, 23, 42), bullet=(37, 99, 235),
                 chip=(239, 246, 255), wm=(255, 255, 255, 12), box_line=(255, 196, 0), box_fg=(255, 255, 255),
                 box_hi=(255, 196, 0), foot=(191, 219, 254)),
    # 지금 색(어두운 회색) + 글자 대비만 높임
    "dark": dict(bg=(52, 58, 66), head_bg=(52, 58, 66), head_fg=(255, 255, 255), head_sub=(226, 232, 240),
                 panel=(38, 43, 50), panel_line=(38, 43, 50), title=(255, 255, 255), text=(236, 239, 243),
                 dim=(170, 177, 186), accent=(255, 196, 0), accent_fg=(20, 20, 20), bullet=(255, 196, 0),
                 chip=(232, 234, 236), wm=(255, 255, 255, 9), box_line=(255, 196, 0), box_fg=(255, 255, 255),
                 box_hi=(255, 196, 0), foot=(170, 177, 186)),
}


def watermark(img, color):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    f = F("Black", 92)
    for cx, cy in ((330, 520), (800, 760), (330, 1000)):
        t = Image.new("RGBA", (760, 140), (0, 0, 0, 0))
        ImageDraw.Draw(t).text((10, 10), HANDLE, font=f, fill=color)
        t = t.rotate(28, expand=True)
        layer.alpha_composite(t, (cx - t.width // 2, cy - t.height // 2))
    img.alpha_composite(layer)


def chip(d, x, y, text, font, bg, fg, padx=12, h=44, r=6):
    w = tw(d, text, font) + padx * 2
    d.rounded_rectangle((x, y, x + w, y + h), r, fill=bg)
    d.text((x + padx, y + h / 2), text, font=font, fill=fg, anchor="mm" if False else "lm")
    return x + w


def wrap(d, text, font, maxw):
    """띄어쓰기 기준 줄바꿈(한 단어가 너무 길면 글자 단위)"""
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
            lines.append(cur[:k])
            cur = cur[k:]
    if cur:
        lines.append(cur)
    return lines


def summary_lines(x):
    """요약 줄: 보도자료 부제(최대 3)"""
    out = []
    for s in x.get("subs", []):
        if re.match(r"\s*[【※]", s):
            continue
        s = disp(re.sub(r"^\s*[-·◦○●▶▷◈]\s*", "", s).replace("「", "").replace("」", "")).strip()
        if len(s) >= 6:
            out.append(s)
    return out[:3]


PAD = 34  # 패널 안쪽 여백


def layout(d, rows, sizes, maxw):
    ts, ss, max_sub_lines, max_subs = sizes
    tf, sf = F("Black", ts), F("Medium", ss)
    blocks, total = [], 0
    for x in rows:
        tl = [l.strip(" ·") for l in wrap(d, short_title(x["title"]), tf, maxw)]
        tl = [l for l in tl if l]
        if len(tl) > 2:
            tl = tl[:2]
            tl[1] = fit(d, tl[1] + "…", tf, maxw)
        subs = []
        for s in summary_lines(x)[:max_subs]:
            sl = wrap(d, s, sf, maxw - 34)
            if len(sl) > max_sub_lines:
                sl = sl[:max_sub_lines]
                sl[-1] = fit(d, sl[-1] + " …", sf, maxw - 34)
            subs.append(sl)
        h = PAD + 50 + 16 + len(tl) * int(ts * 1.3) + 12 + sum(len(sl) for sl in subs) * int(ss * 1.5) \
            + len(subs) * 8 + PAD - 8
        blocks.append((tl, subs, h))
        total += h
    total += (len(rows) - 1) * 26
    return blocks, total


def draw_card(rows, total, label, rng, path, theme="light"):
    T = THEMES[theme]
    img = Image.new("RGBA", (W, H), T["bg"] + (255,))
    d = ImageDraw.Draw(img)
    L, R = 40, W - 40

    # 머리
    d.rectangle((0, 0, W, 262), fill=T["head_bg"])
    chip(d, 60, 44, "%s · %s" % (label, rng), F("Bold", 30), T["accent"], T["accent_fg"], padx=18, h=52, r=8)
    d.text((58, 104), "부동산 정책 브리핑", font=F("Black", 74), fill=T["head_fg"])
    d.text((62, 204), "꼭 알아둘 정책 %d가지 · 국토교통부 발표 %d건 중" % (len(rows), total),
           font=F("Medium", 31), fill=T["head_sub"])
    if theme == "dark":
        d.rectangle((L, 258, R, 264), fill=(255, 255, 255))
    watermark(img, T["wm"])
    d = ImageDraw.Draw(img)

    top, bottom = 286, 1106
    maxw = R - L - PAD * 2
    tries = [(58, 37, 3, 3), (54, 35, 3, 3), (50, 34, 2, 3), (46, 32, 2, 3), (46, 32, 2, 2), (44, 30, 1, 3)] \
        if len(rows) == 1 else \
        [(50, 34, 2, 3), (48, 33, 2, 3), (46, 32, 2, 3), (48, 33, 2, 2), (46, 32, 2, 2), (44, 30, 1, 3), (42, 29, 1, 2)]
    for sizes in tries:
        blocks, need = layout(d, rows, sizes, maxw)
        if need <= bottom - top:
            break
    ts, ss = sizes[0], sizes[1]
    tf, sf = F("Black", ts), F("Medium", ss)
    y = top + max(0, min(20, (bottom - top - need) / 2))

    for i, (x, (tl, subs, h)) in enumerate(zip(rows, blocks)):
        # 남는 공간은 패널을 조금 키워서 나눠 씀
        extra = max(0, (bottom - top - need) - 40) / len(rows) if len(rows) else 0
        ph = h + min(extra, 120)
        d.rounded_rectangle((L, y, R, y + ph), 22, fill=T["panel"], outline=T["panel_line"], width=2)
        cx, cy = L + PAD, y + PAD
        tag = next((t for t in x.get("tags", []) if t not in ("해명",)), (x.get("tags") or ["기타"])[0])
        dd = dt.date.fromisoformat(x["date"])
        nx = chip(d, cx, cy, str(i + 1), F("Black", 30), T["accent"], T["accent_fg"], padx=15, h=46, r=8)
        nx = chip(d, nx + 10, cy, tag, F("Bold", 28), T["chip"], TAG_COLOR.get(tag, (60, 60, 60)), padx=14, h=46, r=8)
        d.text((R - PAD, cy + 23), "%d.%d(%s) 발표" % (dd.month, dd.day, "월화수목금토일"[dd.weekday()]),
               font=F("Medium", 28), fill=T["dim"], anchor="rm")
        yy = cy + 50 + 16 + (min(extra, 120) / 3)
        for t in tl:
            d.text((cx, yy), t, font=tf, fill=T["title"])
            yy += int(ts * 1.3)
        yy += 12
        for sl in subs:
            d.ellipse((cx + 4, yy + ss * 0.55, cx + 16, yy + ss * 0.55 + 12), fill=T["bullet"])
            for s in sl:
                d.text((cx + 32, yy), s, font=sf, fill=T["text"])
                yy += int(ss * 1.5)
            yy += 8
        y += ph + 26

    # 아래쪽
    more = total - len(rows)
    by = 1128
    d.rounded_rectangle((L, by, R, by + 74), 12, outline=T["box_line"], width=3)
    if more > 0:
        msg = [("이 밖에도 ", T["box_fg"]), ("정책 %d건" % more, T["box_hi"]), (" 더 있어요", T["box_fg"])]
    else:
        msg = [("원문·자료는 ", T["box_fg"]), ("국토교통부 보도자료", T["box_hi"]), ("에서", T["box_fg"])]
    f = F("Bold", 36)
    x0 = W / 2 - sum(tw(d, t, f) for t, _ in msg) / 2
    for t, c in msg:
        d.text((x0, by + 37), t, font=f, fill=c, anchor="lm")
        x0 += tw(d, t, f)
    d.rounded_rectangle((L, 1218, R, 1290), 12, fill=T["accent"])
    d.text((W / 2, 1254), "전체 정책·원문 보기 → 프로필 링크", font=F("Bold", 36), fill=T["accent_fg"], anchor="mm")
    d.text((L + 4, 1321), "데이터로 보는 재테크 · 자료 국토교통부 보도자료", font=F("Regular", 22), fill=T["foot"], anchor="lm")
    hx = R - tw(d, HANDLE, F("Black", 34)) - 36
    d.rounded_rectangle((hx, 1300, R, 1342), 8, fill=T["accent"])
    d.text((hx + 18, 1321), HANDLE, font=F("Black", 34), fill=T["accent_fg"], anchor="lm")

    img.convert("RGB").save(path, optimize=True)


def caption(rows, total, label, rng):
    """인스타·스레드 문구 (인스타는 링크가 안 눌려서 주소는 넣지 않음)"""
    lines = ["📢 이번 주 꼭 알아둘 부동산 정책 | %s (%s)" % (label, rng), ""]
    for i, x in enumerate(rows, 1):
        tag = next((t for t in x.get("tags", []) if t != "해명"), (x.get("tags") or ["기타"])[0])
        lines.append("%d. [%s] %s" % (i, tag, short_title(x["title"])))
        for s in summary_lines(x):
            lines.append("   · " + s)
        lines.append("")
    if total > len(rows):
        lines.append("이 밖에도 이번 주 정책 %d건 더 발표됐어요" % (total - len(rows)))
    lines += ["자료: 국토교통부 보도자료", "", "원문·전체 정책은 프로필 링크(블로그)에서 👆", "",
              "#데이터로보는재테크 #부동산정책 #주택공급 #부동산 #내집마련"]
    return "\n".join(lines)


def week_label(monday):
    thu = monday + dt.timedelta(days=3)
    first = thu.replace(day=1)
    first_thu = first + dt.timedelta(days=(3 - first.weekday()) % 7)
    return "%d월 %d주차" % (thu.month, (thu - first_thu).days // 7 + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", choices=["last", "this"], default="last")
    ap.add_argument("--today", help="YYYY-MM-DD (시험용)")
    ap.add_argument("--theme", default="light", choices=list(THEMES), help="색 (light/navy/dark)")
    ap.add_argument("--n", type=int, default=N_ROWS, choices=[1, 2], help="카드에 올릴 정책 수")
    a = ap.parse_args()

    pj = os.path.join(OUT_DIR, "policy.json")
    if not os.path.exists(pj):
        print("정책 카드: policy.json 이 없어 건너뜀 (수집 실패)")
        return
    with open(pj, encoding="utf-8") as f:
        data = json.load(f)
    today = dt.date.fromisoformat(a.today) if a.today else dt.datetime.now(KST).date()
    mon = today - dt.timedelta(days=today.weekday())
    if a.week == "last":
        mon -= dt.timedelta(days=7)
    end = mon + dt.timedelta(days=6)
    if a.week == "this":
        end = min(end, today)   # 이번 주는 오늘까지

    cand = pick(data["items"], mon, end)
    if not cand:
        print("정책 카드: 해당 주 발표 없음 → 건너뜀")
        return
    rows = cand[:a.n]
    label, rng = week_label(mon), "%d.%d~%d.%d" % (mon.month, mon.day, end.month, end.day)

    os.makedirs(OUT_DIR, exist_ok=True)
    draw_card(rows, len(cand), label, rng, os.path.join(OUT_DIR, "week.png"), a.theme)
    with open(os.path.join(OUT_DIR, "caption_week.txt"), "w", encoding="utf-8") as f:
        f.write(caption(rows, len(cand), label, rng))
    with open(os.path.join(OUT_DIR, "card.json"), "w", encoding="utf-8") as f:
        keep = ("id", "title", "date", "dept", "url", "pdf", "tags", "section")
        json.dump({"key": mon.isoformat() + "_policy", "day": today.isoformat(), "week_start": mon.isoformat(),
                   "label": label, "range": rng, "total": len(cand),
                   "rows": [dict({k: x.get(k) for k in keep}, short=short_title(x["title"]), summary=summary_lines(x),
                                 tag=next((t for t in x.get("tags", []) if t != "해명"), (x.get("tags") or ["기타"])[0]))
                            for x in rows],
                   "others": [{k: x.get(k) for k in ("id", "title", "date", "url", "tags")} for x in cand[len(rows):]]},
                  f, ensure_ascii=False, indent=1)
    print("정책 카드: %s %d건 중 %d건 → %s/week.png" % (label, len(cand), len(rows), OUT_DIR))


if __name__ == "__main__":
    main()
