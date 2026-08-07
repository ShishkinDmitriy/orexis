"""Ed25519 signing for the settlement token — the actuate boundary, cryptographically.

Actuation is the one irreversible power we did NOT relax in trusted-agent mode, so the valve
command must carry a token signed by the **host** (match_sig) and **clearing** (val_sig); the
pump verifies both before opening. Crypto proportional to irreversibility. See
knowledge/domain/executor.md, knowledge/decisions/authn-authz-capabilities.md.

Keys live in a gitignored `world/<name>/secrets/` (run `agora-keygen <world>` once). v1 in-process simplification:
the settlement service holds both signing keys; a separately-hosted supplier signing its own
match is a v2 refinement.
"""

from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .config import REPO_ROOT

def KEYS_DIR() -> "object":
    """This world's secrets. A function, not a constant, because which world a process belongs
    to is discovered — and two worlds must not be able to sign for each other."""
    from .genesis import current_world, secrets_dir

    return secrets_dir(current_world())


def canonical(payload: dict) -> bytes:
    """Deterministic bytes for a payload (sig fields excluded by the caller)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def priv_path(name: str):
    return KEYS_DIR() / f"{name}.key"


def pub_path(name: str):
    return KEYS_DIR() / f"{name}.pub"


def load_private(name: str) -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(priv_path(name).read_bytes(), password=None)


def load_public(name: str) -> Ed25519PublicKey:
    return serialization.load_pem_public_key(pub_path(name).read_bytes())


def sign(key: Ed25519PrivateKey, data: bytes) -> str:
    return base64.b64encode(key.sign(data)).decode()


def verify(pub: Ed25519PublicKey, data: bytes, sig_b64: str) -> bool:
    try:
        pub.verify(base64.b64decode(sig_b64), data)
        return True
    except Exception:
        return False


def verify_command(payload: dict, host_pub, clearing_pub) -> bool:
    """Device-side check: open only for a token signed by BOTH host and clearing.

    This is the *edge's* half of actuation, which is why it lives in the kernel rather than in
    `capabilities/actuation/`: a device verifies without holding the capability, and a
    simulator or a firmware stub must be able to check a command without loading the module
    that issued it.
    """
    if host_pub is None or clearing_pub is None:
        return False
    match_sig, val_sig = payload.get("match_sig"), payload.get("val_sig")
    if not match_sig or not val_sig:
        return False
    cmd = {k: v for k, v in payload.items() if k not in ("match_sig", "val_sig")}
    data = canonical(cmd)
    return verify(host_pub, data, match_sig) and verify(clearing_pub, data, val_sig)

# Creating keys is NOT here: it is a once-per-world act by the sovereign, and an agent that
# could mint a society's signing keys could sign for it. An actuator LOADS the two it is given
# and can do nothing else. See onboarding/keygen.py.
