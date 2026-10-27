import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pipeline.closing import update_flow_rows, apply_data, NotReady
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from data_freshness import audit, IST

class DailySync(unittest.TestCase):
    def test_flow_upsert_corrects_without_double_counting(self):
        row={'date':'2026-10-27','fii':{'buy':10.,'sell':4.,'net':6.},'dii':{'buy':5.,'sell':8.,'net':-3.}}
        d={'days':[], 'month':{'label':'October 2026 (to 26 Oct)','fii':{'buy':100.,'sell':80.,'net':20.},'dii':{'buy':100.,'sell':90.,'net':10.}}}
        update_flow_rows(d,copy.deepcopy(row))
        first=copy.deepcopy(d)
        update_flow_rows(d,copy.deepcopy(row)); self.assertEqual(d,first)
        row['fii'].update(buy=12.,net=8.)
        update_flow_rows(d,row)
        self.assertEqual(d['month']['fii']['net'],28.)
        self.assertEqual(len(d['days']),1)

    def test_month_rollover_does_not_carry_last_month(self):
        d={'days':[], 'month':{'label':'October 2026 (to 30 Oct)'}}
        row={'date':'2026-11-02','fii':{'buy':10.,'sell':4.,'net':6.},'dii':{'buy':5.,'sell':8.,'net':-3.}}
        update_flow_rows(d,row)
        self.assertEqual(d['month']['fii']['net'],6.)
        self.assertTrue(d['month']['partial'])

    def test_older_snapshot_cannot_regress_ticker(self):
        with tempfile.TemporaryDirectory() as t:
            data=Path(t)/'data';data.mkdir()
            (data/'meta.json').write_text(json.dumps({'ticker':[{'label':'Nifty 50','asOf':'2026-10-27'}]}))
            with patch('pipeline.closing.dataset',return_value={}):
                with self.assertRaises(NotReady): apply_data('2026-10-26',t)

    def test_new_ipo_does_not_hide_stale_flows_and_weekend_uses_friday(self):
        with tempfile.TemporaryDirectory() as t:
            data=Path(t)/'data';(data/'posts').mkdir(parents=True)
            (data/'posts/ipo.json').write_text(json.dumps({'category':'startups','publishedAt':'2026-10-25T19:00:00+05:30'}))
            (data/'fii_dii.json').write_text(json.dumps({'days':[{'date':'2026-10-22'}]}))
            target, findings=audit(t,dt.datetime(2026,10,25,22,tzinfo=IST))
            self.assertEqual(target,'2026-10-23')
            self.assertTrue(any('FII/DII' in f for f in findings))
            self.assertTrue(any('Market close' in f for f in findings))

    def test_holiday_rolls_back(self):
        with tempfile.TemporaryDirectory() as t:
            data=Path(t)/'data';data.mkdir()
            (data/'market_calendar.json').write_text(json.dumps({'years':[{'holidays':[{'date':'2026-10-20'}]}]}))
            target,_=audit(t,dt.datetime(2026,10,20,22,tzinfo=IST))
            self.assertEqual(target,'2026-10-19')
