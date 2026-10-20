"""Evergreen tool pages for TotalMarket: gold & silver rates (national + city) and
SIP / EMI calculators. Every page teaches as well as shows numbers: plain-language
lessons, worked examples and FAQs, written like a teacher walking a reader through it.

Data: data/rates.json (refreshed by the scheduled runs, see RUNBOOK.md).
Called from build.py; returns (path, html) pairs plus sitemap URLs.
"""
import json, os
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))


def inr(n, dec=0):
    """Indian digit grouping: 1234567 -> 12,34,567."""
    neg = n < 0
    n = abs(n)
    s = f"{n:.{dec}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + tail
    return ("-" if neg else "") + "₹" + whole + (("." + frac) if frac else "")


def lakh(n):
    if n >= 1e7:
        return f"₹{n/1e7:.2f} crore"
    return f"₹{n/1e5:.2f} lakh"


def dlabel(s):
    d = date.fromisoformat(s)
    return d.strftime("%a %-d %b %Y")


def load_rates():
    p = os.path.join(ROOT, "data", "rates.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


# ---------- maths used both for worked examples and checked against the JS ----------
def sip_fv(monthly, annual_pct, years):
    i = annual_pct / 100 / 12
    n = int(years * 12)
    return monthly * ((1 + i) ** n - 1) / i * (1 + i)


def emi(principal, annual_pct, years):
    r = annual_pct / 100 / 12
    n = int(years * 12)
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def faq_ld(qas):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qas]}


