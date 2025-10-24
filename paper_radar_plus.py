#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaperRadar_plus (priority edition)
- 优先：顶会/顶刊（OpenAlex）+ OpenReview 的“新作”
- 其次：arXiv 预印本“新作”补齐
- 仍不足：允许从近 N 天“已推送历史”里重复补齐，并在标题后提示首次推送日期
- 精准：OpenAlex 以 Source ID 过滤（会议=proceedings-article，期刊=journal-article）
- 稳定：arXiv 空页容错；非 arXiv 源走“领域门槛”过滤（point cloud / LiDAR / CAD 等）
- 灵活：每一类可自带 arXiv 查询，作为抓取与回溯补齐的依据
"""
import os, sys, json, argparse, datetime as dt, re, pathlib, time
import yaml, requests
import arxiv  # pip install arxiv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from email.mime.application import MIMEApplication
# feedparser 仅在启用 RSS 时才需要；见 fetch_rss 内的延迟导入

# ------------------ I/O & Utils ------------------
def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)

def load_cache(cache_path: pathlib.Path):
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            return {"seen": {}}
    return {"seen": {}}

def save_cache(cache, cache_path: pathlib.Path):
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

def sanitize(s: str, n=400):
    s = re.sub(r"\s+", " ", s.strip())
    s = re.sub(r"\[[0-9]+\]", "", s)
    s = re.sub(r"\((?:arXiv|doi):[^)]+\)", "", s)
    return (s[:n] + "…") if len(s) > n else s

def split_sentences(text: str):
    SPLIT = re.compile(r'(?<=[.!?。！？])\s+')
    text = re.sub(r'\s+', ' ', text.strip())
    sents = SPLIT.split(text)
    return [s.strip() for s in sents if len(s.strip()) > 20]

def score_sentence(sent: str, domain_terms):
    base = 1.0; kw = 0.0; bonus = 0.0
    for w, wgt in domain_terms.items():
        if re.search(rf'(?i)\b{re.escape(w)}\b', sent):
            kw += wgt
    if re.search(r'(?i)\b(we|our|this paper|propos|present|introduce)\b', sent): bonus += 0.3
    if re.search(r'(?i)\b(state-of-the-art|SOTA|significant|substantial|improv)\b', sent): bonus += 0.2
    if len(sent) > 300: bonus -= 0.1
    return base + kw + bonus

def summarize_abstract(abstract: str, hl_words, max_sentences=3):
    sents = split_sentences(abstract)
    if not sents: return sanitize(abstract, 200)
    domain = {w: 0.6 for w in hl_words}
    scored = [(score_sentence(s, domain), i, s) for i, s in enumerate(sents)]
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    out = []
    for sc, i, s in scored:
        if any(len(set(s.split()) & set(t.split())) > 10 for t in out):
            continue
        out.append(sanitize(s, 350))
        if len(out) >= max_sentences: break
    return " ".join(out)

def highlight(text: str, words):
    if not words: return text
    for w in words:
        try:
            text = re.sub(rf"(?i)\b{re.escape(w)}\b", lambda m: f"**{m.group(0)}**", text)
        except re.error:
            pass
    return text

def score_paper(item, hl_words):
    score = 0.0
    text = (item.get("title","") + " " + item.get("summary","")).lower()
    for w in hl_words:
        if w.lower() in text: score += 1.0
    cats = " ".join(item.get("categories", [])).lower()
    if "cs.cv" in cats: score += 0.4
    if "cs.ro" in cats: score += 0.3
    if "cs.gr" in cats: score += 0.2
    if "eess.iv" in cats: score += 0.2
    if re.search(r'(?i)\b(point cloud|3d)\b', item.get("title","")): score += 0.5
    try:
        days = (dt.datetime.utcnow() - dt.datetime.fromisoformat(item["published"])).days
        score += max(0.0, 3.0 - 0.2 * days)
    except Exception:
        pass
    return score

def join_and_dedup(lists):
    m = {}
    for lst in lists:
        for x in lst:
            k = x.get("id") or x.get("entry_url") or x.get("title")
            m[k] = x
    return list(m.values())

def dedup_by_id(lst):
    seen=set(); out=[]
    for it in lst:
        k = it.get("id") or it.get("entry_url") or it.get("title")
        if k in seen: continue
        seen.add(k); out.append(it)
    return out

# ------------------ Domain Guard & helpers ------------------
DOMAIN_GUARD = [
    "point cloud", "lidar", "LiDAR",
    "scan-to-cad", "CAD", "metrology", "tolerance", "gd&t",
    "registration", "ICP", "deviation"
]
def passes_domain_guard(item):
    text = (item.get("title","") + " " + item.get("summary","")).lower()
    return any(k.lower() in text for k in DOMAIN_GUARD)

def assign_best_category(item, cats_cfg):
    best_idx, best_score = 0, -1e9
    for idx, cat in enumerate(cats_cfg):
        sc = score_paper(item, cat.get("highlight", []))
        if sc > best_score:
            best_idx, best_score = idx, sc
    return best_idx, best_score

def add_src(items, src):
    for it in items: it["src"] = src
    return items

# ------------------ Rendering ------------------
def as_markdown(today_str, groups, cfg):
    lines = []
    lines.append(f"# PaperRadar 每日简报 · {today_str}\n")
    lines.append("> 来源：顶会/顶刊（OpenAlex）/ OpenReview 优先；arXiv 补齐；必要时重复补齐会提示首次推送日期。\n")
    for cat in groups:
        name = cat["name"]; items = cat["items"]; hl = cat.get("highlight", [])
        lines.append(f"\n## {name}\n")
        if not items:
            lines.append("_（暂无匹配）_"); continue
        for it in items:
            title = sanitize(it.get("title",""), 300); title_hl = highlight(title, hl)
            authors = ", ".join(it.get("authors",[])[:4]) + (" et al." if len(it.get("authors",[]))>4 else "")
            date_str = (it.get("published") or "")[:10]; cats = ", ".join(it.get("categories", []))
            ai_sum = summarize_abstract(it.get("summary",""), hl, max_sentences=int(cfg.get("summary_sentences", 3)))
            repeat_note = ""
            if it.get("repeat_from"):
                tmpl = cfg.get("priority",{}).get("repeat_label","（重复推荐：首次推送 {date}）")
                repeat_note = " " + tmpl.format(date=it["repeat_from"])
            lines.append(f"- **[{title_hl}]({it.get('entry_url','')})**{repeat_note}  \n  {authors} · {date_str} · _{cats}_  \n  **AI 简报**：{ai_sum}\n")
    return "\n".join(lines)

def items_to_html(items):
    rows = []
    for it in items:
        title = sanitize(it.get("title",""), 260)
        url = it.get("entry_url","")
        date_str = (it.get("published") or "")[:10]
        authors = ", ".join(it.get("authors",[])[:4]) + (" et al." if len(it.get("authors",[]))>4 else "")
        venue = ", ".join(it.get("categories", [])) or it.get("src","")
        repeat_note = f' <em>（首次推送 {it.get("repeat_from")}）</em>' if it.get("repeat_from") else ""
        rows.append(f'<tr><td><a href="{url}">{title}</a>{repeat_note}<br>'
                    f'<small>{authors} · {date_str} · <em>{venue}</em></small></td></tr>')
    if not rows:
        return "<p>（暂无条目）</p>"
    return ('<table border="0" cellspacing="0" cellpadding="6" style="font-family:Arial,Helvetica,sans-serif;'
            'font-size:14px;line-height:1.5;">' + "".join(rows) + "</table>")

def items_to_text(items):
    lines = []
    for it in items:
      title = sanitize(it.get("title",""), 260)
      url = it.get("entry_url","")
      date_str = (it.get("published") or "")[:10]
      authors = ", ".join(it.get("authors",[])[:4]) + (" et al." if len(it.get("authors",[]))>4 else "")
      venue = ", ".join(it.get("categories", [])) or it.get("src","")
      note = f'（首次推送 {it.get("repeat_from")}）' if it.get("repeat_from") else ""
      lines.append(f"- {title}{note}\n  {authors} · {date_str} · {venue}\n  {url}")
    return "\n".join(lines) if lines else "（暂无条目）"

def _src_counts(items):
    from collections import Counter
    c = Counter(it.get("src","") for it in items)
    return dict(c)

def normalize_src(items):
    for it in items:
        s = (it.get("src") or "").lower()
        if s: 
            continue
        url = (it.get("entry_url") or "").lower()
        cats = " ".join(it.get("categories", [])).lower()
        if "arxiv.org" in url:
            it["src"] = "arxiv"
        elif "openreview.net" in url:
            it["src"] = "openreview"
        elif "openalex.org" in url or cats.startswith("https://openalex.org/s"):
            # 来自 OpenAlex，但没打上 journal/conf 标签
            it["src"] = "openalex"
        else:
            it["src"] = "misc"

def send_digest_email(cfg, today_str, picked_items, digest_path):
    e = (cfg or {}).get("email") or {}
    if not e.get("enabled"):
        return False, "email.disabled"

    # 过滤选择：仅顶刊 or 顶会并入 or 全部
    items = picked_items
    if e.get("only_journals", True):
        journals = [it for it in items if it.get("src") == "openalex_journal"]
        if e.get("include_conferences"):
            confs = [it for it in items if it.get("src") == "openalex_conf"]
            journals += confs
        items = journals

    if len(items) < int(e.get("min_count", 1)):
        return False, f"email.skipped: count<{e.get('min_count',1)}"

    # 构造主题与正文
    subject_tpl = e.get("subject_tpl", "PaperRadar · {date} · {count} 篇")
    subject = subject_tpl.format(date=today_str, count=len(items))
    body_format = (e.get("body_format","html") or "html").lower()
    if body_format == "text":
        body_content = items_to_text(items)
        mime_main = MIMEMultipart()
        mime_main.attach(MIMEText(body_content, "plain", "utf-8"))
    else:
        body_content = items_to_html(items)
        mime_main = MIMEMultipart("alternative")
        mime_main.attach(MIMEText(body_content, "html", "utf-8"))

    # 附件（可选）
    if e.get("attach_digest") and digest_path and os.path.exists(digest_path):
        with open(digest_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(digest_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(digest_path)}"'
            mime_main.attach(part)

    # 头部
    from_addr = e.get("from") or e.get("smtp",{}).get("username")
    to_list = e.get("to") or []
    if not from_addr or not to_list:
        return False, "email.missing.from_or_to"
    mime_main['From'] = formataddr(("PaperRadar Bot", from_addr))
    mime_main['To'] = ", ".join(to_list)
    mime_main['Subject'] = subject

    # SMTP
    smtp_cfg = e.get("smtp") or {}
    host = smtp_cfg.get("host"); port = int(smtp_cfg.get("port", 587))
    username = smtp_cfg.get("username"); password = smtp_cfg.get("password")
    use_ssl = bool(smtp_cfg.get("ssl", False)); use_starttls = bool(smtp_cfg.get("starttls", True))

    if not host or not username or not password:
        return False, "email.missing.smtp_credentials"

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
        server.ehlo()
        if (not use_ssl) and use_starttls:
            server.starttls()
            server.ehlo()
        server.login(username, password)
        server.sendmail(from_addr, to_list, mime_main.as_string())
        server.quit()
        return True, f"email.sent: {len(items)} items to {len(to_list)} recipients"
    except Exception as ex:
        return False, f"email.error: {ex}"

# ------------------ Sources ------------------
# arXiv with empty-page tolerance
def fetch_arxiv(queries, max_results, since_days):
    client = arxiv.Client(page_size=50, delay_seconds=3, num_retries=2)  # smaller page size is more robust
    min_date = dt.datetime.utcnow() - dt.timedelta(days=since_days)
    out = []
    if not queries:
        return out
    for q in queries:
        search = arxiv.Search(
            query=q,
            max_results=min(max_results, 150),
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        try:
            for r in client.results(search):
                pub = r.published.replace(tzinfo=None)
                if pub < min_date: continue
                out.append({
                    "id": r.entry_id, "title": r.title,
                    "authors": [a.name for a in r.authors], "summary": r.summary,
                    "categories": getattr(r, "categories", []),
                    "published": pub.isoformat(),
                    "updated": r.updated.replace(tzinfo=None).isoformat(),
                    "pdf_url": r.pdf_url, "entry_url": r.entry_id,
                })
        except arxiv.UnexpectedEmptyPageError:
            # No more pages for this query; continue with next query
            continue
    return out

# OpenAlex: resolve source ids and fetch works
def resolve_openalex_sources(names=None, issns=None, cache_path="source_cache.json"):
    """
    names: 会议/期刊名称列表（模糊搜索 Source）
    issns: 期刊 ISSN 列表（直接命中 Source）
    返回: { display_key: "https://openalex.org/Sxxxx" }
    """
    cache = {}
    if os.path.exists(cache_path):
        try:
            cache = json.load(open(cache_path, "r", encoding="utf-8"))
        except Exception:
            cache = {}
    out = dict(cache)

    # ISSN → Source
    for s in (issns or []):
        key = f"issn:{s}"
        if key in out: continue
        url = f"https://api.openalex.org/sources/issn:{s}"
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            out[key] = r.json().get("id")

    # name → Source（most relevant 1)
    for name in (names or []):
        key = f"name:{name}"
        if key in out: continue
        url = "https://api.openalex.org/sources"
        params = {"search": name, "per_page": 1, "sort": "relevance_score:desc"}
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                out[key] = results[0].get("id")

    try:
        json.dump(out, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass
    return out

def fetch_openalex_by_source_ids(source_ids, since_days, work_type="journal-article", max_results=200):
    """
    work_type: 'journal-article'（期刊）或 'proceedings-article'（会议）
    """
    base = "https://api.openalex.org/works"
    per_page = 25
    min_date = (dt.datetime.utcnow() - dt.timedelta(days=since_days)).date().isoformat()
    out = []
    for sid in source_ids:
        if not sid: continue
        page, fetched = 1, 0
        while fetched < max_results:
            params = {
                "filter": f"from_publication_date:{min_date},type:{work_type},primary_location.source.id:{sid}",
                "per_page": per_page, "page": page, "sort": "publication_date:desc",
            }
            r = requests.get(base, params=params, timeout=20)
            if r.status_code != 200: break
            results = r.json().get("results", [])
            if not results: break
            for w in results:
                title = w.get("title","")
                authors = [a["author"]["display_name"] for a in w.get("authorships",[]) if a.get("author")]
                # reconstruct abstract from inverted index
                abstr = ""
                inv = w.get("abstract_inverted_index")
                if inv:
                    size = max((max(vs) for vs in inv.values()), default=-1) + 1
                    arr = [""]*size
                    for term, pos_list in inv.items():
                        for pos in pos_list:
                            arr[pos] = term
                    abstr = " ".join(arr)
                pub = (w.get("publication_date") or "")[:10]
                entry_url = w.get("primary_location",{}).get("landing_page_url") or w.get("open_access",{}).get("oa_url") or w.get("id")
                out.append({
                    "id": w.get("id") or title, "title": title, "authors": authors, "summary": abstr or "",
                    "categories": [sid], "published": pub or dt.datetime.utcnow().date().isoformat(),
                    "updated": pub or dt.datetime.utcnow().date().isoformat(),
                    "pdf_url": "", "entry_url": entry_url,
                })
                fetched += 1
                if fetched >= max_results: break
            if len(results) < per_page: break
            page += 1; time.sleep(0.5)
    return out

# OpenReview: recent notes for target venues
def fetch_openreview(venues, since_days, max_results=200):
    base = "https://api.openreview.net/notes"
    min_ms = int((dt.datetime.utcnow() - dt.timedelta(days=since_days)).timestamp()*1000)
    out = []
    for v in venues or []:
        params = {"details":"replies", "limit": max_results, "offset":0, "select":"id,content,tcdate", "term": v}
        try:
            r = requests.get(base, params=params, timeout=20)
            if r.status_code != 200: continue
            for n in r.json().get("notes", []):
                ts = int(n.get("tcdate",0))
                if ts < min_ms: continue
                c = n.get("content",{})
                title = c.get("title","")
                authors = c.get("authors",[]) or c.get("authorids",[]) or []
                abstr = c.get("abstract","") or c.get("tl;dr","") or ""
                t = dt.datetime.utcfromtimestamp(ts/1000).isoformat()
                out.append({
                    "id": f"openreview:{n.get('id')}", "title": title,
                    "authors": authors if isinstance(authors,list) else [authors],
                    "summary": abstr, "categories": [v], "published": t, "updated": t,
                    "pdf_url": c.get("pdf",""), "entry_url": f"https://openreview.net/forum?id={n.get('id')}",
                })
        except Exception:
            continue
    return out

# RSS (optional; lazy import)
def fetch_rss(urls, since_days, max_results=50):
    try:
        import feedparser  # only import when needed
    except Exception:
        return []
    min_dt = dt.datetime.utcnow() - dt.timedelta(days=since_days)
    out = []
    for url in urls or []:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:max_results]:
                title = e.get("title",""); abstr = e.get("summary","") or ""
                pub_parsed = e.get("published_parsed") or e.get("updated_parsed")
                pub = dt.datetime(*pub_parsed[:6]) if pub_parsed else dt.datetime.utcnow()
                if pub < min_dt: continue
                link = e.get("link","")
                out.append({
                    "id": link or title, "title": title, "authors": [],
                    "summary": re.sub("<[^<]+?>","",abstr), "categories": ["RSS"],
                    "published": pub.isoformat(), "updated": pub.isoformat(),
                    "pdf_url": "", "entry_url": link,
                })
        except Exception:
            continue
    return out

# ------------------ Main ------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--since_days", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    since_days = args.since_days if args.since_days is not None else int(cfg.get("since_days", 2))
    out_dir = pathlib.Path(cfg.get("output_dir", "./digests")); ensure_dir(out_dir)
    cache_path = pathlib.Path(cfg.get("cache_path", "./cache.json")); cache = load_cache(cache_path)
    today = dt.datetime.now().date().isoformat()   # 本地日期

    cats_cfg = cfg.get("categories", [])
    if not cats_cfg: cats_cfg = [{"name":"默认","highlight":[]},{"name":"其它","highlight":[]}]
    groups = [{"name": c["name"], "items": [], "highlight": c.get("highlight", [])} for c in cats_cfg]

    toggles = cfg.get("sources", {"arxiv": True})
    prio_cfg = cfg.get("priority", {})
    prefer_top = bool(prio_cfg.get("prefer_top_venues", True))

    # --- Build buckets by priority ---
    high_pri = []
    if prefer_top:
        if toggles.get("openalex_conferences"):
            src_map = resolve_openalex_sources(names=cfg.get("conferences", []), issns=None, cache_path="source_cache.json")
            conf_ids = [v for k,v in src_map.items() if str(k).startswith("name:")]
            high_pri += add_src(fetch_openalex_by_source_ids(conf_ids, since_days, work_type="proceedings-article", max_results=180), "openalex_conf")
        if toggles.get("openalex_journals"):
            src_map = resolve_openalex_sources(names=None, issns=cfg.get("journals_issn", []), cache_path="source_cache.json")
            jour_ids = [v for k,v in src_map.items() if str(k).startswith("issn:")]
            high_pri += add_src(fetch_openalex_by_source_ids(jour_ids, since_days, work_type="journal-article", max_results=180), "openalex_journal")
        if toggles.get("openreview"):
            high_pri += add_src(fetch_openreview(cfg.get("conferences", []), since_days, max_results=180), "openreview")

    # Domain guard for non-arXiv sources
    high_pri = [it for it in high_pri if passes_domain_guard(it)]
    high_pri = dedup_by_id(high_pri)

    # arXiv bucket from per-category queries
    cfg_cats = cfg.get("categories", [])
    queries = [q for c in cfg_cats for q in c.get("arxiv_queries", [])]
    arxiv_bucket = []
    if toggles.get("arxiv") and queries:
        arxiv_bucket = add_src(fetch_arxiv(queries, max_results=200, since_days=since_days), "arxiv")
    arxiv_bucket = dedup_by_id(arxiv_bucket)

    # optional RSS
    rss_bucket = []
    if toggles.get("rss"):
        rss_bucket = add_src(fetch_rss(cfg.get("rss_urls", []), since_days, max_results=60), "rss")
        rss_bucket = [it for it in rss_bucket if passes_domain_guard(it)]
        rss_bucket = dedup_by_id(rss_bucket)

    # --- Selection: new items first ---
    def is_new_item(it):
        return it.get("id") not in cache["seen"]

    high_pri_new = [it for it in high_pri if is_new_item(it)]
    arxiv_new = [it for it in arxiv_bucket if is_new_item(it)]

    def fill_from(items, groups, cats_cfg, cfg):
        per_max = int(cfg.get("per_category_max", 3))
        target_total = int(cfg.get("target_total", 5))
        picked=[]
        for it in items:
            gi, sc = assign_best_category(it, cats_cfg)
            it["_score"]=sc
            # respect per-category and global caps
            if len(groups[gi]["items"]) < per_max and sum(len(g["items"]) for g in groups) < target_total:
                groups[gi]["items"].append(it)
                picked.append(it)
        return picked

    # 1) top venues (new)
    picked_high = fill_from(high_pri_new, groups, cats_cfg, cfg)
    # 2) arXiv (new)
    if sum(len(g["items"]) for g in groups) < int(cfg.get("min_daily", 0) or cfg.get("target_total",5)):
        picked_arxiv = fill_from(arxiv_new, groups, cats_cfg, cfg)

    # 3) fallback: backfill with older NEW items (top venues first, then arXiv)
    need_more = sum(len(g["items"]) for g in groups) < int(cfg.get("min_daily",0) or cfg.get("target_total",5))
    fb_days = int(cfg.get("fallback_days",7))
    if need_more and fb_days > since_days:
        # top venues fallback
        pool_high = []
        if toggles.get("openalex_conferences"):
            src_map_fb = resolve_openalex_sources(names=cfg.get("conferences", []), issns=None, cache_path="source_cache.json")
            conf_ids_fb = [v for k,v in src_map_fb.items() if str(k).startswith("name:")]
            pool_high += add_src(fetch_openalex_by_source_ids(conf_ids_fb, fb_days, work_type="proceedings-article", max_results=200), "openalex_conf")
        if toggles.get("openalex_journals"):
            src_map_fb = resolve_openalex_sources(names=None, issns=cfg.get("journals_issn", []), cache_path="source_cache.json")
            jour_ids_fb = [v for k,v in src_map_fb.items() if str(k).startswith("issn:")]
            pool_high += add_src(fetch_openalex_by_source_ids(jour_ids_fb, fb_days, work_type="journal-article", max_results=200), "openalex_journal")
        pool_high = [it for it in dedup_by_id(pool_high) if is_new_item(it) and passes_domain_guard(it)]
        fill_from(pool_high, groups, cats_cfg, cfg)

        # arXiv fallback
        if toggles.get("arxiv") and queries:
            pool_arxiv = [it for it in dedup_by_id(fetch_arxiv(queries, max_results=200, since_days=fb_days)) if is_new_item(it)]
            fill_from(pool_arxiv, groups, cats_cfg, cfg)

    # 4) repeat fill (within lookback) if still not enough
    picked_repeat = []
    allow_repeat = bool(prio_cfg.get("allow_repeat_fill", True))
    if allow_repeat and sum(len(g["items"]) for g in groups) < int(cfg.get("min_daily",0) or cfg.get("target_total",5)):
        lookback = int(prio_cfg.get("repeat_lookback_days", 7))
        cutoff = (dt.datetime.utcnow().date() - dt.timedelta(days=lookback)).isoformat()
        # build universe of candidates
        universe = dedup_by_id(high_pri + arxiv_bucket + rss_bucket)
        todays_ids = {it["id"] for g in groups for it in g["items"]}
        repeat_pool = []
        # history ids & first-seen dates
        history_ids = {pid: d for pid, d in cache.get("seen", {}).items() if d >= cutoff}

        for it in universe:
            pid = it.get("id")
            if not pid or pid in todays_ids: 
                continue
            if pid in history_ids:
                it["repeat_from"] = history_ids[pid]
                repeat_pool.append(it)

        # score & fill
        scored = []
        for it in repeat_pool:
            gi, sc = assign_best_category(it, cats_cfg)
            it["_score"]=sc; it["_best_cat"]=gi
            scored.append(it)
        scored.sort(key=lambda x: x["_score"], reverse=True)
        per_max = int(cfg.get("per_category_max", 3))
        target_total = int(cfg.get("target_total", 5))
        for it in scored:
            gi = it["_best_cat"]
            if len(groups[gi]["items"]) < per_max and sum(len(g["items"]) for g in groups) < target_total:
                groups[gi]["items"].append(it)
                picked_repeat.append(it)

    # --- Finalize & Output ---
    # write digest
    md = as_markdown(today, groups, cfg)
    ensure_dir(out_dir := pathlib.Path(cfg.get("output_dir","./digests")))
    outfile = out_dir / f"{today}.md"
    outfile.write_text(md, encoding="utf-8")

    # 邮件发送（如启用）
    final_picks = [it for g in groups for it in g["items"]]
    ok, msg = send_digest_email(cfg, today, final_picks, str(outfile))
    print("Email:", msg)

    # update cache only for final picks
    final_picks = [it for g in groups for it in g["items"]]
    new_count = sum(1 for it in final_picks if cache["seen"].get(it["id"]) is None)
    repeat_count = sum(1 for it in final_picks if it.get("repeat_from"))
    for it in final_picks:
        if it["id"] not in cache["seen"]:
            cache["seen"][it["id"]] = today
    save_cache(cache, cache_path)

    picked_total = len(final_picks)
    print(f"{today}: 新论文 {new_count} 篇，入选 {picked_total} 篇（其中重复补齐 {repeat_count} 篇）")
    for g in groups:
        print(f"- {g['name']}: {len(g['items'])} 篇")
    print(f"Digest: {outfile}")

if __name__ == "__main__":
    main()
