#!/usr/bin/env python3
# Cours pour le site (GitHub Actions), sans clé : Kraken (forex, or via PAXG, crypto) + FRED / Réserve fédérale de St. Louis
# (indices US, Nikkei, VIX, taux 10 ans, pétrole, gaz, NZD, historiques longs). Paires manquantes recalculées (croisements).
# Sortie au même format que Yahoo (chart.result[0]) : market.js, intraday.js, season.js.
# Usage : marches_web.py <dossier> <market|intraday|season> [...]
import json,sys,time,datetime,os,urllib.request,csv,io,math
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
def get(u,t=30,n=3):
    for i in range(n):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=t) as f:return f.read().decode('utf-8','replace')
        except Exception as e:
            err=e;time.sleep(2+i*3)
    raise err
def log(*a):print(*a,flush=True)
# ---------- Kraken ----------
KR={'EURUSD':'EURUSD','GBPUSD':'GBPUSD','USDJPY':'USDJPY','AUDUSD':'AUDUSD','USDCAD':'USDCAD','USDCHF':'USDCHF','EURGBP':'EURGBP','EURJPY':'EURJPY','EURCHF':'EURCHF','EURAUD':'EURAUD','EURCAD':'EURCAD','AUDJPY':'AUDJPY','XAUUSD':'PAXGUSD','BTCUSD':'XBTUSD','ETHUSD':'ETHUSD','SOLUSD':'SOLUSD','XRPUSD':'XRPUSD'}
def kraken(pair,itv):
    j=json.loads(get('https://api.kraken.com/0/public/OHLC?pair=%s&interval=%d'%(pair,itv)));time.sleep(1.2)
    if j.get('error'):raise Exception(';'.join(j['error']))
    k=[x for x in j['result'] if x!='last'][0]
    return {int(r[0]):(float(r[1]),float(r[2]),float(r[3]),float(r[4])) for r in j['result'][k]}
