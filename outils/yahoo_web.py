#!/usr/bin/env python3
# Cours Yahoo pour le site (GitHub Actions) : session avec cookie + « crumb » (évite les erreurs 429 des serveurs cloud).
# Usage : yahoo_web.py <dossier> <market|intraday|season|rates> [...]
import json,sys,time,random,datetime,os,urllib.request,urllib.parse,http.cookiejar
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
CJ=http.cookiejar.CookieJar();OP=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CJ))
CRUMB=None
def req(u,t=25):
    r=urllib.request.Request(u,headers={'User-Agent':UA,'Accept':'*/*','Accept-Language':'en-US,en;q=0.9'})
    with OP.open(r,timeout=t) as f:return f.read().decode('utf-8','replace')
def init():
    global CRUMB
    for u in ('https://fc.yahoo.com','https://finance.yahoo.com/'):
        try:req(u)
        except Exception:pass
    for h in ('query2','query1'):
        try:
            c=req('https://%s.finance.yahoo.com/v1/test/getcrumb'%h).strip()
            if c and '<' not in c and len(c)<40:CRUMB=c;break
        except Exception as e:print('crumb',h,'échec',e,flush=True)
    print('crumb', 'ok' if CRUMB else 'absent',flush=True)
def chart(sym,rng,itv):
    q='range=%s&interval=%s'%(rng,itv)+('&crumb='+urllib.parse.quote(CRUMB) if CRUMB else '')
    for i in range(4):
        h='query2' if i%2==0 else 'query1'
        try:
            j=json.loads(req('https://%s.finance.yahoo.com/v8/finance/chart/%s?%s'%(h,urllib.parse.quote(sym,safe=''),q)))
            if j.get('chart',{}).get('result'):return j
            return None
        except urllib.error.HTTPError as e:
            if e.code in (429,503,401):time.sleep(2+i*3+random.random()*2);continue
            print('yahoo',sym,'échec',e,flush=True);return None
        except Exception as e:
            time.sleep(2);last=e
    print('yahoo',sym,'échec (429)',flush=True);return None
def ts():return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec='seconds')
def put(D,name,var,obj):
    p=os.path.join(D,name);open(p+'.tmp','w').write('window.%s=%s;\n'%(var,json.dumps(obj,ensure_ascii=False,separators=(',',':'))));os.replace(p+'.tmp',p)
def many(pairs,rng,itv):
    d={}
    for k,y in pairs:
        r=chart(y,rng,itv)
        if r:d[k]=r
        time.sleep(.6+random.random()*.6)
    return d
MKT='EURUSD:EURUSD=X GBPUSD:GBPUSD=X USDJPY:JPY=X AUDUSD:AUDUSD=X NZDUSD:NZDUSD=X USDCAD:CAD=X USDCHF:USDCHF=X EURGBP:EURGBP=X EURJPY:EURJPY=X EURCHF:EURCHF=X EURAUD:EURAUD=X EURCAD:EURCAD=X EURNZD:EURNZD=X GBPJPY:GBPJPY=X GBPCHF:GBPCHF=X GBPAUD:GBPAUD=X GBPCAD:GBPCAD=X GBPNZD:GBPNZD=X AUDJPY:AUDJPY=X AUDNZD:AUDNZD=X AUDCAD:AUDCAD=X AUDCHF:AUDCHF=X NZDJPY:NZDJPY=X NZDCAD:NZDCAD=X NZDCHF:NZDCHF=X CADJPY:CADJPY=X CADCHF:CADCHF=X CHFJPY:CHFJPY=X XAUUSD:GC=F XAGUSD:SI=F XPTUSD:PL=F COPPER:HG=F USOIL:CL=F UKOIL:BZ=F NATGAS:NG=F US500:^GSPC NAS100:^NDX US30:^DJI GER40:^GDAXI UK100:^FTSE FRA40:^FCHI EU50:^STOXX50E JP225:^N225 AUS200:^AXJO HK50:^HSI VIX:^VIX DXY:DX-Y.NYB US10Y:^TNX BTCUSD:BTC-USD ETHUSD:ETH-USD SOLUSD:SOL-USD XRPUSD:XRP-USD'
INTRA='EURUSD:EURUSD=X GBPUSD:GBPUSD=X USDJPY:JPY=X USDCHF:CHF=X AUDUSD:AUDUSD=X USDCAD:CAD=X NZDUSD:NZDUSD=X EURJPY:EURJPY=X GBPJPY:GBPJPY=X EURGBP:EURGBP=X XAUUSD:GC=F XAGUSD:SI=F USOIL:CL=F US500:ES=F NAS100:NQ=F US30:YM=F GER40:^GDAXI BTCUSD:BTC-USD DXY:DX-Y.NYB'
SEAS='EURUSD:EURUSD=X GBPUSD:GBPUSD=X USDJPY:JPY=X USDCHF:CHF=X AUDUSD:AUDUSD=X USDCAD:CAD=X NZDUSD:NZDUSD=X DXY:DX-Y.NYB XAUUSD:GC=F XAGUSD:SI=F USOIL:CL=F US500:^GSPC NAS100:^NDX US30:^DJI GER40:^GDAXI BTCUSD:BTC-USD'
def P(s):return [x.split(':',1) for x in s.split()]
if __name__=='__main__':
    D=sys.argv[1];modes=sys.argv[2:];init()
    if 'market' in modes:
        d=many(P(MKT),'3mo','1d');print('marché',len(d),flush=True)
        if d:put(D,'market.js','MKT',{'ts':ts(),'d':d})
    if 'intraday' in modes:
        d=many(P(INTRA),'10d','60m');print('intraday',len(d),flush=True)
        if d:put(D,'intraday.js','INTRA_RAW',{'ts':ts(),'d':d})
    if 'season' in modes:
        d=many(P(SEAS),'20y','1mo');print('saison',len(d),flush=True)
        if d:put(D,'season.js','SEAS_RAW',{'ts':ts().split('+')[0][:19],'d':d})
    if 'rates' in modes:
        MC='FGHJKMNQUVXZ';n=datetime.date.today();z={}
        for i in range(15):
            mm=(n.month-1+i)%12;yy=n.year+(n.month-1+i)//12
            r=chart('ZQ%s%02d.CBT'%(MC[mm],yy%100),'5d','1d')
            if r:z['%04d-%02d'%(yy,mm+1)]=r
            time.sleep(.6)
        print('taux',len(z),flush=True)
        if z:put(D,'rates.js','RATES_RAW',{'ts':ts().split('+')[0][:19],'zq':z})