def faq_html(qas, e):
    return ('<section class="lesson"><h2>Questions people ask</h2>'
            + "".join(f'<details class="faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qas)
            + "</section>")


def build(page, e, base, site_url, meta):
    """Return list of (relative_path, html) and list of absolute sitemap URLs."""
    out, urls = [], []
    rates = load_rates()
    if rates:
        for rel, html in gold_pages(rates, page, e, base, meta):
            out.append((rel, html)); urls.append(site_url + "/" + rel.replace("index.html", ""))
    for rel, html in calc_pages(page, e, base, meta):
        out.append((rel, html)); urls.append(site_url + "/" + rel.replace("index.html", ""))
    return out, urls


# ------------------------------------------------------------------ gold & silver
def gold_numbers(r):
    b = r["benchmark"]
    g = b["gold"]
    hist = r.get("history") or []
    prev = hist[-2] if len(hist) >= 2 else None
    ch24 = g["999"] - prev["gold999"] if prev else None
    ch22 = g["916"] - prev["gold916"] if prev else None
    chs = b["silver999"] - prev["silver999"] if prev else None
    return g, b, ch24, ch22, chs


def kpi(label, value, change=None, sub=""):
    cls = ""
    c = ""
    if change is not None:
        cls = " up" if change >= 0 else ""
        sign = "+" if change >= 0 else "−"
        c = f'<span class="c">{sign}{inr(abs(change))} vs previous day</span>'
    return f'<div class="rp-kpi{cls}"><span class="l">{label}</span><span class="v">{value}</span>{c}</div>'


def gold_lesson(g, e):
    # Worked jewellery example on today's 22K benchmark
    per_g = g["916"] / 10
    grams = 10
    metal = per_g * grams
    making = metal * 0.12
    gst = (metal + making) * 0.03
    total = metal + making + gst
    return f"""<section class="lesson">
<h2>Class in 3 minutes: how to read a gold rate</h2>
<ol class="steps">
<li><b>Know the purity.</b> 24 karat (also written 999) is 99.9% pure gold. It is used for coins and bars. Jewellery is usually 22 karat (916), which is 91.6% gold mixed with other metals so it is strong enough to wear. 18 karat (750) is 75% gold and is common in diamond jewellery. Less gold means a lower price per gram.</li>
<li><b>Know the unit.</b> Rates are quoted per 10 grams for gold and per kilogram for silver. Divide by 10 to get the price of one gram of gold.</li>
<li><b>Know what is included.</b> The benchmark rate from IBJA, the jewellers' association, does not include GST or making charges. That is why the shop price is always higher than the number on this page.</li>
<li><b>Know why cities differ.</b> Local jewellers' associations add their own margins and transport and local costs, so Chennai, Mumbai and Delhi can differ by a few hundred rupees.</li>
</ol>
<div class="worked"><b>Worked example: what will a 10 g 22K chain cost?</b>
<table class="dt"><tbody>
<tr><th scope="row">22K rate per gram (today's benchmark ÷ 10)</th><td class="num">{inr(per_g)}</td></tr>
<tr><th scope="row">Gold value for {grams} g</th><td class="num">{inr(metal)}</td></tr>
<tr><th scope="row">Making charges (say 12%; shops charge 8–25%)</th><td class="num">{inr(making)}</td></tr>
<tr><th scope="row">GST at 3% on gold + making</th><td class="num">{inr(gst)}</td></tr>
<tr><th scope="row"><b>Bill you should expect</b></th><td class="num"><b>{inr(total)}</b></td></tr>
</tbody></table>
<p class="wnote">Making charges are the part you can negotiate. Ask the shop to show them as a separate line on the bill, and check the BIS hallmark (HUID number) for purity.</p></div>
</section>"""


def gold_calc(g, silver):
    return f"""<section class="lesson calc" data-calc="gold" data-g24="{g['999']}" data-g22="{g['916']}" data-g18="{g['750']}" data-silver="{silver}">
<h2>Try it: what is my gold worth?</h2>
<p>Enter the weight and purity. The calculator uses today's benchmark rate, so it shows the metal value only, before GST and making charges.</p>
<div class="cform">
<label>Weight (grams)<input type="number" name="grams" value="10" min="0" step="0.1" inputmode="decimal"></label>
<label>Metal<select name="purity"><option value="g24">Gold 24K (999)</option><option value="g22" selected>Gold 22K (916)</option><option value="g18">Gold 18K (750)</option><option value="silver">Silver 999</option></select></label>
<label class="chk"><input type="checkbox" name="gst"> Add 3% GST</label>
</div>
<div class="cout"><span>Value</span><b data-out="value">—</b><small data-out="explain"></small></div>
</section>"""


def gold_pages(r, page, e, base, meta):
    g, b, ch24, ch22, chs = gold_numbers(r)
    d = dlabel(b["date"])
    silver = b["silver999"]
    rr = r.get("retailRange") or {}
    cs = r.get("citySource") or {}
    hist = list(reversed(r.get("history") or []))
    pages = []

    kpis = ('<div class="rp-kpis">'
            + kpi("24K gold · 10 g", inr(g["999"]), ch24)
            + kpi("22K gold · 10 g", inr(g["916"]), ch22)
            + kpi("18K gold · 10 g", inr(g["750"]))
            + kpi("Silver 999 · 1 kg", inr(silver), chs)
            + "</div>")
    per_gram = (f'<div class="tablewrap"><table class="dt"><caption>Price per gram (benchmark, before GST)</caption><thead><tr><th>Purity</th><th>1 g</th><th>8 g (1 sovereign)</th><th>10 g</th></tr></thead><tbody>'
                + "".join(f'<tr><th scope="row">{lbl}</th><td class="num">{inr(g[k]/10)}</td><td class="num">{inr(g[k]/10*8)}</td><td class="num">{inr(g[k])}</td></tr>'
                          for k, lbl in (("999", "24K (999)"), ("916", "22K (916)"), ("750", "18K (750)"), ("585", "14K (585)")))
                + "</tbody></table></div>")
    retail = ""
    if rr:
        lo24, hi24 = rr["gold24"]; lo22, hi22 = rr["gold22"]
        retail = (f'<p class="why"><b>Shop rates today ({e(dlabel(rr["date"]))}):</b> 24K {inr(lo24)}–{inr(hi24)} and 22K {inr(lo22)}–{inr(hi22)} per 10 g, as quoted by '
                  + " and ".join(f'<a href="{e(s["url"])}" rel="nofollow noopener">{e(s["name"])}</a>' for s in rr.get("sources", []))
                  + '. Jewellers add GST and making charges on top.</p>')
    city_rows = "".join(
        f'<tr><th scope="row"><a href="{base}gold-rate-today/{c["slug"]}/">Gold rate in {e(c["name"])}</a></th><td class="num">{inr(c["gold24"])}</td><td class="num">{inr(c["gold22"])}</td></tr>'
        for c in r.get("cities", []))
    cities = (f'<section class="lesson"><h2>Gold rate today in your city</h2><p>Shop rates per 10 g quoted by <a href="{e(cs.get("url"))}" rel="nofollow noopener">{e(cs.get("name"))}</a> ({e(cs.get("asOf"))}). Tap a city for its own page.</p>'
              f'<div class="tablewrap"><table class="dt"><thead><tr><th>City</th><th>24K</th><th>22K</th></tr></thead><tbody>{city_rows}</tbody></table></div></section>') if city_rows else ""
    hist_rows = "".join(f'<tr><th scope="row">{e(dlabel(h["date"]))}</th><td class="num">{inr(h["gold999"])}</td><td class="num">{inr(h["gold916"])}</td><td class="num">{inr(h["silver999"])}</td></tr>' for h in hist)
    history = (f'<section class="lesson"><h2>Gold and silver rate: last {len(hist)} trading days</h2>'
               f'<p>Read this table from top to bottom to see the trend. IBJA publishes on market days only, so weekends and holidays are missing.</p>'
               f'<div class="tablewrap"><table class="dt"><thead><tr><th>Date</th><th>24K / 10 g</th><th>22K / 10 g</th><th>Silver / kg</th></tr></thead><tbody>{hist_rows}</tbody></table></div></section>')
    qas = [
        ("What is the gold rate today in India?", f"The IBJA benchmark for {d} ({b['session']}) is {inr(g['999'])} per 10 grams for 24 karat and {inr(g['916'])} for 22 karat, before 3% GST and making charges."),
        ("What is the silver rate today per kg?", f"The IBJA benchmark for silver 999 on {d} is {inr(silver)} per kilogram, before GST."),
        ("Why is the jeweller's price higher than the rate online?", "Shops add 3% GST, making charges (usually 8–25% of the gold value) and sometimes wastage. Online benchmark rates show the metal only."),
        ("Which is better to buy, 22K or 24K?", "That depends on the purpose. 24K is purer and is used for coins and bars; 22K is harder and is used for jewellery. TotalMarket explains prices but does not recommend buying or selling."),
        ("How often is this page updated?", "The rates refresh with TotalMarket's scheduled updates on every market day, usually in the morning, at midday and after the close."),
    ]
    sources = (f'<section class="sources"><h2>Sources</h2><ul><li><a href="{e(b["url"])}" rel="nofollow noopener">{e(b["source"])}</a> — benchmark rates</li>'
               + (f'<li><a href="{e(cs["url"])}" rel="nofollow noopener">{e(cs["name"])}</a> — city rates</li>' if cs else "")
               + "</ul></section>")
    body = (f'<article class="story tool"><nav class="crumbs"><a href="{base}">Home</a> / <a href="{base}commodities/">Commodities &amp; Forex</a></nav>'
            f'<h1>Gold rate today in India: 24K, 22K and silver price</h1>'
            f'<p class="dek">Benchmark rates for {e(d)} ({e(b["session"])} session), explained step by step so you know what you will actually pay.</p>'
            f'{kpis}<p class="wnote">{e(b.get("note", ""))}</p>{retail}{gold_calc(g, silver)}{per_gram}{cities}{gold_lesson(g, e)}{history}{faq_html(qas, e)}{sources}'
            f'<p class="disc">Rates are for information only. TotalMarket does not recommend buying or selling gold or silver.</p></article>')
    ld = faq_ld(qas)
    pages.append(("gold-rate-today/index.html", page(
        f"Gold rate today in India", f"Gold rate today: 24K {inr(g['999'])}, 22K {inr(g['916'])} per 10 g and silver {inr(silver)} per kg (IBJA, {d}). City rates, history and a jewellery price calculator.",
        f"{base}gold-rate-today/", body, meta,
        seo_title=f"Gold Rate Today ({date.fromisoformat(b['date']).strftime('%-d %b %Y')}): 24K, 22K, 18K & Silver Price in India | TotalMarket",
        keywords=["gold rate today", "gold price today India", "22 carat gold rate", "24 carat gold rate", "18 carat gold rate", "silver rate today",
                  "silver price per kg", "IBJA gold rate", "gold rate per gram", "gold rate Delhi", "gold rate Mumbai", "gold rate Chennai",
                  "gold rate Bangalore", "gold rate Hyderabad", "gold rate Kolkata", "making charges gold", "gold GST", "1 sovereign gold rate"],
        extra_head=f'<script type="application/ld+json">{json.dumps(ld)}</script><script src="{base}assets/tools.js" defer></script>')))

    for c in r.get("cities", []):
        name = c["name"]
        diff24 = c["gold24"] - g["999"]
        others = " · ".join(f'<a href="{base}gold-rate-today/{o["slug"]}/">{e(o["name"])}</a>' for o in r["cities"] if o is not c)
        cq = [
            (f"What is the gold rate in {name} today?", f"Shops in {name} were quoted at {inr(c['gold24'])} for 24K and {inr(c['gold22'])} for 22K per 10 grams ({cs.get('asOf')}, {cs.get('name')})."),
            (f"Why is the {name} gold rate different from the national rate?", f"The {name} shop rate was {inr(abs(diff24))} {'above' if diff24 >= 0 else 'below'} the IBJA benchmark. Local jewellers' associations set city rates and include their own costs and margins."),
            (f"Does the {name} rate include GST?", "No. Add 3% GST and the shop's making charges to estimate your bill."),
        ]
        cbody = (f'<article class="story tool"><nav class="crumbs"><a href="{base}">Home</a> / <a href="{base}gold-rate-today/">Gold rate today</a></nav>'
                 f'<h1>Gold rate today in {e(name)}</h1>'
                 f'<p class="dek">22K and 24K gold price in {e(name)} per gram and per 10 grams, with how to work out your jewellery bill.</p>'
                 '<div class="rp-kpis">'
                 + kpi(f"24K in {e(name)} · 10 g", inr(c["gold24"])) + kpi(f"22K in {e(name)} · 10 g", inr(c["gold22"]))
                 + kpi("22K per gram", inr(c["gold22"] / 10)) + kpi("Silver · 1 kg (national)", inr(silver)) + "</div>"
                 + f'<p class="wnote">City rates from <a href="{e(cs.get("url"))}" rel="nofollow noopener">{e(cs.get("name"))}</a>, {e(cs.get("asOf"))}. Silver is the IBJA national benchmark for {e(d)}.</p>'
                 + f'<p class="why"><b>How {e(name)} compares:</b> the 24K shop rate here is {inr(abs(diff24))} {"above" if diff24 >= 0 else "below"} the national benchmark of {inr(g["999"])}. '
                   f'That gap is normal: it covers the local association\'s margin and costs. It is not GST, which is added on top at the counter.</p>'
                 + gold_calc({"999": c["gold24"], "916": c["gold22"], "750": g["750"]}, silver)
                 + gold_lesson({"916": c["gold22"]}, e)
                 + faq_html(cq, e)
                 + f'<section class="lesson"><h2>Gold rate in other cities</h2><p>{others} · <a href="{base}gold-rate-today/">All India rate</a></p></section>'
                 + f'<p class="disc">Rates are for information only. TotalMarket does not recommend buying or selling gold or silver.</p></article>')
        pages.append((f"gold-rate-today/{c['slug']}/index.html", page(
            f"Gold rate today in {name}", f"Gold rate in {name} today: 24K {inr(c['gold24'])} and 22K {inr(c['gold22'])} per 10 g. Per-gram prices and a jewellery bill calculator.",
            f"{base}gold-rate-today/{c['slug']}/", cbody, meta,
            seo_title=f"Gold Rate in {name} Today: 22K & 24K Price per Gram | TotalMarket",
            keywords=[f"gold rate in {name}", f"{name} gold rate today", f"22 carat gold rate {name}", f"24 carat gold rate {name}", f"gold price {name}",
                      f"silver rate {name}", "gold rate per gram", "gold making charges", "gold rate today"],
            extra_head=f'<script type="application/ld+json">{json.dumps(faq_ld(cq))}</script><script src="{base}assets/tools.js" defer></script>')))
    return pages


# ------------------------------------------------------------------ calculators
def calc_pages(page, e, base, meta):
    out = []
    # SIP worked examples (computed here so the lesson numbers are exact)
    ex = sip_fv(5000, 12, 10); inv = 5000 * 120
    ex20 = sip_fv(5000, 12, 20); inv20 = 5000 * 240
    sip_q = [
        ("What is a SIP?", "A systematic investment plan (SIP) means investing a fixed amount in a mutual fund every month instead of a lump sum. Each instalment buys units at that day's price."),
        ("How is SIP return calculated?", "This calculator uses the standard future-value formula with monthly compounding: FV = P × [((1 + i)^n − 1) ÷ i] × (1 + i), where P is the monthly amount, i is the yearly return ÷ 12 and n is the number of months."),
        ("Is the SIP return guaranteed?", "No. Equity mutual fund returns go up and down every year. The calculator assumes a steady return only to show how compounding works; real results will differ."),
        ("What is a step-up SIP?", "A step-up SIP raises the monthly amount every year, for example by 10% when your salary grows. Try the step-up box in the calculator to see the difference."),
    ]
    sip_body = f"""<article class="story tool"><nav class="crumbs"><a href="{base}">Home</a> / <a href="{base}calculators/">Calculators</a></nav>
<h1>SIP calculator: see how your monthly investment grows</h1>
<p class="dek">Enter an amount, a time period and an expected return. Then read the short lesson below to understand what the numbers mean.</p>
<section class="lesson calc" data-calc="sip">
<div class="cform">
<label>Monthly investment (₹)<input type="number" name="amt" value="5000" min="100" step="500" inputmode="numeric"></label>
<label>Expected return (% a year)<input type="number" name="rate" value="12" min="1" max="30" step="0.5" inputmode="decimal"></label>
<label>Time period (years)<input type="number" name="yrs" value="10" min="1" max="40" step="1" inputmode="numeric"></label>
<label>Step-up every year (%)<input type="number" name="step" value="0" min="0" max="50" step="1" inputmode="numeric"></label>
</div>
<div class="cout three"><div><span>You invest</span><b data-out="invested">—</b></div><div><span>Estimated gain</span><b data-out="gain">—</b></div><div><span>Estimated value</span><b data-out="value">—</b></div></div>
<div class="cbar" aria-hidden="true"><i data-out="bar"></i></div><p class="wnote" data-out="explain"></p>
</section>
<section class="lesson"><h2>Lesson: why time matters more than amount</h2>
<ol class="steps">
<li><b>Start with an example.</b> Say you invest ₹5,000 every month for 10 years and earn 12% a year. You put in {lakh(inv)} and it grows to about {lakh(ex)}.</li>
<li><b>Now only change the time.</b> Keep ₹5,000 a month but continue for 20 years. You put in {lakh(inv20)}, double the money, but it grows to about {lakh(ex20)}, roughly {ex20/ex:.1f} times as much.</li>
<li><b>Why does that happen?</b> This is compounding: the returns you earn start earning returns of their own. In the later years most of the growth comes from past gains, not from your new instalments.</li>
<li><b>What to take away.</b> Starting early, and staying invested through ups and downs, does more of the work than a bigger monthly amount started late.</li>
</ol>
<p class="why"><b>Remember:</b> 12% is an assumption, not a promise. Equity funds can lose money in some years. Check a fund's past record and costs, and speak to a SEBI-registered adviser if you are unsure.</p></section>
{faq_html(sip_q, e)}
<p class="disc">For education only. TotalMarket does not recommend any fund or investment.</p></article>"""
    out.append(("calculators/sip/index.html", page(
        "SIP calculator", "Free SIP calculator with step-up: see how a monthly mutual fund investment grows, plus a simple lesson on compounding with worked examples.",
        f"{base}calculators/sip/", sip_body, meta, seo_title="SIP Calculator: Mutual Fund SIP Return Calculator with Step-Up | TotalMarket",
        keywords=["SIP calculator", "SIP return calculator", "mutual fund calculator", "step up SIP calculator", "SIP calculator monthly",
                  "compound interest calculator", "SIP 5000 per month 10 years", "how SIP works", "SIP formula"],
        extra_head=f'<script type="application/ld+json">{json.dumps(faq_ld(sip_q))}</script><script src="{base}assets/tools.js" defer></script>')))

    # EMI worked example
    P, R, Y = 2000000, 8.5, 20
    m = emi(P, R, Y); tot = m * Y * 12
    first_int = P * R / 100 / 12
    emi_q = [
        ("How is EMI calculated?", "EMI = P × r × (1 + r)^n ÷ ((1 + r)^n − 1), where P is the loan amount, r is the yearly interest rate ÷ 12 and n is the number of monthly instalments."),
        ("Why is most of my early EMI interest?", "Interest is charged on the loan still outstanding. At the start that balance is highest, so most of the EMI goes to interest and little to principal. The split flips over time."),
        ("Does prepaying a loan help?", "Prepaying reduces the outstanding balance, so future interest falls. Check your lender's prepayment terms; floating-rate home loans for individuals usually have no prepayment penalty under RBI rules."),
        ("Can I use this for car and personal loans?", "Yes. The formula is the same for home, car, personal and education loans with fixed monthly instalments."),
    ]
    emi_body = f"""<article class="story tool"><nav class="crumbs"><a href="{base}">Home</a> / <a href="{base}calculators/">Calculators</a></nav>
<h1>EMI calculator for home, car and personal loans</h1>
<p class="dek">Work out your monthly instalment and total interest, then follow the lesson to see where your money goes each year.</p>
<section class="lesson calc" data-calc="emi">
<div class="cform">
<label>Loan amount (₹)<input type="number" name="amt" value="2000000" min="10000" step="50000" inputmode="numeric"></label>
<label>Interest rate (% a year)<input type="number" name="rate" value="8.5" min="1" max="30" step="0.05" inputmode="decimal"></label>
<label>Tenure (years)<input type="number" name="yrs" value="20" min="1" max="30" step="1" inputmode="numeric"></label>
</div>
<div class="cout three"><div><span>Monthly EMI</span><b data-out="emi">—</b></div><div><span>Total interest</span><b data-out="interest">—</b></div><div><span>Total you pay</span><b data-out="total">—</b></div></div>
<div class="cbar" aria-hidden="true"><i data-out="bar"></i></div><p class="wnote" data-out="explain"></p>
<div class="tablewrap"><table class="dt"><caption>Year by year: how each year's EMIs are split</caption><thead><tr><th>Year</th><th>Principal paid</th><th>Interest paid</th><th>Loan left</th></tr></thead><tbody data-out="sched"></tbody></table></div>
</section>
<section class="lesson"><h2>Lesson: what your EMI is really paying for</h2>
<ol class="steps">
<li><b>Take a typical home loan.</b> ₹20 lakh at {R}% for {Y} years gives an EMI of about {inr(m)}.</li>
<li><b>Look at the first month.</b> Interest for month one is ₹20 lakh × {R}% ÷ 12 = {inr(first_int)}. So of your {inr(m)} EMI, only about {inr(m-first_int)} reduces the loan.</li>
<li><b>Add it all up.</b> Over {Y} years you pay about {lakh(tot)} in total, so the interest alone is about {lakh(tot-P)}, more than the loan itself.</li>
<li><b>What changes the picture.</b> A shorter tenure, a lower rate or part-prepayments early in the loan cut total interest the most, because early years carry the most interest. Use the table in the calculator to see this year by year.</li>
</ol></section>
{faq_html(emi_q, e)}
<p class="disc">For education only. Your lender's actual EMI may differ slightly because of rounding and fees.</p></article>"""
    out.append(("calculators/emi/index.html", page(
        "EMI calculator", "Free EMI calculator for home, car and personal loans with a year-by-year schedule, plus a simple lesson on how interest and principal are split.",
        f"{base}calculators/emi/", emi_body, meta, seo_title="EMI Calculator: Home Loan, Car Loan & Personal Loan EMI with Schedule | TotalMarket",
        keywords=["EMI calculator", "home loan EMI calculator", "car loan EMI calculator", "personal loan EMI calculator", "loan EMI calculator",
                  "EMI formula", "home loan interest calculator", "amortization schedule", "loan prepayment"],
        extra_head=f'<script type="application/ld+json">{json.dumps(faq_ld(emi_q))}</script><script src="{base}assets/tools.js" defer></script>')))

    hub = f"""<div class="sechead"><h1>Money calculators and rate trackers</h1><p>Free tools that do the maths and teach you what the answer means.</p></div>
<div class="toolgrid">
<a class="toolcard" href="{base}gold-rate-today/"><b>Gold rate today</b><span>24K, 22K and silver rates, city prices and a jewellery bill calculator.</span></a>
<a class="toolcard" href="{base}calculators/sip/"><b>SIP calculator</b><span>See how a monthly mutual fund investment grows, with step-up.</span></a>
<a class="toolcard" href="{base}calculators/emi/"><b>EMI calculator</b><span>Monthly instalment, total interest and a year-by-year schedule.</span></a>
</div>"""
    out.append(("calculators/index.html", page("Calculators", "Free SIP, EMI and gold value calculators with simple explanations.", f"{base}calculators/", hub, meta,
                                               seo_title="Free Financial Calculators: SIP, EMI & Gold Rate | TotalMarket",
                                               keywords=["financial calculators India", "SIP calculator", "EMI calculator", "gold rate today"])))
    return out


def side_panel(base):
    r = load_rates()
    if not r:
        return ""
    g, b, ch24, ch22, chs = gold_numbers(r)
    def row(lbl, v, ch):
        cls = "" if ch is None else ("up" if ch >= 0 else "down")
        c = "" if ch is None else f'{"+" if ch >= 0 else "−"}{inr(abs(ch))}'
        return f'<tr><th scope="row">{lbl}</th><td class="num">{inr(v)}</td><td class="num {cls}">{c}</td></tr>'
    return (f'<section class="panel"><h2>Gold &amp; silver today <small>IBJA · {date.fromisoformat(b["date"]).strftime("%-d %b")}</small></h2>'
            f'<table class="mt"><tbody>{row("24K · 10 g", g["999"], ch24)}{row("22K · 10 g", g["916"], ch22)}{row("Silver · 1 kg", b["silver999"], chs)}</tbody></table>'
            f'<a class="more" href="{base}gold-rate-today/">City rates &amp; calculator →</a> · <a class="more" href="{base}calculators/">SIP &amp; EMI calculators →</a></section>')
