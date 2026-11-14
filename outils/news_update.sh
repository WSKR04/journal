#!/bin/bash
# Télécharge les flux d'actualités (RSS) pour le journal de trading et écrit news.js.
# Installé par « News auto - Activer.command ». Aucune dépendance : curl + base64 (macOS).
DIR="$HOME/Library/Application Support/TradingJournal"
OUT="$DIR/news.js"
mkdir -p "$DIR"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
FEEDS=(
"investinglive|https://investinglive.com/feed"
"fxstreet|https://www.fxstreet.com/rss/news"
"fed|https://www.federalreserve.gov/feeds/press_all.xml"
"ecb|https://www.ecb.europa.eu/rss/press.html"
"boe|https://www.bankofengland.co.uk/rss/news"
)
TMP="$OUT.tmp"
printf 'window.NEWS_RAW={"ts":"%s","f":{' "$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')" > "$TMP"
first=1
for f in "${FEEDS[@]}"; do
  k="${f%%|*}"; u="${f#*|}"
  body=$(curl -sL --max-time 20 -A "$UA" "$u" | head -c 600000 | base64 | tr -d '\n')
  [ -z "$body" ] && { echo "$(date '+%F %T') échec $k" >> "$DIR/news_update.log"; continue; }
  [ $first -eq 0 ] && printf ',' >> "$TMP"; first=0
  printf '"%s":"%s"' "$k" "$body" >> "$TMP"
done
printf '}};\n' >> "$TMP"
mv -f "$TMP" "$OUT"
# Copie aussi dans le dossier du journal si macOS l'autorise (sinon le journal lit la copie ci-dessus).
JD="$(cat "$DIR/news_journal_dir" 2>/dev/null)"
[ -n "$JD" ] && [ -d "$JD/Données" ] && cp -f "$OUT" "$JD/Données/news.js" 2>/dev/null

# Bougies 1 h (Yahoo) pour Session Recap et Liquidity : toutes les 10 minutes au plus.
IN="$DIR/intraday.js"
if [ ! -f "$IN" ] || [ $(( $(date +%s) - $(stat -f %m "$IN" 2>/dev/null || stat -c %Y "$IN") )) -ge 600 ]; then
  T="$IN.tmp"; printf 'window.INTRA_RAW={"ts":"%s","d":{' "$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')" > "$T"; f1=1; n=0
  for p in EURUSD:EURUSD=X GBPUSD:GBPUSD=X USDJPY:JPY=X USDCHF:CHF=X AUDUSD:AUDUSD=X USDCAD:CAD=X NZDUSD:NZDUSD=X EURJPY:EURJPY=X GBPJPY:GBPJPY=X EURGBP:EURGBP=X XAUUSD:GC=F XAGUSD:SI=F USOIL:CL=F US500:ES=F NAS100:NQ=F US30:YM=F GER40:^GDAXI BTCUSD:BTC-USD DXY:DX-Y.NYB; do
    k="${p%%:*}"; y="${p#*:}"
    R=$(curl -s --max-time 20 -A "$UA" "https://query1.finance.yahoo.com/v8/finance/chart/$(printf '%s' "$y" | sed 's/\^/%5E/;s/=/%3D/')?range=10d&interval=60m")
    case "$R" in \{*) ;; *) continue;; esac
    [ $f1 -eq 0 ] && printf ',' >> "$T"; f1=0; n=$((n+1)); printf '"%s":%s' "$k" "$R" >> "$T"
  done
  printf '}};\n' >> "$T"
  if [ $n -gt 0 ]; then mv -f "$T" "$IN"; [ -n "$JD" ] && [ -d "$JD/Données" ] && cp -f "$IN" "$JD/Données/intraday.js" 2>/dev/null; else rm -f "$T"; fi
  # Sentiment des particuliers (Myfxbook, page publique) : même cadence que les bougies.
  H=$(curl -sL --max-time 25 -A "$UA" -H "Accept-Language: en" "https://www.myfxbook.com/community/outlook" | head -c 1500000 | base64 | tr -d '\n')
  if [ -n "$H" ]; then printf 'window.RETAIL_RAW={"ts":"%s","src":"myfxbook","b64":"%s"};\n' "$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')" "$H" > "$DIR/retail.js.tmp" && mv -f "$DIR/retail.js.tmp" "$DIR/retail.js"; [ -n "$JD" ] && [ -d "$JD/Données" ] && cp -f "$DIR/retail.js" "$JD/Données/retail.js" 2>/dev/null; fi
fi
echo "$(date '+%F %T') ok" >> "$DIR/news_update.log"
tail -n 200 "$DIR/news_update.log" > "$DIR/news_update.log.t" && mv -f "$DIR/news_update.log.t" "$DIR/news_update.log"
