#!/usr/bin/env python3
"""test_prod_components — tests for platform_core.prod production components.

Covers the four production-grade replacements (Task 24):

  (i)   manifest_validator: a valid manifest passes; a malformed one fails.
  (ii)  cedar_compiler: the permit contains all four `when` clauses and the
        schema declares Agent / Tool / InvokeTool.
  (iii) manifest_signing: local RSA sign->verify OK; a tampered manifest fails.
  (iv)  budget_manager_ddb.InMemoryBudget: allows within cap, rejects a single
        over-cap reservation, and rejects the second of two sequential
        reservations that together exceed the cap.

Stdlib unittest (no pytest); imports jsonschema/cryptography.

    python3 demo/test_prod_components.py
"""

from __future__ import annotations

import copy
import json
import os
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import yaml  # noqa: E402

from platform_core.prod import budget_manager_ddb as bm  # noqa: E402
from platform_core.prod import cedar_compiler as cc  # noqa: E402
from platform_core.prod import manifest_signing as ms  # noqa: E402
from platform_core.prod import manifest_validator as mv  # noqa: E402

_EXAMPLE = os.path.join(
    _REPO_ROOT, "governance", "onboarding", "example-agent.manifest.yaml"
)


def _valid_manifest() -> dict:
    with open(_EXAMPLE, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class ManifestValidatorTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        ok, errors = mv.validate_manifest(_EXAMPLE)
        self.assertTrue(ok, f"expected valid manifest to pass, got {errors}")
        self.assertEqual(errors, [])

    def test_valid_dict_passes(self):
        ok, errors = mv.validate_manifest(_valid_manifest())
        self.assertTrue(ok, errors)

    def test_malformed_manifest_fails(self):
        bad = _valid_manifest()
        # Break a required const + drop a required section -> must fail closed.
        bad["apiVersion"] = "not-aegis/v1"
        del bad["budget"]
        ok, errors = mv.validate_manifest(bad)
        self.assertFalse(ok)
        self.assertTrue(errors)

    def test_empty_manifest_fails(self):
        ok, errors = mv.validate_manifest({})
        self.assertFalse(ok)
        self.assertTrue(errors)


class CedarCompilerTests(unittest.TestCase):
    def test_permit_has_all_four_when_clauses(self):
        out = cc.compile_manifest_to_cedar(_valid_manifest())
        self.assertEqual(len(out["policies"]), 1)
        permit = out["policies"][0]
        for clause in (
            "principal.grants.contains(resource.id)",
            "context.userEntitlements.contains(resource.id)",
            "resource.allowedPurposes.contains(context.purpose)",
            "context.userDataClasses.contains(resource.dataClass)",
        ):
            self.assertIn(clause, permit, f"missing when clause: {clause}")
        self.assertIn("permit (", permit)
        self.assertIn('action == Aegis::Action::"InvokeTool"', permit)

    def test_schema_declares_agent_tool_invoketool(self):
        out = cc.compile_manifest_to_cedar(_valid_manifest())
        schema = json.loads(out["schema"])
        ns = schema["Aegis"]
        self.assertIn("Agent", ns["entityTypes"])
        self.assertIn("Tool", ns["entityTypes"])
        self.assertIn("InvokeTool", ns["actions"])
        # Action wiring: Agent principal + Tool resource.
        applies = ns["actions"]["InvokeTool"]["appliesTo"]
        self.assertIn("Agent", applies["principalTypes"])
        self.assertIn("Tool", applies["resourceTypes"])

    def test_tool_ids_surface_from_manifest(self):
        out = cc.compile_manifest_to_cedar(_valid_manifest())
        self.assertIn("servicenow.read_ticket", out["tool_ids"])


class ManifestSigningTests(unittest.TestCase):
    def test_local_rsa_sign_verify_roundtrip(self):
        priv, pub = ms.generate_keypair()
        m = _valid_manifest()
        sig = ms.sign_manifest(priv, m)
        self.assertTrue(ms.verify_manifest(pub, m, sig))

    def test_tampered_manifest_fails_verify(self):
        priv, pub = ms.generate_keypair()
        m = _valid_manifest()
        sig = ms.sign_manifest(priv, m)
        tampered = copy.deepcopy(m)
        tampered["metadata"]["id"] = "exfiltrator-agent"
        self.assertFalse(ms.verify_manifest(pub, tampered, sig))

    def test_bad_signature_fails_closed(self):
        _, pub = ms.generate_keypair()
        self.assertFalse(ms.verify_manifest(pub, _valid_manifest(), b"nope"))

    def test_wrong_key_fails_verify(self):
        priv, _ = ms.generate_keypair()
        _, other_pub = ms.generate_keypair()
        m = _valid_manifest()
        sig = ms.sign_manifest(priv, m)
        self.assertFalse(ms.verify_manifest(other_pub, m, sig))


class InMemoryBudgetTests(unittest.TestCase):
    def test_allows_within_cap(self):
        b = bm.InMemoryBudget()
        r = b.reserve("agent-x", tokens=100, cap=1000)
        self.assertTrue(r.allowed)
        self.assertEqual(r.used_after, 100)

    def test_rejects_single_over_cap_reservation(self):
        b = bm.InMemoryBudget()
        r = b.reserve("agent-x", tokens=1500, cap=1000)
        self.assertFalse(r.allowed)
        self.assertIn("budget_exceeded", r.reason)
        # State unchanged on refusal.
        self.assertEqual(b.used("agent-x"), 0)

    def test_two_sequential_reservations_exceeding_cap_reject_second(self):
        b = bm.InMemoryBudget()
        r1 = b.reserve("agent-x", tokens=700, cap=1000)
        self.assertTrue(r1.allowed)
        r2 = b.reserve("agent-x", tokens=400, cap=1000)  # 700+400 > 1000
        self.assertFalse(r2.allowed)
        # The first reservation stands; the second did not oversell.
        self.assertEqual(b.used("agent-x"), 700)

    def test_exact_cap_boundary_allowed(self):
        b = bm.InMemoryBudget()
        self.assertTrue(b.reserve("k", tokens=1000, cap=1000).allowed)
        # One more token now exceeds.
        self.assertFalse(b.reserve("k", tokens=1, cap=1000).allowed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
