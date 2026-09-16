import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from import_workbuddy import field,dated_field
from render_report import render
class ImportReportTests(unittest.TestCase):
    def test_ambiguous_field_rejected(self):
        with self.assertRaises(ValueError):field({'MACD1':'2','MACD2':'3'},'MACD')
    def test_wrong_fund_date_rejected(self):
        with self.assertRaises(ValueError):dated_field({'自由流通市值[20260914]':'2'},'自由流通市值[','2026-09-15')
    def test_right_date_accepted(self):
        self.assertEqual(dated_field({'自由流通市值[20260915]':'2'},'自由流通市值[','2026-09-15'),'2')
    def test_report_payload_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.html';render({'name':'</script><script>alert(1)</script>'},p)
            self.assertNotIn('</script><script>alert(1)',p.read_text())
            self.assertIn('\\u003c/script>',p.read_text())
