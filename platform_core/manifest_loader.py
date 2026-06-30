"""manifest_loader — stdlib-only loader for Aegis agent manifests.

The reference manifests are YAML, but the standard library ships no YAML parser.
Rather than take a dependency on PyYAML (the brief pins us to stdlib only), this
module implements a *small* YAML subset parser sufficient for Aegis manifests:
mappings, lists, scalars, block scalars (>- / |), inline flow lists ([a, b]),
inline flow maps ({k: v}), comments, and underscore-grouped integers
(50_000_000). If a `.json` sibling exists it is preferred (json is in stdlib).

It also performs a pragmatic validation pass against
governance/onboarding/agent-manifest.schema.json — again with no third-party
validator. We check the clauses the gateway actually depends on: required keys,
const fields, enums, patterns, and numeric bounds. This is intentionally a
"good enough to enforce the contract" validator, not a full JSON-Schema engine.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any


# --------------------------------------------------------------------------- #
# Minimal YAML subset parser (stdlib only)
# --------------------------------------------------------------------------- #

def _strip_comment(line: str) -> str:
    """Remove an unquoted trailing '# comment'."""
    out = []
    in_s = in_d = False
    i = 0
    while i < len(line):
        c = line[i]
        if c == "'" and not in_d:
            in_s = not in_s
        elif c == '"' and not in_s:
            in_d = not in_d
        elif c == "#" and not in_s and not in_d:
            # only a comment if preceded by start-of-line or whitespace
            if i == 0 or line[i - 1] in " \t":
                break
        out.append(c)
        i += 1
    return "".join(out).rstrip()


def _coerce_scalar(tok: str) -> Any:
    tok = tok.strip()
    if tok == "" or tok == "~" or tok.lower() == "null":
        return None
    if tok.lower() == "true":
        return True
    if tok.lower() == "false":
        return False
    if (tok.startswith('"') and tok.endswith('"')) or (
        tok.startswith("'") and tok.endswith("'")
    ):
        return tok[1:-1]
    # underscore-grouped integers: 50_000_000
    cleaned = tok.replace("_", "")
    if re.fullmatch(r"[+-]?\d+", cleaned):
        return int(cleaned)
    if re.fullmatch(r"[+-]?\d*\.\d+", cleaned):
        return float(cleaned)
    return tok


def _parse_flow(tok: str) -> Any:
    """Parse an inline flow collection: [a, b] or {k: v, k2: v2}."""
    tok = tok.strip()
    if tok.startswith("[") and tok.endswith("]"):
        inner = tok[1:-1].strip()
        if not inner:
            return []
        return [_coerce_scalar(p) for p in _split_top(inner)]
    if tok.startswith("{") and tok.endswith("}"):
        inner = tok[1:-1].strip()
        out: dict[str, Any] = {}
        if not inner:
            return out
        for part in _split_top(inner):
            k, _, v = part.partition(":")
            out[k.strip()] = _coerce_scalar(v)
        return out
    return _coerce_scalar(tok)


def _split_top(s: str) -> list[str]:
    """Split on commas that are not inside nested brackets/quotes."""
    parts, depth, buf = [], 0, []
    in_s = in_d = False
    for c in s:
        if c == "'" and not in_d:
            in_s = not in_s
        elif c == '"' and not in_s:
            in_d = not in_d
        if not in_s and not in_d:
            if c in "[{":
                depth += 1
            elif c in "]}":
                depth -= 1
            elif c == "," and depth == 0:
                parts.append("".join(buf).strip())
                buf = []
                continue
        buf.append(c)
    if "".join(buf).strip():
        parts.append("".join(buf).strip())
    return parts


def _value_or_flow(tok: str) -> Any:
    tok = tok.strip()
    if tok.startswith("[") or tok.startswith("{"):
        return _parse_flow(tok)
    return _coerce_scalar(tok)


class _Line:
    __slots__ = ("indent", "text")

    def __init__(self, indent: int, text: str):
        self.indent = indent
        self.text = text


def _tokenize(raw: str) -> list[_Line]:
    lines: list[_Line] = []
    for raw_line in raw.splitlines():
        stripped = _strip_comment(raw_line)
        if stripped.strip() == "":
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append(_Line(indent, stripped.strip()))
    return lines


def _parse_block(lines: list[_Line], idx: int, indent: int) -> tuple[Any, int]:
    # Determine whether this block is a list or a mapping.
    if idx >= len(lines):
        return None, idx
    first = lines[idx]
    if first.text.startswith("- "):
        return _parse_list(lines, idx, indent)
    return _parse_map(lines, idx, indent)


def _parse_block_scalar(lines: list[_Line], idx: int, parent_indent: int) -> tuple[str, int]:
    chunks = []
    while idx < len(lines) and lines[idx].indent > parent_indent:
        chunks.append(lines[idx].text)
        idx += 1
    return " ".join(chunks), idx


def _parse_map(lines: list[_Line], idx: int, indent: int) -> tuple[dict, int]:
    out: dict[str, Any] = {}
    while idx < len(lines):
        line = lines[idx]
        if line.indent < indent:
            break
        if line.indent > indent:
            # Shouldn't happen at this level; treat defensively.
            break
        text = line.text
        key, sep, rest = text.partition(":")
        if not sep:
            break
        key = key.strip()
        rest = rest.strip()
        idx += 1
        if rest in (">-", ">", "|", "|-", ">+", "|+"):
            value, idx = _parse_block_scalar(lines, idx, line.indent)
            out[key] = value
        elif rest == "":
            # nested block (map or list) — or empty
            if idx < len(lines) and lines[idx].indent > line.indent:
                value, idx = _parse_block(lines, idx, lines[idx].indent)
                out[key] = value
            else:
                out[key] = None
        else:
            out[key] = _value_or_flow(rest)
    return out, idx


def _parse_list(lines: list[_Line], idx: int, indent: int) -> tuple[list, int]:
    out: list[Any] = []
    while idx < len(lines):
        line = lines[idx]
        if line.indent != indent or not line.text.startswith("- "):
            if line.indent < indent:
                break
            if not line.text.startswith("-"):
                break
        item_text = line.text[2:].strip()
        if ":" in item_text and not (
            item_text.startswith("[") or item_text.startswith("{")
        ):
            # list item is itself a mapping; synthesize a sub-block.
            sub_indent = line.indent + 2
            synthetic = [_Line(sub_indent, item_text)]
            j = idx + 1
            while j < len(lines) and lines[j].indent > line.indent:
                synthetic.append(lines[j])
                j += 1
            value, _ = _parse_map(synthetic, 0, sub_indent)
            out.append(value)
            idx = j
        else:
            out.append(_value_or_flow(item_text))
            idx += 1
    return out, idx


def parse_yaml(text: str) -> Any:
    """Parse the Aegis-manifest subset of YAML into Python objects."""
    lines = _tokenize(text)
    if not lines:
        return {}
    value, _ = _parse_block(lines, 0, lines[0].indent)
    return value


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def load_manifest(path: str) -> dict:
    """Load a manifest from a .yaml/.yml or .json file.

    If a sibling .json exists for a .yaml path it is preferred (json is in the
    stdlib and is unambiguous). This honors the brief's "load a .json copy if
    yaml stdlib is unavailable" escape hatch while still parsing YAML natively.
    """
    base, ext = os.path.splitext(path)
    if ext in (".yaml", ".yml"):
        json_sibling = base + ".json"
        if os.path.exists(json_sibling):
            with open(json_sibling, "r", encoding="utf-8") as fh:
                return json.load(fh)
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    if ext == ".json":
        return json.loads(raw)
    return parse_yaml(raw)


# --------------------------------------------------------------------------- #
# Pragmatic schema validation (no third-party validator)
# --------------------------------------------------------------------------- #

class ManifestValidationError(Exception):
    """Raised when a manifest fails the minimum-bar schema checks."""


_DATA_CLASSES = {"public", "pii", "phi", "fti", "cji", "edu", "sud", "card", "npi"}
_PACKS = {"slg", "education", "healthcare-lifesciences", "enterprise"}
_SCOPES = {"read", "write", "execute", "admin"}
_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,62}[a-z0-9]$")
_OWNER_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")
_TOOL_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,126}[a-z0-9]$")
_PROFILE_RE = re.compile(r"^[a-z][a-z0-9-]{1,126}[a-z0-9]$")


def validate_manifest(m: dict) -> list[str]:
    """Validate a manifest against the schema clauses the gateway depends on.

    Returns a list of human-readable error strings (empty == valid). This is a
    pragmatic check of required keys, const fields, enums, patterns, and bounds
    — the same gates docs/04 §2 (the minimum bar) describes — not a complete
    JSON-Schema engine.
    """
    errs: list[str] = []

    def req(d: dict, key: str, where: str) -> bool:
        if not isinstance(d, dict) or key not in d or d[key] in (None, "", [], {}):
            errs.append(f"{where}: missing required key '{key}'")
            return False
        return True

    if m.get("apiVersion") != "aegis/v1":
        errs.append("apiVersion must be 'aegis/v1'")
    if m.get("kind") != "Agent":
        errs.append("kind must be 'Agent'")

    md = m.get("metadata", {})
    if req(m, "metadata", "root") and isinstance(md, dict):
        for k in ("id", "owner", "packs", "classification"):
            req(md, k, "metadata")
        if isinstance(md.get("id"), str) and not _ID_RE.match(md["id"]):
            errs.append(f"metadata.id '{md['id']}' violates id pattern")
        if isinstance(md.get("owner"), str) and not _OWNER_RE.match(md["owner"]):
            errs.append(f"metadata.owner '{md['owner']}' violates owner pattern")
        for p in md.get("packs", []) or []:
            if p not in _PACKS:
                errs.append(f"metadata.packs: '{p}' not a known pack")
        for c in md.get("classification", []) or []:
            if c not in _DATA_CLASSES:
                errs.append(f"metadata.classification: '{c}' not a known data class")
        br = md.get("blast_radius", "low")
        if br not in ("low", "medium", "high"):
            errs.append(f"metadata.blast_radius '{br}' invalid")

    gr = m.get("grants", {})
    if req(m, "grants", "root") and isinstance(gr, dict):
        tools = gr.get("tools")
        if not tools or not isinstance(tools, list):
            errs.append("grants.tools must be a non-empty list")
        else:
            classification = set(md.get("classification", []) or [])
            for t in tools:
                if not isinstance(t, dict):
                    errs.append("grants.tools[] entries must be mappings")
                    continue
                if not _TOOL_RE.match(str(t.get("id", ""))):
                    errs.append(f"grants.tools.id '{t.get('id')}' violates pattern")
                if t.get("scope") not in _SCOPES:
                    errs.append(f"grants.tools.scope '{t.get('scope')}' invalid")
                for dc in t.get("data_classes", []) or []:
                    if dc not in classification:
                        errs.append(
                            f"grants.tools[{t.get('id')}].data_classes '{dc}' "
                            f"not a subset of metadata.classification"
                        )
        for cid in gr.get("consequential", []) or []:
            if not _TOOL_RE.match(str(cid)):
                errs.append(f"grants.consequential '{cid}' violates pattern")
            # Minimum-bar point 2: consequential id must NOT be an executable grant.
            grant_ids = {t.get("id") for t in (tools or []) if isinstance(t, dict)}
            if cid in grant_ids:
                errs.append(
                    f"grants.consequential '{cid}' is also an executable grant "
                    f"(minimum-bar point 2 violation)"
                )

    gd = m.get("grounding", {})
    if req(m, "grounding", "root") and isinstance(gd, dict):
        req(gd, "knowledge_base", "grounding")
        gt = gd.get("grounding_threshold")
        if not isinstance(gt, (int, float)) or not (0 <= gt <= 0.99):
            errs.append("grounding.grounding_threshold must be a number in [0, 0.99]")

    bd = m.get("budget", {})
    if req(m, "budget", "root") and isinstance(bd, dict):
        cap = bd.get("monthly_token_cap")
        if not isinstance(cap, int) or cap < 1:
            errs.append("budget.monthly_token_cap must be a positive integer")
        prof = bd.get("inference_profile")
        if not isinstance(prof, str) or not _PROFILE_RE.match(prof):
            errs.append(f"budget.inference_profile '{prof}' violates pattern")
        cb = bd.get("cap_behavior", "hard")
        if cb not in ("hard", "soft"):
            errs.append(f"budget.cap_behavior '{cb}' invalid")
        ths = bd.get("alert_thresholds")
        if not ths or not isinstance(ths, list):
            errs.append("budget.alert_thresholds must be a non-empty list")
        else:
            for th in ths:
                if not isinstance(th, (int, float)) or not (0 < th <= 1.0):
                    errs.append(f"budget.alert_thresholds value {th} out of (0, 1]")

    ev = m.get("evals", {})
    if req(m, "evals", "root") and isinstance(ev, dict):
        req(ev, "suite", "evals")
        mpr = ev.get("min_pass_rate")
        if not isinstance(mpr, (int, float)) or not (0 <= mpr <= 1.0):
            errs.append("evals.min_pass_rate must be a number in [0, 1]")

    hg = m.get("human_gate", {})
    if req(m, "human_gate", "root") and isinstance(hg, dict):
        if hg.get("mode") not in (
            "step_functions_wait_for_task_token",
            "interrupt_before",
            "none",
        ):
            errs.append(f"human_gate.mode '{hg.get('mode')}' invalid")
        if not isinstance(hg.get("separation_of_duties"), bool):
            errs.append("human_gate.separation_of_duties must be a boolean")

    sg = m.get("signing", {})
    if req(m, "signing", "root") and isinstance(sg, dict):
        req(sg, "publisher", "signing")
        req(sg, "signature", "signing")

    return errs


def validate_or_raise(m: dict) -> None:
    errs = validate_manifest(m)
    if errs:
        raise ManifestValidationError(
            "Manifest failed schema validation:\n  - " + "\n  - ".join(errs)
        )
