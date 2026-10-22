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
    ("nifty-50/", "Nifty 50"), ("ipo/", "IPO हब"), ("gold-rate-today/", "गोल्ड रेट"), ("silver-rate-today/", "सिल्वर रेट"),
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
<nav class="footlinks" aria-label="Market data"><b>मार्केट डेटा:</b> <a href="{base}nifty-50/">Nifty 50 आज</a> · <a href="{base}gold-rate-today/">आज का गोल्ड रेट</a> · <a href="{base}silver-rate-today/">आज का सिल्वर रेट</a> · <a href="{base}fii-dii-data/">FII DII डेटा</a> · <a href="{base}ipo/">IPO</a> · <a href="{base}results/">नतीजों का कैलेंडर</a> · <a href="{base}market-report/">डेली मार्केट रिपोर्ट</a> · <a href="{base}learn/">सीखें</a></nav>
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
                 f'<li><a href="{base}nifty-50/">Nifty 50 आज: क्लोज़ और चार्ट</a></li><li><a href="{base}gold-rate-today/">आज का सोने का भाव (24K, 22K)</a></li>'
                 f'<li><a href="{base}silver-rate-today/">आज का चांदी का भाव</a></li><li><a href="{base}ipo/">IPO: खुले, आने वाले और लिस्टेड</a></li>'
                 f'<li><a href="{base}fii-dii-data/">FII और DII ने कितना खरीदा-बेचा</a></li><li><a href="{base}results/">इस हफ्ते किसके नतीजे</a></li>'
                 f'<li><a href="{base}{"stock-market-holidays-2026/"}">शेयर बाज़ार की छुट्टियां</a></li></ul><small>ये डेटा पेज अभी अंग्रेज़ी में हैं।</small></aside>')
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
