"""Newsroom settings. Defaults are safe: mock provider, zero budget for paid calls, publishing off.

Settings come from (lowest to highest precedence): the defaults below, an optional JSON file
(`newsroom/var/settings.json` or TM_NEWSROOM_SETTINGS), and environment variables for secrets.
Secrets (API keys, owner key, GitHub tokens) are ONLY read from environment variables and are
never written to the database, logs, HTML or commits.

Settings cannot switch production publishing on: that is a code constant in permissions.py.
"""
import json
import os
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # repository root (contains build.py)
PKG = Path(__file__).resolve().parent
VAR = Path(os.environ.get("TM_NEWSROOM_VAR") or (PKG / "var"))

CATEGORIES = ("markets", "policy", "commodities", "global", "tech", "startups")

# Official / primary sources first (Researcher ranks these highest). Anything else is
# "secondary" and can only support a story, never be the sole evidence for a policy claim.
DEFAULT_ALLOWLIST = {
    "rbi.org.in": "official", "sebi.gov.in": "official", "nseindia.com": "official",
    "nsearchives.nseindia.com": "official", "bseindia.com": "official", "pib.gov.in": "official",
    "mospi.gov.in": "official", "nsdl.co.in": "official", "finmin.nic.in": "official",
    "indiabudget.gov.in": "official",
    "mock.totalmarket.local": "official",   # demo fixtures only
}


@dataclass
class Settings:
    provider: str = "mock"                 # "mock" only until the owner approves a paid provider
    model: str = "mock-deterministic-1"
    enabled_agents: tuple = ("boss", "researcher", "writer", "fact_checker", "designer")
    categories: tuple = CATEGORIES
    daily_story_limit: int = 12
    concurrency: int = 3                   # bounded worker pool
    retry_limit: int = 2                   # retries after the first attempt
    budget_daily_inr: float = 0.0          # hard cap for PAID calls; 0 = no paid calls at all
    budget_monthly_inr: float = 0.0
    calls_per_minute: int = 60             # provider rate limit
    allowlist: dict = field(default_factory=lambda: dict(DEFAULT_ALLOWLIST))
    network_fetch: bool = False            # Phase 1 uses fixtures; live fetching is off
    require_owner_approval: bool = True    # cannot be set False (enforced in permissions)
    db_path: str = ""

    def db(self) -> Path:
        return Path(self.db_path) if self.db_path else VAR / "newsroom.db"

    def public(self) -> dict:
        """Settings as shown on the dashboard (no secrets live here)."""
        d = asdict(self)
        d["db_path"] = str(self.db())
        return d


def load(path=None, **overrides) -> Settings:
    s = Settings()
    p = Path(path or os.environ.get("TM_NEWSROOM_SETTINGS") or (VAR / "settings.json"))
    data = {}
    if p.is_file():
        data = json.loads(p.read_text(encoding="utf-8"))
    data.update(overrides)
    known = {f.name for f in fields(Settings)}
    for k, v in data.items():
        if k not in known:
            raise ValueError(f"unknown setting: {k}")
        if isinstance(getattr(s, k), tuple) and isinstance(v, list):
            v = tuple(v)
        setattr(s, k, v)
    if s.require_owner_approval is not True:
        raise ValueError("require_owner_approval cannot be disabled")
    if s.concurrency < 1 or s.concurrency > 16:
        raise ValueError("concurrency must be 1..16")
    return s


def secret(name: str) -> str:
    """Read a secret from the environment only (never from settings files)."""
    return os.environ.get(name, "")
