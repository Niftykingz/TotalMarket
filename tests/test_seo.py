"""Search-facing checks on the built site (run after `py build.py`), following Google Search Central basics."""
import os, re, glob, json, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SITE = "https://totalmarket.co.in"


def read(rel):
    with open(os.path.join(DOCS, rel), encoding="utf-8") as fh:
        return fh.read()


def html_pages():
    for f in glob.glob(os.path.join(DOCS, "**", "*.html"), recursive=True):
        if os.sep + "assets" + os.sep not in f:
            yield os.path.relpath(f, DOCS).replace(os.sep, "/"), read(os.path.relpath(f, DOCS))


def ld_blocks(h):
    out = []
    for s in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        data = json.loads(s.replace("<\\/", "</"))
        out += data if isinstance(data, list) else [data]
    return out


class SEO(unittest.TestCase):
    def test_titles_and_descriptions(self):
        bad, seen_t, seen_d = [], {}, {}
        for rel, h in html_pages():
            if "noindex" in h:
                continue
            t = re.search(r"<title>(.*?)</title>", h, re.S).group(1)
            d = re.search(r'<meta name="description" content="([^"]*)"', h).group(1)
            tt = re.sub(r"&#?\w+;", "x", t)
            if len(tt) > 65: bad.append(f"{rel}: title {len(tt)} chars")
            if not 50 <= len(d) <= 170: bad.append(f"{rel}: description {len(d)} chars")
            if re.search(r"\b(developing story|lorem|todo|tbd)\b", d, re.I): bad.append(f"{rel}: placeholder description")
            if t in seen_t: bad.append(f"{rel}: duplicate title with {seen_t[t]}")
            if d in seen_d: bad.append(f"{rel}: duplicate description with {seen_d[d]}")
            seen_t[t] = rel; seen_d[d] = rel
        self.assertEqual(bad, [], "\n".join(bad[:40]))

    def test_structured_data_parses_and_is_complete(self):
        home = ld_blocks(read("index.html"))
        types = {b.get("@type") for b in home}
        self.assertIn("WebSite", types)
        self.assertIn("NewsMediaOrganization", types)
        org = next(b for b in home if b.get("@type") == "NewsMediaOrganization")
        self.assertTrue(org["logo"]["url"].endswith("/assets/logo.png"))
        for key in ("publishingPrinciples", "correctionsPolicy", "actionableFeedbackPolicy"):
            path = org[key].replace(SITE, "").strip("/")
            self.assertTrue(os.path.exists(os.path.join(DOCS, path, "index.html")), key)
        n = 0
        for rel, h in html_pages():
            for b in ld_blocks(h):  # every block must be valid JSON (json.loads above)
                if b.get("@type") == "NewsArticle":
                    n += 1
                    for k in ("headline", "datePublished", "dateModified", "image", "author", "publisher"):
                        self.assertIn(k, b, f"{rel}: {k}")
                    self.assertLessEqual(len(b["headline"]), 110, rel)
                    self.assertTrue(all(u.startswith(SITE + "/covers/") for u in b["image"]), rel)
        self.assertGreater(n, 50)

    def test_article_images_are_large_and_exist(self):
        for rel, h in html_pages():
            m = re.search(r'<meta property="og:image" content="([^"]+)"', h)
            self.assertTrue(m, rel)
            path = m.group(1).replace(SITE, "").lstrip("/")
            self.assertTrue(os.path.exists(os.path.join(DOCS, path)), f"{rel}: og image missing {path}")

    def test_favicon_files(self):
        from PIL import Image
        for f, size in (("favicon.ico", 48), ("assets/favicon-48.png", 48), ("assets/favicon-96.png", 96), ("assets/favicon-144.png", 144)):
            im = Image.open(os.path.join(DOCS, f))
            self.assertEqual(im.size, (size, size), f)
        h = read("index.html")
        self.assertIn('href="/favicon.ico"', h)
        self.assertIn('href="/assets/favicon-48.png"', h)
        robots = read("robots.txt")
        self.assertNotRegex(robots, r"Disallow:\s*/(assets|covers|favicon)")

    def test_sitemap_covers_indexable_pages(self):
        sm = read("sitemap.xml")
        urls = set(re.findall(r"<loc>([^<]+)</loc>", sm))
        for rel, h in html_pages():
            if "noindex" in h or rel == "404.html":
                self.assertNotIn(SITE + "/" + rel.replace("index.html", ""), urls, f"noindex page in sitemap: {rel}")
            else:
                self.assertIn(SITE + "/" + rel.replace("index.html", ""), urls, f"missing from sitemap: {rel}")
        for p in ("editorial-policy/", "corrections/", "contact/", "about/"):
            self.assertIn(f"{SITE}/{p}", urls)

    def test_snippet_controls(self):
        h = read("index.html")
        self.assertRegex(h, r'<section class="tickers"[^>]*data-nosnippet')
        self.assertIn("max-image-preview:large", h)


if __name__ == "__main__":
    unittest.main()
