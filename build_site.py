#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera un sito statico leggibile da telefono dai riassunti in <vault>/wiki/riassunti/.
- File .md sciolti  -> video singolo (una card in homepage).
- Sottocartelle     -> playlist: una card in homepage -> un index con i video -> pagina per video.
Non tocca nessun'altra cartella del vault. Output in ./docs/.
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
OUT = os.path.join(HERE, "docs")

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin: 0; padding: 1.1rem 1.1rem 4rem;
  font: 1.05rem/1.7 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  max-width: 44rem; margin-inline: auto; color: #1a1a1a; background: #fbfbfa; }
@media (prefers-color-scheme: dark) {
  body { color: #e6e6e6; background: #17181a; }
  a { color: #7db3ff; } blockquote { border-color: #3a3d42; color: #b8bcc2; }
  code { background: #2a2c30; } hr { border-color: #2a2c30; }
  .card { background: #1e2023; border-color: #2a2c30; } .muted { color: #9aa0a6; }
  .tag { background: #2a2c30; color: #cbd0d6; }
  .btn { background: #2b6fd6 !important; } .btn:hover { background: #3f7fe0 !important; } }
a { color: #1a5fb4; text-decoration: none; } a:hover { text-decoration: underline; }
h1 { font-size: 1.7rem; line-height: 1.25; margin: .2rem 0 1rem; }
h2 { font-size: 1.3rem; margin: 2rem 0 .6rem; } h3 { font-size: 1.1rem; margin: 1.4rem 0 .5rem; }
p { margin: .7rem 0; }
blockquote { margin: 1rem 0; padding: .2rem 0 .2rem 1rem; border-left: 3px solid #d0d0d0; color: #555; }
code { background: #ececec; padding: .1rem .35rem; border-radius: .3rem; font-size: .9em; }
hr { border: none; border-top: 1px solid #e2e2e2; margin: 2rem 0; }
ul, ol { margin: .7rem 0; padding-left: 1.4rem; } li { margin: .25rem 0; }
.topbar { margin-bottom: 1.5rem; padding-bottom: .8rem; border-bottom: 1px solid #e2e2e2; }
.topbar a { font-weight: 600; }
.muted { color: #6b7075; font-size: .92rem; }
.tag { display: inline-block; background: #eceff3; color: #4a5560; font-size: .72rem;
  font-weight: 700; letter-spacing: .03em; text-transform: uppercase;
  padding: .12rem .45rem; border-radius: .4rem; margin-bottom: .35rem; }
.card { display: block; border: 1px solid #e6e6e6; background: #fff; border-radius: .7rem;
  padding: .9rem 1rem; margin: .7rem 0; }
.card:hover { text-decoration: none; border-color: #9ab8e0; }
.card h2 { margin: 0 0 .2rem; font-size: 1.15rem; } .card .muted { display: block; }
.card .desc { margin: .35rem 0 0; }
.btn { display: inline-block; margin: .5rem 0; padding: .55rem 1rem; background: #1a5fb4;
  color: #fff !important; border-radius: .5rem; font-weight: 600; font-size: .95rem; }
.btn:hover { background: #154c92; text-decoration: none; }
"""

# ---------- markdown -> HTML (sottoinsieme usato nei riassunti) ----------

def parse_frontmatter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].strip("\n").splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            text = text[end + 4:]
    return meta, text.lstrip("\n")

def inline(s, known):
    s = html.escape(s, quote=False)
    codes = []
    s = re.sub(r"`([^`]+)`", lambda m: codes.append(m.group(1)) or "\x00%d\x00" % (len(codes) - 1), s)
    def _link(m):
        label, url = m.group(1), m.group(2)
        cls = ' class="btn"' if label.lstrip().startswith("»") else ''
        return '<a href="%s"%s target="_blank" rel="noopener">%s</a>' % (url, cls, label)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", _link, s)
    def _wiki(m):
        target, label = m.group(1).strip(), (m.group(2) or m.group(1)).strip()
        slug = target.split("/")[-1]
        return '<a href="%s.html">%s</a>' % (slug, label) if slug in known else label
    s = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", _wiki, s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>" % html.escape(codes[int(m.group(1))], quote=False), s)
    return s

def md_to_html(text, known):
    lines = text.split("\n"); out = []; i = 0; n = len(lines); lt = [None]
    def close():
        if lt[0]:
            out.append("</%s>" % lt[0]); lt[0] = None
    while i < n:
        s = lines[i].strip()
        if not s: close(); i += 1; continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m: close(); l = len(m.group(1)); out.append("<h%d>%s</h%d>" % (l, inline(m.group(2), known), l)); i += 1; continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s): close(); out.append("<hr>"); i += 1; continue
        if s.startswith(">"):
            close(); buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(buf), known)); continue
        m = re.match(r"^[-*]\s+(.*)$", s)
        if m:
            if lt[0] != "ul": close(); out.append("<ul>"); lt[0] = "ul"
            out.append("<li>%s</li>" % inline(m.group(1), known)); i += 1; continue
        m = re.match(r"^\d+\.\s+(.*)$", s)
        if m:
            if lt[0] != "ol": close(); out.append("<ol>"); lt[0] = "ol"
            out.append("<li>%s</li>" % inline(m.group(1), known)); i += 1; continue
        close(); buf = []
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|>|[-*]\s|\d+\.\s|-{3,}$|\*{3,}$)", lines[i].strip()):
            buf.append(lines[i].strip()); i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf), known))
    close()
    return "\n".join(out)

def page(title, body, topbar):
    return ("<!doctype html>\n<html lang=\"it\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta name=\"robots\" content=\"noindex\">\n<title>%s</title>\n<style>%s</style>\n"
            "</head>\n<body>\n%s\n%s\n</body>\n</html>\n"
            % (html.escape(title), CSS, topbar, body))

def read_md(path):
    with open(path, encoding="utf-8") as fh:
        return parse_frontmatter(fh.read())

def sub(meta):
    return " · ".join(x for x in [meta.get("autore", ""), meta.get("durata", ""), meta.get("visto", "")] if x)

def main():
    os.makedirs(OUT, exist_ok=True)
    home_cards = []

    # --- playlist (sottocartelle) ---
    for d in sorted(os.listdir(SRC)):
        pdir = os.path.join(SRC, d)
        if not os.path.isdir(pdir):
            continue
        files = sorted(glob.glob(os.path.join(pdir, "*.md")))
        if not files:
            continue
        known = {os.path.splitext(os.path.basename(f))[0] for f in files}
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
        pname = None; autore = None; vids = []
        for f in files:
            slug = os.path.splitext(os.path.basename(f))[0]
            meta, text = read_md(f)
            pname = pname or meta.get("playlist") or d.replace("-", " ").title()
            autore = autore or meta.get("autore", "")
            title = meta.get("title") or slug
            tb = '<div class="topbar"><a href="index.html">← %s</a> · <a href="../index.html">Home</a></div>' % html.escape(pname)
            with open(os.path.join(OUT, d, slug + ".html"), "w", encoding="utf-8") as fh:
                fh.write(page(title, md_to_html(text, known), tb))
            vids.append({"slug": slug, "title": title, "durata": meta.get("durata", ""),
                         "visto": meta.get("visto", ""), "descr": meta.get("descrizione", "")})
        vids.sort(key=lambda v: v["visto"], reverse=True)
        # index della playlist
        rows = []
        for v in vids:
            meta_line = " · ".join(x for x in [v["durata"], v["visto"]] if x)
            desc = ('<span class="desc">%s</span>' % html.escape(v["descr"])) if v["descr"] else ""
            rows.append('<a class="card" href="%s.html"><h2>%s</h2><span class="muted">%s</span>%s</a>'
                        % (v["slug"], html.escape(v["title"]), html.escape(meta_line), desc))
        pintro = ('<h1>%s</h1><p class="muted">%d video · %s</p>'
                  % (html.escape(pname), len(vids), html.escape(autore)))
        tb = '<div class="topbar"><a href="../index.html">← Tutti i riassunti</a></div>'
        with open(os.path.join(OUT, d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(page(pname, pintro + "\n".join(rows), tb))
        # card in homepage
        home_cards.append({"kind": "playlist", "visto": vids[0]["visto"],
            "html": '<a class="card" href="%s/index.html"><span class="tag">Playlist · %d video</span>'
                    '<h2>%s</h2><span class="muted">%s</span></a>'
                    % (d, len(vids), html.escape(pname), html.escape(autore))})

    # --- video singoli (file sciolti) ---
    loose = sorted(glob.glob(os.path.join(SRC, "*.md")))
    known_loose = {os.path.splitext(os.path.basename(f))[0] for f in loose}
    for f in loose:
        slug = os.path.splitext(os.path.basename(f))[0]
        meta, text = read_md(f)
        title = meta.get("title") or slug
        tb = '<div class="topbar"><a href="index.html">← Tutti i riassunti</a></div>'
        with open(os.path.join(OUT, slug + ".html"), "w", encoding="utf-8") as fh:
            fh.write(page(title, md_to_html(text, known_loose), tb))
        home_cards.append({"kind": "video", "visto": meta.get("visto", ""),
            "html": '<a class="card" href="%s.html"><h2>%s</h2><span class="muted">%s</span></a>'
                    % (slug, html.escape(title), html.escape(sub(meta)))})

    # --- homepage: playlist prima, poi video singoli (ognuno per data desc) ---
    home_cards.sort(key=lambda c: (c["kind"] != "playlist", c["visto"] and c["visto"] or ""), reverse=False)
    pl = [c["html"] for c in home_cards if c["kind"] == "playlist"]
    vd = sorted([c for c in home_cards if c["kind"] == "video"], key=lambda c: c["visto"], reverse=True)
    body = ('<h1>%s</h1><p class="muted">Riassunti accurati dei video guardati. Un tocco per aprirne uno.</p>'
            % html.escape(SITE_TITLE)) + "\n".join(pl + [c["html"] for c in vd])
    tb = '<div class="topbar"><a href="index.html">%s</a></div>' % html.escape(SITE_TITLE)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page(SITE_TITLE, body, tb))
    print("OK: %d playlist, %d video singoli -> %s" % (len(pl), len(vd), OUT))

if __name__ == "__main__":
    main()
