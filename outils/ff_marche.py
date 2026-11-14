#!/usr/bin/env python3
# Calendrier Forex Factory (semaine en cours + suivante) -> ff_calendar.js (les cours Yahoo sont dans yahoo_web.py)
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
