"""T3 — free-text NER masking is mandatory in real-data mode (fail-closed).

The deterministic Safe Harbor regex pass catches STRUCTURED identifiers (SSN,
email, card, ...). It CANNOT catch a bare NAME in prose — that requires an NER
engine. When real customer data is permitted (ALLOW_REAL_DATA truthy) the
masker must therefore require an NER engine and FAIL CLOSED without one, rather
than silently degrading to regex-only and leaking free-text names.

These tests assert:
  * real-data mode without an NER engine raises (fail-closed);
  * real-data mode WITH an NER engine masks free-text names + keeps Safe Harbor;
  * demo mode (default) still works with regex-only, behaviour unchanged.
"""

import os

import pytest

from platform_core import masker


class _FakeNER:
    """Minimal stand-in for Amazon Comprehend DetectPiiEntities.

    Redacts a fixed set of first names to model free-text PERSON detection.
    Returns the (masked_text, count) tuple the masker contract accepts.
    """

    NAMES = ("Alice", "Bob", "Carol")

    def redact(self, text):
        count = 0
        for name in self.NAMES:
            occurrences = text.count(name)
            if occurrences:
                text = text.replace(name, "[NAME-REDACTED]")
                count += occurrences
        return text, count


@pytest.fixture(autouse=True)
def _clean_masker_state():
    """Isolate ALLOW_REAL_DATA and the process-default NER engine per test."""
    saved_env = os.environ.get("ALLOW_REAL_DATA")
    saved_engine = masker.get_ner_engine()
    masker.configure_ner_engine(None)
    os.environ.pop("ALLOW_REAL_DATA", None)
    try:
        yield
    finally:
        masker.configure_ner_engine(saved_engine)
        if saved_env is None:
            os.environ.pop("ALLOW_REAL_DATA", None)
        else:
            os.environ["ALLOW_REAL_DATA"] = saved_env


def test_real_data_mode_without_ner_engine_raises():
    os.environ["ALLOW_REAL_DATA"] = "true"
    assert masker.real_data_mode() is True
    with pytest.raises(masker.MaskingError):
        masker.mask_report("Contact Alice at a@b.com", ["pii"])


def test_real_data_mode_without_ner_engine_fails_closed_via_mask():
    # The mask() wrapper converts the fault into the boundary-deny signal.
    os.environ["ALLOW_REAL_DATA"] = "1"
    with pytest.raises(masker.MaskingFailClosed):
        masker.mask("Contact Alice", ["pii"])


def test_real_data_mode_with_ner_engine_masks_name_and_structured():
    os.environ["ALLOW_REAL_DATA"] = "yes"
    masker.configure_ner_engine(_FakeNER())
    res = masker.mask_report("Alice SSN 123-45-6789", ["pii"])
    # Free-text name masked by NER, structured SSN masked by Safe Harbor regex.
    assert "Alice" not in res.masked_text
    assert "123-45-6789" not in res.masked_text
    assert res.counts.get("NER") == 1
    assert res.counts.get("SSN") == 1


def test_ner_engine_may_be_passed_per_call_in_real_data_mode():
    os.environ["ALLOW_REAL_DATA"] = "on"
    res = masker.mask_report("Bob emailed b@c.com", ["pii"], ner_engine=_FakeNER())
    assert "Bob" not in res.masked_text
    assert res.counts.get("NER") == 1


def test_demo_mode_regex_baseline_unchanged_without_engine():
    # Default (ALLOW_REAL_DATA unset) => demo mode. Regex Safe Harbor still runs;
    # no engine required, and free-text names are simply left (documented limit).
    assert masker.real_data_mode() is False
    res = masker.mask_report("Alice at 123-45-6789", ["pii"])
    assert res.masked_text == "Alice at [SSN-REDACTED]"
    assert res.counts.get("SSN") == 1
    assert "NER" not in res.counts


def test_ner_engine_fault_fails_closed():
    os.environ["ALLOW_REAL_DATA"] = "true"

    class _Boom:
        def redact(self, text):
            raise RuntimeError("comprehend unreachable")

    masker.configure_ner_engine(_Boom())
    with pytest.raises(masker.MaskingError):
        masker.mask_report("Alice", ["pii"])
