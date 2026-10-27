"""Conservative public-page fallback when same-day official cash flows are missing.
No login, cookies or access-control workarounds. Both sources must agree.
"""
import argparse
import datetime as dt
from decimal import Decimal
import json
from pathlib import Path
import re
from pipeline.closing import IST, ROOT, update_flow_rows
from pipeline.source_audit import fetch_public_text, clean

MC = 'https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/'
TL = 'https://trendlyne.com/macro-data/fii-dii/latest/'
NUM = r'[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}'

def parse_pair(day, moneycontrol, trendlyne):
    D = dt.date.fromisoformat(day)
    stamp = re.escape(D.strftime('%d-%b-%Y').lower())
    row = re.search(stamp + r'\s+(?:'+stamp+r'\s+)?' + r'\s+'.join('('+NUM+')' for _ in range(6)), clean(moneycontrol))
    if not row:
        raise ValueError('Moneycontrol has no complete same-date cash row')
    vals = [Decimal(v.replace(',','')) for v in row.groups()]
    out = {'date':day}
    for who, v in [('fii',vals[:3]),('dii',vals[3:])]:
        if abs(v[0]-v[1]-v[2]) > Decimal('0.02'):
            raise ValueError('cash purchases minus sales does not reconcile')
        pat = who+r' were net (buyers|sellers) of\s*₹?\s*('+NUM+r')\s*cr in the cash segment on\s*'+re.escape(D.strftime('%d %b %Y').lstrip('0').lower())
        m = re.search(pat, clean(trendlyne))
        if not m:
            raise ValueError('Trendlyne has no same-date corroboration')
        net = abs(Decimal(m[2].replace(',',''))) * (-1 if m[1]=='sellers' else 1)
        if net != v[2]:
            raise ValueError('cash net figures disagree between sources')
        out[who] = dict(zip(('buy','sell','net'),map(float,v)))
    return out

def refresh(day, root=ROOT, fetcher=fetch_public_text):
    p=Path(root)/'data/fii_dii.json'
    fd=json.loads(p.read_text(encoding='utf-8'))
    latest=max((r.get('date','') for r in fd.get('days',[])),default='')
    if latest >= day:
        return 'same-date or newer verified flows already saved'
    row=parse_pair(day,fetcher(MC),fetcher(TL))
    row['source']={'name':'Moneycontrol: provisional cash activity; net flows corroborated with Trendlyne','url':MC}
    row['verifiedAt']=dt.datetime.now(IST).replace(microsecond=0).isoformat()
    update_flow_rows(fd,row)
    fd['source']=row['source'];fd['updatedAt']=row['verifiedAt']
    fd['corroboratingSources']=[{'name':'Trendlyne: same-date net cash flows','url':TL}]
    p.write_text(json.dumps(fd,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    return 'updated provisional cash flows from two agreeing dated sources'

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--date',default=dt.datetime.now(IST).date().isoformat());a=ap.parse_args()
    try:
        print(refresh(a.date))
    except Exception as exc:
        # Keep prior dated values; the later collector run retries and freshness alerts stay active.
        print('::warning title=Awaiting verified cash flows::'+str(exc))
