"""agora-keygen — create one world's signing keys, once, before it is onboarded.

  agora-keygen society

**Two worlds are two societies and must not be able to sign for each other**, so the pair belongs
to a world rather than to the installation: `world/<name>/secrets/`, never committed.

This is here and not in the runtime for the same reason `agora-influx` is. An agent that could
*mint* a society's keys could sign for that society — it could authorise a match it never won and
validate its own voucher. An actuator holds the two keys it is given, mounted into its container
alone, and can do nothing else with them; `agent.signing` therefore keeps `load_private`, `sign`
and `verify`, and creating a keypair happens here.

The keys sign an actuation command jointly: the host authorises the match and clearing validates
it, and the firmware refuses a command missing either. See knowledge/domain/clearing.md.

See knowledge/domain/onboarding.md.
"""

from __future__ import annotations

import argparse
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agent import genesis, signing


def create_keypair(name: str) -> None:
    """Write `<name>.key` and `<name>.pub` into the current world's secrets directory.

    PEM/PKCS8, because `agent.signing.load_private` reads it back that way — the format is a
    contract between the two halves and is not this tool's to choose alone.

    Note it OVERWRITES. Regenerating a world's keys invalidates every signature made with the old
    pair, including any voucher a device still holds. That is a seam, not a feature.
    """
    signing.KEYS_DIR().mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    signing.priv_path(name).write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    signing.pub_path(name).write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )


def main() -> None:
    p = argparse.ArgumentParser(
        prog="agora-keygen",
        description="Create one world's signing keys. Two worlds are two societies and must "
                    "not be able to sign for each other.",
    )
    p.add_argument("world",
                   help="which world. Available: " + ", ".join(genesis.worlds()))
    os.environ["AGORA_WORLD"] = p.parse_args().world
    for name in ("host", "clearing"):
        create_keypair(name)
    print(f"created {signing.KEYS_DIR()}/[host|clearing].[key|pub]")


if __name__ == "__main__":
    main()
