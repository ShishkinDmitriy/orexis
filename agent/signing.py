"""Signing a device command: the boundary no step crosses unsigned.

Actuation is the one irreversible power, so a device opens only for a command it can prove the
agent that holds it (`actuation:hasActuator`) sent. The runtime signs every command a step sends
with that agent's Ed25519 key before the transport carries it; the device holds the agent's public
key and nothing else. The market's two signatures — a host authorising a match, clearing
validating it — come back with the market; until then the holder is the one who may ask.

A SIGNED COMMAND IS THE PAYLOAD AND THREE FIELDS: `jti`, an id the device takes once, so a replay
opens nothing; `exp`, the instant after which it is refused, in the one timeline (`clock.now()`)
as epoch seconds; and `sig`, the signature over the canonical bytes of everything else — sorted
keys, no spaces, `sig` excluded — which a device recomputes exactly.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from agent import clock

#  HOW LONG A COMMAND IS GOOD FOR, in the timeline's seconds: long enough for a broker to carry it,
#  short enough that one held back is refused.
TTL_S = 60.0


def canonical(payload: dict) -> bytes:
    """The bytes a signature is over: the payload without `sig`, keys sorted, no spaces."""
    return json.dumps({k: v for k, v in payload.items() if k != "sig"}, sort_keys=True,
                      separators=(",", ":")).encode()


def load_key(path) -> Ed25519PrivateKey:
    """The agent's own key, as `orexis-keygen` wrote it into the world's secrets."""
    return serialization.load_pem_private_key(Path(path).read_bytes(), password=None)


def sign(payload: dict, key: Ed25519PrivateKey, *, ttl_s: float = TTL_S) -> dict:
    """`payload` with a fresh `jti`, an `exp` `ttl_s` into the timeline, and the `sig` over both."""
    signed = {**payload, "jti": uuid.uuid4().hex, "exp": round((clock.now() + timedelta(seconds=ttl_s)).timestamp(), 3)}
    signed["sig"] = base64.b64encode(key.sign(canonical(signed))).decode()
    return signed


def verify(payload: dict, public: Ed25519PublicKey, *, spent: set, now: float) -> bool:
    """Whether a device should open: signed by `public`, not yet expired at `now` (epoch seconds
    in the timeline), and an id it has not taken — which it then has. Any failure is a refusal.
    The stand-ins carry a copy of this, held to it by a test, since their image holds no agent."""
    sig, jti, exp = payload.get("sig"), payload.get("jti"), payload.get("exp")
    if not sig or not jti or exp is None or jti in spent or float(exp) < now:
        return False
    try:
        public.verify(base64.b64decode(sig), canonical(payload))
    except Exception:                                               # noqa: BLE001
        return False
    spent.add(jti)
    return True
