"""Send story alerts to Telegram: cover photo + title + dek + a clear 'full details' link.

    TG_TOKEN=... [TG_CHAT=id1,id2] python3 tools/telegram_notify.py <story-id> [...]
Token and chat come from GitHub secrets only; never commit them.
"""
import glob
import html
import json
import os
import sys
import urllib.parse
import urllib.request

SITE = "https://totalmarket.co.in"


def chats(tok):
    chat = os.environ.get("TG_CHAT", "")
    if chat:
        return [c.strip() for c in chat.split(",") if c.strip()]
    with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=30) as r:
        res = json.load(r).get("result", [])
    ids = []
    for u in res:
        c = (u.get("message") or u.get("my_chat_member") or u.get("channel_post") or {}).get("chat", {})
        if c.get("id") and str(c["id"]) not in ids:
            ids.append(str(c["id"]))
    return ids


def caption(p, url):
    return (f"<b>{html.escape(p.get('title', ''))}</b>\n\n{html.escape(p.get('dek', ''))}\n\n"
            f"👉 <b>Click here for full details, charts and data:</b>\n{url}\n\n#TotalMarket")


def main(ids):
    tok = os.environ.get("TG_TOKEN")
    if not tok:
        print("TELEGRAM_BOT_TOKEN not set; skipping.")
        return 0
    to = chats(tok)
    if not to:
        print("No chat found: press Start on the bot, then re-run.")
        return 0
    for sid in ids:
        f = f"data/posts/{sid}.json"
        if not os.path.exists(f):
            continue
        p = json.load(open(f, encoding="utf-8"))
        url = f"{SITE}/news/{sid}/"
        jpg = sorted(glob.glob(f"docs/covers/{sid}-*.jpg"))
        if jpg:
            method, data = "sendPhoto", {"photo": f"{SITE}/covers/{os.path.basename(jpg[-1])}", "caption": caption(p, url), "parse_mode": "HTML"}
        else:
            method, data = "sendMessage", {"text": caption(p, url), "parse_mode": "HTML"}
        for c in to:
            data["chat_id"] = c
            req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{method}", data=urllib.parse.urlencode(data).encode())
            try:
                print(sid, urllib.request.urlopen(req, timeout=30).status)
            except Exception as e:
                print("failed", sid, e)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
