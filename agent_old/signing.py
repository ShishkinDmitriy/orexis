"""Ed25519 signing for the settlement token — the actuate boundary, cryptographically.

Actuation is the one irreversible power we did NOT relax in trusted-agent mode, so the valve
command must carry a token signed by the **host** (match_sig) and **clearing** (val_sig); the
pump verifies both before opening. Crypto proportional to irreversibility. See
knowledge/domain/executor.md, knowledge/decisions/authn-authz-capabilities.md.

Keys live in a gitignored `world/<name>/secrets/` (run `orexis-keygen <world>` once). v1 in-process simplification:
the settlement service holds both signing keys; a separately-hosted supplier signing its own
match is a v2 refinement.
"""

from __future__ import annotations

import base64
import json

import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

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


# --- identity keys: every agent, not only host and clearing (#144) --------------------------
#
# The same PEM contract as above, one pair per agent, minted by `orexis-keygen` beside the
# world's own. The PUBLIC halves are published in the world graph (base64 of the raw 32 bytes,
# `orexis:signingKey` / `orexis:sealingKey`), because a verifier cannot read another agent's secrets —
# that is the isolation — and the world is the one place every member already reads.


def raw_public_b64(pub) -> str:
    """A public key as the graph carries it: base64 of the raw 32 bytes, no PEM ceremony."""
    return base64.b64encode(pub.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


def signing_public_from_b64(raw_b64: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(base64.b64decode(raw_b64))


def sealing_public_from_b64(raw_b64: str) -> X25519PublicKey:
    return X25519PublicKey.from_public_bytes(base64.b64decode(raw_b64))


def sign_priv_path(name: str):
    """An AGENT identity's signing key — suffixed, unlike host/clearing's bare `.key`.

    Not tidiness: `onboarding/certs.py` issues `<agent_id>.crt`/`<agent_id>.key` for TLS, so
    the bare name IS the TLS namespace for agents, and the first keygen run that minted agent
    identities into it overwrote every agent's TLS private key with a signing key — the broker
    refused the lot at next connect. host and clearing keep `.key`: they predate this, hold no
    TLS certs to collide with, and their filenames are a compose-mount and firmware contract.
    """
    return KEYS_DIR() / f"{name}.sign.key"


def sign_pub_path(name: str):
    return KEYS_DIR() / f"{name}.sign.pub"


def load_signing_private(name: str) -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(sign_priv_path(name).read_bytes(), password=None)


def seal_priv_path(name: str):
    return KEYS_DIR() / f"{name}.seal.key"


def load_sealing_private(name: str) -> X25519PrivateKey:
    return serialization.load_pem_private_key(seal_priv_path(name).read_bytes(), password=None)


# --- sealing: confidentiality to one recipient over an untrusted bus (#145) -----------------
#
# An ephemeral-static X25519 exchange, HKDF, ChaCha20-Poly1305 — the sealed-box construction,
# spelled out with the library already in use rather than importing a second one. Ed25519 keys
# SIGN and do not encrypt, which is why sealing has its own pair: same curve family, different
# operation, and conflating them is the mistake this comment exists to head off.

_SEAL_INFO = b"orexis-seal-v1"


def seal(recipient: X25519PublicKey, plaintext: bytes) -> str:
    """Seal bytes to one recipient: base64(ephemeral_pub || nonce || ciphertext).

    A fresh ephemeral key per message, so two claims to one winner share nothing, and the
    sender needs no key of its own — sealing is addressed, not signed. Authenticity is the
    signature chain's business, deliberately apart.
    """
    ephemeral = X25519PrivateKey.generate()
    shared = ephemeral.exchange(recipient)
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_SEAL_INFO).derive(shared)
    nonce = os.urandom(12)
    ciphertext = ChaCha20Poly1305(key).encrypt(nonce, plaintext, None)
    eph_pub = ephemeral.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(eph_pub + nonce + ciphertext).decode()


def unseal(own: X25519PrivateKey, sealed_b64: str) -> bytes | None:
    """Open a sealed payload, or None — a payload that will not open is logged by the caller,
    never guessed at: wrong recipient and tampered ciphertext are indistinguishable here, and
    both mean the same thing operationally (this was not honestly addressed to me)."""
    try:
        blob = base64.b64decode(sealed_b64)
        eph_pub, nonce, ciphertext = blob[:32], blob[32:44], blob[44:]
        shared = own.exchange(X25519PublicKey.from_public_bytes(eph_pub))
        key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                   info=_SEAL_INFO).derive(shared)
        return ChaCha20Poly1305(key).decrypt(nonce, ciphertext, None)
    except Exception:
        return None
