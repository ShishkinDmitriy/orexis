"""orexis-onboard — everything between a ratified world and a society that can be started.

  orexis-onboard society

**Genesis ends with a world; it does not end with a society.** A world says what exists and how
it is wired, and that is a complete description of nothing running. Between it and a first
`podman compose up` there is a phase with no name until now, made of four tools that each read
the same world's documents and grant exactly what its wiring implies:

  orexis-influx <world>    a bucket per agent, and a token that opens only it
  orexis-mqtt <world>      a credential per principal, and the broker ACL, derived — where it has a bus
  orexis-compose <world>   the roster, as services
  orexis-dashboards <w>    what this world observes, as a Grafana folder

**A step runs where the world has what it serves.** History is every agent's, so every world is
granted it; the bus is a broker the world's society names, so `orexis-mqtt` runs only where one is
named (`reading.PREMISES`), and a world with none — Hanoi, the courier, the tower — is onboarded
without it and told so in one line; metrics are where the world says it is monitored.

**What an agent runs is declared, and checked here before anything is granted.** Each agent's roles
are stated in its own self graph; `reading.refused` boots every agent as its container would and
refuses an agent declaring no role, a role whose needs its world lacks, and what would arrive for an
agent and be read by none of its roles (#927).

Calling that phase **onboarding** is not decoration. It names the moment an agent stops being a
description and acquires the means to act: an account of its own on the series store, a
credential of its own on the bus, and a container to run in. That is what onboarding means for a
person joining anything — not deciding what they may do, which was settled earlier, but handing
them the keys that let them do it.

**Nothing here decides anything.** Every grant is derived from the wiring the sovereign already
ratified, which is why this can be a single command and why re-running it is safe. Adding an
agent to a world and running this again is the whole of onboarding it; there is no list to keep
in step, because there is no list.

**Taking an agent away is not the mirror of adding one.** A re-run grants what the wiring implies
and takes nothing back: it ends by REPORTING what the world still holds that its wiring no longer
implies — a credential, a certificate, a token, a bucket — and each line names the command that
would take it. That is `--revoke <principal>` on `orexis-mqtt` and on `orexis-influx`, explicit
every time, because each is a decision a re-run may not make: an agent absent today may be back
tomorrow, and its bucket is the record of what happened while it was here (#28, #29).

**It is not birth.** Onboarding gives an agent what it needs from the outside world;
birth is the agent authoring its own beliefs, once, on its first start — inside its own
container, from the files mounted beside it, with nobody watching. One is done TO an agent and
is repeatable; the other is done BY it and is not. See knowledge/domain/onboarding/onboarding.md and the
lifecycle table in knowledge/domain/kernel/agent.md.

**Order matters, and only in one place.** Validation comes first because onboarding a world that
does not hold together mints credentials for agents that will refuse to start. The others are
independent — but `orexis-mqtt` reloads the broker at the end, so it is last among the two
provisioners, and compose is written after them because it is the thing you then run.

See knowledge/domain/onboarding/onboarding.md.
"""

from __future__ import annotations

import argparse
import logging

from agent.store import DocumentRefused

from . import certs, compose, dashboards, influx, installation, mqtt, reading
from .worlds import world_dir, worlds

log = logging.getLogger("onboard")


