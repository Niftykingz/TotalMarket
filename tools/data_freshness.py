"""Audit each daily data surface independently of article publication."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

def audit(root=ROOT, now=None):
    root = Path(root)
    now = now or dt.datetime.now(IST)
    def read(name, fallback):
        p = root / 'data' / name
        return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else fallback
    cal = read('market_calendar.json', {})
    holidays = {h['date'] for y in cal.get('years', []) for h in y.get('holidays', [])}
    expected = now.date() if now.hour >= 20 else now.date() - dt.timedelta(days=1)
    while expected.weekday() >= 5 or expected.isoformat() in holidays:
        expected -= dt.timedelta(days=1)
    target = expected.isoformat()
    findings = []
    def check(name, date):
        date = str(date or '')[:10]
        if not date or date < target:
            findings.append(f'{name}: latest {date or "undated"}; expected {target}')
    fd = read('fii_dii.json', {})
    check('FII/DII cash flows', max((r.get('date','') for r in fd.get('days',[])),default=''))
    for card in read('meta.json',{}).get('ticker',[]):
        if card.get('label') in ('Dow', 'Nasdaq') and str(card.get('asOf','')) >= (expected-dt.timedelta(days=1)).isoformat():
            continue
        check('Ticker / '+card.get('label','unknown'), card.get('asOf'))
    rates = read('rates.json',{})
    check('IBJA gold/silver benchmark', rates.get('benchmark',{}).get('date'))
    check('Retail bullion quotes', rates.get('retailRange',{}).get('date'))
    events = read('corporate_events.json',{})
    check('Corporate calendar verification', events.get('updatedAt'))
    results = read('results.json',[])
    check('Results calendar coverage', max((r.get('date','') for r in results),default=''))
    global_ = read('global.json',{})
    check('Overseas index refresh', global_.get('updatedAt'))
    posts = [json.loads(p.read_text(encoding='utf-8')) for p in (root/'data/posts').glob('*.json')]
    closes = [p for p in posts if p.get('reportType') == 'weekly_market' or 'market-close' in p.get('slug','')]
    check('Market close / sectors / breadth / movers', max((p.get('publishedAt','') for p in closes),default=''))
    return target, findings

if __name__ == '__main__':
    target, findings = audit()
    print(f'Daily data audit, expected session {target}')
    for item in findings:
        print('::error title=Stale daily market data::'+item)
    raise SystemExit(bool(findings))
