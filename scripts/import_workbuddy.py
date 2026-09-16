#!/usr/bin/env python3
"""Import saved WorkBuddy v2 CSV evidence; never invoke natural-language screening."""
import argparse, csv, hashlib, json
from pathlib import Path
from screen import number

def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def day(v):return v[:4]+'-'+v[4:6]+'-'+v[6:8] if len(v)==8 else v[:10]
def field(row,needle):
    matches=[k for k in row if needle in k]
    if len(matches)!=1:raise ValueError(f'字段不唯一: {needle}: {matches}')
    return row[matches[0]] or None

def dated_field(row,needle,T):
    expected=needle+T.replace("-","")+"]"
    if expected not in row:raise ValueError("缺少目标日期字段: "+expected)
    return row[expected] or None

def build(src,T,evidence=None):
    src=Path(src);raw=src/'raw';pool=json.loads((src/'pool_codes.json').read_text())
    stocks={c:{'code':c,'name':'','daily':{},'weekly':{},'fund':{'date':T}} for c in pool}
    manifest=[]
    def read(name):
        p=raw/name;rs=rows(p);manifest.append({'file':'raw/'+name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':len(rs)});return rs
    calendar=set()
    def ingest(name,target,mapping):
        for r in read(name):
            code=r['证券代码'];d=day(r['日期'])
            if code not in stocks or d>T:continue
            s=stocks[code];s['name']=r['证券简称'];dest=s[target].setdefault(d,{'date':d})
            for key,needle in mapping.items():
                if key in dest:raise ValueError(f'重复字段 {code} {d} {key}')
                dest[key]=field(r,needle)
            if name=='B_close_vol_65d.csv' and number(dest.get('volume')) is not None and number(dest['volume'])>0:calendar.add(d)
    ingest('B_close_vol_65d.csv','daily',{'close':'收盘价','volume':'成交量'})
    ingest('B_macd_diff_dea.csv','daily',{'macd':'MACD指标选项:MACD','diff':'MACD指标选项:DIFF','dea':'MACD指标选项:DEA'})
    ingest('B_weekly_macd.csv','weekly',{'macd':'MACD指标选项:MACD','diff':'MACD指标选项:DIFF','dea':'MACD指标选项:DEA'})
    ingest('B_cci_dde_10d.csv','daily',{'cci':'CCI顺势指标'})
    ingest('B_pvt_30d.csv','daily',{'vpt':'PVT量价趋势指标'})
    ingest('B_weekly_pvt.csv','weekly',{'vpt':'PVT量价趋势指标'})
    for r in read('F_E_cci100_fund.csv'):
        if r['股票代码'] in stocks:
            stocks[r['股票代码']]['fund'].update(free_float=dated_field(r,'自由流通市值[',T),super_net=dated_field(r,'特大单净额[',T))
    for r in read('F_C_volpct.csv'):
        if r['股票代码'] in stocks:stocks[r['股票代码']]['fund']['pct']=dated_field(r,'涨跌幅:前复权[',T)
    for s in stocks.values():
        code=s['code'];p=code[:3]
        s['board']='其他' if code.endswith('.BJ') else '创业板' if code.endswith('.SZ') and p in ('300','301') else '科创板' if code.endswith('.SH') and p=='688' else '主板' if (code.endswith('.SH') and p in ('600','601','603','605')) or (code.endswith('.SZ') and p in ('000','001','002','003')) else None
    compared=0;diffs=[]
    for r in read('F_A_macd_chain.csv'):
        code=r['股票代码']
        if code not in stocks:continue
        for k,v in r.items():
            if not k.startswith('macd(macd值)['):continue
            d=day(k.split('[')[1].split(']')[0]);a=number(v);b=number(stocks[code]['daily'].get(d,{}).get('macd'))
            if a is None or b is None:continue
            compared+=1
            if abs(a-b)>number('0.005'):diffs.append({'code':code,'date':d,'filter':str(a),'indicator':str(b)})
    universe=read('universe_all_a.csv')
    def profile(ok,source,definition,reason=''):return dict(verified=ok,source=source,definition=definition,reason=reason)
    profiles={
      'prices':profile(True,'raw/B_close_vol_65d.csv','不复权日收盘价，元；成交量同源；简单算术均线'),
      'daily_macd':profile(True,'raw/B_macd_diff_dea.csv','iFinD证券指标日线输出；采用本次记录的12/26/9不复权口径；不与自然语言过滤通道混用'),
      'weekly_macd':profile(True,'raw/B_weekly_macd.csv','iFinD周线指标输出；按自然周末交易日取值，本周截至T；12/26/9不复权'),
      'free_float':profile(True,'raw/F_E_cci100_fund.csv','T日自由流通市值，人民币元'),
      'pct':profile(True,'raw/F_C_volpct.csv','T日涨跌幅:前复权，百分数；独立于不复权走势'),
      'board':profile(True,'股票代码及交易所后缀','已识别A股代码段映射三类板块；北交所不在范围；未识别代码未知')}
    missing={'super_net':'特大单分类与净额定义尚未核实','big_net':'DDE净额、主动大单差額与所需大单净额未证实等价',
       'cci':'CCI源码和参数尚未核实','vpt':'PVT与目标VPT的公式等价性未核实','weekly_vpt':'周PVT与目标VPT的公式等价性未核实',
       'mavpt':'缺少已核实的MAVPT参数和数据','weekly_mavpt':'缺少周MAVPT', 'minute_vpt':'缺少收盘30分钟VPT','minute_mavpt':'缺少收盘30分钟MAVPT',
       'asi':'缺少日ASI数列与参数','minute_asi':'缺少30分钟ASI','minute_asit':'缺少30分钟ASIT'}
    for k,reason in missing.items():profiles[k]=profile(False,'本次导出未能提供完整口径证据','未确认',reason)
    # CSV headers alone do not establish indicator parameters or adjustment basis.
    for key,p in profiles.items():
        if p['verified']:
            p.update(verified=False,reason='本批次口径证据尚未审阅: '+key)
    if evidence:
        if evidence.get('as_of')!=T:raise ValueError('口径证据日期不匹配')
        actual={r['file']:r['sha256'] for r in manifest}
        if evidence.get('files')!=actual:raise ValueError('口径证据与原始CSV哈希不匹配，必须重新审阅')
        profiles.update(evidence.get('profiles',{}))
    for s in stocks.values():
        s['daily']=list(s['daily'].values());s['weekly']=list(s['weekly'].values())
    return {'as_of':T,'calendar':sorted(calendar),'calendar_source':'从本候选池正成交量日期并集推导；非独立交易所日历，待交叉核验',
      'profiles':profiles,'stocks':list(stocks.values()),'scope':{'kind':'candidate_pool','coverage_verified':False,'note':f'仅校验已有{len(pool)}只候选股；全A股导出仅{len(universe)}行，未证明全市场覆盖'},
      'provenance':manifest,'audit':{'macd_comparisons':compared,'macd_mismatch_count':len(diffs),'macd_tolerance':'0.005','macd_mismatches':diffs,
        'notes':['筛选通道与指标通道有数值差异；本次统一使用证券指标通道，尚未与客户端逐值核验','周序列改用自然周和交易日，不按指标数值变化分组','不将未证实的资金定义或PVT别名当作通过','日历为观测数据推导；无完整OHLC，展示真实收盘走势','未证明预筛选无漏选；结论仅限当前候选池']}}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--as-of',required=True);p.add_argument('--out',required=True);p.add_argument('--profiles',help='人工/Agent审阅的口径及原始文件哈希清单');a=p.parse_args()
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(build(a.source,a.as_of,json.loads(Path(a.profiles).read_text()) if a.profiles else None),ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
