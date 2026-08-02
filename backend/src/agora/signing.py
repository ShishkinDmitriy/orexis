"""Ed25519 signing for the settlement token — the actuate boundary, cryptographically.

Actuation is the one irreversible power we did NOT relax in trusted-agent mode, so the valve
command must carry a token signed by the **host** (match_sig) and **clearing** (val_sig); the
pump verifies both before opening. Crypto proportional to irreversibility. See
knowledge/domain/executor.md, knowledge/decisions/authn-authz-capabilities.md.

Keys live in a gitignored keys/ dir (run `agora-keygen` once). v1 in-process simplification:
the settlement service holds both signing keys; a separately-hosted supplier signing its own
match is a v2 refinement.
"""

from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .config import PROJECT_ROOT

KEYS_DIR = PROJECT_ROOT.parent / "keys"


def canonical(payload: dict) -> bytes:
    """Deterministic bytes for a payload (sig fields excluded by the caller)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _priv_path(name: str):
    return KEYS_DIR / f"{name}.key"


def _pub_path(name: str):
    return KEYS_DIR / f"{name}.pub"


def create_keypair(name: str) -> None:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    _priv_path(name).write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    _pub_path(name).write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )


def load_private(name: str) -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(_priv_path(name).read_bytes(), password=None)


def load_public(name: str) -> Ed25519PublicKey:
    return serialization.load_pem_public_key(_pub_path(name).read_bytes())


def sign(key: Ed25519PrivateKey, data: bytes) -> str:
    return base64.b64encode(key.sign(data)).decode()


def verify(pub: Ed25519PublicKey, data: bytes, sig_b64: str) -> bool:
    try:
        pub.verify(base64.b64decode(sig_b64), data)
        return True
    except Exception:
        return False


def main() -> None:
    """agora-keygen — create the host + clearing signing keys (run once)."""
    for name in ("host", "clearing"):
        create_keypair(name)
        print(f"created keys/{name}.key + keys/{name}.pub")
