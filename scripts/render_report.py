#!/usr/bin/env python3
"""Render an offline heatmap and price chart from deterministic results."""
import argparse,json
from pathlib import Path

def render(result,out):
    template=(Path(__file__).parent.parent/'assets'/'dashboard.html').read_text(encoding='utf-8')
    payload=json.dumps(result,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    Path(out).write_text(template.replace('__SCREEN_DATA__',payload),encoding='utf-8')
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);a=p.parse_args();render(json.loads(Path(a.input).read_text()),a.out)
if __name__=='__main__':main()
