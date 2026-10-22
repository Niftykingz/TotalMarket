"""Audit every generated page for basic SEO and accessibility rules (run after `py build.py`)."""
import os, re, glob, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")


def pages():
    for f in glob.glob(os.path.join(DOCS, "**", "*.html"), recursive=True):
        if os.sep + "assets" + os.sep in f or f.endswith("404.html"):
            continue
        with open(f, encoding="utf-8") as fh:
            yield os.path.relpath(f, DOCS), fh.read()


class PageAudit(unittest.TestCase):
    def test_pages_exist(self):
        self.assertGreater(sum(1 for _ in pages()), 50)

    def test_seo_basics(self):
        problems = []
        for rel, h in pages():
            if not re.search(r'<html lang="(en-IN|hi-IN)"', h): problems.append(f"{rel}: lang")
            if len(re.findall(r"<h1[ >]", h)) != 1: problems.append(f"{rel}: h1 count {len(re.findall(r'<h1[ >]', h))}")
            if 'rel="canonical"' not in h: problems.append(f"{rel}: canonical")
            if '<meta name="description"' not in h: problems.append(f"{rel}: description")
            if 'property="og:image"' not in h: problems.append(f"{rel}: og:image")
            if "max-image-preview:large" not in h and "noindex" not in h: problems.append(f"{rel}: image preview")
        self.assertEqual(problems, [], "\n".join(problems[:40]))

    def test_images(self):
        problems = []
        for rel, h in pages():
            for img in re.findall(r"<img\b[^>]*>", h):
                if " alt=" not in img: problems.append(f"{rel}: missing alt {img[:80]}")
                if "width=" not in img or "height=" not in img: problems.append(f"{rel}: missing size {img[:80]}")
                if "/covers/" in img and "srcset=" not in img: problems.append(f"{rel}: cover without srcset")
        self.assertEqual(problems, [], "\n".join(problems[:40]))

    def test_articles_have_structured_data(self):
        for rel, h in pages():
            if rel.startswith(("news" + os.sep, "hi" + os.sep + "news")):
                self.assertIn('"NewsArticle"', h, rel)

    def test_never_labelled_live(self):
        for rel, h in pages():
            self.assertNotIn('class="tk tk-live"', h, rel)


if __name__ == "__main__":
    unittest.main()
