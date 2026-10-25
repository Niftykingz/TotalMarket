"""Prepare social drafts from existing TotalMarket stories. No posting capability."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "data" / "posts"
OUT = ROOT / "social" / "drafts"

def prepare(limit=20):
    OUT.mkdir(parents=True, exist_ok=True)
    count = 0
    for source in sorted(POSTS.glob("*.json"), reverse=True):
        try:
            story = json.loads(source.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        title = str(story.get("title") or "").strip()
        sources = story.get("sources") or []
        if not title or not isinstance(sources, list) or not any(isinstance(s, dict) and str(s.get("url", "")).startswith("https://") for s in sources):
            continue
        key = hashlib.sha256(source.name.encode()).hexdigest()[:16]
        dest = OUT / (key + ".json")
        if dest.exists():
            continue
        dek = str(story.get("dek") or "").strip()
        url = "https://totalmarket.co.in/"  # Replace with verified canonical article URL at approval time.
        draft = {
            "id": key, "state": "pending_approval", "source_file": source.relative_to(ROOT).as_posix(),
            "title": title, "category": story.get("category"), "publishedAt": story.get("publishedAt"),
            "sources": sources, "article_url": None,
            "instagram": {"caption": (title + "\n\n" + dek).strip() + "\n\nRead more at TotalMarket.", "image_path": None},
            "x": {"text": (title + (" — " + dek if dek else ""))[:240] + "\n\nSource: TotalMarket", "image_path": None},
            "approval": {"approved": False, "approved_by": None, "approved_at": None},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        dest.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        count += 1
        if count >= limit:
            break
    return count

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    print(f"Prepared {prepare(args.limit)} new drafts; nothing published.")
