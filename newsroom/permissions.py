"""Who may do what. Enforced in code; no agent, prompt or settings file can change it.

Roles
  owner      Mayur. Approves/rejects stories, raises budgets. Authenticated with the
             TM_NEWSROOM_OWNER_KEY environment variable.
  boss       Editor-in-chief agent. Ranks, assigns, moves stages, prepares owner review.
  agent      Specialist agents. Write only their own task outputs.
  developer  Builds local previews / commits on the development branch (Phase 3).
  publisher  Publishing agent (Phase 4). Needs TM_PUBLISH_TOKEN *and* PRODUCTION_PUBLISHING.

The permission table is a frozen mapping; nothing writes to it at runtime.
"""
import hmac
from types import MappingProxyType

from .config import secret

# Production publishing is OFF in this build. Turning it on is a code change the owner
# must review and approve; it is deliberately not a setting.
PRODUCTION_PUBLISHING = False

PERMISSIONS = MappingProxyType({
    "owner": frozenset({"approve", "reject", "request_changes", "raise_budget", "view", "settings"}),
    "boss": frozenset({"rank", "assign", "move_stage", "prepare_review", "view"}),
    "agent": frozenset({"task_output", "view"}),
    "developer": frozenset({"preview", "commit_dev_branch", "view"}),
    "publisher": frozenset({"publish", "view"}),
})


class PermissionDenied(PermissionError):
    pass


def require(role: str, action: str):
    if action not in PERMISSIONS.get(role, frozenset()):
        raise PermissionDenied(f"role '{role}' may not '{action}'")


def owner_authenticated(key: str) -> bool:
    expected = secret("TM_NEWSROOM_OWNER_KEY")
    return bool(expected) and bool(key) and hmac.compare_digest(expected.encode(), str(key).encode())


def require_owner(key: str, action: str):
    require("owner", action)
    if not owner_authenticated(key):
        raise PermissionDenied("owner key missing or wrong (set TM_NEWSROOM_OWNER_KEY and pass it)")


def publisher_credential() -> bool:
    return bool(secret("TM_PUBLISH_TOKEN"))
