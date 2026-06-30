"""model_gateway — offline, deterministic "model" with governance wiring.

Implements docs/02-REFERENCE-ARCHITECTURE.md §4: the Model Gateway centralizes
all model access so no agent calls a model directly. It enforces an approved
model-profile allowlist per agent, task-based routing (cheap model to
classify/route, stronger model only to draft), prompt-version pinning,
JSON-schema validation of structured output, and a contextual-grounding score
that flags hallucination.

This is 100% OFFLINE and DETERMINISTIC — no network, no API key. The "model" is
a small rule-based function so a live demo always produces the same output and
the same grounding verdict.

Public API:
    ModelGateway.invoke(agent_id, task, prompt, sources, ...) -> ModelResult
    ModelResult: .text .structured .grounded .tokens_in .tokens_out .model_profile
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


class ModelGatewayError(Exception):
    """Raised on profile-allowlist, prompt-pin, or schema-validation failures."""


# Two deterministic "model profiles": a cheap router and a stronger drafter.
CLASSIFY_PROFILE = "aip-classify-haiku-sim"
DRAFT_PROFILE = "aip-draft-sonnet-sim"


@dataclass
class ModelResult:
    text: str
    structured: dict | None
    grounded: bool
    grounding_score: float
    relevance_score: float
    model_profile: str
    prompt_version: str
    tokens_in: int
    tokens_out: int
    flags: list = field(default_factory=list)


def _estimate_tokens(text: str) -> int:
    # Deterministic token estimate: ~1 token per 4 chars, min 1.
    return max(1, len(text) // 4)


def _content_words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}


def _grounding_score(answer: str, sources: list) -> float:
    """Fraction of answer content-words found in the provided sources.

    A stubbed contextual-grounding check: grounded only if the answer's claims
    appear in the sources. Returns a 0.0–0.99 score (Bedrock's range).
    """
    answer_words = _content_words(answer)
    if not answer_words:
        return 0.0
    source_words = set()
    for s in sources or []:
        source_words |= _content_words(s.get("text", "") if isinstance(s, dict) else str(s))
    if not source_words:
        return 0.0
    overlap = answer_words & source_words
    score = len(overlap) / len(answer_words)
    return min(round(score, 2), 0.99)


class ModelGateway:
    """Routes governed, deterministic model calls per agent."""

    def __init__(self):
        # agent_id -> {"profiles": set, "prompts": {version: hash}}
        self._allowlist: dict[str, dict] = {}

    def register_agent(
        self,
        agent_id: str,
        allowed_profiles=None,
        pinned_prompts=None,
    ) -> None:
        self._allowlist[agent_id] = {
            "profiles": set(
                allowed_profiles or [CLASSIFY_PROFILE, DRAFT_PROFILE]
            ),
            "prompts": dict(pinned_prompts or {}),
        }

    def _profile_for_task(self, task: str) -> str:
        # Task-based routing: classify -> cheap; draft -> stronger.
        return CLASSIFY_PROFILE if task == "classify" else DRAFT_PROFILE

    def invoke(
        self,
        agent_id: str,
        task: str,
        prompt: str,
        sources=None,
        prompt_version: str = "v1",
        prompt_hash: str | None = None,
        output_schema: dict | None = None,
        grounding_threshold: float = 0.85,
    ) -> ModelResult:
        if agent_id not in self._allowlist:
            raise ModelGatewayError(f"agent '{agent_id}' not registered with model gateway")

        cfg = self._allowlist[agent_id]
        profile = self._profile_for_task(task)

        # Approved-profile allowlist per agent.
        if profile not in cfg["profiles"]:
            raise ModelGatewayError(
                f"model profile '{profile}' not in allowlist for agent '{agent_id}'"
            )

        # Prompt-version pinning (hash-pinned, drift-failing).
        pins = cfg["prompts"]
        if pins:
            if prompt_version not in pins:
                raise ModelGatewayError(
                    f"prompt version '{prompt_version}' not pinned for '{agent_id}'"
                )
            if prompt_hash is not None and pins[prompt_version] != prompt_hash:
                raise ModelGatewayError(
                    f"prompt-pin drift: '{prompt_version}' hash mismatch "
                    f"(pinned {pins[prompt_version]}, got {prompt_hash})"
                )

        sources = sources or []
        flags: list[str] = []

        # ----- the deterministic "model" -------------------------------- #
        if task == "classify":
            text, structured = self._classify(prompt, sources)
        else:
            text, structured = self._draft(prompt, sources)

        # Contextual grounding score (hallucination filter).
        grounding_score = _grounding_score(text, sources)
        relevance_score = grounding_score  # single-signal stub
        grounded = grounding_score >= grounding_threshold
        if not grounded:
            flags.append(
                f"hallucination_flag: grounding {grounding_score} < "
                f"threshold {grounding_threshold}"
            )

        # JSON-schema validation of structured output.
        if output_schema is not None and structured is not None:
            schema_errs = _validate_against_schema(structured, output_schema)
            if schema_errs:
                raise ModelGatewayError(
                    "structured output failed schema validation: "
                    + "; ".join(schema_errs)
                )

        tokens_in = _estimate_tokens(prompt) + sum(
            _estimate_tokens(s.get("text", "") if isinstance(s, dict) else str(s))
            for s in sources
        )
        tokens_out = _estimate_tokens(text) + (
            _estimate_tokens(json.dumps(structured)) if structured else 0
        )

        return ModelResult(
            text=text,
            structured=structured,
            grounded=grounded,
            grounding_score=grounding_score,
            relevance_score=relevance_score,
            model_profile=profile,
            prompt_version=prompt_version,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            flags=flags,
        )

    # ----- deterministic task implementations --------------------------- #
    def _classify(self, prompt: str, sources: list):
        p = prompt.lower()
        if any(w in p for w in ("password", "login", "account locked", "reset")):
            category, priority = "access-management", "high"
        elif any(w in p for w in ("slow", "performance", "latency")):
            category, priority = "performance", "medium"
        elif any(w in p for w in ("trash", "pickup", "garbage", "missed")):
            category, priority = "sanitation-311", "medium"
        elif any(w in p for w in ("pothole", "street", "road")):
            category, priority = "streets-311", "medium"
        else:
            category, priority = "general", "low"
        structured = {"category": category, "priority": priority}
        # Echo source-grounded language so grounding scores reflect the sources.
        cited = " ".join(
            (s.get("text", "") if isinstance(s, dict) else str(s)) for s in sources
        )
        text = (
            f"Classified as {category} (priority {priority}). "
            f"{cited}"
        ).strip()
        return text, structured

    def _draft(self, prompt: str, sources: list):
        # Draft answer strictly from the sources (keeps it grounded).
        if sources:
            cited = " ".join(
                (s.get("text", "") if isinstance(s, dict) else str(s))
                for s in sources
            )
            # The draft is composed strictly from the retrieved source text so
            # the contextual-grounding score stays high (claims trace to source).
            text = cited.strip()
            source_ids = [
                s.get("id") for s in sources if isinstance(s, dict) and s.get("id")
            ]
            structured = {"draft": text, "source_ids": source_ids}
        else:
            # No sources -> ungrounded free-generation (will be flagged).
            text = "Unverified free-form answer with no supporting source."
            structured = {"draft": text, "source_ids": []}
        return text, structured


# --------------------------------------------------------------------------- #
# Minimal JSON-Schema validator (subset: type, required, properties, enum)
# --------------------------------------------------------------------------- #

def _validate_against_schema(obj, schema) -> list:
    errs: list[str] = []
    t = schema.get("type")
    if t == "object":
        if not isinstance(obj, dict):
            return [f"expected object, got {type(obj).__name__}"]
        for key in schema.get("required", []):
            if key not in obj:
                errs.append(f"missing required property '{key}'")
        props = schema.get("properties", {})
        for key, subschema in props.items():
            if key in obj:
                errs.extend(
                    _prefix(key, _validate_against_schema(obj[key], subschema))
                )
    elif t == "array":
        if not isinstance(obj, list):
            return [f"expected array, got {type(obj).__name__}"]
        items = schema.get("items")
        if items:
            for i, el in enumerate(obj):
                errs.extend(_prefix(f"[{i}]", _validate_against_schema(el, items)))
    elif t == "string":
        if not isinstance(obj, str):
            errs.append(f"expected string, got {type(obj).__name__}")
    elif t == "number":
        if not isinstance(obj, (int, float)) or isinstance(obj, bool):
            errs.append(f"expected number, got {type(obj).__name__}")
    elif t == "integer":
        if not isinstance(obj, int) or isinstance(obj, bool):
            errs.append(f"expected integer, got {type(obj).__name__}")
    if "enum" in schema and obj not in schema["enum"]:
        errs.append(f"value {obj!r} not in enum {schema['enum']}")
    return errs


def _prefix(p, errs):
    return [f"{p}.{e}" if not e.startswith("[") else f"{p}{e}" for e in errs]
