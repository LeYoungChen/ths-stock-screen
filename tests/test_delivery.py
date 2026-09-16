import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_report import build_report, validate_universe
class DeliveryTests(unittest.TestCase):
    def test_only_fixed_name_self_contained_html(self):
        doc={'as_of':'2026-09-15','calendar':['2026-09-10','2026-09-11','2026-09-14','2026-09-15'],'stocks':[{'code':'000001.SZ'}], 'scope':{'kind':'full_universe','coverage_verified':True,'evidence':'synthetic fixture','expected_codes':['000001.SZ'],'universe':{'as_of':'2026-09-15','source':'synthetic fixture','total':1}}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'input.json';source.write_text(json.dumps(doc))
            out=root/'delivery';result=build_report(source,out)
            self.assertEqual(result.name,'选股结果.html')
            self.assertEqual([p.name for p in out.iterdir()],['选股结果.html'])
            html=result.read_text();self.assertIn('"pool": 1',html)
            self.assertNotIn('__SCREEN_DATA__',html)
            self.assertNotIn('同目录 results.json',html)

    def test_candidate_pool_rejected(self):
        with self.assertRaises(ValueError):validate_universe({'scope':{'kind':'candidate_pool'},'stocks':[]})
    def test_missing_stock_rejected(self):
        doc={'as_of':'2026-09-15','stocks':[{'code':'a'}], 'scope':{'kind':'full_universe','coverage_verified':True,'evidence':'record','expected_codes':['a','b'],'universe':{'as_of':'2026-09-15','source':'record','total':2}}}
        with self.assertRaises(ValueError):validate_universe(doc)
    def test_workbuddy_requires_ifind(self):
        doc={'runtime':'workbuddy','as_of':'2026-09-15','stocks':[{'code':'a'}], 'scope':{'kind':'full_universe','coverage_verified':True,'evidence':'record','expected_codes':['a'],'universe':{'as_of':'2026-09-15','source':'record','total':1,'provider':'other'}}}
        with self.assertRaises(ValueError):validate_universe(doc)
        doc['scope']['universe']['provider']='ifind-mcp'
        validate_universe(doc)
    def test_stale_universe_rejected(self):
        doc={'as_of':'2026-09-15','stocks':[{'code':'a'}], 'scope':{'kind':'full_universe','coverage_verified':True,'evidence':'record','expected_codes':['a'],'universe':{'as_of':'2026-09-14','source':'record','total':1}}}
        with self.assertRaises(ValueError):validate_universe(doc)
