"""CI-only: screenshot preview pages (TradingView widgets need the open internet)."""
import http.server, functools, threading, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
pages = sys.argv[3:]
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for spec in pages:
        path, name = spec.split("=")
        for dev, w, h, mob in (("desktop", 1280, 900, False), ("mobile", 390, 844, True)):
            pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1, is_mobile=mob)
            logs = []
            pg.on("console", lambda m, logs=logs: logs.append(f"{m.type}: {m.text}"[:300]))
            pg.on("pageerror", lambda ex, logs=logs: logs.append(f"pageerror: {ex}"[:300]))
            pg.goto(f"http://127.0.0.1:8765/{path}", wait_until="load", timeout=60000)
            pg.wait_for_timeout(3000)
            pg.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 250)); } window.scrollTo(0, 0); }""")
            pg.wait_for_timeout(15000)
            pg.screenshot(path=str(out / f"{name}-{dev}.png"), full_page=True)
            info = pg.evaluate("""() => [...document.querySelectorAll('.tvw')].map(el => ({tv: el.dataset.tv, loaded: el.dataset.loaded || '', html: el.innerHTML.length,
                iframes: [...el.querySelectorAll('iframe')].map(f => [f.offsetWidth, f.offsetHeight, (f.src||'').slice(0,90)])}))""")
            (out / f"{name}-{dev}.json").write_text(__import__("json").dumps({"widgets": info, "console": logs}, indent=1))
            pg.close()
    b.close()
