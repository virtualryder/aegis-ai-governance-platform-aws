"""cedar_compiler — compile an agent manifest into Cedar policy + AVP schema.

This is the real "agent.yaml -> Cedar" compiler. Given an Aegis agent manifest
(and, implicitly, its declared tool list), it emits:

    (a) a Cedar POLICY string implementing least-privilege as an INTERSECTION
        (agent grant AND user entitlement) plus purpose limitation and a
        data-class boundary, and
    (b) the AVP Cedar-JSON SCHEMA (Agent principal, Tool resource, InvokeTool
        action with the userEntitlements / userDataClasses / purpose context).

Both match the pattern proven live in infra/golden-pilot/avp-cedar.yaml and
deployed to Amazon Verified Permissions (DEPLOYED-AND-VALIDATED.md Run 3).

    compile_manifest_to_cedar(manifest) -> {"schema": <json str>,
                                            "policies": [<cedar str>, ...]}

The emitted policy is the default-deny permit the platform relies on: a call is
permitted only when the agent's grants contain the tool, the acting human is
entitled to the tool, the declared purpose is allowed for the tool, and the
call's data class is within the tool's boundary. Everything else is denied.
"""

from __future__ import annotations

import json

# Cedar namespace used across Aegis (matches avp-cedar.yaml).
NAMESPACE = "Aegis"

# The AVP Cedar-JSON schema, structurally identical to the deployed golden pilot.
_CEDAR_SCHEMA = {
    NAMESPACE: {
        "entityTypes": {
            "Agent": {
                "shape": {
                    "type": "Record",
                    "attributes": {
                        "grants": {
                            "type": "Set",
                            "element": {"type": "String"},
                        }
                    },
                }
            },
            "Tool": {
                "shape": {
                    "type": "Record",
                    "attributes": {
                        "id": {"type": "String"},
                        "dataClass": {"type": "String"},
                        "allowedPurposes": {
                            "type": "Set",
                            "element": {"type": "String"},
                        },
                    },
                }
            },
        },
        "actions": {
            "InvokeTool": {
                "appliesTo": {
                    "principalTypes": ["Agent"],
                    "resourceTypes": ["Tool"],
                    "context": {
                        "type": "Record",
                        "attributes": {
                            "userEntitlements": {
                                "type": "Set",
                                "element": {"type": "String"},
                            },
                            "userDataClasses": {
                                "type": "Set",
                                "element": {"type": "String"},
                            },
                            "purpose": {"type": "String"},
                        },
                    },
                }
            }
        },
    }
}


def build_cedar_schema() -> dict:
    """Return the AVP Cedar-JSON schema as a Python dict."""
    return json.loads(json.dumps(_CEDAR_SCHEMA))  # deep copy


# The four-clause default-deny permit (intersection + purpose + data class).
_PERMIT_TEMPLATE = """\
permit (
  principal is {ns}::Agent,
  action == {ns}::Action::"InvokeTool",
  resource is {ns}::Tool
)
when {{
  principal.grants.contains(resource.id) &&
  context.userEntitlements.contains(resource.id) &&
  resource.allowedPurposes.contains(context.purpose) &&
  context.userDataClasses.contains(resource.dataClass)
}};"""


def build_permit_policy() -> str:
    """Return the least-privilege intersection permit policy (Cedar text)."""
    return _PERMIT_TEMPLATE.format(ns=NAMESPACE)


def _tool_ids(manifest: dict) -> list:
    grants = manifest.get("grants", {}) or {}
    tools = grants.get("tools", []) or []
    return [t.get("id") for t in tools if isinstance(t, dict) and t.get("id")]


def compile_manifest_to_cedar(manifest: dict) -> dict:
    """Compile an agent manifest into a Cedar schema + policy set.

    Returns {"schema": <json string>, "policies": [<cedar policy string>], ...}.
    The permit is agent-agnostic by design (entities carry the agent grants /
    tool attributes at is-authorized time), exactly as deployed on AVP; the
    manifest's tool list is surfaced as metadata for registration/tests.
    """
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a dict")

    agent_id = (manifest.get("metadata", {}) or {}).get("id", "unknown")
    tools = _tool_ids(manifest)

    schema_str = json.dumps(build_cedar_schema(), separators=(",", ":"))
    permit = build_permit_policy()

    return {
        "agent_id": agent_id,
        "tool_ids": tools,
        "schema": schema_str,
        "policies": [permit],
    }
