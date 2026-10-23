# Merge the routing-check help books and the Cisco Live routing book into one self-contained HTML file.
# Sources stay split (src/viewer.css, src/viewer.js); the single file is a build output.
# usage: python3 -I build.py
import html, json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
HELP = os.path.expanduser("~/work/routing-check/help")
CL_BOOK = os.path.expanduser("~/Desktop/ciscolive-routing-book")
OUT = os.path.join(ROOT, "routing-books.html")
REPO_BOOKS = ["bgp-book", "ospf-book", "isis-book", "srsrv6-book", "evpn-book", "mvpn-book", "qos-book"]
CL_ID = "cl"
CL_TITLE = "ルーティング技術書 — Cisco Live セッションからの書き下ろし"


# ---------- CSS scoping ----------
def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)

def scope_selector(sel, scope):
    sel = sel.strip()
    if not sel:
        return sel
    m = re.match(r"^(:root|html|body)\b(.*)$", sel)
    if m:
        rest = m.group(2).strip()
        rest = re.sub(r"^(html|body)\b", "", rest).strip()
        return f"{scope} {rest}".strip() if rest else scope
    return f"{scope} {sel}"

def scope_css(css, scope):
    css = strip_comments(css)
    out, i, n = [], 0, len(css)
    while i < n:
        brace = css.find("{", i)
        if brace < 0:
            break
        head = css[i:brace].strip()
        depth, j = 1, brace + 1
        while j < n and depth:
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        body = css[brace + 1:j - 1]
        if head.startswith("@media") or head.startswith("@supports"):
            out.append(f"{head}{{{scope_css(body, scope)}}}")
        elif head.startswith("@"):
            out.append(f"{head}{{{body}}}")
        else:
            sels = ",".join(scope_selector(s, scope) for s in head.split(","))
            out.append(f"{sels}{{{body.strip()}}}")
        i = j
    return "\n".join(out)


