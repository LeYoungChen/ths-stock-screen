import sys, unittest, copy
from pathlib import Path
from datetime import date, timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:
 import screen
except ImportError:
 screen=None

class Rules(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(screen, '需要可执行的固定33项校验引擎')
  dates=[]; d=date(2026,6,1)
  while d<=date(2026,9,15):
   if d.weekday()<5:dates.append(d.isoformat())
   d+=timedelta(days=1)
  keys=['prices','daily_macd','weekly_macd','cci','vpt','mavpt','weekly_vpt','weekly_mavpt','minute_vpt','minute_mavpt','asi','minute_asi','minute_asit','super_net','big_net','free_float','pct','board']
  profiles={k:{'verified':True,'source':'test fixture','definition':'explicit fixture'} for k in keys}
  daily=[{'date':d,'close':str(100+i),'volume':'100','macd':str(i+1),'diff':str(i+2),'dea':'1','cci':str(i+101),'vpt':str(i+1),'mavpt':'0','asi':str(i+1)} for i,d in enumerate(dates)]
  weekly=[{'date':d,'macd':str(i+1),'diff':str(i+2),'dea':'0','vpt':str(i+1),'mavpt':'0'} for i,d in enumerate(['2026-08-28','2026-09-04','2026-09-11','2026-09-15'])]
  self.doc={'as_of':'2026-09-15','calendar':dates,'profiles':profiles,'scope':{'kind':'candidate_pool','coverage_verified':False},'stocks':[{'code':'300001.SZ','name':'测试','board':'创业板','daily':daily,'weekly':weekly,'minute':[{'timestamp':'2026-09-15T15:00:00+08:00','complete':True,'vpt':'2','mavpt':'1','asi':'2','asit':'1'}],'fund':{'date':'2026-09-15','free_float':'2000000000','super_net':'3000000','big_net':'3000000','pct':'1'}}]}
 def calc(self):return screen.evaluate(self.doc)['stocks'][0]
 def test_all_33_pass(self):
  r=self.calc();self.assertEqual(len(r['conditions']),33);self.assertEqual(r['passed'],33);self.assertEqual(r['verdict'],'pass')
 def test_exact_thresholds(self):
  s=self.doc['stocks'][0];s['fund'].update(free_float='1000000000',super_net='1000000',big_net='1000000',pct='0');s['daily'][-1]['volume']='120'
  r=self.calc()['conditions']
  for i in (18,19,20,31,32):self.assertEqual(r[str(i)]['status'],'fail')
 def test_ma_equality_rules(self):
  for r in self.doc['stocks'][0]['daily']:r['close']='100'
  r=self.calc()['conditions']
  self.assertEqual(r['6']['status'],'fail');self.assertEqual(r['8']['status'],'pass');self.assertEqual(r['1']['status'],'fail')
 def test_equal_week_values_remain_distinct(self):
  w=self.doc['stocks'][0]['weekly'];w[-1].update(macd='1',diff='1');w[-2].update(macd='1',diff='1');w[-3].update(macd='-1',diff='-1')
  r=self.calc()['conditions'];self.assertEqual(r['15']['status'],'fail');self.assertEqual(r['16']['status'],'fail')
 def test_missing_week_not_replaced_by_older(self):
  self.doc['stocks'][0]['weekly'].pop(-2)
  self.assertEqual(self.calc()['conditions']['16']['status'],'unknown')
 def test_future_observations_do_not_change_history(self):
  a=self.calc();self.doc['stocks'][0]['daily'].append({'date':'2026-09-16','close':'0','macd':'-99'})
  self.doc['stocks'][0]['weekly'].append({'date':'2026-09-18','macd':'-100'})
  self.assertEqual(a,self.calc())
 def test_missing_date_not_substituted(self):
  self.doc['stocks'][0]['daily'].pop(-2)
  self.assertEqual(self.calc()['conditions']['12']['status'],'unknown')
 def test_missing_dea_not_assumed_pass(self):
  del self.doc['stocks'][0]['daily'][-1]['dea']
  self.assertEqual(self.calc()['conditions']['14']['status'],'unknown')
 def test_unverified_fields_unknown_even_when_values_exist(self):
  for key in ('vpt','super_net','big_net'):self.doc['profiles'][key]['verified']=False
  r=self.calc()['conditions']
  for i in (18,19,23,24,25):self.assertEqual(r[str(i)]['status'],'unknown')
 def test_asi_new_high_is_strict(self):
  s=self.doc['stocks'][0]['daily'];s[-1]['asi']=s[-2]['asi']
  self.assertEqual(self.calc()['conditions']['27']['status'],'fail')
 def test_stale_and_incomplete_minute_unknown(self):
  m=self.doc['stocks'][0]['minute'][0];m['timestamp']='2026-09-15T14:30:00+08:00'
  self.assertEqual(self.calc()['conditions']['26']['status'],'unknown')
  m['timestamp']='2026-09-15T15:00:00+08:00';m['complete']=False
  self.assertEqual(self.calc()['conditions']['28']['status'],'unknown')
 def test_duplicates_rejected(self):
  self.doc['stocks'][0]['daily'].append(copy.deepcopy(self.doc['stocks'][0]['daily'][-1]))
  with self.assertRaises(ValueError):self.calc()
 def test_nonfinite_is_unknown(self):
  self.doc['stocks'][0]['fund']['super_net']='NaN'
  self.assertEqual(self.calc()['conditions']['18']['status'],'unknown')
 def test_zero_denominator_unknown(self):
  self.doc['stocks'][0]['fund']['free_float']='0'
  self.assertEqual(self.calc()['conditions']['18']['status'],'unknown')
 def test_false_and_unknown_is_false(self):
  self.doc['stocks'][0]['daily'][-1]['macd']=None;self.doc['stocks'][0]['daily'][-2]['macd']='-1'
  self.assertEqual(self.calc()['conditions']['13']['status'],'fail')
 def test_scope_does_not_claim_market_coverage(self):
  self.doc['stocks'][0]['fund']['pct']='-1'
  r=screen.evaluate(self.doc);self.assertFalse(r['market_complete']);self.assertEqual(r['scope']['kind'],'candidate_pool')
 def test_fund_date_required(self):
  self.doc['stocks'][0]['fund']['date']='2026-09-14'
  self.assertEqual(self.calc()['conditions']['18']['status'],'unknown')
 def test_chart_contains_only_real_close_data(self):
  r=self.calc();self.assertEqual(r['chart']['kind'],'close');self.assertLessEqual(len(r['chart']['bars']),60)
  self.assertTrue(all('open' not in b for b in r['chart']['bars']))
 def test_ranking_is_deterministic(self):
  s=copy.deepcopy(self.doc['stocks'][0]);s['code']='300002.SZ';s['fund']['pct']='-1';self.doc['stocks'].append(s)
  r=screen.evaluate(self.doc);self.assertEqual(r['stocks'][0]['code'],'300001.SZ')
if __name__=='__main__':unittest.main()
