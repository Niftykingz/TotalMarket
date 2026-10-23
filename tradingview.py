"""TradingView market widgets (free, TradingView-branded, third-party data).

These widgets show TradingView's own prices; TotalMarket never copies them into articles,
graphics or data files. Each group is labelled with the data level TradingView provides
for widgets (checked in a real browser: .github/workflows/preview-screens.yml).
"""
import html
import json

e = lambda s: html.escape(str(s), quote=True)

# (group, data level as TradingView provides it to free widgets, [(symbol, name)]).
# Checked in a real browser on 24 Oct 2026: NSE and MCX symbols are NOT available in free
# widgets ("only available on TradingView"); BSE indices come as end-of-day data ("E" badge).
GROUPS = [
    ("India", "BSE indices, end of day", [("BSE:SENSEX", "Sensex"), ("BSE:BSE100", "BSE 100"), ("BSE:BSE500", "BSE 500"), ("BSE:BANK", "BSE Bankex")]),
    ("Commodities", "International prices, indicative", [("OANDA:XAUUSD", "Gold ($/oz)"), ("OANDA:XAGUSD", "Silver ($/oz)"), ("TVC:UKOIL", "Brent crude ($)"), ("TVC:USOIL", "WTI crude ($)"), ("CAPITALCOM:NATURALGAS", "Natural gas ($)")]),
    ("Forex", "Indicative quotes", [("FX_IDC:USDINR", "USD/INR"), ("FX_IDC:EURINR", "EUR/INR"), ("FX_IDC:GBPINR", "GBP/INR"), ("FX_IDC:JPYINR", "JPY/INR"), ("CAPITALCOM:DXY", "Dollar index")]),
    ("Crypto", "Real-time", [("BINANCE:BTCUSDT", "Bitcoin"), ("BINANCE:ETHUSDT", "Ether"), ("BINANCE:SOLUSDT", "Solana"), ("BINANCE:XRPUSDT", "XRP")]),
    ("Global", "Index CFDs, indicative", [("FOREXCOM:SPXUSD", "S&P 500 (CFD)"), ("FOREXCOM:DJI", "Dow Jones (CFD)"), ("FOREXCOM:NSXUSD", "Nasdaq 100 (CFD)"), ("CAPITALCOM:J225", "Japan 225 (CFD)"), ("CAPITALCOM:HK50", "Hong Kong 50 (CFD)")]),
]

NOTE = ("Prices by TradingView, shown for reference. NSE (Nifty) and MCX prices are not available in TradingView's free widgets; "
        "BSE indices are end of day, global indices are CFD prices, commodity and currency quotes are indicative, crypto is real-time. "
        "TotalMarket's stories use only source-verified figures.")


def _slot(kind, config, cls, label):
    return (f'<div class="tvw {cls}" data-tv="{kind}" data-tv-config="{e(json.dumps(config))}" aria-label="{e(label)}">'
            f'<noscript>Market prices need JavaScript.</noscript></div>')


def ticker_tape():
    picks = ["BSE:SENSEX", "OANDA:XAUUSD", "OANDA:XAGUSD", "TVC:UKOIL", "FX_IDC:USDINR", "BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "FOREXCOM:SPXUSD", "FOREXCOM:NSXUSD"]
    names = {s: n for _, _, items in GROUPS for s, n in items}
    cfg = {"symbols": [{"proName": s, "title": names[s]} for s in picks], "showSymbolLogo": False, "isTransparent": True,
           "displayMode": "regular", "locale": "en"}
    return (f'<section class="tvtape" aria-label="Market prices from TradingView" data-nosnippet>'
            f'{_slot("ticker-tape", cfg, "tape", "Scrolling market prices")}'
            f'<p class="tvnote">Prices by TradingView · Sensex end of day · gold, oil, forex indicative · crypto real-time · Nifty not available</p></section>')


def overview_panel(shead):
    tabs, panels = [], []
    for i, (g, level, items) in enumerate(GROUPS):
        tabs.append(f'<button type="button" class="wt{" on" if i == 0 else ""}" data-panel="tvp{i}">{e(g)}</button>')
        cards = "".join(_slot("single-quote", {"symbol": s, "width": "100%", "isTransparent": True, "locale": "en"}, "q", n)
                        for s, n in items)
        panels.append(f'<div class="tvgrid" id="tvp{i}"{"" if i == 0 else " hidden"}><p class="asof tvlev">{e(level)}</p>{cards}</div>')
    return (f'<section class="panel tvpanel" aria-label="Market prices (TradingView)" data-nosnippet>'
            f'{shead}<div class="wtabs">{"".join(tabs)}</div>{"".join(panels)}<p class="dfoot">{e(NOTE)}</p></section>')
