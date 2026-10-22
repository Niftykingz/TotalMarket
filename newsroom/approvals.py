"""Revisions, owner approval and the publish gate.

* A revision is an immutable snapshot of the complete article package (draft + graphic
  spec + graphic file hash). Its SHA-256 identifies exactly what was reviewed.
* Approval is tied to that SHA. A new revision automatically invalidates it.
* `publish_gate()` lists every reason a story cannot be published. In this build it always
  includes "production publishing is disabled".
"""
import json

from . import permissions, workflow
from .database import now
from .models import Stage, digest


def create_revision(db, story_id, content, created_by):
    sha = digest(content)
    cur = db.one("SELECT number, sha256 FROM revisions WHERE story_id=? ORDER BY number DESC LIMIT 1", (story_id,))
    if cur and cur["sha256"] == sha:
        return sha, cur["number"]
    number = (cur["number"] + 1) if cur else 1
    db.x("INSERT INTO revisions(story_id, number, content, sha256, created_by, created_at) VALUES (?,?,?,?,?,?)",
         (story_id, number, json.dumps(content, ensure_ascii=False, sort_keys=True), sha, created_by, now()))
    prev = db.one("SELECT current_revision, stage FROM stories WHERE id=?", (story_id,))
    db.x("UPDATE stories SET current_revision=?, updated_at=? WHERE id=?", (sha, now(), story_id))
    db.audit(created_by, "revision", story_id, number=number, sha=sha)
    if prev and prev["current_revision"] and valid_approval(db, story_id, prev["current_revision"]):
        db.x("INSERT INTO approvals(story_id, revision_sha, decision, actor, note, created_at) VALUES (?,?,?,?,?,?)",
             (story_id, prev["current_revision"], "invalidated", "system", f"superseded by revision {number}", now()))
        db.audit("system", "approval_invalidated", story_id, old=prev["current_revision"], new=sha)
        if prev["stage"] in (Stage.APPROVED.value, Stage.PUBLISHED.value):
            workflow.move(db, story_id, Stage.DRAFTED, "system", "material change after approval: re-check required")
    return sha, number


def current_revision(db, story_id):
    r = db.one("SELECT * FROM revisions WHERE story_id=? ORDER BY number DESC LIMIT 1", (story_id,))
    if r:
        r["content"] = json.loads(r["content"])
    return r


def valid_approval(db, story_id, sha):
    last = db.one("SELECT decision FROM approvals WHERE story_id=? AND revision_sha=? ORDER BY id DESC LIMIT 1", (story_id, sha))
    return bool(last and last["decision"] == "approve")


def checks_for(db, story_id, rev):
    """Fact-check results for exactly the article and graphic inside revision `rev`."""
    c = rev["content"]
    art = db.one("SELECT status FROM fact_checks WHERE story_id=? AND target='article' AND subject_sha=? ORDER BY id DESC LIMIT 1",
                 (story_id, c["article_sha"]))
    gfx = db.one("SELECT status FROM fact_checks WHERE story_id=? AND target='graphic' AND subject_sha=? ORDER BY id DESC LIMIT 1",
                 (story_id, c["graphic_sha"]))
    return (art or {}).get("status"), (gfx or {}).get("status")


def decide(db, story_id, decision, owner_key, revision_sha, note=""):
    """Owner decision. `revision_sha` must be the revision the owner actually read."""
    action = {"approve": "approve", "reject": "reject", "request_changes": "request_changes"}[decision]
    permissions.require_owner(owner_key, action)
    st = db.one("SELECT stage, current_revision FROM stories WHERE id=?", (story_id,))
    if st["stage"] != Stage.OWNER_REVIEW.value:
        raise permissions.PermissionDenied(f"story is at {st['stage']}, not OWNER_REVIEW")
    if revision_sha != st["current_revision"]:
        raise permissions.PermissionDenied("the story changed since you opened it; review the latest revision")
    if decision == "approve":
        rev = current_revision(db, story_id)
        a, g = checks_for(db, story_id, rev)
        if a != "VERIFIED" or g != "VERIFIED":
            raise permissions.PermissionDenied(f"mandatory checks not passed (article={a}, graphic={g})")
    db.x("INSERT INTO approvals(story_id, revision_sha, decision, actor, note, created_at) VALUES (?,?,?,?,?,?)",
         (story_id, revision_sha, decision, "owner", note, now()))
    db.audit("owner", decision, story_id, revision=revision_sha, note=note)
    target = {"approve": Stage.APPROVED, "reject": Stage.REJECTED, "request_changes": Stage.ASSIGNED}[decision]
    workflow.move(db, story_id, target, "owner", note or decision)
    return target


def publish_gate(db, story_id):
    """Every reason this story may not be published. Empty list = allowed."""
    reasons = []
    if not permissions.PRODUCTION_PUBLISHING:
        reasons.append("production publishing is disabled in this build (Phase 4, needs owner authorization)")
    if not permissions.publisher_credential():
        reasons.append("no publisher credential (TM_PUBLISH_TOKEN)")
    st = db.one("SELECT * FROM stories WHERE id=?", (story_id,))
    if st["demo"]:
        reasons.append("demonstration story: never publishable")
    rev = current_revision(db, story_id)
    if not rev:
        return reasons + ["no revision"]
    if st["stage"] != Stage.APPROVED.value:
        reasons.append(f"stage is {st['stage']}, not APPROVED")
    if not valid_approval(db, story_id, rev["sha256"]):
        reasons.append("no owner approval for the current revision")
    a, g = checks_for(db, story_id, rev)
    if a != "VERIFIED":
        reasons.append(f"article fact check is {a}")
    if g != "VERIFIED":
        reasons.append(f"graphic check is {g}")
    qa = db.one("SELECT outcome FROM qa_reports WHERE story_id=? AND revision_sha=? ORDER BY id DESC LIMIT 1", (story_id, rev["sha256"]))
    if not qa or qa["outcome"] != "PASS":
        reasons.append("no QA PASS for the current revision")
    if db.one("SELECT 1 FROM publications WHERE story_id=? AND revision_sha=?", (story_id, rev["sha256"])):
        reasons.append("this revision is already published")
    return reasons


class PublishRefused(PermissionError):
    pass


def publish(db, story_id, role="publisher"):
    """The only code path that can record a publication. Refuses unless every gate passes."""
    permissions.require(role, "publish")
    reasons = publish_gate(db, story_id)
    db.audit(role, "publish_attempt", story_id, allowed=not reasons, reasons=reasons)
    if reasons:
        raise PublishRefused("; ".join(reasons))
    raise PublishRefused("publishing agent not implemented in Phase 1")  # pragma: no cover