def onboard(world: str, rotate: bool = False, check: bool = True) -> None:
    """Grant a ratified world everything it needs to be started.

    Safe to re-run: each step is idempotent unless `rotate` is asked for, which is the one
    destructive option here — it replaces credentials that are currently in use, so anything
    holding an old one is locked out until it is restarted with the new.
    """
    if check:
        # Onboarding a world whose documents will not load is worse than refusing: it mints real
        # credentials for agents that will refuse to boot, and leaves them lying around. So the
        # world is read as onboarding reads it first — as an agent boots it, and then onboarding's
        # own kinds — and a graph of a kind no reader declares is refused with it: every reader
        # passes over such a graph in silence, so a misspelled kind is caught here or nowhere.
        try:
            unread = reading.unread(world_dir(world))
        except DocumentRefused as refused:
            raise SystemExit(f"orexis-onboard: world {world!r} does not load — {refused}; nothing granted")
        if unread:
            raise SystemExit(f"orexis-onboard: world {world!r} holds graphs of a kind no reader declares — "
                             f"{'; '.join(unread)}; nothing granted")
        # What an agent runs is declared — its roles, in its own self graph — and held to its world
        # both ways before anything is granted: a role whose needs the world lacks, and what would
        # arrive for an agent and be read by none of its roles. An agent declaring no role would boot,
        # load nothing and run nothing, which no credential should be minted for
        # (a-package-is-loaded-only-for-a-role-the-agent-is-declared-in).
        refused = reading.refused(world_dir(world))
        if refused:
            raise SystemExit(f"orexis-onboard: world {world!r} declares its agents' roles in a way it does not "
                             f"bear out — {'; '.join(refused)}; nothing granted")
        # And a world posed in a state its own constraints say cannot be is refused the same way: a
        # constraint is what the world says is possible, so this is the world contradicting itself,
        # which no agent repairs — it would say so in every pass and mend nothing (constraint.md).
        contradicted = [f"{a} holds {c}" for a in compose.roster(world) for c in reading.contradicted(world_dir(world), a)]
        if contradicted:
            raise SystemExit(f"orexis-onboard: world {world!r} is posed in a state its own constraints say is "
                             f"impossible — {'; '.join(contradicted)}; nothing granted")

    log.info("onboarding %s", world)
    # A world asking to be monitored where the installation serves metrics nowhere is refused before
    # anything is granted, as a world that will not load is: every tool below would refuse it anyway,
    # one of them after the credentials were minted.
    told = installation.purposes(world)
    log.info("  its agents write %s", " and ".join(p.lower() for p in told))
    # What the documents leave out is derived before anything is rendered from them: a broker whose
    # world asserts no url is allocated one here, beside every other world's, and every tool below
    # only reads what was asserted or allocated (onboarding.derived).
    installation.write_derivation()
    influx.provision(world, rotate=rotate)
    # THE BUS, where the world's society names a broker: its credentials, its ACL, the agents'
    # certificates and the reload all serve one, and a world naming none has nothing for them to
    # serve — `broker` refuses to answer an address for it, so nothing below asks.
    bus = reading.BUS in reading.premises(world_dir(world))
    if bus:
        mqtt.provision(world, rotate=rotate)
        if not mqtt.reload_broker(world):
            # Not fatal, and not silent. A broker that never reloaded holds the OLD acl, and
            # mosquitto accepts a SUBSCRIBE it will not honour — so this looks like an agent that
            # went quiet rather than like an error.
            log.warning("  ! the ACL on disk is ahead of the broker until it restarts or reloads")
    else:
        log.info("  no bus — its society names no mqtt4ssn:Broker, so no broker credential, ACL or certificate")
    compose.generate(world)
    dashboards.generate(world)
    if bus and not certs.world_ca(world).exists():
        log.warning("  ! no certificate authority for this world")
    report(world)
    log.info("onboarded %s — `cd world/%s && podman compose up -d` to start it", world, world)


def report(world: str) -> list[str]:
    """What exists for this world that its wiring no longer implies — a credential, a certificate,
    a token or a bucket of a principal the society does not state. Said, and nothing taken: a
    grant is derived from the wiring, so adding an agent is re-running this, but taking one away
    is not the mirror of it. An agent absent today may be back tomorrow, its bucket is the record
    of what happened while it was here, and its certificate is refused by nothing until the
    authority says so — each of which is a decision, made by `--revoke` on the tool that granted
    it and never by a re-run. The series store is asked where the admin token is here, and the
    line says so where it is not.
    """
    from influxdb_client.rest import ApiException

    found = mqtt.stale(world) + influx.stale_files(world)
    try:
        found += influx.stale_grants(world)
    except influx.AdminError as exc:
        log.info("  the series store was not asked what it holds for %s — %s", world, exc)
    except (influx.StoreUnreachable, ApiException) as exc:
        #  THE STORE'S OWN REFUSALS, and only those: a report must not fail the onboarding it
        #  ends, and a store that is down is the ordinary case on a host that is not the bench —
        #  but a fault in the report itself is not the store's and is not swallowed here. The
        #  first cut caught everything, and hid a path error of its own for one test run.
        log.warning("  ! the series store could not be asked what it holds for %s: %s", world, exc)
    for line in found:
        log.warning("  stale  %s", line)
    if not found:
        log.info("  nothing stale — everything held is implied by the wiring")
    return found


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-onboard",
        description="Grant a ratified world its credentials and its compose file, all derived "
                    "from that world's own wiring.",
    )
    p.add_argument("world",
                   help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--rotate", action="store_true",
                   help="replace credentials that already exist. Anything still holding an old "
                        "one is locked out until restarted.")
    p.add_argument("--no-check", action="store_true",
                   help="skip loading the world first. Only useful when you are onboarding a world "
                        "you are deliberately part-way through authoring.")
    args = p.parse_args()
    onboard(args.world, rotate=args.rotate, check=not args.no_check)


if __name__ == "__main__":
    main()
