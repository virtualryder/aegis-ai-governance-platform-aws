"""masker — deterministic, fail-closed boundary masking.

Implements the "Masking that fails closed" control from
docs/02-REFERENCE-ARCHITECTURE.md §6 and minimum-bar point 7. Sensitive data
(PII/PHI/FTI/CJI/EDU/card) must never land in a prompt, a log, or the audit
unmasked. If masking cannot run, the boundary DENIES rather than leaks.

Two layers, by design:

1. Deterministic Safe Harbor pass (ALWAYS on). Regexes over the structured
   identifiers the active pack enables (SSN, email, phone, card, MRN, student
   id). Deterministic — the same input always yields the same masked output and
   the same field count, which matters for a live demo. Production maps this to
   Amazon Comprehend / Comprehend Medical / Macie + S3 Object Lambda.

2. Free-text / unstructured PII pass via a pluggable NER engine (Named Entity
   Recognition, e.g. Amazon Comprehend `DetectPiiEntities`). Regexes cannot
   find a bare NAME in prose; that requires NER. The engine is OPTIONAL in
   default/demo mode and MANDATORY in real-data mode.

Real-data mode is controlled by the `ALLOW_REAL_DATA` environment variable
(truthy = real data permitted; unset/false = synthetic demo data). When
real-data mode is ON, an NER engine MUST be configured; if none is available
the masker FAILS CLOSED (raises MaskingError) rather than silently degrading to
regex-only and leaking free-text names. In demo mode the behaviour is unchanged:
the regex Safe Harbor baseline always runs, and NER runs only if an engine has
been configured.

Entity coverage (structured, regex Safe Harbor pass — mapped to data classes):
    SSN          -> pii / fti
    EMAIL        -> pii
    PHONE        -> pii
    CREDIT_CARD  -> card  (Luhn-validated so non-card digit runs are NOT masked)
    MRN          -> phi   (medical record number)
    STUDENT_ID   -> edu   (FERPA)
Free-text names and other unstructured PII are NOT covered by regex; they
require the NER engine (mandatory in real-data mode).

NER engine contract (duck-typed): an object with a `redact(text) -> result`
method where `result` is either a `(masked_text, count)` tuple or an object
exposing `.masked_text` and `.count`.

Public API:
    mask(text, data_classes, ner_engine=None) -> masked_text  (MaskingFailClosed on fault)
    mask_report(text, data_classes, ner_engine=None) -> MaskResult
    configure_ner_engine(engine)  /  get_ner_engine()         (process default NER hook)
    MaskingError                                              (masking cannot run)
    MaskingFailClosed                                        (boundary-deny signal)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


class MaskingError(Exception):
    """Raised when masking cannot run. The boundary must DENY, never leak."""


class MaskingFailClosed(Exception):
    """Boundary-level fail-closed signal: masking failed, so access is denied."""


# --------------------------------------------------------------------------- #
# Entity definitions
# --------------------------------------------------------------------------- #

# Map each entity to the data classes that should trigger it.
_ENTITY_CLASSES = {
    "SSN": {"pii", "fti"},
    "EMAIL": {"pii"},
    "PHONE": {"pii"},
    "CREDIT_CARD": {"card"},
    "MRN": {"phi"},
    "STUDENT_ID": {"edu"},
}

# Order matters: mask the most specific / longest patterns first so we do not,
# e.g., partially consume a credit-card number as a phone number.
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
# Candidate card: 13-19 digits, optionally separated by spaces or hyphens.
_CARD_CANDIDATE_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
# Phone: US-style; deliberately conservative to avoid eating SSNs/cards.
_PHONE_RE = re.compile(
    r"\b(?:\+?1[ .\-]?)?(?:\(\d{3}\)|\d{3})[ .\-]\d{3}[ .\-]\d{4}\b"
)
# MRN: explicit "MRN" prefix to avoid false positives on arbitrary numbers.
_MRN_RE = re.compile(r"\bMRN[:#]?\s?[A-Z0-9\-]{4,12}\b", re.IGNORECASE)
# Student id: explicit "SID"/"Student ID" prefix (FERPA-protected identifier).
_STUDENT_RE = re.compile(
    r"\b(?:SID|Student\s?ID)[:#]?\s?[A-Z0-9\-]{4,12}\b", re.IGNORECASE
)

_REDACT = {
    "SSN": "[SSN-REDACTED]",
    "EMAIL": "[EMAIL-REDACTED]",
    "PHONE": "[PHONE-REDACTED]",
    "CREDIT_CARD": "[CARD-REDACTED]",
    "MRN": "[MRN-REDACTED]",
    "STUDENT_ID": "[STUDENT-ID-REDACTED]",
}


@dataclass
class MaskResult:
    masked_text: str
    counts: dict = field(default_factory=dict)
    masked_fields: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Real-data mode + pluggable NER engine (free-text / unstructured PII)
# --------------------------------------------------------------------------- #

_REAL_DATA_TRUTHY = {"1", "true", "yes", "on"}

# Process-wide default NER engine. None => no NER available. In production this
# is wired to Amazon Comprehend DetectPiiEntities (or Comprehend Medical).
_DEFAULT_NER_ENGINE = None

_NER_REDACT = "[NAME-REDACTED]"


def real_data_mode() -> bool:
    """True when ALLOW_REAL_DATA is truthy (real customer data permitted).

    Default (unset/false) is synthetic/demo data. In real-data mode the NER
    engine is mandatory and the masker fails closed without it.
    """
    return os.environ.get("ALLOW_REAL_DATA", "").strip().lower() in _REAL_DATA_TRUTHY


def configure_ner_engine(engine) -> None:
    """Register the process-default NER engine (or None to clear it)."""
    global _DEFAULT_NER_ENGINE
    _DEFAULT_NER_ENGINE = engine


def get_ner_engine():
    """Return the process-default NER engine (may be None)."""
    return _DEFAULT_NER_ENGINE


def _resolve_ner_engine(ner_engine):
    return ner_engine if ner_engine is not None else _DEFAULT_NER_ENGINE


def _apply_ner(engine, text):
    """Run the NER engine over `text`; return (masked_text, count).

    Accepts either a `(masked_text, count)` tuple or an object exposing
    `.masked_text` and `.count`. Any engine fault is surfaced as MaskingError so
    the boundary fails closed rather than leaking unmasked free-text PII.
    """
    try:
        result = engine.redact(text)
    except Exception as exc:  # engine fault -> fail closed
        raise MaskingError(f"NER engine failed: {exc}") from exc

    if isinstance(result, tuple) and len(result) == 2:
        masked_text, count = result
    elif hasattr(result, "masked_text") and hasattr(result, "count"):
        masked_text, count = result.masked_text, result.count
    else:
        raise MaskingError(
            "NER engine returned an unsupported result; expected (masked_text, "
            "count) or an object with .masked_text/.count"
        )

    if not isinstance(masked_text, str):
        raise MaskingError("NER engine returned non-str masked_text")
    try:
        count = int(count)
    except (TypeError, ValueError) as exc:
        raise MaskingError("NER engine returned non-integer count") from exc
    return masked_text, count


def luhn_ok(digits: str) -> bool:
    """Validate a digit string with the Luhn algorithm (PCI PAN check)."""
    nums = [int(c) for c in digits if c.isdigit()]
    if len(nums) < 13 or len(nums) > 19:
        return False
    checksum = 0
    parity = len(nums) % 2
    for i, n in enumerate(nums):
        if i % 2 == parity:
            n *= 2
            if n > 9:
                n -= 9
        checksum += n
    return checksum % 10 == 0


def _active_entities(data_classes) -> list[str]:
    classes = set(data_classes or [])
    active = [
        ent for ent, cls in _ENTITY_CLASSES.items() if cls & classes
    ]
    # Deterministic, specificity-ordered processing.
    order = ["CREDIT_CARD", "SSN", "EMAIL", "PHONE", "MRN", "STUDENT_ID"]
    return [e for e in order if e in active]


def mask_report(text, data_classes, ner_engine=None) -> MaskResult:
    """Mask `text` for the given data classes; return text + per-entity counts.

    The deterministic Safe Harbor regex pass ALWAYS runs. A free-text NER pass
    runs when an engine is available. In real-data mode (ALLOW_REAL_DATA truthy)
    an NER engine is MANDATORY: if none is configured this raises MaskingError so
    the boundary fails closed instead of leaking unmasked free-text names.

    Raises MaskingError if masking cannot run (caller must treat as fail-closed).
    """
    if text is None:
        raise MaskingError("cannot mask None input")
    if not isinstance(text, str):
        raise MaskingError(f"cannot mask non-str input of type {type(text).__name__}")

    engine = _resolve_ner_engine(ner_engine)
    if real_data_mode() and engine is None:
        # Fail closed: real customer data may contain free-text names that the
        # regex Safe Harbor pass cannot catch. Do NOT silently fall back.
        raise MaskingError(
            "real-data mode (ALLOW_REAL_DATA) requires a configured NER engine "
            "to mask free-text/unstructured PII; none available — failing closed"
        )

    counts: dict[str, int] = {}
    masked_fields: list[str] = []
    out = text

    for ent in _active_entities(data_classes):
        if ent == "CREDIT_CARD":
            def _card_sub(match):
                token = match.group(0)
                if luhn_ok(token):
                    counts["CREDIT_CARD"] = counts.get("CREDIT_CARD", 0) + 1
                    masked_fields.append("CREDIT_CARD")
                    return _REDACT["CREDIT_CARD"]
                return token  # not a real PAN -> leave alone (Luhn-aware)

            out = _CARD_CANDIDATE_RE.sub(_card_sub, out)
            continue

        pattern = {
            "SSN": _SSN_RE,
            "EMAIL": _EMAIL_RE,
            "PHONE": _PHONE_RE,
            "MRN": _MRN_RE,
            "STUDENT_ID": _STUDENT_RE,
        }[ent]

        n = len(pattern.findall(out))
        if n:
            counts[ent] = counts.get(ent, 0) + n
            masked_fields.extend([ent] * n)
            out = pattern.sub(_REDACT[ent], out)

    # Free-text / unstructured PII (e.g. bare NAMES) via the NER engine. Runs
    # after the deterministic Safe Harbor pass so both layers apply. Mandatory
    # in real-data mode (enforced above); optional in demo mode.
    if engine is not None:
        out, ner_count = _apply_ner(engine, out)
        if ner_count:
            counts["NER"] = counts.get("NER", 0) + ner_count
            masked_fields.extend(["NER"] * ner_count)

    return MaskResult(masked_text=out, counts=counts, masked_fields=masked_fields)


def mask(text, data_classes, ner_engine=None) -> str:
    """Convenience wrapper returning only the masked text.

    On any masking fault this raises MaskingFailClosed so the gateway boundary
    denies the call rather than risking a leak.
    """
    try:
        return mask_report(text, data_classes, ner_engine=ner_engine).masked_text
    except MaskingError as exc:
        raise MaskingFailClosed(
            f"masking could not run, denying at boundary: {exc}"
        ) from exc


def contains_sensitive(text, data_classes, ner_engine=None) -> bool:
    """True if `text` still contains maskable sensitive data for these classes."""
    return bool(mask_report(text, data_classes, ner_engine=ner_engine).counts)
