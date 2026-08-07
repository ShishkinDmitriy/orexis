"""agora-infra-certs — identities for the services, and whom the broker trusts. An INFRA step.

  agora-infra-certs                    # certificates for the shared services
  agora-infra-certs --host pi.local    # the name clients will actually verify

**Separate from onboarding on purpose.** Onboarding grants a *world's* agents the means to act;
this grants the *installation's* broker an identity. They are different lifecycles: infra may be
deployed at a different time, on a different host, by someone holding none of these worlds — and
a world may be onboarded a dozen times without the broker's certificate changing once. Mixing
them would mean onboarding a world required write access to wherever the broker runs, which is
false as soon as the broker is not on this machine.

So there are two directions of trust, and they are established by two commands:

  clients verify a SERVICE     installation CA -> broker.crt, grafana.crt   this command
  broker verifies its CLIENTS  each world CA   -> agent certificates        agora-mqtt <world>

The only thing that crosses is one **public** file per world, `world/<w>/secrets/ca.crt`. On a
single host this command reads it directly; on a split deployment it has to be delivered, and
`--trust` takes the paths. No private key ever crosses: the world's CA key stays with the world,
and the installation CA key stays here, beside the admin token that no agent may hold either.

`--rotate` on the installation CA invalidates every agent's *view* of the broker at once —
everything must be handed the new `ca.crt` before it will connect. That is a different and much
larger act than reissuing one agent, which is why it is never a side effect of anything.
"""

from __future__ import annotations

import argparse
import logging
from agent.config import REPO_ROOT
from .certs import _ca, _leaf, _write

log = logging.getLogger("broker-cert")

INFRA_SECRETS = REPO_ROOT / "infra" / "secrets"

# The name clients will verify. It has to match what the WORLDS state as ag:brokerHost, or every
# agent rejects the certificate — but this side cannot read the worlds on a split deployment, so
# it is an argument with a default rather than a lookup.
DEFAULT_HOST = "localhost"


GRAFANA_DIR = REPO_ROOT / "infra" / "grafana" / "certs"


def issue(host: str = DEFAULT_HOST, rotate: bool = False) -> None:
    """The installation authority, and a server certificate for each service that needs one.

    One authority for both, because they are one installation — an operator who trusts this CA
    to reach the broker is the same operator reaching the dashboard. That is the opposite of the
    per-world CAs, which exist precisely so two societies cannot vouch for each other.
    """
    # Browser-facing: grafana is opened in one, and the broker shares this authority — a
    # browser verifying grafana must verify a signature made by this key.
    ca = _ca(INFRA_SECRETS, "agora installation CA", rotate, browser_facing=True)
    for service, published in (("grafana", GRAFANA_DIR),):
        if _leaf(INFRA_SECRETS, service, host, ca, server=True, rotate=rotate,
                 browser_facing=True):
            log.info("  cert   %-14s CN=%s", service, host)
        # Published beside the service that mounts it. The originals stay in infra/secrets/,
        # which is where the admin token lives and which nothing else is given.
        _write(published / f"{service}.crt",
               (INFRA_SECRETS / f"{service}.crt").read_bytes(), private=False)
        _write(published / f"{service}.key",
               (INFRA_SECRETS / f"{service}.key").read_bytes(), private=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="agora-infra-certs",
        description="Issue the infrastructure's server certificates and assemble the "
                    "authorities the broker trusts. Not onboarding — run it where infra runs.",
    )
    p.add_argument("--host", default=DEFAULT_HOST,
                   help=f"the name clients reach the broker by; must match ag:brokerHost in the "
                        f"worlds that use it (default: {DEFAULT_HOST})")
    p.add_argument("--rotate", action="store_true",
                   help="reissue the installation CA and broker certificate. Everything that "
                        "verifies the broker must be handed the new ca.crt before it reconnects.")
    args = p.parse_args()

    issue(args.host, rotate=args.rotate)
    log.info("restart the services to read these")


if __name__ == "__main__":
    main()
