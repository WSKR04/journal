#!/bin/bash
# Télécharge les données lentes du journal : COT (CFTC), saisonnalité (Yahoo), macro (Banque mondiale, BIS) et futures Fed Funds.
# Installé par « Données auto - Activer.command » (toutes les 6 heures). Dépendances : curl (macOS).
DIR="$HOME/Library/Application Support/TradingJournal"; mkdir -p "$DIR"
LOG="$DIR/data_update.log"; UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
JD="$(cat "$DIR/news_journal_dir" 2>/dev/null)"
put(){ mv -f "$DIR/$1.tmp" "$DIR/$1"; [ -n "$JD" ] && [ -d "$JD/Données" ] && cp -f "$DIR/$1" "$JD/Données/$1" 2>/dev/null; }
ok(){ case "$1" in \[*|\{*) return 0;; *) return 1;; esac; }
# --- COT (Legacy, futures only) : 2 ans, marchés suivis
CODES="'099741','096742','097741','092741','090741','232741','112741','095741','098662','088691','084691','067651','13874A','209742','124603','133741'"
J=$(curl -sG --max-time 60 -A "$UA" "https://publicreporting.cftc.gov/resource/6dca-aqww.json" \
  --data-urlencode "\$select=market_and_exchange_names,report_date_as_yyyy_mm_dd,cftc_contract_market_code,open_interest_all,noncomm_positions_long_all,noncomm_positions_short_all,comm_positions_long_all,comm_positions_short_all,nonrept_positions_long_all,nonrept_positions_short_all" \
  --data-urlencode "\$where=cftc_contract_market_code in($CODES) AND report_date_as_yyyy_mm_dd > '$(date -v-800d +%Y-%m-%d 2>/dev/null || date -d '-800 days' +%Y-%m-%d)'" \
  --data-urlencode "\$order=report_date_as_yyyy_mm_dd DESC" --data-urlencode "\$limit=5000")
if ok "$J"; then printf 'window.COT_RAW={"ts":"%s","d":%s};\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$J" > "$DIR/cot.js.tmp" && put cot.js && echo "$(date '+%F %T') cot ok" >> "$LOG"; else echo "$(date '+%F %T') cot échec" >> "$LOG"; fi
# --- Saisonnalité : historique mensuel 20 ans (Yahoo)
SYMS="EURUSD:EURUSD=X GBPUSD:GBPUSD=X USDJPY:JPY=X USDCHF:CHF=X AUDUSD:AUDUSD=X USDCAD:CAD=X NZDUSD:NZDUSD=X DXY:DX-Y.NYB XAUUSD:GC=F XAGUSD:SI=F USOIL:CL=F US500:^GSPC NAS100:^NDX US30:^DJI GER40:^GDAXI BTCUSD:BTC-USD"
OUT="$DIR/season.js.tmp"; printf 'window.SEAS_RAW={"ts":"%s","d":{' "$(date +%Y-%m-%dT%H:%M:%S)" > "$OUT"; first=1; n=0
for p in $SYMS; do k="${p%%:*}"; y="${p#*:}"
  R=$(curl -s --max-time 30 -A "$UA" "https://query1.finance.yahoo.com/v8/finance/chart/$(printf '%s' "$y" | sed 's/\^/%5E/;s/=/%3D/')?range=20y&interval=1mo")
  ok "$R" || continue
  [ $first -eq 0 ] && printf ',' >> "$OUT"; first=0; n=$((n+1)); printf '"%s":%s' "$k" "$R" >> "$OUT"; sleep 1
done
printf '}};\n' >> "$OUT"
if [ $n -gt 0 ]; then put season.js; echo "$(date '+%F %T') saison ok ($n)" >> "$LOG"; else rm -f "$OUT"; echo "$(date '+%F %T') saison échec" >> "$LOG"; fi

# --- Macro : Banque mondiale (annuel, 2001+) + BIS via DBnomics (taux directeurs, inflation mensuelle)
OUT="$DIR/macro.js.tmp"; printf 'window.MACRO_RAW={"ts":"%s","wb":{' "$(date +%Y-%m-%dT%H:%M:%S)" > "$OUT"; first=1; n=0
for ind in FP.CPI.TOTL.ZG NY.GDP.MKTP.KD.ZG SL.UEM.TOTL.ZS BN.CAB.XOKA.GD.ZS GC.DOD.TOTL.GD.ZS NY.GDP.MKTP.CD; do
  R=$(curl -s --max-time 60 -A "$UA" "https://api.worldbank.org/v2/country/all/indicator/$ind?format=json&date=2001:$(date +%Y)&per_page=20000")
  ok "$R" || continue; [ $first -eq 0 ] && printf ',' >> "$OUT"; first=0; n=$((n+1)); printf '"%s":%s' "$ind" "$R" >> "$OUT"
done
C=$(curl -s --max-time 60 -A "$UA" "https://api.worldbank.org/v2/country?format=json&per_page=400"); ok "$C" || C=null
G="M.US+M.XM+M.GB+M.JP+M.CH+M.CA+M.AU+M.NZ"
P=$(curl -s --max-time 60 -A "$UA" "https://api.db.nomics.world/v22/series/BIS/WS_CBPOL/$G?observations=1&format=json"); ok "$P" || P=null
Q=$(curl -s --max-time 60 -A "$UA" "https://api.db.nomics.world/v22/series/BIS/WS_LONG_CPI/M.US.771+M.XM.771+M.GB.771+M.JP.771+M.CH.771+M.CA.771+M.AU.771+M.NZ.771+M.US.628+M.XM.628+M.GB.628+M.JP.628+M.CH.628+M.CA.628+M.AU.628+M.NZ.628?observations=1&format=json"); ok "$Q" || Q=null
printf '},"ctry":%s,"pol":%s,"cpi":%s};\n' "$C" "$P" "$Q" >> "$OUT"
if [ $n -gt 0 ] || [ "$P" != null ]; then put macro.js; echo "$(date '+%F %T') macro ok ($n)" >> "$LOG"; else rm -f "$OUT"; echo "$(date '+%F %T') macro échec" >> "$LOG"; fi
# --- Fed Funds futures (Yahoo, CBOT) : 15 prochains mois → probabilités FOMC
OUT="$DIR/rates.js.tmp"; printf 'window.RATES_RAW={"ts":"%s","zq":{' "$(date +%Y-%m-%dT%H:%M:%S)" > "$OUT"; first=1; n=0
MC=(F G H J K M N Q U V X Z); y=$(date +%Y); m=$((10#$(date +%m)))
for i in $(seq 0 14); do mm=$(( (m-1+i)%12 )); yy=$(( y + (m-1+i)/12 )); t="ZQ${MC[$mm]}$(printf '%02d' $((yy%100))).CBT"
  R=$(curl -s --max-time 20 -A "$UA" "https://query1.finance.yahoo.com/v8/finance/chart/$t?range=5d&interval=1d")
  ok "$R" || continue; [ $first -eq 0 ] && printf ',' >> "$OUT"; first=0; n=$((n+1)); printf '"%04d-%02d":%s' "$yy" "$((mm+1))" "$R" >> "$OUT"; sleep 1
done
printf '}};\n' >> "$OUT"
if [ $n -gt 0 ]; then put rates.js; echo "$(date '+%F %T') rates ok ($n)" >> "$LOG"; else rm -f "$OUT"; echo "$(date '+%F %T') rates échec" >> "$LOG"; fi
tail -n 200 "$LOG" > "$LOG.t" && mv -f "$LOG.t" "$LOG"
