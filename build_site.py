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

/* --- lettura: barra di avanzamento, pillola, spunte di sezione --- */
#rp { position: fixed; top: 0; left: 0; height: 3px; width: 0;
  background: #1a5fb4; z-index: 50; transition: width .3s ease; }
#rd { position: fixed; right: .8rem; bottom: .8rem; z-index: 50;
  background: rgba(255,255,255,.94); border: 1px solid #e2e2e2; border-radius: 2rem;
  padding: .4rem .8rem; font-size: .82rem; font-weight: 700; color: #4a5560;
  box-shadow: 0 2px 10px rgba(0,0,0,.09); cursor: pointer; user-select: none; }
#rd.done { background: #1a7f37; border-color: #1a7f37; color: #fff; }
.sec { border: none; background: none; cursor: pointer; font-size: .78rem; font-weight: 700;
  color: #9aa0a6; padding: .1rem .45rem; margin-left: .5rem; border-radius: 1rem;
  vertical-align: middle; }
.sec:hover { background: #eceff3; color: #4a5560; }
.sec.ok { color: #1a7f37; }
.pill { display: inline-block; font-size: .7rem; font-weight: 700; letter-spacing: .03em;
  padding: .1rem .45rem; border-radius: 1rem; margin-left: .4rem; vertical-align: middle;
  background: #eceff3; color: #4a5560; }
.pill.done { background: #1a7f37; color: #fff; }
.card.read { opacity: .72; }
@media (prefers-color-scheme: dark) {
  #rd { background: rgba(30,32,35,.94); border-color: #2a2c30; color: #cbd0d6; }
  #rd.done { background: #1a7f37; border-color: #1a7f37; color: #fff; }
  .sec:hover { background: #2a2c30; color: #cbd0d6; }
  .sec.ok { color: #4ac26b; } .pill { background: #2a2c30; color: #cbd0d6; }
  .pill.done { background: #1a7f37; color: #fff; } }
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

# Indirizzo del piccolo server (Worker Cloudflare) che tiene i progressi di lettura
# uguali su tutti i dispositivi. Se è vuoto, il sito funziona lo stesso: i progressi
# restano nel browser di ciascun dispositivo.
SYNC_API = ""   # <- si riempie dopo il deploy del Worker (wrangler deploy)

# Ponte verso il server dei progressi: due sole funzioni, prendi e manda.
SYNC_JS = r"""
window.SB = (function () {
  var API = '__API__';
  function url() { return API + '/state'; }
  return {
    attivo: !!API,
    prendi: function () {
      if (!API) return Promise.resolve(null);
      return fetch(url(), { cache: 'no-store' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; });
    },
    manda: function (page, n, b, finale) {
      if (!API) return;
      var dati = JSON.stringify({ page: page, n: n, b: b });
      try {
        fetch(url(), {
          method: 'POST', body: dati, keepalive: !!finale,
          headers: { 'Content-Type': 'application/json' }
        }).catch(function () {});
      } catch (e) {}
    }
  };
})();
"""

# --- tracciamento della lettura (solo nelle pagine di testo) ---
# Conta come letto solo ciò che è rimasto davvero davanti agli occhi:
# ogni blocco deve stare nella fascia centrale dello schermo per un tempo
# proporzionale alla sua lunghezza (~240 parole/min). Scrollare fino in fondo
# e risalire non fa accumulare nulla; nemmeno tenere la scheda in secondo piano.
READER_JS = r"""
(function () {
  var KEY = 'sb2:' + location.pathname;
  var WPS = 4;             // parole al secondo (~240 wpm)
  var MIN = 0.7, MAX = 6;  // secondi per blocco: minimo e tetto
  var PASS = 0.5;          // se l'ho letto almeno a metà e sono andato oltre, conta
  var IDLE = 120000;       // fermo da 2 min = non sta leggendo
  var DONE = 0.9;          // 90% dei contenuti = letto

  var nodes = [].slice.call(document.querySelectorAll('p, li, blockquote'))
    .filter(function (n) { return !n.closest('.topbar') && n.textContent.trim().length > 1; });
  if (nodes.length < 3) return;

  var words = nodes.map(function (n) {
    return Math.max(1, n.textContent.trim().split(/\s+/).length);
  });
  var need = words.map(function (w) {
    return Math.min(MAX, Math.max(MIN, w / WPS));
  });
  var total = words.reduce(function (a, b) { return a + b; }, 0);
  var acc = words.map(function () { return 0; });
  var read = words.map(function () { return false; });

  // ripristina lo stato salvato (se la pagina non è cambiata)
  try {
    var s = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (s && s.n === nodes.length && typeof s.b === 'string') {
      for (var i = 0; i < nodes.length; i++) read[i] = s.b.charAt(i) === '1';
    }
  } catch (e) {}

  var bar = document.createElement('div'); bar.id = 'rp';
  var dot = document.createElement('div'); dot.id = 'rd';
  document.body.appendChild(bar); document.body.appendChild(dot);

  // spunte di sezione: ogni h2 governa i blocchi fino all'h2 successivo
  var secs = [];
  var heads = [].slice.call(document.querySelectorAll('h2'));
  heads.forEach(function (h) {
    var idx = [];
    for (var i = 0; i < nodes.length; i++) {
      if (h.compareDocumentPosition(nodes[i]) & Node.DOCUMENT_POSITION_FOLLOWING) {
        var prev = null;
        for (var k = 0; k < heads.length; k++) {
          if (heads[k].compareDocumentPosition(nodes[i]) & Node.DOCUMENT_POSITION_FOLLOWING) prev = heads[k];
        }
        if (prev === h) idx.push(i);
      }
    }
    if (!idx.length) return;
    var b = document.createElement('button');
    b.className = 'sec'; b.type = 'button';
    b.title = 'Segna questa sezione come letta / non letta';
    h.appendChild(b);
    var sec = { el: b, idx: idx };
    b.addEventListener('click', function () {
      var allRead = idx.every(function (i) { return read[i]; });
      idx.forEach(function (i) { read[i] = !allRead; acc[i] = allRead ? 0 : need[i]; });
      paint(); save();
    });
    secs.push(sec);
  });

  function pct() {
    var w = 0;
    for (var i = 0; i < nodes.length; i++) if (read[i]) w += words[i];
    return w / total;
  }
  function paint() {
    var p = pct();
    bar.style.width = (p * 100).toFixed(1) + '%';
    var done = p >= DONE;
    dot.textContent = done ? '✓ Letto' : Math.round(p * 100) + '%';
    dot.className = done ? 'done' : '';
    secs.forEach(function (s) {
      var ok = s.idx.every(function (i) { return read[i]; });
      s.el.className = ok ? 'sec ok' : 'sec';
      s.el.textContent = ok ? '✓' : '○';
    });
  }
  function bits() {
    var b = '';
    for (var i = 0; i < nodes.length; i++) b += read[i] ? '1' : '0';
    return b;
  }
  var saveT = 0, syncT = 0, ultimo = '';
  function save(finale) {
    var b = bits();
    clearTimeout(saveT);
    saveT = setTimeout(function () {
      try {
        localStorage.setItem(KEY, JSON.stringify({
          v: 2, n: nodes.length, b: b, p: Math.round(pct() * 100), t: Date.now()
        }));
      } catch (e) {}
    }, 400);
    // verso il server: di rado, per non consumare la quota gratuita
    if (!window.SB || !SB.attivo || b === ultimo) return;
    if (finale) { ultimo = b; SB.manda(location.pathname, nodes.length, b, true); return; }
    clearTimeout(syncT);
    syncT = setTimeout(function () {
      ultimo = b;
      SB.manda(location.pathname, nodes.length, b, false);
    }, 8000);
  }

  // all'apertura: unisco i progressi già fatti su altri dispositivi
  if (window.SB && SB.attivo) {
    SB.prendi().then(function (st) {
      if (!st || !st.pages) return;
      var r = st.pages[location.pathname];
      if (!r || r.n !== nodes.length) return;
      var cambiato = false;
      for (var i = 0; i < nodes.length; i++) {
        if (r.b.charAt(i) === '1' && !read[i]) { read[i] = true; acc[i] = need[i]; cambiato = true; }
      }
      if (cambiato) { paint(); save(); }
    });
  }

  // quali blocchi sono nella fascia centrale dello schermo (dove si legge davvero)
  var visible = Object.create(null);
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      var i = nodes.indexOf(en.target);
      if (i < 0) return;
      if (en.isIntersecting) visible[i] = 1; else delete visible[i];
    });
  }, { rootMargin: '-25% 0px -25% 0px', threshold: 0 });
  nodes.forEach(function (n) { io.observe(n); });

  var last = Date.now();
  ['scroll', 'mousemove', 'keydown', 'touchstart', 'wheel', 'click'].forEach(function (ev) {
    addEventListener(ev, function () { last = Date.now(); }, { passive: true });
  });

  setInterval(function () {
    if (document.hidden || Date.now() - last > IDLE) return;
    var changed = false, i;
    for (i in visible) {
      i = +i;
      if (read[i]) continue;
      acc[i] += 0.25;
      if (acc[i] >= need[i]) { read[i] = true; changed = true; }
    }
    // blocco letto almeno a metà e ormai scorso sopra la fascia di lettura:
    // è il comportamento di chi legge un paragrafo e prosegue.
    for (i = 0; i < nodes.length; i++) {
      if (read[i] || acc[i] < need[i] * PASS) continue;
      if (nodes[i].getBoundingClientRect().bottom < innerHeight * 0.25) {
        read[i] = true; changed = true;
      }
    }
    if (changed) { paint(); save(); }
  }, 250);

  dot.addEventListener('click', function () {
    var all = pct() >= DONE;
    for (var i = 0; i < nodes.length; i++) { read[i] = !all; acc[i] = all ? 0 : need[i]; }
    paint(); save();
  });
  dot.title = 'Tocca per segnare tutto come letto / non letto';

  paint();
  addEventListener('beforeunload', function () { save(true); });
  addEventListener('visibilitychange', function () { if (document.hidden) save(true); });
})();
"""

# Nelle pagine-elenco: mostra accanto a ogni voce se è già stata letta.
HOME_JS = r"""
(function () {
  var remoto = null;
  function st(href) {
    var p, loc = null;
    try {
      p = new URL(href, location.href).pathname;
      loc = JSON.parse(localStorage.getItem('sb2:' + p) || 'null');
    } catch (e) { return null; }
    var rem = remoto && remoto.pages ? remoto.pages[p] : null;
    if (!loc) return rem || null;
    if (!rem) return loc;
    return (rem.p || 0) > (loc.p || 0) ? rem : loc;   // vince chi ha letto di più
  }
  function disegna() {
  [].slice.call(document.querySelectorAll('a.card')).forEach(function (a) {
    var vecchio = a.querySelector('.pill');
    if (vecchio) vecchio.remove();
    var items = a.getAttribute('data-items'), tag, n = 0, tot = 0;
    if (items) {                                   // card di una playlist
      items.split(',').forEach(function (h) {
        tot++;
        var s = st(h);
        if (s && s.p >= 90) n++;
      });
      if (!n) return;
      tag = document.createElement('span');
      tag.className = 'pill' + (n === tot ? ' done' : '');
      tag.textContent = n === tot ? '✓ Letti tutti' : n + '/' + tot + ' letti';
    } else {                                       // card di un singolo riassunto
      var s = st(a.getAttribute('href'));
      if (!s || !s.p) return;
      tag = document.createElement('span');
      tag.className = 'pill' + (s.p >= 90 ? ' done' : '');
      tag.textContent = s.p >= 90 ? '✓ Letto' : s.p + '%';
      if (s.p >= 90) a.className += ' read';
    }
    var h2 = a.querySelector('h2');
    if (h2) h2.appendChild(tag);
  });
  }
  disegna();
  // poi chiedo al server se su un altro dispositivo ho letto altro
  if (window.SB && SB.attivo) {
    SB.prendi().then(function (st) { if (st) { remoto = st; disegna(); } });
  }
})();
"""

def page(title, body, topbar, script=""):
    js = ("<script>%s</script>\n" % script) if script else ""
    return ("<!doctype html>\n<html lang=\"it\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta name=\"robots\" content=\"noindex\">\n<title>%s</title>\n<style>%s</style>\n"
            "</head>\n<body>\n%s\n%s\n%s</body>\n</html>\n"
            % (html.escape(title), CSS, topbar, body, js))

def read_md(path):
    with open(path, encoding="utf-8") as fh:
        return parse_frontmatter(fh.read())

def data_it(s):
    """2026-07-16 -> 16/07/2026 (come si scrivono le date in Italia)."""
    s = (s or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    return "%s/%s/%s" % (m.group(3), m.group(2), m.group(1)) if m else s

def sub(meta):
    return " · ".join(x for x in [meta.get("autore", ""), meta.get("durata", ""),
                                  data_it(meta.get("visto", ""))] if x)

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
                fh.write(page(title, md_to_html(text, known), tb, READER_JS))
            try:
                ordine = int(str(meta.get("ordine", "")).strip())
            except ValueError:
                ordine = 10 ** 6          # senza "ordine:" finisce in coda, ma stabile
            vids.append({"slug": slug, "title": title, "durata": meta.get("durata", ""),
                         "visto": meta.get("visto", ""), "descr": meta.get("descrizione", ""),
                         "ordine": ordine})
        # ordine cronologico: prima la data di visione, poi il campo "ordine" del
        # frontmatter (utile quando più video sono stati visti lo stesso giorno)
        vids.sort(key=lambda v: (v["visto"], v["ordine"], v["title"]))
        # index della playlist
        rows = []
        for v in vids:
            meta_line = " · ".join(x for x in [v["durata"], data_it(v["visto"])] if x)
            desc = ('<span class="desc">%s</span>' % html.escape(v["descr"])) if v["descr"] else ""
            rows.append('<a class="card" href="%s.html"><h2>%s</h2><span class="muted">%s</span>%s</a>'
                        % (v["slug"], html.escape(v["title"]), html.escape(meta_line), desc))
        pintro = ('<h1>%s</h1><p class="muted">%d video · %s</p>'
                  % (html.escape(pname), len(vids), html.escape(autore)))
        tb = '<div class="topbar"><a href="../index.html">← Tutti i riassunti</a></div>'
        with open(os.path.join(OUT, d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(page(pname, pintro + "\n".join(rows), tb, HOME_JS))
        # card in homepage (data-items: serve a contare quanti video ho già letto)
        items = ",".join("%s/%s.html" % (d, v["slug"]) for v in vids)
        home_cards.append({"kind": "playlist", "visto": vids[-1]["visto"],
            "html": '<a class="card" href="%s/index.html" data-items="%s"><span class="tag">Playlist · %d video</span>'
                    '<h2>%s</h2><span class="muted">%s</span></a>'
                    % (d, html.escape(items, quote=True), len(vids), html.escape(pname), html.escape(autore))})

    # --- video singoli (file sciolti) ---
    loose = sorted(glob.glob(os.path.join(SRC, "*.md")))
    known_loose = {os.path.splitext(os.path.basename(f))[0] for f in loose}
    for f in loose:
        slug = os.path.splitext(os.path.basename(f))[0]
        meta, text = read_md(f)
        title = meta.get("title") or slug
        tb = '<div class="topbar"><a href="index.html">← Tutti i riassunti</a></div>'
        with open(os.path.join(OUT, slug + ".html"), "w", encoding="utf-8") as fh:
            fh.write(page(title, md_to_html(text, known_loose), tb, READER_JS))
        home_cards.append({"kind": "video", "visto": meta.get("visto", ""),
            "html": '<a class="card" href="%s.html"><h2>%s</h2><span class="muted">%s</span></a>'
                    % (slug, html.escape(title), html.escape(sub(meta)))})

    # --- homepage: playlist prima, poi video singoli (ognuno per data desc) ---
    home_cards.sort(key=lambda c: (c["kind"] != "playlist", c["visto"] and c["visto"] or ""), reverse=False)
    pl = [c["html"] for c in home_cards if c["kind"] == "playlist"]
    vd = sorted([c for c in home_cards if c["kind"] == "video"], key=lambda c: c["visto"], reverse=True)
    body = ('<h1>%s</h1><p class="muted">Riassunti accurati dei video guardati. Un tocco per aprirne uno. '
            'Quelli già letti si segnano da soli.</p>'
            % html.escape(SITE_TITLE)) + "\n".join(pl + [c["html"] for c in vd])
    tb = '<div class="topbar"><a href="index.html">%s</a></div>' % html.escape(SITE_TITLE)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page(SITE_TITLE, body, tb, HOME_JS))
    print("OK: %d playlist, %d video singoli -> %s" % (len(pl), len(vd), OUT))

if __name__ == "__main__":
    main()
