"""Structured records exchanged between agents, with validation.

Agents never pass free-form text to each other: every output is a dict checked against a
schema here before it is stored. Invalid output is an agent failure (retried, then blocked).
"""
import enum
import hashlib
import json
import re


class Stage(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    DEDUPLICATED = "DEDUPLICATED"
    PRIORITIZED = "PRIORITIZED"
    ASSIGNED = "ASSIGNED"
    RESEARCHED = "RESEARCHED"
    DRAFTED = "DRAFTED"
    FACT_CHECKED = "FACT_CHECKED"
    GRAPHICS_READY = "GRAPHICS_READY"
    SEO_READY = "SEO_READY"
    INTEGRATED = "INTEGRATED"
    QA_PASSED = "QA_PASSED"
    OWNER_REVIEW = "OWNER_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    # side states
    DUPLICATE = "DUPLICATE"
    SKIPPED = "SKIPPED"          # Boss decided not to cover
    BLOCKED = "BLOCKED"          # retries exhausted / QA or fact check rejected
    SUSPENDED = "SUSPENDED"      # budget exhausted
    REJECTED = "REJECTED"        # owner rejected


class Priority(str, enum.Enum):
    BREAKING = "BREAKING"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


PRIORITY_RANK = {Priority.BREAKING: 0, Priority.HIGH: 1, Priority.NORMAL: 2, Priority.LOW: 3}


class FactStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    NEEDS_CORRECTION = "NEEDS_CORRECTION"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"


class QAOutcome(str, enum.Enum):
    PASS = "PASS"
    RETURN_FOR_CORRECTION = "RETURN_FOR_CORRECTION"
    BLOCKED = "BLOCKED"


class ValidationError(ValueError):
    pass


# ------------------------------------------------------------------ schemas
# type spec: python type, tuple of types, ("list", spec), ("enum", Enum), or a nested dict schema.
# A key ending in "?" is optional.
CANDIDATE = {
    "source_url": str, "source_org": str, "published_at": str, "discovered_at": str,
    "headline": str, "category": str, "instrument?": str, "reliability?": ("enum_str", ("official", "secondary", "unknown")),
    "importance?": (int, float), "demo?": bool, "summary?": str,
}
FACT = {
    "key": str, "label": str, "value": (int, float, str), "unit": str, "as_of": str,
    "doc_id": int, "excerpt": str,
}
EVIDENCE = {"facts": ("list", FACT), "quotes": ("list", {"text": str, "doc_id": int, "speaker": str}),
            "source_refs": ("list", {"doc_id": int, "org": str, "url": str})}
DRAFT = {
    "headline": str, "short_headline": str, "summary": str, "body": ("list", str),
    "takeaways": ("list", str), "entities": ("list", str), "source_refs": ("list", int),
    "claims": ("list", {"text": str, "fact_keys": ("list", str)}),
    "graphic_brief": str, "word_count": int, "language": str,
}
GRAPHIC_ITEM = {"kind": ("enum_str", ("text", "figure", "logo")), "text": str, "label?": str,
                "fact_key?": str, "logo_key?": str, "generated?": bool, "role?": str}
GRAPHIC = {
    "template": str, "method": str, "width": int, "height": int, "items": ("list", GRAPHIC_ITEM),
    "source_fact_keys": ("list", str), "review_status": str, "file?": str, "sha256?": str, "demo?": bool,
}
FINDING = {"claim": str, "status": ("enum", FactStatus), "evidence": (str,), "issue": (str,), "target": str}  # (str,) = may be empty
FACTCHECK = {"status": ("enum", FactStatus), "findings": ("list", FINDING), "checked_numbers": int}


def _check(value, spec, path):
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            raise ValidationError(f"{path}: expected object")
        for key, sub in spec.items():
            opt = key.endswith("?")
            k = key.rstrip("?")
            if k not in value or value[k] is None:
                if opt:
                    continue
                raise ValidationError(f"{path}.{k}: missing")
            _check(value[k], sub, f"{path}.{k}")
        return
    if isinstance(spec, tuple) and spec and spec[0] == "list":
        if not isinstance(value, list):
            raise ValidationError(f"{path}: expected list")
        for i, v in enumerate(value):
            _check(v, spec[1], f"{path}[{i}]")
        return
    if isinstance(spec, tuple) and spec and spec[0] == "enum":
        try:
            spec[1](value)
        except ValueError:
            raise ValidationError(f"{path}: {value!r} not a valid {spec[1].__name__}")
        return
    if isinstance(spec, tuple) and spec and spec[0] == "enum_str":
        if value not in spec[1]:
            raise ValidationError(f"{path}: {value!r} not one of {spec[1]}")
        return
    if spec is str and not isinstance(value, str):
        raise ValidationError(f"{path}: expected text")
    if spec is str and not value.strip():
        raise ValidationError(f"{path}: empty")
    if spec is int and (not isinstance(value, int) or isinstance(value, bool)):
        raise ValidationError(f"{path}: expected integer")
    if spec is bool and not isinstance(value, bool):
        raise ValidationError(f"{path}: expected true/false")
    if isinstance(spec, tuple) and all(isinstance(t, type) for t in spec):
        if not isinstance(value, spec) or isinstance(value, bool):
            raise ValidationError(f"{path}: expected {'/'.join(t.__name__ for t in spec)}")


def validate(value, schema, name="output"):
    _check(value, schema, name)
    return value


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def digest(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def slugify(text: str, limit=80) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].rstrip("-") or "story"
