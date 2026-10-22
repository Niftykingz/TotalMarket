"""TotalMarket हिंदी: Hindi edition at /hi/.

A story gets a Hindi page when its JSON has a `hi` object:
  "hi": {"title", "dek", "body": [..], "why", "indiaImpact", "globalImpact",
         "piggy": {"happened", "matters", "watch": [..]}, "tableTitle",
         "seoTitle", "seoDescription", "tags": [..]}
Only `title` and `body` are required. Hindi text is written for Hindi readers
(not word-for-word translation); market words people search in English
(Sensex, Nifty, IPO, GMP, Q2) stay in English.
"""
import json, re
from datetime import datetime, timezone

FONT = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap">')

CAT_HI = {
    "markets": "शेयर बाज़ार",
    "tech": "टेक और AI",
    "startups": "IPO और स्टार्टअप",
    "policy": "नीति और अर्थव्यवस्था",
    "global": "ग्लोबल बाज़ार",
    "commodities": "सोना-चांदी, क्रूड और रुपया",
}
CAT_DESC_HI = {
    "markets": "Sensex और Nifty की चाल, बड़े शेयरों की खबरें, तिमाही नतीजे और उनकी वजह, आसान हिंदी में।",
    "tech": "AI, बड़ी टेक कंपनियां और भारतीय टेक कंपनियों की खबरें।",
    "startups": "नए IPO, प्राइस बैंड, सब्सक्रिप्शन स्टेटस, लिस्टिंग और स्टार्टअप फंडिंग।",
    "policy": "RBI, SEBI, बजट, टैक्स और सरकार के वे फैसले जो आपके पैसे पर असर डालते हैं।",
    "global": "अमेरिका और एशिया के बाज़ार, बॉन्ड यील्ड, Fed और दुनिया की खबरें जो भारतीय बाज़ार को हिलाती हैं।",
    "commodities": "सोना, चांदी, कच्चा तेल, डॉलर और रुपया: हर चाल का भारत पर क्या असर है।",
}
MONTHS_HI = ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
STATUS_HI = {"developing": "ताज़ा अपडेट जारी", "update": "अपडेट", "updated": "अपडेट"}

# Hindi nav: Hindi pages first, then the (English) data pages people use daily.
NAV_LINKS = [("hi/", "होम")] + [(f"hi/{k}/", v) for k, v in CAT_HI.items()] + [
    ("hi/ipo/", "IPO आज"), ("hi/gold-rate-today/", "सोने का भाव"), ("hi/silver-rate-today/", "चांदी का भाव"), ("nifty-50/", "Nifty 50"),
    ("market-report/", "डेली रिपोर्ट"), ("results/", "नतीजे कैलेंडर"), ("live/", "आज (English)")]

HUB_URLS = []


def has_hi(p):
    h = p.get("hi")
    return isinstance(h, dict) and bool(h.get("title")) and bool(h.get("body"))


def hurl(p, base="/"):
    return f"{base}hi/news/{p['id']}/"


def fmt(d, ist, with_date=True):
    d = d.astimezone(ist)
    h = d.hour % 12 or 12
    part = "सुबह" if d.hour < 12 else ("दोपहर" if d.hour < 16 else ("शाम" if d.hour < 20 else "रात"))
    t = f"{part} {h}:{d.minute:02d}"
    return f"{d.day} {MONTHS_HI[d.month - 1]} {d.year}, {t} IST" if with_date else t + " IST"


