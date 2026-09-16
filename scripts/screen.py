#!/usr/bin/env python3
"""Deterministic, offline, end-of-day 33-rule evaluator. Python stdlib only."""
import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

VERSION = '2.1.0'
LABELS = ['收盘>MA5','收盘>MA10','收盘>MA20','收盘>MA30','收盘>MA60',
          'MA5上行','MA10上行','MA20不下降','MA30不下降','MACD d2>d3','MACD d1>d2','MACD d0>d1',
          '三日MACD>0','三日DIFF>DEA','周MACD上行','三周MACD>0','三周DIFF>DEA',
          '特大单/市值>0.1%','大单/市值>0.1%','自由流通市值>10亿',
          '三周VPT>MAVPT','三日VPT>MAVPT','VPT d2>d3','VPT d1>d2','VPT d0>d1',
          '30分VPT>MAVPT','ASI严格10日新高','30分ASI>ASIT','CCI>100','CCI上行','成交量<1.2倍','涨幅>0','板块范围']
GROUPS = [('均线',1,9),('日MACD',10,14),('周MACD',15,17),('资金市值',18,20),('VPT',21,26),('ASI / CCI',27,30),('量价范围',31,33)]
TZ = timezone(timedelta(hours=8))

def number(v):
    if v is None or isinstance(v,bool): return None
    try:
        n=Decimal(str(v).strip())
        return n if n.is_finite() else None
    except (InvalidOperation,ValueError): return None

def iso(d):
    return date.fromisoformat(d).isoformat()

def monday(d):
    x=date.fromisoformat(d)
    return (x-timedelta(days=x.weekday())).isoformat()

def keyed(rows,T):
    out={}
    for r in rows:
        d=iso(r['date'])
        if d>T: continue
        if d in out: raise ValueError('重复日期: '+d)
        out[d]=r
    return out

def cmp(a,b,op='gt'):
    a,b=number(a),number(b)
    if a is None or b is None:return None
    return a>b if op=='gt' else a>=b if op=='ge' else a<b

def conjunction(vals):
    if any(v is False for v in vals):return False
    if not vals or any(v is None for v in vals):return None
    return True

