"""agora-onboard — everything between a ratified world and a society that can be started.

  agora-onboard society

**Genesis ends with a world; it does not end with a society.** A world says what exists and how
it is wired, and that is a complete description of nothing running. Between it and a first
`podman compose up` there is a phase with no name until now, made of three tools that each read
the same `world.ttl` and grant exactly what its wiring implies:

  agora-influx <world>    a bucket per agent, and a token that opens only it
  agora-mqtt <world>      a credential per principal, and the broker ACL, derived
  agora-compose <world>   the roster, as services

Calling that phase **onboarding** is not decoration. It names the moment an agent stops being a
description and acquires the means to act: an account of its own on the series store, a
credential of its own on the bus, and a container to run in. That is what onboarding means for a
person joining anything — not deciding what they may do, which was settled earlier, but handing
them the keys that let them do it.

**Nothing here decides anything.** Every grant is derived from the wiring the sovereign already
ratified, which is why this can be a single command and why re-running it is safe. Adding an
agent to a world and running this again is the whole of onboarding it; there is no list to keep
in step, because there is no list.

**It is not birth.** Onboarding gives an agent what it needs from the outside world;
birth is the agent authoring its own beliefs, once, on its first start — inside its own
container, from the files mounted beside it, with nobody watching. One is done TO an agent and
is repeatable; the other is done BY it and is not. See knowledge/domain/onboarding.md and the
lifecycle table in knowledge/domain/agent.md.

**Order matters, and only in one place.** Validation comes first because onboarding a world that
does not hold together mints credentials for agents that will refuse to start. The other three
are independent — but `agora-mqtt` reloads the broker at the end, so it is last among the two
provisioners, and compose is written last because it is the thing you then run.

See knowledge/domain/onboarding.md.
"""

from __future__ import annotations

import argparse
import logging

from . import compose, influx, mqtt, validate
from agora.genesis import worlds

log = logging.getLogger("onboard")


def onboard(world: str, rotate: bool = False, check: bool = True) -> None:
    """Grant a ratified world everything it needs to be started.

    Safe to re-run: each step is idempotent unless `rotate` is asked for, which is the one
    destructive option here — it replaces credentials that are currently in use, so anything
    holding an old one is locked out until it is restarted with the new.
    """
    if check and not validate.validate_world(world):
        # Onboarding an inconsistent world is worse than refusing: it mints real credentials for
        # agents that will fail their own startup validation, and leaves them lying around.
        raise SystemExit(f"agora-onboard: world {world!r} does not hold together — nothing granted")

    log.info("onboarding %s", world)
    influx.provision(world, rotate=rotate)
    mqtt.provision(world, rotate=rotate)
    if not mqtt.reload_broker():
        # Not fatal, and not silent. A broker that never reloaded holds the OLD acl, and
        # mosquitto accepts a SUBSCRIBE it will not honour — so this looks like an agent that
        # went quiet rather than like an error.
        log.warning("  ! the ACL on disk is ahead of the broker until it restarts or reloads")
    compose.generate(world)
    log.info("onboarded %s — `cd world/%s && podman compose up -d` to start it", world, world)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="agora-onboard",
        description="Grant a ratified world its credentials and its compose file, all derived "
                    "from that world's own wiring.",
    )
    p.add_argument("world",
                   help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--rotate", action="store_true",
                   help="replace credentials that already exist. Anything still holding an old "
                        "one is locked out until restarted.")
    p.add_argument("--no-check", action="store_true",
                   help="skip validation. Only useful when you are onboarding a world you are "
                        "deliberately part-way through authoring.")
    args = p.parse_args()
    onboard(args.world, rotate=args.rotate, check=not args.no_check)


if __name__ == "__main__":
    main()