# ---------- chapter content ----------
def text_of(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()

def rewrite_links(content, book_id, chapter_id):
    """Turn in-book links into viewer routes; leave SVG-internal and external links alone."""
    parts = re.split(r"(<svg\b.*?</svg>)", content, flags=re.S)
    def fix(m):
        target = m.group(1)
        if target.startswith("#"):
            return f'href="#{book_id}/{chapter_id}/{target[1:]}"'
        m2 = re.match(r"^(?:\.\./chapters/|chapters/)?([\w.-]+)\.html(?:#(.*))?$", target)
        if not m2:
            return m.group(0)
        name, anchor = m2.groups()
        if name == "index" or target.startswith("../index"):
            return 'href="#"'
        return f'href="#{book_id}/{name}' + (f"/{anchor}" if anchor else "") + '"'
    return "".join(p if p.startswith("<svg") else re.sub(r'href="([^"]+)"', lambda m: fix(m) if not re.match(r"^(https?:|mailto:)", m.group(1)) else m.group(0), p)
                   for p in parts)

def sections_of(content):
    return [{"anchor": a, "title": text_of(t)} for a, t in re.findall(r'<h2[^>]*\sid="([^"]+)"[^>]*>(.*?)</h2>', content, re.S)]

def ensure_h2_ids(content, prefix):
    counter = iter(range(10_000))
    return re.sub(r"<h2(?![^>]*\sid=)([^>]*)>", lambda m: f'<h2 id="{prefix}-s{next(counter)}"{m.group(1)}>', content)

def load_repo_book(name):
    base = os.path.join(HELP, name)
    index = open(os.path.join(base, "index.html"), encoding="utf-8").read()
    book_title = re.search(r"<title>(.*?)</title>", index, re.S).group(1).strip()
    order = list(dict.fromkeys(re.findall(r'href="chapters/([\w.-]+)\.html"', index)))
    on_disk = sorted(f[:-5] for f in os.listdir(os.path.join(base, "chapters")) if f.endswith(".html"))
    order += [c for c in on_disk if c not in order]
    book_id = name.replace("-book", "")
    chapters = []
    for cid in order:
        page = open(os.path.join(base, "chapters", f"{cid}.html"), encoding="utf-8").read()
        main = re.search(r"<main[^>]*>(.*)</main>", page, re.S).group(1)
        main = re.sub(r'<nav class="chap-nav">.*?</nav>', "", main, flags=re.S)
        title = re.search(r"<title>(.*?)</title>", page, re.S).group(1)
        title = html.unescape(title.rsplit(" — ", 1)[0].strip())
        content = ensure_h2_ids(rewrite_links(main, book_id, cid), cid)
        chapters.append({"id": cid, "title": title, "sections": sections_of(content), "html": f"<main>{content}</main>"})
    css = open(os.path.join(base, "css", "style.css"), encoding="utf-8").read()
    return {"id": book_id, "title": book_title, "scope": f"bk-{book_id}", "css": scope_css(css, f".bk-{book_id}"), "chapters": chapters}

def load_cl_book():
    meta = open(os.path.join(CL_BOOK, "data", "book.js"), encoding="utf-8").read()
    order = re.findall(r"\{ id: '(ch\d+)', title: '([^']+)' \}", meta)
    chapters = []
    for n, (cid, title) in enumerate(order, 1):
        frag = open(os.path.join(CL_BOOK, "_fragments", f"{cid}.html"), encoding="utf-8").read()
        content = ensure_h2_ids(rewrite_links(frag, CL_ID, cid), cid)
        chapters.append({"id": cid, "title": f"第{n}章 {title}", "sections": sections_of(content),
                         "html": f'<div class="chapter">{content}</div>'})
    css = open(os.path.join(CL_BOOK, "css", "style.css"), encoding="utf-8").read()
    return {"id": CL_ID, "title": CL_TITLE, "scope": f"bk-{CL_ID}", "css": scope_css(css, f".bk-{CL_ID}"), "chapters": chapters}


# ---------- assemble ----------
books = [load_repo_book(b) for b in REPO_BOOKS] + [load_cl_book()]
for b in books:
    for c in b["chapters"]:
        if "</template" in c["html"].lower():
            raise SystemExit(f"{b['id']}/{c['id']}: content contains </template>")

library = [{"id": b["id"], "title": b["title"], "scope": b["scope"],
            "chapters": [{"id": c["id"], "title": c["title"], "sections": c["sections"]} for c in b["chapters"]]} for b in books]
library_json = json.dumps(library, ensure_ascii=False).replace("</", "<\\/")
templates = "\n".join(f'<template id="t--{b["id"]}--{c["id"]}">{c["html"]}</template>' for b in books for c in b["chapters"])
viewer_css = open(os.path.join(ROOT, "src", "viewer.css"), encoding="utf-8").read()
viewer_js = open(os.path.join(ROOT, "src", "viewer.js"), encoding="utf-8").read()
book_css = "\n".join(b["css"] for b in books)

page = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ルーティング技術書 合本</title>
<style>
{viewer_css}
{book_css}
</style>
</head>
<body>
<header class="v-header">
  <button class="v-toggle" type="button" aria-controls="side" aria-expanded="false">目次</button>
  <span class="v-title">ルーティング技術書 合本 ({len(books)} 冊)</span>
  <input class="v-search" type="search" placeholder="章を絞り込み" aria-label="章を絞り込み">
</header>
<div class="v-layout">
  <nav id="side" class="v-side" aria-label="目次"></nav>
  <div id="main" class="v-main"></div>
</div>
<script type="application/json" id="library-data">{library_json}</script>
{templates}
<script>
{viewer_js}
</script>
</body>
</html>
"""
open(OUT, "w", encoding="utf-8").write(page)
print(f"{len(books)} books, {sum(len(b['chapters']) for b in books)} chapters, {os.path.getsize(OUT) / 1_000_000:.1f} MB -> {OUT}")
for b in books:
    print(f"  {b['id']:8} {len(b['chapters']):3} chapters  {b['title'][:50]}")