# ---------- FRED ----------
FB=[0]  # échecs FRED d'affilée : FRED ralentit parfois les serveurs cloud -> abandon rapide
FK=os.environ.get('FRED_KEY','').strip()
def fred(sid,since):
    if FK:  # API officielle (clé gratuite) : fiable depuis GitHub
        j=json.loads(get('https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s&file_type=json&observation_start=%s'%(sid,FK,since),30,2));time.sleep(.6)
        out={}
        for o in j.get('observations',[]):
            try:v=float(o['value'])
            except (ValueError,KeyError):continue
            d=datetime.datetime.strptime(o['date'][:10],'%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
            out[int(d.timestamp())]=(v,v,v,v)
        return out
    if FB[0]>=2:raise Exception('FRED injoignable depuis ce serveur (ajoute le secret FRED_KEY), ignoré')
    try:t=get('https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=%s'%(sid,since),20,1);FB[0]=0
    except Exception:FB[0]+=1;raise
    time.sleep(.5)
    out={}
    for r in csv.reader(io.StringIO(t)):
        if len(r)<2 or r[1] in ('','.') or not r[0][:1].isdigit():continue
        try:v=float(r[1])
        except ValueError:continue
        d=datetime.datetime.strptime(r[0][:10],'%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
        out[int(d.timestamp())]=(v,v,v,v)
    return out
# ---------- BCE via Frankfurter (sans clé, journalier) ----------
def bce(base,quote,since):
    j=json.loads(get('https://api.frankfurter.dev/v1/%s..?base=%s&symbols=%s'%(since,base,quote),30,2));time.sleep(.3)
    out={}
    for d,r in j.get('rates',{}).items():
        v=r.get(quote)
        if v:out[int(datetime.datetime.strptime(d,'%Y-%m-%d').replace(tzinfo=datetime.timezone.utc).timestamp())]=(v,v,v,v)
    return out
# ---------- CBOE (indices US, VIX, taux 10 ans ; OHLC depuis 1975, sans clé) ----------
CB={}
def cboe(sym,mult=1.0):
    if sym not in CB:
        j=json.loads(get('https://cdn-api.cboe.com/api/global/delayed_quotes/charts/historical/%s.json'%sym,60))
        out={}
        for r in j.get('data',[]):
            try:
                c=float(r['close'])*mult;o=float(r['open'])*mult or c;h=float(r['high'])*mult or c;l=float(r['low'])*mult or c
                d=datetime.datetime.strptime(r['date'][:10],'%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
                if c>0:out[int(d.timestamp())]=(o,h,l,c)
            except Exception:pass
        CB[sym]=out;time.sleep(.5)
    return CB[sym]
CBS={'US500':('_SPX',1),'NAS100':('_NDX',1),'US30':('_DJX',100),'VIX':('_VIX',1),'US10Y':('_TNX',.1)}
def inv(s):return {t:(1/o,1/l,1/h,1/c) for t,(o,h,l,c) in s.items() if o and l and h and c}
def mul(a,b):
    return {t:(a[t][0]*b[t][0],a[t][1]*b[t][1],a[t][2]*b[t][2],a[t][3]*b[t][3]) for t in a if t in b}
def div(a,b):return mul(a,inv(b))
def dayk(s):  # clé jour (UTC) pour aligner Kraken (00:00) et FRED
    return {t-t%86400:v for t,v in s.items()}
def dxy(S):
    need=['EURUSD','USDJPY','GBPUSD','USDCAD','USDCHF']
    if not all(k in S for k in need):return None
    ts=set.intersection(*[set(S[k]) for k in need]);out={}
    for t in sorted(ts):
        row=[]
        for i in range(4):
            e,j,g,c,f=(S[k][t][i] for k in need)
            sek=11.0/e  # USDSEK approché (EURSEK ~ 11)
            row.append(50.14348112*e**-0.576*j**0.136*g**-0.119*c**0.091*sek**0.042*f**0.036)
        o,a,b,c=row;out[t]=(o,max(row),min(row),c)
    return out
def chart(sym,s,itv):
    ts=sorted(s);q={'open':[],'high':[],'low':[],'close':[],'volume':[]}
    for t in ts:
        o,h,l,c=s[t];h=max(h,o,c,l);l=min(l,o,c,h)
        for k,v in (('open',o),('high',h),('low',l),('close',c)):q[k].append(round(v,6))
        q['volume'].append(0)
    return {'chart':{'result':[{'meta':{'symbol':sym,'dataGranularity':itv,'gmtoffset':0},'timestamp':ts,'indicators':{'quote':[q]}}],'error':None}}
def ts():return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec='seconds')
def put(D,name,var,obj):
    p=os.path.join(D,name);open(p+'.tmp','w').write('window.%s=%s;\n'%(var,json.dumps(obj,separators=(',',':'))));os.replace(p+'.tmp',p)
def crosses(S):
    X=[('GBPJPY','GBPUSD','*','USDJPY'),('GBPCHF','GBPUSD','*','USDCHF'),('GBPAUD','GBPUSD','/','AUDUSD'),('GBPCAD','GBPUSD','*','USDCAD'),
       ('AUDCAD','AUDUSD','*','USDCAD'),('AUDCHF','AUDUSD','*','USDCHF'),('CADJPY','USDJPY','/','USDCAD'),('CADCHF','USDCHF','/','USDCAD'),('CHFJPY','USDJPY','/','USDCHF'),
       ('EURNZD','EURUSD','/','NZDUSD'),('GBPNZD','GBPUSD','/','NZDUSD'),('AUDNZD','AUDUSD','/','NZDUSD'),('NZDJPY','NZDUSD','*','USDJPY'),('NZDCAD','NZDUSD','*','USDCAD'),('NZDCHF','NZDUSD','*','USDCHF')]
    for k,a,op,b in X:
        if k not in S and a in S and b in S:
            r=mul(S[a],S[b]) if op=='*' else div(S[a],S[b])
            if r:S[k]=r
    d=dxy(S)
    if d:S['DXY']=d
FREDI={'US500':'SP500','NAS100':'NASDAQ100','US30':'DJIA','VIX':'VIXCLS','US10Y':'DGS10'}
FREDD={'NZDUSD':'DEXUSNZ','USOIL':'DCOILWTICO','UKOIL':'DCOILBRENTEU','NATGAS':'DHHNGSP','JP225':'NIKKEI225'}
def market(D):
    S={}
    for k,p in KR.items():
        try:S[k]=dayk(kraken(p,1440))
        except Exception as e:log('kraken',k,'échec',e)
    for k,(sy,m) in CBS.items():
        try:S[k]=cboe(sy,m)
        except Exception as e:log('cboe',k,'échec',e)
    since=(datetime.date.today()-datetime.timedelta(days=200)).isoformat()
    try:S['NZDUSD']=bce('NZD','USD',since)
    except Exception as e:log('bce NZDUSD échec',e)
    for k,sid in list(FREDI.items())+list(FREDD.items()):
        if k in S and len(S[k])>5:continue
        try:S[k]=fred(sid,since)
        except Exception as e:log('fred',k,'échec',e)
    crosses(S)
    lim=int(time.time())-100*86400;d={}
    for k,s in S.items():
        s={t:v for t,v in s.items() if t>=lim}
        if len(s)>5:d[k]=chart(k,s,'1d')
    log('marché',len(d),'actifs :',' '.join(sorted(d)))
    if d:put(D,'market.js','MKT',{'ts':ts(),'d':d})
def intraday(D):
    S={}
    for k in ('EURUSD','GBPUSD','USDJPY','USDCHF','AUDUSD','USDCAD','EURJPY','EURGBP','XAUUSD','BTCUSD'):
        try:S[k]=kraken(KR[k],60)
        except Exception as e:log('kraken 1h',k,'échec',e)
    if 'GBPUSD' in S and 'USDJPY' in S:S['GBPJPY']=mul(S['GBPUSD'],S['USDJPY'])
    x=dxy(S)
    if x:S['DXY']=x
    lim=int(time.time())-10*86400;d={}
    for k,s in S.items():
        s={t:v for t,v in s.items() if t>=lim}
        if len(s)>5:d[k]=chart(k,s,'60m')
    log('intraday',len(d),'actifs :',' '.join(sorted(d)))
    if d:put(D,'intraday.js','INTRA_RAW',{'ts':ts(),'d':d})
FREDL={'EURUSD':('DEXUSEU',0),'GBPUSD':('DEXUSUK',0),'USDJPY':('DEXJPUS',0),'USDCHF':('DEXSZUS',0),'AUDUSD':('DEXUSAL',0),'USDCAD':('DEXCAUS',0),'NZDUSD':('DEXUSNZ',0),
       'DXY':('DTWEXBGS',0),'USOIL':('DCOILWTICO',0)}
def monthly(s):
    m={}
    for t in sorted(s):
        d=datetime.datetime.fromtimestamp(t,datetime.timezone.utc);k=int(datetime.datetime(d.year,d.month,1,tzinfo=datetime.timezone.utc).timestamp())
        o,h,l,c=s[t]
        if k not in m:m[k]=[o,h,l,c]
        else:m[k][1]=max(m[k][1],h);m[k][2]=min(m[k][2],l);m[k][3]=c
    return {k:tuple(v) for k,v in m.items()}
def season(D):
    since=(datetime.date.today()-datetime.timedelta(days=365*20+10)).isoformat();d={};lim=int(time.time())-(365*20+10)*86400
    for k in ('US500','NAS100','US30'):
        try:
            sy,m=CBS[k];s=monthly({t:v for t,v in cboe(sy,m).items() if t>=lim})
            if len(s)>24:d[k]=chart(k,s,'1mo')
        except Exception as e:
            log('cboe saison',k,'échec',e)
            try:
                s=monthly(fred(FREDI[k],since))
                if len(s)>24:d[k]=chart(k,s,'1mo')
            except Exception as e2:log('fred saison',k,'échec',e2)
    for k,(sid,_) in FREDL.items():
        try:
            s=monthly(fred(sid,since))
            if len(s)>24:d[k]=chart(k,s,'1mo')
        except Exception as e:log('fred saison',k,'échec',e)
    for k in ['XAUUSD','BTCUSD']+[x for x in ('EURUSD','GBPUSD','USDJPY','USDCHF','AUDUSD','USDCAD') if x not in d]:
        try:
            s=monthly(dayk(kraken(KR[k],1440)))
            if len(s)>12:d[k]=chart(k,s,'1mo')
        except Exception as e:log('kraken saison',k,'échec',e)
    log('saison',len(d),'actifs :',' '.join(sorted(d)))
    if d:put(D,'season.js','SEAS_RAW',{'ts':ts().split('+')[0][:19],'d':d})
def rates(D):
    # Trajectoire attendue des Fed Funds estimée par la courbe des bons du Trésor (FRED), recalée sur le taux effectif (EFFR).
    since=(datetime.date.today()-datetime.timedelta(days=20)).isoformat();L={}
    for k,sid in (('ef','EFFR'),('m1','DGS1MO'),('m3','DGS3MO'),('m6','DGS6MO'),('y1','DGS1')):
        try:
            s=fred(sid,since)
            if s:L[k]=s[max(s)][3]
        except Exception as e:log('fred rates',sid,'échec',e)
    if not all(k in L for k in ('ef','m1','m3','m6','y1')):log('rates : données FRED incomplètes',sorted(L));return
    off=L['ef']-L['m1']  # écart bons du Trésor / Fed Funds
    seg=[(0,1,L['m1']),(1,3,(3*L['m3']-L['m1'])/2),(3,6,(6*L['m6']-3*L['m3'])/3),(6,12,(12*L['y1']-6*L['m6'])/6),(12,15,(12*L['y1']-6*L['m6'])/6)]
    today=datetime.date.today();zq={}
    for i in range(15):
        f=[v for a,b,v in seg if a<=i<b][0]+off;y=today.year+(today.month-1+i)//12;m=(today.month-1+i)%12+1
        zq['%04d-%02d'%(y,m)]={'chart':{'result':[{'meta':{'regularMarketPrice':round(100-f,4)}}]}}
    log('rates estimés (FRED) : EFFR %.2f, 1M %.2f, 3M %.2f, 6M %.2f, 1A %.2f'%(L['ef'],L['m1'],L['m3'],L['m6'],L['y1']))
    put(D,'rates.js','RATES_RAW',{'ts':ts().split('+')[0][:19],'src':'fred','zq':zq})
if __name__=='__main__':
    D=sys.argv[1]
    for m in sys.argv[2:]:
        try:{'market':market,'intraday':intraday,'season':season,'rates':rates}[m](D)
        except Exception as e:log(m,'échec',e)
