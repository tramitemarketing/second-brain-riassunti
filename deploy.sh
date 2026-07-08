#!/usr/bin/env bash
# Rigenera il sito dai riassunti (wiki/riassunti) e lo pubblica su GitHub.
# Cloudflare Pages, collegato al repo, ridistribuisce automaticamente ad ogni push.
# Uso:  bash deploy.sh
set -e
cd "$(dirname "$0")"
python build_site.py
git add -A
git commit -m "update riassunti $(date +%F)" || echo "niente da committare"
git push
echo "Fatto: push eseguito, il sito si aggiorna da solo tra poco."
