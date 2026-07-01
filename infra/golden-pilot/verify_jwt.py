#!/usr/bin/env python3
"""Cryptographically verify a Cognito ID token the way the Aegis gateway must:
RS256 signature against the pool JWKS, plus iss/aud/exp/token_use, then return the
verified cognito:groups claim. No trust in client-supplied roles. Requires `cryptography`.
Usage: verify_jwt.py <token_file> <jwks_file> <issuer> <audience>"""
import sys, json, base64, time
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

def b64url(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def verify(token, jwks, issuer, audience, now=None):
    now = now or int(time.time())
    h, p, sig = token.split(".")
    header = json.loads(b64url(h)); payload = json.loads(b64url(p))
    if header.get("alg") != "RS256":
        raise ValueError(f"alg {header.get('alg')} != RS256 (alg-confusion guard)")
    try:
        jwk = next(k for k in jwks["keys"] if k["kid"] == header["kid"])
    except StopIteration:
        raise ValueError("no JWKS key matches token kid")
    n = int.from_bytes(b64url(jwk["n"]), "big"); e = int.from_bytes(b64url(jwk["e"]), "big")
    pub = rsa.RSAPublicNumbers(e, n).public_key()
    try:
        pub.verify(b64url(sig), f"{h}.{p}".encode(), padding.PKCS1v15(), hashes.SHA256())
    except InvalidSignature:
        raise ValueError("signature verification FAILED")
    if payload.get("iss") != issuer: raise ValueError("iss mismatch")
    if payload.get("aud") != audience: raise ValueError("aud mismatch")
    if payload.get("token_use") != "id": raise ValueError("token_use != id")
    if int(payload.get("exp", 0)) <= now: raise ValueError("token expired")
    return payload

if __name__ == "__main__":
    tok = open(sys.argv[1]).read().strip(); jwks = json.load(open(sys.argv[2]))
    payload = verify(tok, jwks, sys.argv[3], sys.argv[4])
    print("VERIFY OK  user=%s  groups=%s" % (payload.get("cognito:username"), payload.get("cognito:groups")))
