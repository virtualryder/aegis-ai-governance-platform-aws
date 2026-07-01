"""manifest_signing — cryptographic signed-manifest verification.

Replaces the offline "signature-present" check (manifest_loader only asserts
signing.publisher + signing.signature exist) with REAL cryptographic
verification. Two backends:

  (a) LOCAL RSA (via `cryptography`): RSASSA-PSS + SHA-256 over the manifest's
      canonical bytes. generate_keypair(), sign_manifest(), verify_manifest().

  (b) AWS KMS asymmetric interface (via boto3): kms_sign() / kms_verify() using
      SigningAlgorithm RSASSA_PSS_SHA_256 and MessageType=RAW. These call AWS
      and are NOT exercised in tests — they document the production path.

Fail-closed contract: verify_* return False on ANY error (bad signature,
tampered manifest, malformed key, missing signature) — never raise-through to a
caller who might treat an exception as "unknown / allow".
"""

from __future__ import annotations

import json
from typing import Union

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


# --------------------------------------------------------------------------- #
# Canonicalization — the exact bytes that get signed/verified.
# --------------------------------------------------------------------------- #
def canonical_bytes(manifest: dict) -> bytes:
    """Deterministic canonical serialization of a manifest for signing.

    The `signing.signature` field is excluded (a signature cannot cover itself).
    Keys are sorted and separators are tight so the same manifest always yields
    the same bytes on any platform.
    """
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a dict")
    payload = {k: v for k, v in manifest.items() if k != "signing"}
    signing = manifest.get("signing")
    if isinstance(signing, dict):
        # Keep publisher/algorithm (they are part of the signed claim) but drop
        # the signature value itself.
        payload["signing"] = {
            k: v for k, v in signing.items() if k != "signature"
        }
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


# --------------------------------------------------------------------------- #
# (a) LOCAL RSA backend — RSASSA-PSS + SHA-256
# --------------------------------------------------------------------------- #
def generate_keypair(key_size: int = 2048):
    """Generate an RSA keypair. Returns (private_key, public_key)."""
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=key_size
    )
    return private_key, private_key.public_key()


def _pss():
    return padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH,
    )


def sign_bytes(private_key, message: bytes) -> bytes:
    """Sign raw bytes with RSASSA-PSS + SHA-256."""
    return private_key.sign(message, _pss(), hashes.SHA256())


def sign_manifest(private_key, manifest: dict) -> bytes:
    """Sign a manifest's canonical bytes; returns the raw signature bytes."""
    return sign_bytes(private_key, canonical_bytes(manifest))


def verify_bytes(public_key, message: bytes, signature: bytes) -> bool:
    """Verify a signature over raw bytes. Fail closed on any error."""
    try:
        public_key.verify(signature, message, _pss(), hashes.SHA256())
        return True
    except InvalidSignature:
        return False
    except Exception:  # noqa: BLE001 - malformed key/sig => reject
        return False


def verify_manifest(public_key, manifest: dict, signature: bytes) -> bool:
    """Verify a manifest against a detached signature. Fail closed.

    Any tampering with the manifest changes its canonical bytes and the
    verification fails.
    """
    try:
        message = canonical_bytes(manifest)
    except Exception:  # noqa: BLE001 - unserializable => reject
        return False
    return verify_bytes(public_key, message, signature)


# --------------------------------------------------------------------------- #
# Key (de)serialization helpers — used to persist the trusted publisher key.
# --------------------------------------------------------------------------- #
def public_key_pem(public_key) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def load_public_key_pem(pem: Union[bytes, str]):
    if isinstance(pem, str):
        pem = pem.encode("utf-8")
    return serialization.load_pem_public_key(pem)


# --------------------------------------------------------------------------- #
# (b) AWS KMS asymmetric backend — production path (boto3). Not called in tests.
# --------------------------------------------------------------------------- #
KMS_SIGNING_ALGORITHM = "RSASSA_PSS_SHA_256"


def kms_sign(key_id: str, message: bytes, kms_client=None) -> bytes:
    """Sign `message` with an asymmetric KMS key (RSASSA_PSS_SHA_256, RAW).

    Production path; requires AWS credentials + an asymmetric KMS key. Returns
    the raw signature bytes. Not exercised in offline tests.
    """
    if kms_client is None:  # pragma: no cover - real AWS call
        import boto3

        kms_client = boto3.client("kms")
    resp = kms_client.sign(
        KeyId=key_id,
        Message=message,
        MessageType="RAW",
        SigningAlgorithm=KMS_SIGNING_ALGORITHM,
    )
    return resp["Signature"]


def kms_verify(
    key_id: str, message: bytes, signature: bytes, kms_client=None
) -> bool:
    """Verify a signature via KMS. Fail closed on any error.

    Production path; not exercised in offline tests.
    """
    try:
        if kms_client is None:  # pragma: no cover - real AWS call
            import boto3

            kms_client = boto3.client("kms")
        resp = kms_client.verify(
            KeyId=key_id,
            Message=message,
            MessageType="RAW",
            Signature=signature,
            SigningAlgorithm=KMS_SIGNING_ALGORITHM,
        )
        return bool(resp.get("SignatureValid", False))
    except Exception:  # noqa: BLE001 - fail closed
        return False
