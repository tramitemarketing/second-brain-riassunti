#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera un sito statico leggibile da telefono a partire SOLO dai riassunti
in <vault>/wiki/riassunti/. Non tocca nessun'altra cartella del vault
(niente concepts, entities, progetti, raw). Output in ./public/.

Uso:  python build_site.py
"""
import os
import re
import html
import glob

SITE_TITLE = "Second Brain di Divan — Riassunti"

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.normpath(os.path.join(HERE, "..", "ai"))
SRC = os.path.join(VAULT, "wiki", "riassunti")
OUT = os.path.join(HERE, "public")

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 1.1rem 1.1rem 4rem;
  font: 1.05rem/1.7 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  max-width: 44rem; margin-inline: auto;
  color: #1a1a1a; background: #fbfbfa;
}
@media (prefers-color-scheme: dark) {
  body { color: #e6e6e6; background: #17181a; }
  a { color: #7db3ff; }
  blockquote { border-color: #3a3d42; color: #b8bcc2; }
  code { background: #2a2c30; }
  hr { border-color: #2a2c30; }
  .card { background: #1e2023; border-color: #2a2c30; }
  .muted { color: #9aa0a6; }
}
a { color: #1a5fb4; text-decoration: none; }
a:hover { text-decoration: underline; }
h1 { font-size: 1.7rem; line-height: 1.25; margin: .2rem 0 1rem; }
h2 { font-size: 1.3rem; margin: 2rem 0 .6rem; }
h3 { font-size: 1.1rem; margin: 1.4rem 0 .5rem; }
p { margin: .7rem 0; }
blockquote { margin: 1rem 0; padding: .2rem 0 .2rem 1rem;
  border-left: 3px solid #d0d0d0; color: #555; }
code { background: #ececec; padding: .1rem .35rem; border-radius: .3rem;
  font-size: .9em; }
hr { border: none; border-top: 1px solid #e2e2e2; margin: 2rem 0; }
ul, ol { margin: .7rem 0; padding-left: 1.4rem; }
li { margin: .25rem 0; }
.topbar { margin-bottom: 1.5rem; padding-bottom: .8rem;
  border-bottom: 1px solid #e2e2e2; }
.topbar a { font-weight: 600; }
.muted { color: #6b7075; font-size: .92rem; }
.card { display: block; border: 1px solid #e6e6e6; background: #fff;
  border-radius: .7rem; padding: .9rem 1rem; margin: .7rem 0; }
.card:hover { text-decoration: none; border-color: #9ab8e0; }
.card h2 { margin: 0 0 .2rem; font-size: 1.15rem; }
.card .muted { display: block; }
"""

# ---------- convertitore markdown (sottoinsieme usato nei riassunti) ----------

def parse_frontmatter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end].strip("\n")
            for line in block.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            text = text[end + 4:]
    return meta, text.lstrip("\n")

def inline(s, known):
    s = html.escape(s, quote=False)
    # code spans -> placeholder per proteggerli
    codes = []
    def _code(m):
        codes.append(m.group(1))
        return "\x00%d\x00" % (len(codes) - 1)
    s = re.sub(r"`([^`]+)`", _code, s)
    # link markdown [testo](url)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    # wikilink [[target|label]] o [[target]] -> link se pubblicato, altrimenti testo
    def _wiki(m):
        target = m.group(1).strip()
        label = (m.group(2) or m.group(1)).strip()
        slug = target.split("/")[-1]
        if slug in known:
            return '<a href="%s.html">%s</a>' % (slug, label)
        return label
    s = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", _wiki, s)
    # bold poi italic
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    # ripristina i code span
    s = re.sub(r"\x00(\d+)\x00",
               lambda m: "<code>%s</code>" % html.escape(codes[int(m.group(1))], quote=False), s)
    return s

def md_to_html(text, known):
    lines = text.split("\n")
    out, i, n = [], 0, len(lines)
    list_type = None
    def close_list():
        nonlocal list_type
        if list_type:
            out.append("</%s>" % list_type)
            list_type = None
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            close_list(); i += 1; continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_list()
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2), known), lvl))
            i += 1; continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            close_list(); out.append("<hr>"); i += 1; continue
        if stripped.startswith(">"):
            close_list()
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(buf), known))
            continue
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            if list_type != "ul":
                close_list(); out.append("<ul>"); list_type = "ul"
            out.append("<li>%s</li>" % inline(m.group(1), known)); i += 1; continue
        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            if list_type != "ol":
                close_list(); out.append("<ol>"); list_type = "ol"
            out.append("<li>%s</li>" % inline(m.group(1), known)); i += 1; continue
        # paragrafo: unisci righe consecutive non vuote
        close_list()
        buf = []
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|>|[-*]\s|\d+\.\s|-{3,}$|\*{3,}$)", lines[i].strip()):
            buf.append(lines[i].strip()); i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf), known))
    close_list()
    return "\n".join(out)

def page(title, body, is_index):
    back = "" if is_index else '<div class="topbar"><a href="index.html">← Tutti i riassunti</a></div>'
    home = '<div class="topbar"><a href="index.html">%s</a></div>' % html.escape(SITE_TITLE) if is_index else back
    return (
        "<!doctype html>\n<html lang=\"it\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<meta name=\"robots\" content=\"noindex\">\n"
        "<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n%s\n%s\n</body>\n</html>\n"
        % (html.escape(title), CSS, home, body)
    )

def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(os.path.join(SRC, "*.md")))
    known = {os.path.splitext(os.path.basename(f))[0] for f in files}
    entries = []
    for f in files:
        slug = os.path.splitext(os.path.basename(f))[0]
        with open(f, encoding="utf-8") as fh:
            meta, text = parse_frontmatter(fh.read())
        title = meta.get("title") or slug
        body = md_to_html(text, known)
        with open(os.path.join(OUT, slug + ".html"), "w", encoding="utf-8") as fh:
            fh.write(page(title, body, is_index=False))
        entries.append({
            "slug": slug, "title": title,
            "autore": meta.get("autore", ""), "durata": meta.get("durata", ""),
            "visto": meta.get("visto", ""),
        })
    entries.sort(key=lambda e: e["visto"], reverse=True)
    cards = []
    for e in entries:
        sub = " · ".join(x for x in [e["autore"], e["durata"], e["visto"]] if x)
        cards.append(
            '<a class="card" href="%s.html"><h2>%s</h2><span class="muted">%s</span></a>'
            % (e["slug"], html.escape(e["title"]), html.escape(sub))
        )
    intro = "<h1>%s</h1><p class=\"muted\">Riassunti accurati dei video guardati. Un tocco per aprirne uno.</p>" % html.escape(SITE_TITLE)
    body = intro + ("\n".join(cards) if cards else "<p class=\"muted\">Ancora nessun riassunto.</p>")
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page(SITE_TITLE, body, is_index=True))
    print("OK: %d riassunti -> %s" % (len(entries), OUT))

if __name__ == "__main__":
    main()
