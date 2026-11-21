#!/bin/bash
# Met à jour les données du journal en ligne (lancé par GitHub Actions toutes les 15 min).
# $1 = dossier du site à publier, $2 = adresse du site en ligne (pour reprendre les données déjà publiées).
SITE="$1"; BASE="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
export HOME="${RUNNER_TEMP:-/tmp}/journal-home"; D="$HOME/Library/Application Support/TradingJournal"; P="$HOME/prec"
mkdir -p "$D" "$P" "$SITE/Données"
LOGF="$SITE/Données/etat.txt"; exec > >(tee "$LOGF") 2>&1
echo "Début $(date -u)"
FILES="ff_calendar.js market.js news.js intraday.js retail.js cot.js season.js macro.js rates.js"
# 1) Données déjà en ligne = filet de sécurité si une source échoue
for f in $FILES; do curl -sfL --max-time 60 "$BASE/Donn%C3%A9es/$f" -o "$P/$f" || rm -f "$P/$f"; done
M=$((10#$(date -u +%M))); H=$((10#$(date -u +%H))); F="${FORCE:-0}"
# 2) Actualités RSS + bougies 1 h + sentiment particuliers : à chaque passage
bash "$HERE/news_update.sh" || true
# 3) Calendrier : toutes les heures
if [ "$F" = 1 ] || [ $M -lt 15 ] || [ ! -f "$P/ff_calendar.js" ]; then python3 "$HERE/ff_marche.py" "$D" || true; fi
# 4) COT, saisonnalité, macro, taux : toutes les 6 heures
if [ "$F" = 1 ] || { [ $((H % 6)) -eq 0 ] && [ $M -lt 15 ]; } || [ ! -f "$P/cot.js" ] || [ ! -f "$P/macro.js" ]; then bash "$HERE/data_update.sh" || true; fi
# 4b) Cours (Kraken + FRED, sans clé) : bougies 1 h à chaque passage, journalier toutes les heures, saisonnalité toutes les 6 h
Y="intraday"; if [ "$F" = 1 ] || [ $M -lt 15 ] || [ ! -f "$P/market.js" ]; then Y="$Y market"; fi
if [ "$F" = 1 ] || { [ $((H % 6)) -eq 0 ] && [ $M -lt 15 ]; } || [ ! -f "$P/season.js" ]; then Y="$Y season"; fi
if [ "$F" = 1 ] || [ $M -lt 15 ] || [ ! -f "$P/rates.js" ]; then Y="$Y rates"; fi
python3 "$HERE/marches_web.py" "$D" $Y || true
# 5) Publier : données fraîches, sinon les précédentes
for f in $FILES; do
  if [ -s "$D/$f" ]; then cp -f "$D/$f" "$SITE/Données/$f"; elif [ -s "$P/$f" ]; then cp -f "$P/$f" "$SITE/Données/$f"; fi
done
ls -la "$SITE/Données"
for l in "$D"/*.log; do [ -f "$l" ] && { echo "== $(basename "$l")"; tail -n 40 "$l"; }; done
echo "Fin $(date -u)"
