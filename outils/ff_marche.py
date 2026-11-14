#!/usr/bin/env python3
# Calendrier Forex Factory (semaine en cours + suivante) et cours journaliers Yahoo (3 mois) -> ff_calendar.js, market.js
import json,sys,time,urllib.request,urllib.parse,datetime,os
D=sys.argv[1];UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
def get(u,t=30):
    r=urllib.request.Request(u,headers={'User-Agent':UA,'Accept':'application/json'})
    with urllib.request.urlopen(r,timeout=t) as f:return json.load(f)
ts=datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec='seconds')
def put(name,var,obj):
    p=os.path.join(D,name);open(p+'.tmp','w').write('window.%s=%s;\n'%(var,json.dumps(obj,ensure_ascii=False,separators=(',',':'))));os.replace(p+'.tmp',p)
it=[]
for w in ('thisweek','nextweek'):
    try:
        a=get('https://nfs.faireconomy.media/ff_calendar_%s.json'%w)
        if isinstance(a,list):it+=a
    except Exception as e:print('ff',w,'échec',e)
if it:put('ff_calendar.js','FF_CAL',{'ts':ts,'items':it});print('ff ok',len(it))
S='EURUSD:EURUSD=X GBPUSD:GBPUSD=X USDJPY:JPY=X AUDUSD:AUDUSD=X NZDUSD:NZDUSD=X USDCAD:CAD=X USDCHF:USDCHF=X EURGBP:EURGBP=X EURJPY:EURJPY=X EURCHF:EURCHF=X EURAUD:EURAUD=X EURCAD:EURCAD=X EURNZD:EURNZD=X GBPJPY:GBPJPY=X GBPCHF:GBPCHF=X GBPAUD:GBPAUD=X GBPCAD:GBPCAD=X GBPNZD:GBPNZD=X AUDJPY:AUDJPY=X AUDNZD:AUDNZD=X AUDCAD:AUDCAD=X AUDCHF:AUDCHF=X NZDJPY:NZDJPY=X NZDCAD:NZDCAD=X NZDCHF:NZDCHF=X CADJPY:CADJPY=X CADCHF:CADCHF=X CHFJPY:CHFJPY=X XAUUSD:GC=F XAGUSD:SI=F XPTUSD:PL=F COPPER:HG=F USOIL:CL=F UKOIL:BZ=F NATGAS:NG=F US500:^GSPC NAS100:^NDX US30:^DJI GER40:^GDAXI UK100:^FTSE FRA40:^FCHI EU50:^STOXX50E JP225:^N225 AUS200:^AXJO HK50:^HSI VIX:^VIX DXY:DX-Y.NYB US10Y:^TNX BTCUSD:BTC-USD ETHUSD:ETH-USD SOLUSD:SOL-USD XRPUSD:XRP-USD'
d={}
for p in S.split():
    k,y=p.split(':',1)
    try:
        r=get('https://query1.finance.yahoo.com/v8/finance/chart/%s?range=3mo&interval=1d'%urllib.parse.quote(y,safe=''),20)
        if isinstance(r,dict) and r.get('chart',{}).get('result'):d[k]=r
    except Exception as e:print('yahoo',k,'échec',e)
    time.sleep(.4)
if d:put('market.js','MKT',{'ts':ts,'d':d});print('marché ok',len(d))
