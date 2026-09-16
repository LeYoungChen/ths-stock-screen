#!/usr/bin/env python3
"""Generate the sole user deliverable: 选股结果.html. No sidecar files."""
import argparse
import json
from pathlib import Path
from screen import evaluate
from render_report import render

def validate_universe(doc):
    scope=doc.get('scope',{});universe=scope.get('universe',{})
    expected=scope.get('expected_codes',[])
    actual=[s['code'] for s in doc.get('stocks',[])]
    if (scope.get('kind')!='full_universe' or scope.get('coverage_verified') is not True
        or not scope.get('evidence') or not expected or len(expected)!=len(set(expected))
        or len(actual)!=len(set(actual)) or set(actual)!=set(expected)
        or not universe.get('source') or universe.get('as_of')!=doc.get('as_of')
        or isinstance(universe.get('total'),bool) or universe.get('total')!=len(expected)):
        raise ValueError('全A股覆盖校验未通过：须提供同日完整名录、来源、核对总数和每只股票记录；不能交付候选池作为最终结果')
    if doc.get('runtime','').lower() in ('workbuddy','workbuddy-ai') and universe.get('provider')!='ifind-mcp':
        raise ValueError('WorkBuddy必须直接调用同花顺ifind-mcp连接器取得全A股名录和数据')

def build_report(source,out_dir):
    doc=json.loads(Path(source).read_text(encoding='utf-8'))
    validate_universe(doc)
    result=evaluate(doc)
    directory=Path(out_dir);directory.mkdir(parents=True,exist_ok=True)
    report=directory/'选股结果.html'
    render(result,report)
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True)
    parser.add_argument('--out-dir',default='.',help='仅写入选股结果.html的交付目录')
    args=parser.parse_args()
    print(build_report(args.input,args.out_dir).resolve())
if __name__=='__main__':main()
