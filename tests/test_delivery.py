import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_report import build_report
class DeliveryTests(unittest.TestCase):
    def test_only_fixed_name_self_contained_html(self):
        doc={'as_of':'2026-09-15','calendar':['2026-09-10','2026-09-11','2026-09-14','2026-09-15'],'stocks':[]}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'input.json';source.write_text(json.dumps(doc))
            out=root/'delivery';result=build_report(source,out)
            self.assertEqual(result.name,'选股结果.html')
            self.assertEqual([p.name for p in out.iterdir()],['选股结果.html'])
            html=result.read_text();self.assertIn('"pool": 0',html)
            self.assertNotIn('__SCREEN_DATA__',html)
            self.assertNotIn('同目录 results.json',html)