def plain(v):
    if isinstance(v,Decimal):return str(v)
    if isinstance(v,dict):return {k:plain(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [plain(x) for x in v]
    return v

def chart_data(daily,cal,T):
    bars=[]
    for d in cal:
        r=daily.get(d,{})
        c=number(r.get('close'));v=number(r.get('volume'))
        if c is None or c<=0 or v is None or v<=0:continue
        b={'date':d,'close':float(c),'volume':float(v)}
        o,h,l=[number(r.get(k)) for k in ('open','high','low')]
        if all(x is not None and x>0 for x in (o,h,l)) and h>=max(o,c) and l<=min(o,c):
            b.update(open=float(o),high=float(h),low=float(l))
        bars.append(b)
    bars=bars[-60:]
    changes={}
    # Return windows use trading dates, not the last n available observations.
    for n in (5,20,60):
        a=number(daily.get(T,{}).get('close'))
        b=number(daily.get(cal[-1-n],{}).get('close')) if len(cal)>n else None
        changes[str(n)]=float((a/b-1)*100) if a is not None and b is not None and b>0 else None
    return {'kind':'candlestick' if bars and all('open' in b for b in bars) else 'close',
            'bars':bars,'changes':changes,'basis':'不复权收盘价变化，非含分红总回报'}

def build_funnel(stocks,scope,T=None):
    """Sequential replay: only confirmed failures remove a stock, once."""
    current={s['code']:s for s in stocks};steps=[];pending=set();upstream=[]
    previous=None
    for stage in scope.get('selection_history',[]):
        before=stage['input_codes'];after=stage['remaining_codes']
        if len(before)!=len(set(before)) or len(after)!=len(set(after)):
            raise ValueError('预筛历史代码重复')
        before,after=set(before),set(after)
        if not stage.get('source') or stage.get('as_of')!=T or not stage.get('label'):
            raise ValueError('预筛历史缺少来源、名称或日期不匹配')
        if not after<=before or (previous is not None and before!=previous):
            raise ValueError('预筛历史必须是连续的逐步子集，不能拼接独立查询数量')
        upstream.append({'label':stage['label'],'entered':len(before),'removed':len(before-after),
                         'remaining':len(after),'removed_codes':sorted(before-after),'source':stage['source']})
        previous=after
    if previous is not None and previous!=set(current):raise ValueError('预筛终点与本次输入候选池不一致')
    start=len(current)
    for i,label in enumerate(LABELS,1):
        entered=len(current)
        removed=sorted(c for c,s in current.items() if s['conditions'][str(i)]['status']=='fail')
        pending.update(c for c,s in current.items() if s['conditions'][str(i)]['status']=='unknown')
        for c in removed:del current[c]
        pending.intersection_update(current)
        steps.append({'rule':i,'label':label,'entered':entered,'removed':len(removed),
                      'remaining':len(current),'pending':len(pending),'removed_codes':removed})
    groups=[]
    for label,a,b in GROUPS:
        group=steps[a-1:b]
        groups.append({'label':label,'entered':group[0]['entered'],'removed':sum(x['removed'] for x in group),
                       'remaining':group[-1]['remaining'],'pending':group[-1]['pending']})
    return {'start':start,'upstream':upstream,'steps':steps,'groups':groups,'remaining':len(current),
            'pending':len(pending),'passed':len(current)-len(pending),
            'note':'按条件1–33顺序回放，股票只在首次已知失败处扣除；待核验保留。扣除归因随顺序变化，最终结果不变。'}

def evaluate(doc):
    T=iso(doc['as_of'])
    rawcal=doc['calendar']
    if len(rawcal)!=len(set(rawcal)):raise ValueError('交易日历重复')
    cal=sorted(iso(d) for d in rawcal if iso(d)<=T)
    if len(cal)<4 or cal[-1]!=T:raise ValueError('截至日必须在显式交易日历中，至少需要4个交易日')
    ds=list(reversed(cal[-4:]))
    weeks=sorted(set(monday(d) for d in cal))[-3:][::-1]
    ends=[max(d for d in cal if monday(d)==w) for w in weeks]
    out=[];seen=set()
    for s in doc['stocks']:
        code=s['code']
        if code in seen:raise ValueError('股票代码重复: '+code)
        seen.add(code)
        daily=keyed(s.get('daily',[]),T);weekly=keyed(s.get('weekly',[]),T)
        profiles={**doc.get('profiles',{}),**s.get('profiles',{})}
        fund=s.get('fund',{}) if s.get('fund',{}).get('date')==T else {}
        conditions={}
        def add(i,result,values,fields,reason=''):
            bad=[k for k in fields if profiles.get(k,{}).get('verified') is not True or not profiles.get(k,{}).get('source') or not profiles.get(k,{}).get('definition')]
            if bad:
                result=None
                reason='；'.join(profiles.get(k,{}).get('reason') or ('口径未确认: '+k) for k in bad)
            conditions[str(i)]={'label':LABELS[i-1],'status':'pass' if result is True else 'fail' if result is False else 'unknown',
                'values':plain(values),'reason':reason or ('缺少对应日期的有效数据' if result is None else ''),
                'sources':list(dict.fromkeys(profiles.get(k,{}).get('source','未取得') for k in fields)),
                'definitions':{k:profiles.get(k,{}).get('definition','未确认') for k in fields}}
        def val(d,k):return number(daily.get(d,{}).get(k))
        def avg(n,d):
            j=cal.index(d);win=cal[max(0,j-n+1):j+1]
            if len(win)!=n:return None
            vals=[val(x,'close') for x in win]
            # Missing/zero volume is treated as a missing trading bar, not forward-filled.
            if any(x is None or x<=0 for x in vals) or any(val(x,'volume') is None or val(x,'volume')<=0 for x in win):return None
            return sum(vals)/n
        for i,n in enumerate((5,10,20,30,60),1):
            a,b=val(T,'close'),avg(n,T);add(i,cmp(a,b),{T:{'close':a,'ma':b,'period':n}},['prices'])
        for i,n in enumerate((5,10,20,30),6):
            a,b=avg(n,T),avg(n,ds[1]);add(i,cmp(a,b,'gt' if n in (5,10) else 'ge'),{T:a,ds[1]:b,'period':n},['prices'])
        for i,(a,b) in enumerate(((ds[2],ds[3]),(ds[1],ds[2]),(ds[0],ds[1])),10):
            va,vb=val(a,'macd'),val(b,'macd');add(i,cmp(va,vb),{a:va,b:vb},['daily_macd'])
        add(13,conjunction([cmp(val(d,'macd'),0) for d in ds[:3]]),{d:val(d,'macd') for d in ds[:3]},['daily_macd'])
        add(14,conjunction([cmp(val(d,'diff'),val(d,'dea')) for d in ds[:3]]),{d:{'diff':val(d,'diff'),'dea':val(d,'dea')} for d in ds[:3]},['daily_macd'])
        wm=[number(weekly.get(d,{}).get('macd')) for d in ends]
        add(15,cmp(wm[0],wm[1]) if len(wm)>=2 else None,dict(zip(ends,wm)),['weekly_macd'])
        add(16,conjunction([cmp(x,0) for x in wm]) if len(wm)==3 else None,dict(zip(ends,wm)),['weekly_macd'])
        wp={d:{'diff':number(weekly.get(d,{}).get('diff')),'dea':number(weekly.get(d,{}).get('dea'))} for d in ends}
        add(17,conjunction([cmp(x['diff'],x['dea']) for x in wp.values()]) if len(wp)==3 else None,wp,['weekly_macd'])
        ff=number(fund.get('free_float'))
        for i,key in ((18,'super_net'),(19,'big_net')):
            a=number(fund.get(key));ratio=a/ff if a is not None and ff is not None and ff>0 else None
            add(i,cmp(ratio,'0.001'),{'date':T,'net_cny':a,'free_float_cny':ff,'ratio':ratio},[key,'free_float'])
        add(20,cmp(ff,'1000000000'),{'date':T,'cny':ff},['free_float'])
        vals={d:{k:number(weekly.get(d,{}).get(k)) for k in ('vpt','mavpt')} for d in ends}
        add(21,conjunction([cmp(v['vpt'],v['mavpt']) for v in vals.values()]) if len(vals)==3 else None,vals,['weekly_vpt','weekly_mavpt'])
        vals={d:{k:val(d,k) for k in ('vpt','mavpt')} for d in ds[:3]}
        add(22,conjunction([cmp(v['vpt'],v['mavpt']) for v in vals.values()]),vals,['vpt','mavpt'])
        for i,(a,b) in enumerate(((ds[2],ds[3]),(ds[1],ds[2]),(ds[0],ds[1])),23):
            va,vb=val(a,'vpt'),val(b,'vpt');add(i,cmp(va,vb),{a:va,b:vb},['vpt'])
        end=datetime.fromisoformat(T+'T15:00:00+08:00');minute={}
        matches=[]
        for r in s.get('minute',[]):
            ts=datetime.fromisoformat(r['timestamp'])
            if ts.tzinfo is None:raise ValueError('分钟线时间必须含时区')
            if ts.astimezone(TZ)==end and r.get('complete') is True:matches.append(r)
        if len(matches)>1:raise ValueError('收盘分钟线重复')
        if matches:minute=matches[0]
        add(26,cmp(minute.get('vpt'),minute.get('mavpt')),minute,['minute_vpt','minute_mavpt'])
        av={d:val(d,'asi') for d in cal[-10:]}
        checks=[cmp(av.get(T),v) for d,v in av.items() if d!=T]
        add(27,conjunction(checks) if len(av)==10 else None,av,['asi'])
        add(28,cmp(minute.get('asi'),minute.get('asit')),minute,['minute_asi','minute_asit'])
        add(29,cmp(val(T,'cci'),100),{T:val(T,'cci')},['cci'])
        add(30,cmp(val(T,'cci'),val(ds[1],'cci')),{T:val(T,'cci'),ds[1]:val(ds[1],'cci')},['cci'])
        a,b=val(T,'volume'),val(ds[1],'volume')
        add(31,cmp(a,b*Decimal('1.2'),'lt') if b is not None and b>0 and a is not None and a>0 else None,{T:a,ds[1]:b},['prices'])
        add(32,cmp(fund.get('pct'),0),{'date':T,'pct':fund.get('pct')},['pct'])
        bd=s.get('board')
        add(33,bd in ('主板','创业板','科创板') if bd else None,{'board':bd},['board'])
        counts={st:sum(c['status']==st for c in conditions.values()) for st in ('pass','fail','unknown')}
        verdict='pass' if counts['pass']==33 else 'fail' if counts['fail'] else 'pending'
        out.append({'code':code,'name':s.get('name',''),'board':bd or '待核验','conditions':conditions,
                    'passed':counts['pass'],'failed':counts['fail'],'unknown':counts['unknown'],
                    'verdict':verdict,'chart':chart_data(daily,cal,T)})
    # Unknown never counts as a pass; use fixed denominator 33. No price/momentum-based return prediction.
    out.sort(key=lambda r:(r['verdict']!='pass',-r['passed'],r['failed'],r['code']))
    scope=doc.get('scope',{'kind':'candidate_pool','coverage_verified':False})
    complete=scope.get('kind')=='full_universe' and scope.get('coverage_verified') is True and bool(scope.get('evidence')) and scope.get('expected_codes') is not None and set(scope['expected_codes'])==seen
    return {'version':VERSION,'as_of':T,'dates':ds,'labels':LABELS,'groups':GROUPS,'scope':scope,'market_complete':complete,
            'funnel':build_funnel(out,scope,T),'stocks':out,'audit':doc.get('audit',{}),'calendar_source':doc.get('calendar_source','未注明'),
            'totals':{'pool':len(out),'pass':sum(r['verdict']=='pass' for r in out),'pending':sum(r['verdict']=='pending' for r in out),'fail':sum(r['verdict']=='fail' for r in out)},
            'ranking':'按通过数降序、失败数升序、代码排序；固定分母33；不代表收益预测',
            'provenance':doc.get('provenance',[])}

def write_outputs(result,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'funnel.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['条件编号','条件','进入','本步剔除','剩余','剩余中累计待核验','本步剔除代码'])
        for s in result['funnel']['steps']:w.writerow([s['rule'],s['label'],s['entered'],s['removed'],s['remaining'],s['pending'],';'.join(s['removed_codes'])])
    with (out/'conditions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['代码','名称','条件编号','条件','状态','实际值','原因'])
        for s in result['stocks']:
            for i,c in s['conditions'].items():w.writerow([s['code'],s['name'],i,c['label'],c['status'],json.dumps(c['values'],ensure_ascii=False),c['reason']])
    for filename,predicate in [('passed.csv',lambda s:s['verdict']=='pass'),('partial.csv',lambda s:s['verdict']!='pass')]:
        with (out/filename).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['代码','名称','通过','不通过','未知','5日收盘变化%','20日收盘变化%','范围'])
            for s in result['stocks']:
                if predicate(s):w.writerow([s['code'],s['name'],s['passed'],s['failed'],s['unknown'],s['chart']['changes']['5'],s['chart']['changes']['20'],'当前候选池'])

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();r=evaluate(json.loads(Path(a.input).read_text()));write_outputs(r,a.out)
    print(json.dumps(r['totals'],ensure_ascii=False))
if __name__=='__main__':main()
