"""masker — deterministic, fail-closed boundary masking.

Implements the "Masking that fails closed" control from
docs/02-REFERENCE-ARCHITECTURE.md §6 and minimum-bar point 7. Sensitive data
(PII/PHI/FTI/CJI/EDU/card) must never land in a prompt, a log, or the audit
unmasked. If masking cannot run, the boundary DENIES rather than leaks.

Production uses Amazon Comprehend / Comprehend Medical / Macie + S3 Object
Lambda. This is the offline analog: deterministic regexes over the entity sets
the active pack enables. Determinism matters for a live demo — the same input
always yields the same masked output, and the same field count.

Entity coverage (mapped to data classes):
    SSN          -> pii / fti
    EMAIL        -> pii
    PHONE        -> pii
    CREDIT_CARD  -> card  (Luhn-validated so non-card digit runs are NOT masked)
    MRN          -> phi   (medical record number)
    STUDENT_ID   -> edu   (FERPA)

Public API:
    mask(text, data_classes) -> masked_text         (raises MaskingError on fault)
    mask_report(text, data_classes) -> MaskResult    (text + per-entity counts)
    MaskingFailClosed                                (boundary-deny signal)
"""

from __future__ import annotations

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


def mask_report(text, data_classes) -> MaskResult:
    """Mask `text` for the given data classes; return text + per-entity counts.

    Raises MaskingError if masking cannot run (caller must treat as fail-closed).
    """
    if text is None:
        raise MaskingError("cannot mask None input")
    if not isinstance(text, str):
        raise MaskingError(f"cannot mask non-str input of type {type(text).__name__}")

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

    return MaskResult(masked_text=out, counts=counts, masked_fields=masked_fields)


def mask(text, data_classes) -> str:
    """Convenience wrapper returning only the masked text.

    On any masking fault this raises MaskingFailClosed so the gateway boundary
    denies the call rather than risking a leak.
    """
    try:
        return mask_report(text, data_classes).masked_text
    except MaskingError as exc:
        raise MaskingFailClosed(
            f"masking could not run, denying at boundary: {exc}"
        ) from exc


def contains_sensitive(text, data_classes) -> bool:
    """True if `text` still contains maskable sensitive data for these classes."""
    return bool(mask_report(text, data_classes).counts)
