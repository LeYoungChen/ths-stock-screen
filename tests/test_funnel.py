import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from screen import build_funnel

def stock(code,fail=(),unknown=()):
    return {'code':code,'conditions':{str(i):{'status':'fail' if i in fail else 'unknown' if i in unknown else 'pass'} for i in range(1,34)}}
class FunnelTests(unittest.TestCase):
    def test_no_double_count_and_unknown_retained(self):
        f=build_funnel([stock('a',(1,10)),stock('b',unknown=(1,)),stock('c',(10,)),stock('d')],{})
        self.assertEqual(f['start'],4);self.assertEqual(f['remaining'],2)
        self.assertEqual(sum(s['removed'] for s in f['steps']),2)
        self.assertEqual(f['steps'][0]['removed_codes'],['a'])
        self.assertEqual(f['steps'][9]['removed_codes'],['c'])
        self.assertEqual(f['pending'],1);self.assertEqual(f['passed'],1)
        self.assertEqual(f['groups'][0]['remaining'],3)
        self.assertEqual(f['groups'][1]['remaining'],2)
        for s in f['steps']:self.assertEqual(s['entered']-s['removed'],s['remaining'])
    def test_empty_pool(self):
        f=build_funnel([],{});self.assertEqual(f['remaining'],0);self.assertEqual(len(f['steps']),33)
    def test_missing_history_is_not_invented(self):
        self.assertEqual(build_funnel([stock('a')],{})['upstream'],[])
    def test_upstream_uses_sets_not_invented_subtractions(self):
        scope={'selection_history':[{'label':'预筛','as_of':'2026-09-15','source':'record.csv','input_codes':['a','b'],'remaining_codes':['a']}]}
        f=build_funnel([stock('a')],scope,'2026-09-15');self.assertEqual(f['upstream'][0]['removed'],1)
        scope['selection_history'][0]['remaining_codes']=['c']
        with self.assertRaises(ValueError):build_funnel([stock('a')],scope,'2026-09-15')
    def test_unconnected_or_wrong_date_history_rejected(self):
        scope={'selection_history':[{'label':'预筛','as_of':'2026-09-14','source':'record','input_codes':['a','b'],'remaining_codes':['b']}]}
        with self.assertRaises(ValueError):build_funnel([stock('a')],scope,'2026-09-15')