def ago(p, ist):
    mins = int((datetime.now(ist) - p["_dt"]).total_seconds() // 60)
    if mins < 60: return f"{max(mins, 1)} मिनट पहले"
    if mins < 60 * 24: return f"{mins // 60} घंटे पहले"
    d = p["_dt"].astimezone(ist)
    return f"{d.day} {MONTHS_HI[d.month - 1]}"


def footer(base, site_url, piggy_img):
    return f"""<footer class="wrap foot" lang="hi">
<p><b>निवेश सलाह नहीं।</b> TotalMarket सिर्फ खबरें बताता और समझाता है। यह किसी भी शेयर को खरीदने, बेचने या रखने की सलाह नहीं देता और SEBI-रजिस्टर्ड निवेश सलाहकार या रिसर्च एनालिस्ट नहीं है। निवेश से पहले खुद रिसर्च करें या रजिस्टर्ड सलाहकार से बात करें।</p>
<nav class="footlinks" aria-label="Market data"><b>मार्केट डेटा:</b> <a href="{base}nifty-50/">Nifty 50 आज</a> · <a href="{base}hi/gold-rate-today/">आज का सोने का भाव</a> · <a href="{base}hi/silver-rate-today/">आज का चांदी का भाव</a> · <a href="{base}fii-dii-data/">FII DII डेटा</a> · <a href="{base}hi/ipo/">IPO आज</a> · <a href="{base}results/">नतीजों का कैलेंडर</a> · <a href="{base}market-report/">डेली मार्केट रिपोर्ट</a> · <a href="{base}learn/">सीखें</a></nav>
<p class="footpig">{piggy_img("head96", "fp-av")}<span><b>Boss Piggy AI</b> ने लिखा, TotalMarket की AI मार्केट डेस्क। हर खबर AI ने दिए गए स्रोतों के आधार पर तैयार की है और नीचे स्रोतों के लिंक दिए हैं। <a href="{base}hi/about/">TotalMarket के बारे में</a> · <a href="{site_url}/hi/rss.xml">RSS फ़ीड</a> · <a href="{base}" lang="en">English edition</a></span></p>
</footer>"""


def _chip(p, e):
    st = STATUS_HI.get(str(p.get("status") or "").lower())
    badge = f'<span class="stbadge st-{e(str(p["status"]).lower())}">{e(st)}</span>' if st else ""
    return f'<span class="chip" style="--dot:var(--c-{p["category"]})">{e(CAT_HI[p["category"]])}</span>{badge}'


def _meta_row(p, c):
    e, ist = c["e"], c["ist"]
    bits = [f'<time datetime="{e(p["_dt"].isoformat())}">{e(fmt(p["_dt"], ist))}</time>']
    up = c["parse_dt"](p.get("updatedAt"))
    if up and up > p["_dt"]:
        bits.append(f'<span class="upd">अपडेट <time datetime="{e(up.isoformat())}">{e(fmt(up, ist))}</time></span>')
    if p.get("readMins"): bits.append(f'{int(p["readMins"])} मिनट में पढ़ें')
    src = (p.get("sources") or [{}])[0].get("name")
    if src: bits.append(e(src))
    return '<div class="meta">' + "".join(f"<span>{b}</span>" for b in bits) + "</div>"


def _card(p, c):
    e, h = c["e"], p["hi"]
    dek = f'<p>{e(h.get("dek"))}</p>' if h.get("dek") else ""
    alt = f'कवर ग्राफ़िक: {h["title"]}'
    return (f'<article class="card" style="--dot:var(--c-{p["category"]})"><img class="thumb" src="{c["cover_url"](p)}" width="1600" height="900" alt="{e(alt)}" loading="lazy" decoding="async">'
            f'<div class="cbody">{_chip(p, e)}<h3><a href="{hurl(p, c["base"])}">{e(h["title"])}</a></h3>{dek}{_meta_row(p, c)}</div></article>')


def _piggy(p, c):
    e, g = c["e"], (p["hi"].get("piggy") or {})
    if not g.get("happened"):
        return ""
    watch = g.get("watch") or []
    if isinstance(watch, str): watch = [watch]
    rows = [("क्या हुआ", e(g["happened"]))]
    if g.get("matters"): rows.append(("क्यों अहम है", e(g["matters"])))
    if watch: rows.append(("आगे क्या देखें", "<ul>" + "".join(f"<li>{e(w)}</li>" for w in watch) + "</ul>"))
    asof = fmt(c["parse_dt"](p.get("updatedAt")) or p["_dt"], c["ist"])
    return (f'<aside class="pg-box" aria-label="Boss Piggy समझाते हैं">'
            f'<div class="pg-head">{c["piggy_img"]("head96", "pg-av")}<div><b>Boss Piggy समझाते हैं</b><small>इस खबर के तथ्यों की आसान व्याख्या · {e(asof)} तक</small></div></div>'
            + "".join(f'<div class="pg-row"><h3>{k}</h3><div>{v}</div></div>' for k, v in rows)
            + '<p class="pg-note">सिर्फ समझाने के लिए, नीचे दिए स्रोतों पर आधारित। किसी भी चीज़ को खरीदने, बेचने या रखने की सलाह नहीं।</p></aside>')


def _table(p, c):
    t = p.get("table")
    if not isinstance(t, dict) or not t.get("rows"):
        return ""
    t2 = dict(t, title=p["hi"].get("tableTitle") or t.get("title"))
    return c["data_table"]({"table": t2})


def _impacts(h, e):
    boxes = []
    if h.get("globalImpact"):
        boxes.append(f'<div class="impact glob"><b><span class="ico" aria-hidden="true">◍</span>दुनिया पर असर</b><p>{e(h["globalImpact"])}</p></div>')
    if h.get("indiaImpact"):
        boxes.append(f'<div class="impact ind"><b><span class="ico" aria-hidden="true">▲</span>भारत पर असर</b><p>{e(h["indiaImpact"])}</p></div>')
    return ('<div class="impacts">' + "".join(boxes) + "</div>") if boxes else ""


def article(p, posts, meta, c):
    e, base, h = c["e"], c["base"], p["hi"]
    path = hurl(p, base)
    link = c["abs_url"](path)
    en_link = c["abs_url"](c["url"](p))
    title = h["title"]
    from urllib.parse import quote
    srcs = "".join(f'<li><a href="{e(s.get("url"))}" rel="noopener nofollow" target="_blank">{e(s.get("name") or s.get("url"))}</a></li>'
                   for s in (p.get("sources") or []) if re.match(r"https?://", str(s.get("url", ""))))
    related = [x for x in posts if has_hi(x) and x["id"] != p["id"]][:4]
    rel = ('<section class="related"><h2 class="edhead"><b>और हिंदी खबरें</b></h2><div class="grid">' + "".join(_card(x, c) for x in related) + "</div></section>") if related else ""
    d = h.get("seoDescription") or h.get("dek") or h["body"][0]
    d = d if len(d) <= 160 else d[:157].rsplit(" ", 1)[0] + "…"
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "inLanguage": "hi-IN",
          "headline": title[:110], "description": d,
          "datePublished": p["_dt"].isoformat(), "dateModified": (c["parse_dt"](p.get("updatedAt")) or p["_dt"]).isoformat(),
          "mainEntityOfPage": link, "image": [c["cover_url"](p, True)], "articleSection": CAT_HI[p["category"]],
          "author": {"@type": "Organization", "name": c["site_name"], "url": c["site_url"] + "/hi/about/"},
          "publisher": {"@type": "Organization", "name": c["site_name"], "logo": {"@type": "ImageObject", "url": f'{c["site_url"]}/assets/logo.png'}},
          "translationOfWork": {"@id": en_link}}
    kw = (h.get("tags") or []) + p["_tags"][:4]
    extra = (f'<meta property="article:published_time" content="{e(p["_dt"].isoformat())}">'
             f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<" + chr(92) + "/")}</script>')
    body_html = "".join(f"<p>{e(t)}</p>" for t in h["body"])
    dek = f'<p class="dek">{e(h.get("dek"))}</p>' if h.get("dek") else ""
    chg = f'<p class="chg"><b>क्या बदला</b>{e(h["changeNote"])}</p>' if h.get("changeNote") else ""
    why = f'<p class="why"><b>क्यों अहम है</b>{e(h["why"])}</p>' if h.get("why") else ""
    rep = ""
    if p.get("report"):
        rep = '<p class="hi-note">नीचे दी गई पूरी रिपोर्ट की तालिकाएं अंग्रेज़ी में हैं।</p>' + c["report"].render(p.get("report"))
    text = quote(title + " " + link)
    lk = c["like_key"](p)
    body = f"""<article class="story" lang="hi" style="--dot:var(--c-{p['category']})">
<nav class="crumbs"><a href="{base}hi/">होम</a> / <a href="{base}hi/{p['category']}/">{e(CAT_HI[p['category']])}</a></nav>
<img class="hero" src="{c['cover_url'](p)}" width="1600" height="900" alt="{e('कवर ग्राफ़िक: ' + title)}" fetchpriority="high" decoding="async">
{_chip(p, e)}
<h1>{e(title)}</h1>
{dek}
{_meta_row(p, c)}
<p class="hi-note" lang="en"><a href="{c['url'](p)}">Read this story in English →</a></p>
<div class="byline">{c['piggy_img']("head96", "by-av")}<span><b>Boss Piggy AI</b> · TotalMarket AI मार्केट डेस्क</span></div>
{chg}
<div class="body">{body_html}</div>
{_piggy(p, c)}
{rep}
{_table(p, c)}
{_impacts(h, e)}
{why}
<section class="engage" aria-label="इस खबर पर अपनी राय दें">
<div class="eg-text"><b>क्या यह खबर काम की लगी?</b><span>लाइक करें और कमेंट में अपनी राय बताएं।</span></div>
<div class="eg-btns"><button type="button" class="like-btn" data-like-key="{lk}" aria-pressed="false"><span class="heart" aria-hidden="true">&#9829;</span> <span class="lc">Like</span></button>
<a class="cm-btn" href="#comments"><span aria-hidden="true">&#128172;</span> कमेंट</a></div>
</section>
<div class="share" aria-label="शेयर करें">
<a href="https://wa.me/?text={text}" target="_blank" rel="noopener">WhatsApp पर शेयर करें</a>
<a href="https://twitter.com/intent/tweet?text={quote(title)}&url={quote(link)}" target="_blank" rel="noopener">X पर शेयर करें</a>
<a href="https://t.me/share/url?url={quote(link)}&text={quote(title)}" target="_blank" rel="noopener">Telegram पर शेयर करें</a>
<button type="button" class="copy" data-url="{e(link)}">लिंक कॉपी करें</button>
</div>
{'<div class="sources"><h2>स्रोत</h2><ul>' + srcs + '</ul></div>' if srcs else ''}
<p class="disc">Boss Piggy AI ने TotalMarket के लिए लिखा। यह खबर ऊपर दिए स्रोतों पर आधारित है; ज़रूरी तथ्य और आंकड़े मूल स्रोत से ज़रूर मिलाएं। यह सिर्फ जानकारी के लिए है, निवेश सलाह नहीं।</p>
{c['comments_block'](p)}
</article>
<div class="fab" aria-label="Like या कमेंट"><button type="button" class="fab-like" data-like-key="{lk}" aria-label="इस खबर को लाइक करें">&#9829; <span class="lc">Like</span></button><a class="fab-cm" href="#comments">&#128172; कमेंट</a></div>
{rel}"""
    st = h.get("seoTitle")
    return c["page"](title, d, path, body, meta, og_type="article", extra_head=extra, image=c["cover_url"](p, True),
                     seo_title=(st + " | TotalMarket हिंदी") if st and len(st) <= 46 else st, keywords=kw, news_kw=kw[:10],
                     lang="hi", alternates=[("en", en_link), ("hi", link)], switch=(c["url"](p), "English"))


def _mini(p, c):
    e = c["e"]
    return (f'<a class="mini" href="{hurl(p, c["base"])}"><img src="{c["cover_url"](p)}" width="1600" height="900" alt="" loading="lazy" decoding="async">'
            f'<span><b>{e(p["hi"]["title"])}</b><small>{e(ago(p, c["ist"]))}</small></span></a>')


def home(hp, meta, c):
    e, base = c["e"], c["base"]
    intro = (f'<aside class="pg-intro" lang="hi" aria-label="Boss Piggy">{c["piggy_img"]("head96", "pg-av", True)}'
             f'<p><b>नमस्ते, मैं Boss Piggy हूं।</b> शेयर बाज़ार, IPO, सोना-चांदी और दुनिया की खबरें मैं आपको आसान हिंदी में समझाऊंगा: क्या हुआ, क्यों अहम है और आगे क्या देखना है। '
             f'<a href="{base}learn/">बेसिक बातें सीखें →</a></p></aside>')
    if not hp:
        body = '<h1>TotalMarket हिंदी</h1>' + intro + '<div class="empty"><p>पहली हिंदी खबरें जल्द आ रही हैं।</p></div>'
    else:
        lead = next((p for p in hp[:8] if p.get("lead")), hp[0])
        others = [p for p in hp if p is not lead]
        hero = (f'<a class="hero1" href="{hurl(lead, base)}" style="--dot:var(--c-{lead["category"]})"><img src="{c["cover_url"](lead)}" width="1600" height="900" alt="" fetchpriority="high">'
                f'<span class="hov"><em>{e(CAT_HI[lead["category"]])}</em><b>{e(lead["hi"]["title"])}</b><i>{e(lead["hi"].get("dek") or "")}</i>'
                f'<small>{e(ago(lead, c["ist"]))} · Boss Piggy AI · {int(lead.get("readMins") or 2)} मिनट</small></span></a>')
        side = (f'<aside class="widget stories"><div class="wtabs"><button type="button" class="wt on" data-panel="st0">ताज़ा खबरें</button></div>'
                f'<div class="wp" id="st0">{"".join(_mini(p, c) for p in others[:6])}</div></aside>')
        quick = ('<aside class="widget hi-quick"><h2 class="edhead"><b>रोज़ के काम के पेज</b></h2><ul>'
                 f'<li><a href="{base}nifty-50/">Nifty 50 आज: क्लोज़ और चार्ट</a></li><li><a href="{base}hi/gold-rate-today/">आज का सोने का भाव (24K, 22K)</a></li>'
                 f'<li><a href="{base}hi/silver-rate-today/">आज का चांदी का भाव</a></li><li><a href="{base}hi/ipo/">IPO: खुले, आने वाले और लिस्टेड</a></li>'
                 f'<li><a href="{base}fii-dii-data/">FII और DII ने कितना खरीदा-बेचा</a></li><li><a href="{base}results/">इस हफ्ते किसके नतीजे</a></li>'
                 f'<li><a href="{base}{"stock-market-holidays-2026/"}">शेयर बाज़ार की छुट्टियां</a></li></ul><small>Nifty, FII-DII, नतीजे और छुट्टियों के पेज अभी अंग्रेज़ी में हैं।</small></aside>')
        body = (f'<h1 class="sr">TotalMarket हिंदी: शेयर बाज़ार, IPO, सोना-चांदी की खबरें आसान हिंदी में</h1>' + intro
                + f'<div class="topgrid">{hero}{side}{quick}</div>'
                + '<section class="related"><h2 class="edhead"><b>सभी हिंदी खबरें</b></h2><div class="grid">' + "".join(_card(p, c) for p in others[6:40]) + "</div></section>"
                if len(others) > 6 else
                f'<h1 class="sr">TotalMarket हिंदी: शेयर बाज़ार, IPO, सोना-चांदी की खबरें आसान हिंदी में</h1>' + intro + f'<div class="topgrid">{hero}{side}{quick}</div>')
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": "TotalMarket हिंदी", "url": c["site_url"] + "/hi/", "inLanguage": "hi-IN"}
    return c["page"]("TotalMarket हिंदी", "आज का शेयर बाज़ार: Sensex, Nifty, IPO सब्सक्रिप्शन, सोने-चांदी का भाव, तिमाही नतीजे और ग्लोबल बाज़ार की खबरें आसान हिंदी में।",
                     f"{base}hi/", body, meta, seo_title="शेयर बाज़ार आज: Sensex, Nifty, IPO, सोने का भाव | TotalMarket हिंदी",
                     keywords=["शेयर बाज़ार आज", "शेयर मार्केट न्यूज़", "Sensex आज", "Nifty आज", "IPO न्यूज़ हिंदी", "सोने का भाव आज", "share market news in hindi"],
                     extra_head=f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>',
                     lang="hi", alternates=[("en", c["site_url"] + "/"), ("hi", c["site_url"] + "/hi/")], switch=(base, "English"))


def section(k, hp, meta, c):
    e, base = c["e"], c["base"]
    items = [p for p in hp if p["category"] == k]
    grid = ('<div class="grid">' + "".join(_card(p, c) for p in items[:80]) + "</div>") if items else '<div class="empty"><p>इस सेक्शन में हिंदी खबरें जल्द आएंगी। तब तक <a href="' + base + k + '/" lang="en">English में पढ़ें</a>।</p></div>'
    body = f'<div class="sechead" lang="hi"><h1>{e(CAT_HI[k])}</h1><p>{e(CAT_DESC_HI[k])}</p></div>{grid}'
    return c["page"](CAT_HI[k] + " की ताज़ा खबरें", CAT_DESC_HI[k], f"{base}hi/{k}/", body, meta, noindex=not items,
                     seo_title=f"{CAT_HI[k]} की ताज़ा खबरें हिंदी में | TotalMarket", lang="hi",
                     alternates=[("en", f'{c["site_url"]}/{k}/'), ("hi", f'{c["site_url"]}/hi/{k}/')], switch=(f"{base}{k}/", "English"))


def about(meta, c):
    base = c["base"]
    body = f"""<article class="story" lang="hi"><h1>TotalMarket हिंदी के बारे में</h1><div class="body">
<p>TotalMarket भारतीय निवेशकों और ट्रेडर्स के लिए मुफ्त न्यूज़ साइट है। हिंदी एडिशन में हम हर दिन की सबसे ज़रूरी खबरें आसान हिंदी में देते हैं: शेयर बाज़ार की चाल, IPO, तिमाही नतीजे, सोना-चांदी, कच्चा तेल, रुपया और ग्लोबल बाज़ार।</p>
<p><b>कैसे बनती है।</b> हर खबर Boss Piggy AI, यानी TotalMarket की AI मार्केट डेस्क, खबर के नीचे दिए स्रोतों के आधार पर तैयार करती है। कंपनी के नतीजों के आंकड़े जहां संभव हो NSE पर कंपनी की आधिकारिक फाइलिंग से लिए जाते हैं।</p>
<p><b>सटीकता।</b> खबर में सिर्फ वही तथ्य होते हैं जो स्रोतों में हैं। AI से भी गलती हो सकती है, इसलिए कोई भी फैसला लेने से पहले मूल स्रोत ज़रूर देखें।</p>
<p><b>निवेश सलाह नहीं।</b> TotalMarket किसी शेयर को खरीदने, बेचने या रखने की सलाह नहीं देता, टारगेट प्राइस नहीं देता और SEBI में निवेश सलाहकार या रिसर्च एनालिस्ट के रूप में रजिस्टर्ड नहीं है।</p>
<p><a href="{base}about/" lang="en">About TotalMarket (English)</a></p></div></article>"""
    return c["page"]("TotalMarket हिंदी के बारे में", "TotalMarket हिंदी कैसे काम करता है, खबरें कैसे बनती हैं और हमारी नीतियां।", f"{base}hi/about/", body, meta,
                     lang="hi", alternates=[("en", c["site_url"] + "/about/"), ("hi", c["site_url"] + "/hi/about/")], switch=(f"{base}about/", "English"))


def rss(hp, c):
    e = c["e"]
    items = "".join(
        f"""<item><title>{e(p['hi']['title'])}</title><link>{c['abs_url'](hurl(p, c['base']))}</link><guid isPermaLink="true">{c['abs_url'](hurl(p, c['base']))}</guid>
<pubDate>{p['_dt'].astimezone(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate><category>{e(CAT_HI[p['category']])}</category><description>{e(p['hi'].get('dek') or p['hi']['body'][0])}</description></item>"""
        for p in hp[:50])
    now = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>TotalMarket हिंदी</title><link>{c['site_url']}/hi/</link>
<description>शेयर बाज़ार, IPO, सोना-चांदी की खबरें आसान हिंदी में</description><language>hi-in</language><lastBuildDate>{now}</lastBuildDate>
{items}
</channel></rss>
"""


def build(posts, meta, c):
    hp = [p for p in posts if has_hi(p)]
    out = [("hi/index.html", home(hp, meta, c)), ("hi/about/index.html", about(meta, c)), ("hi/rss.xml", rss(hp, c))]
    HUB_URLS[:] = [c["site_url"] + "/hi/", c["site_url"] + "/hi/about/"]
    for k in CAT_HI:
        out.append((f"hi/{k}/index.html", section(k, hp, meta, c)))
        if any(p["category"] == k for p in hp):
            HUB_URLS.append(f'{c["site_url"]}/hi/{k}/')
    for p in hp:
        out.append((f"hi/news/{p['id']}/index.html", article(p, posts, meta, c)))
    return out


# ---------------------------------------------------------------- Hindi data pages
# Built from the same data files as the English pages (data/rates.json, data/ipos.json),
# so they refresh automatically whenever those files are updated.
import os as _os
from datetime import date as _date

_ROOT = _os.path.dirname(_os.path.abspath(__file__))
PAIRS = {"gold-rate-today/": "hi/gold-rate-today/", "silver-rate-today/": "hi/silver-rate-today/", "ipo/": "hi/ipo/"}
WEEKDAYS_HI = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]


def hdate(s, weekday=False):
    try:
        d = _date.fromisoformat(str(s)[:10])
    except Exception:
        return str(s or "")
    out = f"{d.day} {MONTHS_HI[d.month - 1]} {d.year}"
    return (WEEKDAYS_HI[d.weekday()] + ", " + out) if weekday else out


def _inr(n, dec=0):
    import tools
    return tools.inr(n, dec)


def _kpi(label, value, sub=""):
    return f'<div class="rp-kpi"><span class="l">{label}</span><b>{value}</b>{f"<span class=c>{sub}</span>" if sub else ""}</div>'


def _faq(qas, e):
    return ('<section class="lesson"><h2>लोग अक्सर पूछते हैं</h2>'
            + "".join(f'<details class="faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qas) + "</section>")


def _faq_ld(qas):
    return {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": "hi-IN",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qas]}


def _piggy_data(rows, c):
    e = c["e"]
    return (f'<aside class="pg-box" aria-label="Boss Piggy समझाते हैं"><div class="pg-head">{c["piggy_img"]("head96", "pg-av")}<div><b>Boss Piggy समझाते हैं</b>'
            f'<small>इस पेज के आंकड़ों को आसान हिंदी में समझें</small></div></div>'
            + "".join(f'<div class="pg-row"><h3>{k}</h3><div>{v}</div></div>' for k, v in rows)
            + '<p class="pg-note">सिर्फ समझाने के लिए। किसी भी चीज़ को खरीदने, बेचने या रखने की सलाह नहीं।</p></aside>')


def _related(hp, cats, c, title):
    items = [p for p in hp if p["category"] in cats][:4]
    return ('<section class="related"><h2 class="edhead"><b>' + c["e"](title) + '</b></h2><div class="grid">' + "".join(_card(p, c) for p in items) + "</div></section>") if items else ""


def gold_page(r, hp, meta, c):
    e, base = c["e"], c["base"]
    b = r["benchmark"]; g = b["gold"]
    rr = r.get("retailRange") or {}; cs = r.get("citySource") or {}
    hist = list(reversed(r.get("history") or []))
    city = next((x for x in r.get("cities", []) if x["slug"] == "mumbai"), (r.get("cities") or [None])[0])
    day = hdate(rr.get("date") or b["date"], True)
    kpis = '<div class="rp-kpis">'
    if city:
        kpis += _kpi("24 कैरेट · 10 ग्राम (दुकान भाव)", _inr(city["gold24"]), e(city["name"]) + ", " + e(cs.get("name", ""))) + _kpi("22 कैरेट · 10 ग्राम (दुकान भाव)", _inr(city["gold22"]), "गहनों वाला सोना")
    kpis += _kpi("24 कैरेट · IBJA बेंचमार्क", _inr(g["999"]), hdate(b["date"]) + " तक जांचा गया") + _kpi("18 कैरेट · IBJA", _inr(g["750"])) + "</div>"
    city_rows = "".join(f'<tr><th scope="row">{e(x["name"])}</th><td class="num">{_inr(x["gold24"])}</td><td class="num">{_inr(x["gold22"])}</td><td class="num">{_inr(x["gold24"]/10)}</td></tr>' for x in r.get("cities", []))
    cities = (f'<section class="lesson"><h2>शहर के हिसाब से आज का सोने का भाव</h2><p>दुकान भाव प्रति 10 ग्राम, स्रोत <a href="{e(cs.get("url"))}" rel="nofollow noopener">{e(cs.get("name"))}</a> ({e(cs.get("asOf"))})। इसमें GST और मेकिंग चार्ज शामिल नहीं।</p>'
              f'<div class="tablewrap"><table class="dt"><thead><tr><th>शहर</th><th>24 कैरेट</th><th>22 कैरेट</th><th>24K प्रति ग्राम</th></tr></thead><tbody>{city_rows}</tbody></table></div></section>') if city_rows else ""
    purity = ('<div class="tablewrap"><table class="dt"><caption>IBJA बेंचमार्क: शुद्धता के हिसाब से भाव (GST से पहले)</caption><thead><tr><th>शुद्धता</th><th>1 ग्राम</th><th>8 ग्राम</th><th>10 ग्राम</th></tr></thead><tbody>'
              + "".join(f'<tr><th scope="row">{lbl}</th><td class="num">{_inr(g[k]/10)}</td><td class="num">{_inr(g[k]/10*8)}</td><td class="num">{_inr(g[k])}</td></tr>'
                        for k, lbl in (("999", "24 कैरेट (999)"), ("916", "22 कैरेट (916)"), ("750", "18 कैरेट (750)"), ("585", "14 कैरेट (585)")) if k in g)
              + "</tbody></table></div>")
    m = r.get("mcx") or {}
    mcx = (f'<p class="why"><b>MCX फ्यूचर्स</b>{e(m.get("contract", ""))}: सोना {_inr(m["gold"])} प्रति 10 ग्राम ({m.get("goldChangePct", 0):+.2f}%), {e(m.get("asOf", ""))}, स्रोत '
           f'<a href="{e((m.get("source") or {}).get("url"))}" rel="nofollow noopener">{e((m.get("source") or {}).get("name"))}</a>। फ्यूचर्स भाव ट्रेडर्स के लिए होता है, दुकान भाव से अलग।</p>') if m.get("gold") else ""
    g22 = city["gold22"] if city else g["916"]
    mk, gst = round(g22 * 0.12), round(g22 * 1.12 * 0.03)
    calc = (f'<section class="lesson"><h2>उदाहरण: 10 ग्राम की 22 कैरेट चेन असल में कितने की पड़ेगी?</h2><div class="worked"><table class="dt"><tbody>'
            f'<tr><th scope="row">सोने की कीमत (22 कैरेट, 10 ग्राम)</th><td class="num">{_inr(g22)}</td></tr>'
            f'<tr><th scope="row">मेकिंग चार्ज 12% (दुकान के हिसाब से 8–25%)</th><td class="num">{_inr(mk)}</td></tr>'
            f'<tr><th scope="row">GST 3% (सोना + मेकिंग पर)</th><td class="num">{_inr(gst)}</td></tr>'
            f'<tr><th scope="row"><b>कुल</b></th><td class="num"><b>{_inr(g22 + mk + gst)}</b></td></tr></tbody></table>'
            '<p>मेकिंग चार्ज पर मोलभाव हो सकता है; सोने का भाव और GST तय होते हैं। हमेशा BIS हॉलमार्क (HUID नंबर) वाला सोना लें।</p></div></section>')
    hrows = "".join(f'<tr><th scope="row">{e(hdate(h["date"]))}</th><td class="num">{_inr(h["gold999"])}</td><td class="num">{_inr(h["gold916"])}</td></tr>' for h in hist)
    history = (f'<section class="lesson"><h2>पिछले {len(hist)} कारोबारी दिनों का भाव (IBJA)</h2><div class="tablewrap"><table class="dt"><thead><tr><th>तारीख</th><th>24 कैरेट / 10 ग्राम</th><th>22 कैरेट / 10 ग्राम</th></tr></thead><tbody>{hrows}</tbody></table></div></section>') if hrows else ""
    pig = _piggy_data([("यह पेज क्या दिखाता है", "दुकानों के आज के भाव (शहर के हिसाब से) और IBJA का बेंचमार्क भाव, जिससे ज्वैलर्स अपने भाव तय करते हैं।"),
                       ("भाव क्यों बदलता है", "भारत में सोने का भाव दो चीज़ों से बनता है: दुनिया में सोने का डॉलर भाव और रुपया-डॉलर रेट। रुपया मज़बूत हो तो सोना सस्ता, कमज़ोर हो तो महंगा।"),
                       ("ध्यान रखें", "<ul><li>दुकान का बिल = सोने का भाव + मेकिंग चार्ज + 3% GST</li><li>22 कैरेट गहनों के लिए, 24 कैरेट सिक्के और बिस्किट के लिए</li><li>हॉलमार्क और HUID ज़रूर जांचें</li></ul>")], c)
    qas = [("आज सोने का भाव क्या है?", (f"{day} को {city['name']} में 24 कैरेट सोना {_inr(city['gold24'])} और 22 कैरेट {_inr(city['gold22'])} प्रति 10 ग्राम है ({cs.get('name', '')} के मुताबिक), GST और मेकिंग चार्ज अलग।") if city else f"IBJA के मुताबिक 24 कैरेट {_inr(g['999'])} प्रति 10 ग्राम।"),
           ("22 कैरेट और 24 कैरेट में क्या फर्क है?", "24 कैरेट 99.9% शुद्ध होता है और सिक्के-बिस्किट में इस्तेमाल होता है। 22 कैरेट (91.6%) में थोड़ी दूसरी धातु मिली होती है ताकि गहने मज़बूत बनें।"),
           ("ज्वैलर का भाव ऑनलाइन भाव से ज़्यादा क्यों होता है?", "दुकान 3% GST, मेकिंग चार्ज (आमतौर पर 8–25%) और कभी-कभी वेस्टेज जोड़ती है। ऑनलाइन बेंचमार्क में सिर्फ धातु की कीमत होती है।"),
           ("IBJA भाव क्या है?", "India Bullion and Jewellers Association हर कारोबारी दिन सोने-चांदी का बेंचमार्क भाव जारी करता है, जिसे कई ज्वैलर्स और बैंक आधार मानते हैं।"),
           ("यह पेज कब अपडेट होता है?", "हर कारोबारी दिन TotalMarket के तय अपडेट में, आमतौर पर सुबह, दोपहर और बाज़ार बंद होने के बाद।")]
    src = (f'<section class="sources"><h2>स्रोत</h2><ul><li><a href="{e(b["url"])}" rel="nofollow noopener">{e(b["source"])}</a> — बेंचमार्क भाव</li>'
           + (f'<li><a href="{e(cs["url"])}" rel="nofollow noopener">{e(cs["name"])}</a> — शहरों के भाव</li>' if cs else "") + "</ul></section>")
    body = (f'<article class="story tool" lang="hi"><nav class="crumbs"><a href="{base}hi/">होम</a> / <a href="{base}hi/commodities/">सोना-चांदी</a></nav>'
            f'<h1>आज का सोने का भाव: 24 कैरेट, 22 कैरेट ({e(day)})</h1>'
            f'<p class="dek">भारत के बड़े शहरों में आज का गोल्ड रेट, IBJA बेंचमार्क और असल बिल का आसान हिसाब।</p>'
            f'{kpis}<p class="wnote">IBJA: {e(hdate(b["date"]))} ({e(b.get("session", ""))}) का नवीनतम जांचा गया भाव। भाव में 3% GST और मेकिंग चार्ज शामिल नहीं।</p>'
            f'{mcx}{pig}{cities}{calc}{purity}{history}{_faq(qas, e)}'
            f'<p class="cm-note">चांदी का भाव देखें: <a href="{base}hi/silver-rate-today/">आज का चांदी का भाव</a> · <a href="{base}gold-rate-today/" lang="en">Gold rate today (English)</a></p>{src}'
            f'<p class="disc">भाव सिर्फ जानकारी के लिए हैं। TotalMarket सोना-चांदी खरीदने या बेचने की सलाह नहीं देता।</p></article>'
            + _related(hp, ("commodities",), c, "सोना-चांदी की ताज़ा खबरें"))
    return c["page"]("आज का सोने का भाव", f"आज का सोने का भाव ({day}): 24 कैरेट और 22 कैरेट गोल्ड रेट प्रति 10 ग्राम, दिल्ली, मुंबई, चेन्नई समेत बड़े शहरों में, IBJA बेंचमार्क और GST-मेकिंग चार्ज का हिसाब।"[:165],
                     f"{base}hi/gold-rate-today/", body, meta, seo_title="आज का सोने का भाव: 24K, 22K गोल्ड रेट प्रति 10 ग्राम",
                     keywords=["सोने का भाव आज", "आज का गोल्ड रेट", "24 कैरेट सोने का भाव", "22 कैरेट सोने का भाव", "gold rate today in hindi"],
                     extra_head=f'<script type="application/ld+json">{json.dumps(_faq_ld(qas), ensure_ascii=False)}</script>',
                     lang="hi", alternates=[("en", c["site_url"] + "/gold-rate-today/"), ("hi", c["site_url"] + "/hi/gold-rate-today/")], switch=(f"{base}gold-rate-today/", "English"))


def silver_page(r, hp, meta, c):
    e, base = c["e"], c["base"]
    b = r["benchmark"]; s_kg = b["silver999"]
    sr = r.get("silverRetail") or {}; m = r.get("mcx") or {}
    hist = list(reversed(r.get("history") or []))
    shop = sr.get("range") or [None, None]
    day = hdate(sr.get("date") or b["date"], True)
    kpis = '<div class="rp-kpis">'
    if shop[0]:
        kpis += _kpi("चांदी · 1 किलो (दुकान भाव)", _inr(shop[0]) + ("" if shop[0] == shop[1] else "–" + _inr(shop[1])), e((sr.get("source") or {}).get("name", "")))
        kpis += _kpi("चांदी · 10 ग्राम", _inr(shop[0] / 100)) + _kpi("चांदी · 1 ग्राम", _inr(shop[0] / 1000, 2))
    kpis += _kpi("चांदी 999 · IBJA (1 किलो)", _inr(s_kg), hdate(b["date"]) + " तक जांचा गया") + "</div>"
    mcx = (f'<p class="why"><b>MCX फ्यूचर्स</b>{e(m.get("contract", ""))}: चांदी {_inr(m["silver"])} प्रति किलो ({m.get("silverChangePct", 0):+.2f}%), {e(m.get("asOf", ""))}। फ्यूचर्स भाव दुकान भाव से अलग होता है।</p>') if m.get("silver") else ""
    hrows = "".join(f'<tr><th scope="row">{e(hdate(h["date"]))}</th><td class="num">{_inr(h["silver999"])}</td><td class="num">{_inr(h["silver999"]/1000, 2)}</td></tr>' for h in hist)
    history = (f'<section class="lesson"><h2>पिछले {len(hist)} कारोबारी दिनों का भाव (IBJA)</h2><div class="tablewrap"><table class="dt"><thead><tr><th>तारीख</th><th>1 किलो</th><th>1 ग्राम</th></tr></thead><tbody>{hrows}</tbody></table></div></section>') if hrows else ""
    per = (shop[0] or s_kg) / 1000; coin = per * 100
    calc = (f'<section class="lesson"><h2>उदाहरण: 100 ग्राम का चांदी का सिक्का</h2><div class="worked"><table class="dt"><tbody>'
            f'<tr><th scope="row">भाव प्रति ग्राम</th><td class="num">{_inr(per, 2)}</td></tr><tr><th scope="row">100 ग्राम की कीमत</th><td class="num">{_inr(coin)}</td></tr>'
            f'<tr><th scope="row">GST 3%</th><td class="num">{_inr(coin*0.03)}</td></tr><tr><th scope="row"><b>कुल (विक्रेता के प्रीमियम से पहले)</b></th><td class="num"><b>{_inr(coin*1.03)}</b></td></tr></tbody></table></div></section>')
    pig = _piggy_data([("यह पेज क्या दिखाता है", "आज का चांदी का दुकान भाव, IBJA बेंचमार्क और MCX फ्यूचर्स, प्रति किलो, 10 ग्राम और 1 ग्राम में।"),
                       ("चांदी सोने से ज़्यादा क्यों हिलती है", "चांदी गहनों के साथ-साथ सोलर पैनल और इलेक्ट्रॉनिक्स में भी लगती है, इसलिए उद्योगों की मांग बदलने पर इसका भाव सोने से ज़्यादा ऊपर-नीचे होता है।"),
                       ("ध्यान रखें", "<ul><li>999 चांदी सिक्के-बार के लिए, 925 (स्टर्लिंग) गहनों के लिए</li><li>भाव में 3% GST और मेकिंग चार्ज शामिल नहीं</li></ul>")], c)
    qas = [("आज चांदी का भाव क्या है?", (f"{day} को दुकानों में चांदी करीब {_inr(shop[0])} प्रति किलो है ({(sr.get('source') or {}).get('name', '')} के मुताबिक), GST अलग।") if shop[0] else f"IBJA के मुताबिक चांदी 999 {_inr(s_kg)} प्रति किलो।"),
           ("1 ग्राम चांदी का भाव कैसे निकालें?", "प्रति किलो भाव को 1,000 से भाग दें। 10 ग्राम के लिए 100 से भाग दें।"),
           ("चांदी 999 और 925 में क्या फर्क है?", "999 चांदी 99.9% शुद्ध होती है। 925 या स्टर्लिंग सिल्वर 92.5% शुद्ध होती है और गहनों-बर्तनों में इस्तेमाल होती है।")]
    body = (f'<article class="story tool" lang="hi"><nav class="crumbs"><a href="{base}hi/">होम</a> / <a href="{base}hi/commodities/">सोना-चांदी</a></nav>'
            f'<h1>आज का चांदी का भाव: प्रति किलो, 10 ग्राम और 1 ग्राम ({e(day)})</h1>'
            f'<p class="dek">आज का सिल्वर रेट, IBJA बेंचमार्क, MCX फ्यूचर्स और पिछले दिनों का ट्रेंड, आसान हिंदी में।</p>'
            f'{kpis}<p class="wnote">IBJA: {e(hdate(b["date"]))} का नवीनतम जांचा गया भाव। भाव में 3% GST शामिल नहीं।</p>{mcx}{pig}{calc}{history}{_faq(qas, e)}'
            f'<p class="cm-note"><a href="{base}hi/gold-rate-today/">आज का सोने का भाव</a> · <a href="{base}silver-rate-today/" lang="en">Silver rate today (English)</a></p>'
            f'<p class="disc">भाव सिर्फ जानकारी के लिए हैं। TotalMarket चांदी खरीदने या बेचने की सलाह नहीं देता।</p></article>'
            + _related(hp, ("commodities",), c, "सोना-चांदी की ताज़ा खबरें"))
    return c["page"]("आज का चांदी का भाव", f"आज का चांदी का भाव ({day}): सिल्वर रेट प्रति किलो, 10 ग्राम और 1 ग्राम, IBJA बेंचमार्क, MCX फ्यूचर्स और 100 ग्राम सिक्के का पूरा हिसाब।"[:165],
                     f"{base}hi/silver-rate-today/", body, meta, seo_title="आज का चांदी का भाव: सिल्वर रेट प्रति किलो, 1 ग्राम",
                     keywords=["चांदी का भाव आज", "आज का सिल्वर रेट", "चांदी का रेट प्रति किलो", "silver rate today in hindi"],
                     extra_head=f'<script type="application/ld+json">{json.dumps(_faq_ld(qas), ensure_ascii=False)}</script>',
                     lang="hi", alternates=[("en", c["site_url"] + "/silver-rate-today/"), ("hi", c["site_url"] + "/hi/silver-rate-today/")], switch=(f"{base}silver-rate-today/", "English"))


STATUS_IPO_HI = {"open": "अभी खुले IPO", "upcoming": "आने वाले IPO", "closed": "बंद, लिस्टिंग का इंतज़ार", "listing": "आज लिस्टिंग", "listed": "हाल में लिस्ट हुए"}


def _ipo_card(x, st, c):
    e, base = c["e"], c["base"]
    rows = [("तारीख", f'{hdate(x.get("open"))} – {hdate(x.get("close"))}' if x.get("open") else "—"),
            ("प्राइस बैंड", x.get("priceBand") or "—"), ("लॉट साइज़", f'{x["lot"]} शेयर' if x.get("lot") else "—")]
    if x.get("minAmount"): rows.append(("कम से कम निवेश", _inr(x["minAmount"])))
    if x.get("issueSize"): rows.append(("इश्यू साइज़", x["issueSize"]))
    if x.get("allotment"): rows.append(("अलॉटमेंट", hdate(x["allotment"])))
    if x.get("listing"): rows.append(("लिस्टिंग", hdate(x["listing"])))
    sub = x.get("subscription") or {}
    if sub.get("total") is not None:
        parts = [f'कुल {sub["total"]} गुना'] + [f'{lbl} {sub[k]} गुना' for k, lbl in (("qib", "QIB"), ("nii", "HNI/NII"), ("retail", "रिटेल")) if sub.get(k) is not None]
        rows.append(("सब्सक्रिप्शन", ", ".join(parts) + f' ({sub.get("asOf", "")}, {(sub.get("source") or {}).get("name", "")})'))
    if x.get("listingPrice"):
        rows.append(("लिस्टिंग भाव", f'{_inr(x["listingPrice"], 2 if x["listingPrice"] % 1 else 0)} (इश्यू भाव {_inr(x.get("issuePrice") or 0)} से {x.get("listingGainPct", 0):+.2f}%)'))
    if (x.get("gmp") or {}).get("value") and st in ("open", "upcoming", "closed"):
        rows.append(("GMP (अनौपचारिक)", f'{x["gmp"]["value"]} ({x["gmp"].get("asOf", "")}) · ग्रे मार्केट प्रीमियम अनाधिकारिक है, भरोसेमंद संकेत नहीं'))
    tr = "".join(f'<tr><th scope="row">{e(k)}</th><td>{e(v)}</td></tr>' for k, v in rows)
    return (f'<section class="lesson ipo-hi"><h3><a href="{base}ipo/{e(x["slug"])}/" lang="en">{e(x["name"])} IPO</a> <span class="stbadge">{e(x.get("segment", ""))}</span></h3>'
            f'<div class="tablewrap"><table class="dt"><tbody>{tr}</tbody></table></div></section>')


def ipo_page(hp, meta, c):
    import hubs
    e, base = c["e"], c["base"]
    data = hubs.load_ipos() if hasattr(hubs, "load_ipos") else json.load(open(_os.path.join(_ROOT, "data", "ipos.json"), encoding="utf-8"))
    today = datetime.now(c["ist"]).date()
    groups = {}
    for x in data.get("ipos", []):
        groups.setdefault(hubs.ipo_status(x, today), []).append(x)
    secs = ""
    for st in ("listing", "open", "upcoming", "closed", "listed"):
        if groups.get(st):
            secs += f'<h2 class="edhead"><b>{STATUS_IPO_HI[st]}</b></h2>' + "".join(_ipo_card(x, st, c) for x in groups[st])
    lessons = [("IPO क्या है?", "जब कोई कंपनी पहली बार आम लोगों को अपने शेयर बेचती है, उसे IPO कहते हैं। इसके बाद शेयर NSE और BSE पर बाकी शेयरों की तरह खरीदे-बेचे जाते हैं।"),
               ("प्राइस बैंड और कट-ऑफ", "कंपनी एक दायरा तय करती है, जैसे ₹660–693। आखिरी भाव आमतौर पर ऊपरी भाव होता है। रिटेल निवेशक 'कट-ऑफ' चुनकर तय होने वाला भाव स्वीकार कर सकते हैं।"),
               ("लॉट साइज़", "IPO में तय बंडल यानी लॉट में आवेदन होता है। लॉट 21 शेयर का और भाव ₹693 हो तो कम से कम निवेश 21 × ₹693 = ₹14,553।"),
               ("'10 गुना सब्सक्राइब' का मतलब", "हर उपलब्ध शेयर के लिए 10 शेयरों के आवेदन आए। रिटेल हिस्सा ओवरसब्सक्राइब हो तो अलॉटमेंट कंप्यूटर लॉटरी से होता है, इसलिए बहुत लोगों को शेयर नहीं मिलते।"),
               ("GMP पर भरोसा क्यों न करें", "ग्रे मार्केट प्रीमियम अनाधिकारिक, बिना नियम का भाव है। यह जल्दी बदलता है और कई बार लिस्टिंग इससे बहुत अलग होती है।")]
    learn = '<section class="lesson"><h2>Boss Piggy की IPO क्लास</h2>' + "".join(f'<details class="faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in lessons) + "</section>"
    host = (f'<aside class="pg-host" lang="hi">{c["piggy_img"]("full", "pg-full")}<div><span class="pg-name">Boss Piggy · आपका मार्केट गाइड</span>'
            '<h2>IPO में पैसा लगाने से पहले ये तीन बातें देखें</h2><p>कंपनी क्या करती है, पैसा किस काम में लगेगा (नए शेयर या OFS), और भाव कमाई के हिसाब से कितना है। सिर्फ सब्सक्रिप्शन या GMP देखकर फैसला न करें।</p>'
            '<small>Boss Piggy खबरें और बातें समझाते हैं; वे कभी नहीं बताते कि क्या खरीदें या बेचें।</small></div></aside>')
    body = (f'<article class="story tool" lang="hi"><nav class="crumbs"><a href="{base}hi/">होम</a> / <a href="{base}hi/startups/">IPO और स्टार्टअप</a></nav>'
            f'<h1>IPO आज: खुले, आने वाले और लिस्ट हुए IPO</h1>'
            f'<p class="dek">प्राइस बैंड, लॉट साइज़, सब्सक्रिप्शन स्टेटस, अलॉटमेंट और लिस्टिंग की तारीख एक जगह। आंकड़े {e(data.get("asOf", ""))} तक।</p>'
            f'{host}{secs}{learn}<p class="cm-note"><a href="{base}ipo/" lang="en">IPO hub (English)</a> पर हर IPO का पूरा पेज और स्रोत हैं।</p>'
            f'<p class="disc">यह पेज सिर्फ जानकारी के लिए है। TotalMarket किसी IPO में आवेदन करने या न करने की सलाह नहीं देता।</p></article>'
            + _related(hp, ("startups",), c, "IPO की ताज़ा हिंदी खबरें"))
    names = ", ".join(x["name"] for x in (groups.get("open") or [])[:3])
    d = (f"आज के IPO: {names} का सब्सक्रिप्शन स्टेटस, प्राइस बैंड, लॉट साइज़, अलॉटमेंट और लिस्टिंग की तारीख। आने वाले और हाल में लिस्ट हुए IPO भी।" if names
         else "आने वाले IPO, सब्सक्रिप्शन स्टेटस, प्राइस बैंड, लॉट साइज़, अलॉटमेंट और लिस्टिंग की तारीख, आसान हिंदी में।")[:165]
    return c["page"]("IPO आज: सब्सक्रिप्शन स्टेटस और आने वाले IPO", d, f"{base}hi/ipo/", body, meta, seo_title="IPO आज: सब्सक्रिप्शन स्टेटस, आने वाले IPO | TotalMarket",
                     keywords=["IPO आज", "आने वाले IPO", "IPO सब्सक्रिप्शन स्टेटस", "IPO GMP आज", "upcoming IPO in hindi"],
                     lang="hi", alternates=[("en", c["site_url"] + "/ipo/"), ("hi", c["site_url"] + "/hi/ipo/")], switch=(f"{base}ipo/", "English"))


def data_pages(posts, meta, c):
    hp = [p for p in posts if has_hi(p)]
    out = []
    try:
        r = json.load(open(_os.path.join(_ROOT, "data", "rates.json"), encoding="utf-8"))
        out += [("hi/gold-rate-today/index.html", gold_page(r, hp, meta, c)), ("hi/silver-rate-today/index.html", silver_page(r, hp, meta, c))]
    except Exception as ex:
        print("WARNING Hindi gold/silver pages skipped:", ex)
    out.append(("hi/ipo/index.html", ipo_page(hp, meta, c)))
    HUB_URLS.extend(c["site_url"] + "/" + rel.replace("index.html", "") for rel, _ in out)
    return out


def link_english(rel, html_, site_url, base="/"):
    """Add hreflang + a direct 'हिंदी' switch to an English page that has a Hindi twin."""
    key = rel.replace("index.html", "")
    if key not in PAIRS:
        return html_
    hi = PAIRS[key]
    tags = (f'<link rel="alternate" hreflang="en" href="{site_url}/{key}"><link rel="alternate" hreflang="hi" href="{site_url}/{hi}">'
            f'<link rel="alternate" hreflang="x-default" href="{site_url}/{key}">')
    return html_.replace("</head>", tags + "</head>", 1).replace(f'class="langsw" href="{base}hi/"', f'class="langsw" href="{base}{hi}"', 1).replace('>हिंदी</a>', '>हिंदी में देखें</a>', 1)
