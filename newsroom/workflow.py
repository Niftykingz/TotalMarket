"""Story pipeline state machine.

Forward path:
  DISCOVERED → DEDUPLICATED → PRIORITIZED → ASSIGNED → RESEARCHED → DRAFTED → FACT_CHECKED
  → GRAPHICS_READY → SEO_READY → INTEGRATED → QA_PASSED → OWNER_REVIEW → APPROVED → PUBLISHED

Correction loops move a story back (e.g. failed fact check → DRAFTED or RESEARCHED,
owner requests changes → ASSIGNED). Any transition not listed here is refused.

Stages owned by agents that are not enabled yet (SEO, Developer, QA in Phase 1) may be
passed through by the Boss only to reach OWNER_REVIEW as a *preview*; the publish gate
separately demands a QA PASS, so such a story can never be published.
"""
from .models import Stage as S

FORWARD = [S.DISCOVERED, S.DEDUPLICATED, S.PRIORITIZED, S.ASSIGNED, S.RESEARCHED, S.DRAFTED,
           S.FACT_CHECKED, S.GRAPHICS_READY, S.SEO_READY, S.INTEGRATED, S.QA_PASSED,
           S.OWNER_REVIEW, S.APPROVED, S.PUBLISHED]

TRANSITIONS = {a: {b} for a, b in zip(FORWARD, FORWARD[1:])}
_extra = {
    S.DISCOVERED: {S.DUPLICATE},
    S.DEDUPLICATED: {S.DUPLICATE},
    S.PRIORITIZED: {S.SKIPPED},
    S.ASSIGNED: {S.BLOCKED, S.SUSPENDED},
    S.RESEARCHED: {S.ASSIGNED, S.BLOCKED, S.SUSPENDED},                 # missing source → research again
    S.DRAFTED: {S.RESEARCHED, S.ASSIGNED, S.BLOCKED, S.SUSPENDED},     # failed fact check → rewrite / re-research
    S.FACT_CHECKED: {S.DRAFTED, S.BLOCKED, S.SUSPENDED},               # graphic failed → back to designer, article kept
    S.GRAPHICS_READY: {S.DRAFTED, S.FACT_CHECKED, S.OWNER_REVIEW, S.BLOCKED},  # → OWNER_REVIEW only as Phase-1 preview
    S.SEO_READY: {S.DRAFTED, S.BLOCKED},
    S.INTEGRATED: {S.DRAFTED, S.SEO_READY, S.BLOCKED},
    S.QA_PASSED: {S.DRAFTED, S.BLOCKED},
    S.OWNER_REVIEW: {S.ASSIGNED, S.DRAFTED, S.REJECTED},               # request changes / reject
    S.APPROVED: {S.DRAFTED},                                           # material change invalidates approval
    S.PUBLISHED: {S.DRAFTED},                                          # correction after publication
    S.SUSPENDED: {S.ASSIGNED, S.RESEARCHED, S.DRAFTED},                # resumed after owner raises budget
    S.BLOCKED: {S.ASSIGNED, S.RESEARCHED, S.DRAFTED},                  # Boss reassigns after a fix
}
for k, v in _extra.items():
    TRANSITIONS.setdefault(k, set()).update(v)

PREVIEW_SKIP = {(S.GRAPHICS_READY, S.OWNER_REVIEW)}   # allowed only when SEO/Dev/QA agents are disabled


class TransitionError(RuntimeError):
    pass


def check(current, target, enabled_agents=()):
    a, b = S(current), S(target)
    if b not in TRANSITIONS.get(a, set()):
        raise TransitionError(f"{a.value} → {b.value} is not an allowed transition")
    if (a, b) in PREVIEW_SKIP and {"seo", "developer", "qa"} & set(enabled_agents):
        raise TransitionError("SEO/Developer/QA are enabled: the story must go through them")
    return b


def move(db, story_id, target, actor, reason="", enabled_agents=()):
    st = db.one("SELECT stage FROM stories WHERE id=?", (story_id,))
    if not st:
        raise TransitionError(f"story {story_id} not found")
    if S(st["stage"]) == S(target):
        return S(target)
    b = check(st["stage"], target, enabled_agents)
    from .database import now
    db.x("UPDATE stories SET stage=?, updated_at=? WHERE id=?", (b.value, now(), story_id))
    db.audit(actor, "stage", story_id, frm=st["stage"], to=b.value, reason=reason)
    return b
