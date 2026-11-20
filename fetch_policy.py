# -*- coding: utf-8 -*-
"""
국토교통부 보도자료에서 부동산 정책만 모아 site/policy/ 를 만든다. (인증키 필요 없음)

  - 주택토지 분야 보도자료 + 다른 분야라도 제목에 부동산 키워드가 있는 것
  - 상세 페이지에서 부제(요약 줄)·담당부서·PDF 링크를 읽음
  - 이전 결과는 배포된 policy.json(GitHub Pages)에서 읽어 이어 붙임 → 저장소 커밋 불필요
    (처음 실행이거나 읽기 실패면 --pages 만큼 거슬러 올라가 채움)

출력
  site/policy/policy.json   전체 목록(최근 365일)
  site/policy/index.html    정책 모아보기 페이지(주차별, 분류 필터)

사용
  python fetch_policy.py                # 평소(매일)
  python fetch_policy.py --pages 4      # 처음 한 번, 더 많이 채우기
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.request

BASE = "https://www.molit.go.kr/USR/NEWS/m_71/"
PAGES_URL = "https://gogokimbiz-spec.github.io/sudogwon-rt/policy/"
OUT_DIR = os.environ.get("POLICY_DIR") or os.path.join("site", "policy")
KST = dt.timezone(dt.timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

# 다른 분야 보도자료 중 이 단어가 제목에 있으면 포함
KEYWORDS = ["주택", "부동산", "공급", "분양", "청약", "전세", "월세", "임대", "재건축", "재개발",
            "정비사업", "토지거래", "규제지역", "투기과열", "조정대상", "대출", "신도시", "택지",
            "아파트", "주거", "집값", "매매", "입주", "미분양", "공시가격", "보유세", "양도세", "취득세"]

# 분류(첫 번째로 걸린 것 하나 + 추가 태그 여러 개 가능)
TAGS = [
    ("동정",      ["[장관동정]", "[차관동정]", "동정]"]),
    ("해명",      ["[해명]", "[설명]", "[참고]", "사실이 아닙", "확정된 바 없"]),
    ("공급",      ["공급", "착공", "인허가", "신도시", "택지", "공공주택", "모듈러", "입주", "만호", "만 호", "부지", "비축", "만 가구"]),
    ("청약·분양", ["청약", "분양", "당첨", "부정청약", "사전청약"]),
    ("전월세",    ["전세", "월세", "임대", "임차", "전세사기", "주거급여", "주거복지", "최저주거"]),
    ("정비사업",  ["재건축", "재개발", "정비사업", "리모델링", "도심복합", "노후계획", "재건축부담금"]),
    ("규제·금융", ["토지거래허가", "규제지역", "투기과열", "조정대상", "대출", "LTV", "DSR", "세제", "보유세",
                   "양도세", "취득세", "종부세", "공시가격", "위법", "불법", "부정", "적발", "기획조사"]),
    ("통계·동향", ["동향", "통계", "실태조사", "가격", "거래량", "미분양 현황", "주택시장"]),
    ("법령·제도", ["개정", "시행령", "시행규칙", "법률", "국무회의", "입법예고", "제도", "시행", "완화"]),
]
TAG_ORDER = [t for t, _ in TAGS] + ["기타"]


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa
            last = e
            time.sleep(2 + i * 3)
    raise last


def clean(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_list(page_html):
    """목록 페이지 → [{id, title, section, date}]"""
    items = []
    tbody = re.search(r"<tbody[^>]*>(.*?)</tbody>", page_html, re.S)
    if not tbody:
        return items
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbody.group(1), re.S):
        m_id = re.search(r"dtl\.jsp\?[^\"']*?id=(\d+)", tr)
        m_title = re.search(r'class="bd_title"[^>]*>(.*?)</td>', tr, re.S)
        m_sec = re.search(r'class="bd_field"[^>]*>(.*?)</td>', tr, re.S)
        m_date = re.search(r'class="bd_date"[^>]*>(.*?)</td>', tr, re.S)
        if not (m_id and m_title and m_date):
            continue
        items.append({
            "id": m_id.group(1),
            "title": clean(m_title.group(1)),
            "section": clean(m_sec.group(1)) if m_sec else "",
            "date": clean(m_date.group(1))[:10],
        })
    return items


def parse_detail(page_html):
    """상세 페이지 → {subs, dept, time, pdf, hwp}"""
    out = {"subs": [], "dept": "", "time": "", "pdf": "", "hwp": ""}
    m = re.search(r'<ul class="bd_view_ul_lst">(.*?)</ul>', page_html, re.S)
    if m:
        out["subs"] = [clean(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", m.group(1), re.S) if clean(x)]
    m = re.search(r'<ul class="bd_view_ul_info">(.*?)</ul>', page_html, re.S)
    if m:
        info = m.group(1)
        d = re.search(r"담당부서</strong>\s*<span>(.*?)</span>", info, re.S)
        t = re.search(r"등록일</strong>\s*<span>(.*?)</span>", info, re.S)
        out["dept"] = clean(d.group(1)) if d else ""
        out["time"] = clean(t.group(1)) if t else ""
        for href in re.findall(r'href="([^"]+)"', info):
            h = html.unescape(href)
            if h.startswith("/"):
                h = "https://www.molit.go.kr" + h
            low = h.lower()
            if not out["pdf"] and "dwn.jsp" in low and ".pdf" in low:
                out["pdf"] = h
            elif not out["hwp"] and "download" in low and (".hwp" in low):
                out["hwp"] = h
    return out


def tag_of(title, subs):
    """제목에서 먼저 찾고, 모자라면 부제에서 보충. 주제 태그는 최대 2개(+동정/해명)."""
    head = []
    if re.match(r"\s*\[\S*동정\]", title):
        head.append("동정")
    if re.match(r"\s*\[(해명|설명|참고)\]", title) or "확정된 바 없" in title:
        head.append("해명")
    topics = []
    for text in (title, " ".join(subs)):
        for name, words in TAGS:
            if name in ("동정", "해명") or name in topics:
                continue
            if name == "법령·제도" and text is not title:
                continue  # '시행' 같은 흔한 말은 제목에서만
            if any(w in text for w in words):
                topics.append(name)
        if len(topics) >= 2:
            break
    tags = head + topics[:2]
    return tags or ["기타"]


def is_realestate(item):
    if item["section"] == "주택토지":
        return True
    return any(k in item["title"] for k in KEYWORDS)


def load_prev():
    # 1) 로컬(직전 빌드 결과가 있으면) 2) 배포된 사이트
    local = os.path.join(OUT_DIR, "policy.json")
    if os.path.exists(local):
        try:
            with open(local, encoding="utf-8") as f:
                return json.load(f).get("items", [])
        except Exception:
            pass
    try:
        return json.loads(get(PAGES_URL + "policy.json?t=%d" % time.time(), tries=2)).get("items", [])
    except Exception as e:
        print("이전 policy.json 없음(처음 실행?):", e)
        return []


def week_start(date_str):
    d = dt.date.fromisoformat(date_str)
    return d - dt.timedelta(days=d.weekday())


def week_label(monday):
    # 그 주 목요일이 속한 달 기준 'M월 N주차'
    thu = monday + dt.timedelta(days=3)
    first = thu.replace(day=1)
    first_thu = first + dt.timedelta(days=(3 - first.weekday()) % 7)
    n = (thu - first_thu).days // 7 + 1
    return "%d월 %d주차" % (thu.month, n)


def collect(pages):
    found = {}
    # 주택토지 분야
    for p in range(1, pages + 1):
        url = BASE + "lst.jsp?search_section=p_sec_2&psize=30&lcmspage=%d" % p
        for it in parse_list(get(url)):
            found[it["id"]] = it
        time.sleep(1)
    # 전체(다른 분야 중 부동산 관련 제목)
    for p in range(1, pages + 1):
        url = BASE + "lst.jsp?psize=30&lcmspage=%d" % p
        for it in parse_list(get(url)):
            if it["id"] not in found and is_realestate(it):
                found[it["id"]] = it
        time.sleep(1)
    return list(found.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=0, help="목록 몇 페이지(30건씩) 볼지. 0=자동(처음 4, 평소 1)")
    ap.add_argument("--keep-days", type=int, default=365)
    args = ap.parse_args()

    prev = load_prev()
    by_id = {x["id"]: x for x in prev}
    pages = args.pages or (1 if prev else 4)
    print("이전 %d건, 목록 %d페이지 확인" % (len(prev), pages))

    try:
        listed = collect(pages)
    except Exception as e:
        print("목록 읽기 실패:", e)
        listed = []
        if not prev:
            sys.exit(0)  # 아무것도 없으면 조용히 끝(다른 단계에 영향 X)

    new = 0
    for it in listed:
        old = by_id.get(it["id"])
        if old and old.get("dept"):
            old.update({"title": it["title"], "section": it["section"], "date": it["date"]})
            continue
        try:
            det = parse_detail(get(BASE + "dtl.jsp?id=" + it["id"]))
            time.sleep(0.7)
        except Exception as e:
            print("상세 실패", it["id"], e)
            det = {"subs": [], "dept": "", "time": "", "pdf": "", "hwp": ""}
        it.update(det)
        it["url"] = BASE + "dtl.jsp?id=" + it["id"]
        by_id[it["id"]] = it
        new += 1

    cutoff = (dt.datetime.now(KST).date() - dt.timedelta(days=args.keep_days)).isoformat()
    items = [x for x in by_id.values() if x.get("date", "") >= cutoff]
    for x in items:
        x["tags"] = tag_of(x["title"], x.get("subs", []))
    items.sort(key=lambda x: (x.get("time") or x["date"], x["id"]), reverse=True)

    now = dt.datetime.now(KST)
    this_mon = now.date() - dt.timedelta(days=now.weekday())
    last_mon = this_mon - dt.timedelta(days=7)
    data = {
        "updated": now.strftime("%Y-%m-%d %H:%M"),
        "source": "국토교통부 보도자료 (공공누리 제1유형)",
        "this_week": {"start": this_mon.isoformat(), "label": week_label(this_mon),
                      "ids": [x["id"] for x in items if week_start(x["date"]) == this_mon]},
        "last_week": {"start": last_mon.isoformat(), "label": week_label(last_mon),
                      "ids": [x["id"] for x in items if week_start(x["date"]) == last_mon]},
        "items": items,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "policy.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    from build_policy_page import build_page
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_page(data))
    print("정책 %d건(새로 %d건) → %s" % (len(items), new, OUT_DIR))


if __name__ == "__main__":
    main()
