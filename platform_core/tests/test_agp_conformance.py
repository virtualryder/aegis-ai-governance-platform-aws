"""AGP: Aegis platform_core is the canonical reference implementation of the pattern."""
import platform_core as m


def test_reference_declares_agp_version():
    assert m.AEGIS_GOVERNANCE_PATTERN_VERSION == "1.0"
    assert m.__version__.count(".") >= 2
