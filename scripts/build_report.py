#!/usr/bin/env python3
"""Generate the sole user deliverable: 选股结果.html. No sidecar files."""
import argparse
import json
from pathlib import Path
from screen import evaluate
from render_report import render

def build_report(source,out_dir):
    result=evaluate(json.loads(Path(source).read_text(encoding='utf-8')))
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
