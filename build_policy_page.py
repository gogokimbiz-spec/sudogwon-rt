# -*- coding: utf-8 -*-
"""policy.json → site/policy/index.html (정책 모아보기 페이지). fetch_policy.py 가 불러 씀."""
import datetime as dt
import html
import json

TAG_COLOR = {
    "공급": "#2563eb", "청약·분양": "#7c3aed", "전월세": "#0d9488", "정비사업": "#c2410c",
    "규제·금융": "#dc2626", "통계·동향": "#4b5563", "법령·제도": "#0369a1", "해명": "#a16207",
    "동정": "#94a3b8", "기타": "#94a3b8",
}
SITE = "https://gogokimbiz-spec.github.io/sudogwon-rt/"


def _week_start(s):
    d = dt.date.fromisoformat(s)
    return d - dt.timedelta(days=d.weekday())


def _week_label(monday):
    thu = monday + dt.timedelta(days=3)
    first = thu.replace(day=1)
    first_thu = first + dt.timedelta(days=(3 - first.weekday()) % 7)
    return "%d월 %d주차" % (thu.month, (thu - first_thu).days // 7 + 1)


def _card(x):
    e = html.escape
    tags = "".join('<span class="tag" style="--c:%s">%s</span>' % (TAG_COLOR.get(t, "#94a3b8"), e(t))
                   for t in x.get("tags", []))
    subs = "".join("<li>%s</li>" % e(s) for s in x.get("subs", []))
    links = '<a href="%s" target="_blank" rel="noopener">원문 보기</a>' % e(x["url"])
    if x.get("pdf"):
        links += ' · <a href="%s" target="_blank" rel="noopener">PDF</a>' % e(x["pdf"])
    d = dt.date.fromisoformat(x["date"])
    wd = "월화수목금토일"[d.weekday()]
    return (
        '<article class="item" data-tags="%s">'
        '<div class="meta">%s</div>'
        '<div class="date">%d.%d(%s)%s</div>'
        '<h3>%s</h3>%s'
        '<div class="foot">%s<span class="links">%s</span></div>'
        "</article>"
    ) % (
        e(" ".join(x.get("tags", []))), tags, d.month, d.day, wd,
        (" · " + e(x["section"])) if x.get("section") and x["section"] != "주택토지" else "",
        e(x["title"]), ("<ul>%s</ul>" % subs) if subs else "",
        ('<span class="dept">%s</span>' % e(x["dept"])) if x.get("dept") else "<span></span>", links,
    )


def build_page(data):
    items = data["items"]
    weeks = {}
    for x in items:
        weeks.setdefault(_week_start(x["date"]), []).append(x)

    used = []
    for x in items:
        for t in x.get("tags", []):
            if t not in used:
                used.append(t)
    order = [t for t in TAG_COLOR if t in used]
    chips = '<button class="chip on" data-t="">전체</button>' + "".join(
        '<button class="chip" data-t="%s">%s</button>' % (html.escape(t), html.escape(t)) for t in order)

    # 이번 주(없으면 지난주) 요약
    tw = data.get("this_week", {})
    lw = data.get("last_week", {})
    head = tw if tw.get("ids") else lw
    ids = set(head.get("ids", []))
    main = [x for x in items if x["id"] in ids and not set(x.get("tags", [])) & {"동정"}]
    cnt = {}
    for x in main:
        for t in x.get("tags", []):
            cnt[t] = cnt.get(t, 0) + 1
    summary = ""
    if head.get("start"):
        summary = (
            '<section class="sum"><div class="sum-h">%s 부동산 정책 <b>%d건</b></div>'
            '<div class="sum-tags">%s</div><ol>%s</ol></section>'
        ) % (
            html.escape(head.get("label", "")), len(main),
            "".join('<span class="tag" style="--c:%s">%s %d</span>' % (TAG_COLOR.get(t, "#94a3b8"), t, n)
                    for t, n in sorted(cnt.items(), key=lambda kv: -kv[1])),
            "".join('<li><a href="#p%s">%s</a></li>' % (x["id"], html.escape(x["title"])) for x in main[:6]),
        )

    body = []
    for mon in sorted(weeks, reverse=True):
        sun = mon + dt.timedelta(days=6)
        body.append('<h2 class="wk">%s <small>%d.%d ~ %d.%d</small></h2>' % (
            _week_label(mon), mon.month, mon.day, sun.month, sun.day))
        for x in weeks[mon]:
            body.append(_card(x).replace('<article class="item"', '<article id="p%s" class="item"' % x["id"], 1))

    jsonld = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "부동산 정책 모아보기 – 국토교통부 보도자료",
        "url": SITE + "policy/", "dateModified": data["updated"].replace(" ", "T") + ":00+09:00",
    }
    return TEMPLATE.format(
        updated=html.escape(data["updated"]), chips=chips, summary=summary, body="\n".join(body),
        n=len(items), site=SITE, jsonld=json.dumps(jsonld, ensure_ascii=False),
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>부동산 정책 모아보기 – 주택공급·청약·전월세·규제 | 수도권 실거래 지도</title>
<meta name="description" content="국토교통부가 발표한 부동산·주택공급 정책을 주차별로 정리합니다. 공급, 청약, 전월세, 정비사업, 규제·금융 분류로 골라 보세요. 매일 자동 갱신.">
<link rel="canonical" href="{site}policy/">
<meta property="og:title" content="부동산 정책 모아보기">
<meta property="og:description" content="국토교통부 부동산·주택공급 정책을 주차별로 정리 (매일 갱신)">
<meta property="og:url" content="{site}policy/">
<script type="application/ld+json">{jsonld}</script>
<style>
:root{{--bg:#f6f7f9;--card:#fff;--fg:#111827;--sub:#6b7280;--line:#e5e7eb;--acc:#2563eb}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif}}
header{{background:#111827;color:#fff;padding:18px 16px 14px}}header a{{color:#cbd5e1;font-size:13px;text-decoration:none}}
h1{{margin:6px 0 2px;font-size:21px}}.upd{{color:#9ca3af;font-size:12px}}
main{{max-width:760px;margin:0 auto;padding:12px 12px 40px}}
.chips{{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0;display:flex;gap:6px;overflow-x:auto}}
.chip{{flex:none;border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 12px;font-size:13px;cursor:pointer}}
.chip.on{{background:#111827;color:#fff;border-color:#111827}}
.sum{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:4px 0 8px}}
.sum-h{{font-size:16px}}.sum-h b{{color:var(--acc)}}.sum-tags{{margin:6px 0}}.sum ol{{margin:6px 0 0;padding-left:20px}}.sum a{{color:var(--fg)}}
.wk{{font-size:16px;margin:22px 4px 8px}}.wk small{{color:var(--sub);font-weight:400;font-size:13px}}
.item{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:8px 0;scroll-margin-top:60px}}
.item h3{{font-size:16px;margin:4px 0 6px;line-height:1.45}}.item ul{{margin:0 0 6px;padding-left:18px;color:#374151;font-size:14px}}
.date{{color:var(--sub);font-size:12px;display:inline-block;margin-left:4px}}.meta{{display:inline}}
.tag{{display:inline-block;font-size:11.5px;font-weight:600;color:var(--c);background:color-mix(in srgb,var(--c) 11%,#fff);border-radius:6px;padding:1px 7px;margin-right:4px}}
.foot{{display:flex;justify-content:space-between;gap:8px;font-size:12.5px;color:var(--sub)}}.foot a{{color:var(--acc);text-decoration:none}}
.item.hide,.wk.hide{{display:none}}
footer{{color:var(--sub);font-size:12px;text-align:center;padding:20px 12px}}footer a{{color:var(--sub)}}
</style></head><body>
<header><a href="{site}">← 수도권 실거래 지도</a><h1>부동산 정책 모아보기</h1>
<div class="upd">국토교통부 보도자료 · {n}건 · {updated} 갱신</div></header>
<main>
<nav class="chips">{chips}</nav>
{summary}
{body}
</main>
<footer>출처: 국토교통부 보도자료(공공누리 제1유형). 제목·부제만 옮겼으며 자세한 내용은 원문을 확인하세요.<br>
<a href="{site}">실거래 지도</a> · <a href="https://sudogwon-rt.blogspot.com">블로그</a> · <a href="{site}privacy.html">개인정보처리방침</a></footer>
<script>
document.querySelectorAll('.chip').forEach(function(b){{b.onclick=function(){{
 document.querySelectorAll('.chip').forEach(function(c){{c.classList.toggle('on',c===b)}});
 var t=b.dataset.t, items=document.querySelectorAll('.item');
 items.forEach(function(it){{it.classList.toggle('hide',!!t&&(' '+it.dataset.tags+' ').indexOf(' '+t+' ')<0)}});
 document.querySelectorAll('.wk').forEach(function(h){{var n=h.nextElementSibling,any=false;
  while(n&&!n.classList.contains('wk')){{if(n.classList.contains('item')&&!n.classList.contains('hide'))any=true;n=n.nextElementSibling}}
  h.classList.toggle('hide',!any)}});
}}}});
</script>
</body></html>
"""
