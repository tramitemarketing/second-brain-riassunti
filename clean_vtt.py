#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pulisce i .vtt (sottotitoli YouTube) in testo leggibile e deduplicato.
Uso: python clean_vtt.py <indir> <outdir>"""
import sys, re, glob, os

def clean(vtt_path):
    out, last = [], None
    for raw in open(vtt_path, encoding="utf-8", errors="ignore"):
        line = raw.rstrip("\n")
        if line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        if "-->" in line:
            continue
        line = re.sub(r"<[^>]+>", "", line)          # tag <c>, <00:00:00.000>
        line = re.sub(r"\s+", " ", line).strip()
        if not line or line == last:
            continue
        out.append(line)
        last = line
    return " ".join(out)

def main():
    indir, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    by_id = {}
    for f in glob.glob(os.path.join(indir, "*.vtt")):
        vid = os.path.basename(f).split(".")[0]
        by_id.setdefault(vid, []).append(f)
    for vid, files in sorted(by_id.items()):
        pref = next((x for x in files if os.path.basename(x) == vid + ".en.vtt"), None)
        chosen = pref or sorted(files)[0]
        txt = clean(chosen)
        with open(os.path.join(outdir, vid + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(txt)
        print("%s -> %d chars (%s)" % (vid, len(txt), os.path.basename(chosen)))

if __name__ == "__main__":
    main()
