"""TradingView market widgets (free, TradingView-branded, third-party data).

These widgets show TradingView's own prices; TotalMarket never copies them into articles,
graphics or data files. Each group is labelled with the data level TradingView provides
for widgets (checked in a real browser: .github/workflows/preview-screens.yml).
"""
import html
import json

e = lambda s: html.escape(str(s), quote=True)

# (TradingView symbol, display name). Only symbols confirmed to render in the free widgets.
GROUPS = [
    ("Indian indices", "Delayed about 15 min", [("BSE:SENSEX", "Sensex"), ("NSE:NIFTY", "Nifty 50"), ("NSE:BANKNIFTY", "Bank Nifty"), ("NSE:INDIAVIX", "India VIX")]),
    ("Commodities", "Delayed / indicative", [("TVC:GOLD", "Gold ($/oz)"), ("TVC:SILVER", "Silver ($/oz)"), ("TVC:UKOIL", "Brent crude ($)"), ("TVC:USOIL", "WTI crude ($)")]),
    ("Forex", "Indicative quotes", [("FX_IDC:USDINR", "USD/INR"), ("FX_IDC:EURINR", "EUR/INR"), ("FX_IDC:GBPINR", "GBP/INR"), ("TVC:DXY", "Dollar index")]),
    ("Crypto", "Real-time", [("BINANCE:BTCUSDT", "Bitcoin (USDT)"), ("BINANCE:ETHUSDT", "Ether (USDT)")]),
]

NOTE = ("Prices by TradingView. Indian index and commodity prices are delayed (about 15 minutes for NSE); "
        "currency quotes are indicative; crypto is real-time. These are third-party prices for reference — "
        "TotalMarket's stories use only source-verified figures.")


def _slot(kind, config, cls, label):
    return (f'<div class="tvw {cls}" data-tv="{kind}" data-tv-config="{e(json.dumps(config))}" aria-label="{e(label)}">'
            f'<noscript>Market prices need JavaScript.</noscript></div>')


def ticker_tape():
    syms = [{"proName": s, "title": n} for _, _, items in GROUPS for s, n in items]
    cfg = {"symbols": syms, "showSymbolLogo": False, "isTransparent": True, "displayMode": "regular", "locale": "en"}
    return (f'<section class="tvtape" aria-label="Market prices from TradingView" data-nosnippet>'
            f'{_slot("ticker-tape", cfg, "tape", "Scrolling market prices")}'
            f'<p class="wrap tvnote">TradingView prices · indices delayed ~15 min · forex indicative · crypto real-time</p></section>')


def overview_panel(shead):
    tabs = [{"title": g, "symbols": [{"s": s, "d": n} for s, n in items], "originalTitle": g} for g, _, items in GROUPS]
    cfg = {"tabs": tabs, "showChart": True, "showSymbolLogo": False, "showFloatingTooltip": True, "isTransparent": True,
           "width": "100%", "height": 460, "locale": "en", "dateRange": "1D", "plotLineColorGrowing": "#16a34a",
           "plotLineColorFalling": "#dc2626", "belowLineFillColorGrowing": "rgba(22,163,74,.08)",
           "belowLineFillColorFalling": "rgba(220,38,38,.08)"}
    levels = " · ".join(f"<b>{e(g)}</b>: {e(lv)}" for g, lv, _ in GROUPS)
    return (f'<section class="panel tvpanel" aria-label="Market prices (TradingView)" data-nosnippet>'
            f'{shead}{_slot("market-overview", cfg, "ov", "Market overview by TradingView")}'
            f'<p class="asof tvlev">{levels}</p><p class="dfoot">{e(NOTE)}</p></section>')
