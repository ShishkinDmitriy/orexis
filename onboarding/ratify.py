"""agora-ratify — mint a version of a world, and say who stands behind it.

  agora-ratify society                      # a new version, same user as the last one
  agora-ratify society --user <uri>         # a different user ratified this one
  agora-ratify society --role ag:Operator   # in a different capacity

**Ratification had to become a command**, and the reason is small and forcing: a version records
a content hash, a hash cannot be hand-written, and without one nothing can tell a world that was
ratified from one that has been edited since. Before this, amending a world meant editing a file
and bumping a number by hand — and forgetting was invisible, which is precisely the failure
`world_version` in the metrics exists to catch and could not.

**It only ever appends.** A new version node is added, linked to its predecessor by
`prov:wasRevisionOf`; nothing already written is rewritten, including which version is current —
that is derived (see `vocabulary/agora/rules.ru`). So the chain in `versions.ttl` is append-only
in the literal sense rather than the aspirational one, and `git log` on that file is the history
of who ratified what and when.

**It is the sovereign's, and it lives here** for the same reason `create_keypair` does: an agent
that could mint a version of its own world could rewrite the terms it is held to. `agent/` may
read a version and must never author one.

See knowledge/decisions/a-version-is-a-snapshot.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

from agent import genesis, versions
from agent.ontology import AG
from agent.store import Store

log = logging.getLogger("ratify")

SOVEREIGN = AG + "Sovereign"

_ENTRY = """
ag:version_{n} a ag:WorldVersion ;
    ag:versionNumber {n} ;
    ag:contentHash "{hash}" ;
    prov:generatedAtTime "{at}"^^xsd:dateTime ;
    prov:wasRevisionOf ag:version_{previous} ;
    prov:qualifiedAttribution [
        prov:agent <{user}> ; prov:hadRole <{role}> ] .
"""


def _built(world: str) -> Store:
    """The world as everything else sees it — files loaded, entailed and derived.

    Built rather than parsed, because the head of the chain is a DERIVED fact and a bare pile of
    Turtle does not have one. Ratifying against anything less would be ratifying something no
    reader would agree with.
    """
    st = Store()
    genesis.refresh_public(st, genesis.world_dir(world))
    return st


def ratify(world: str, user: str | None = None, role: str = SOVEREIGN) -> bool:
    """Record what these files now are. False if there was nothing to record."""
    path = genesis.world_dir(world)
    covered = genesis.ratified_files(path)
    st = _built(world)

    head = versions.current(st.query)
    digest = versions.content_hash(covered)

    if head and head.get("hash") == digest:
        # Nothing changed. Minting a version anyway would make the chain a log of when someone
        # ran a command rather than a record of when the world changed, and every reader that
        # compares versions would start seeing differences that mean nothing.
        log.info("%s is unchanged since version %s — nothing to ratify", world, head["number"])
        return False

    number = int(head["number"]) + 1 if head else 1
    if user is None:
        # Continuity: the same hand unless told otherwise. A first ratification has nobody to
        # inherit from, and guessing there would be inventing an author — so it refuses instead.
        previous = versions.attribution(st.query) if head else None
        if previous is None:
            raise SystemExit(
                "agora-ratify: no previous version to inherit an author from — say who is "
                "ratifying this: agora-ratify %s --user <uri>" % world)
        user = previous

    entry = _ENTRY.format(n=number, previous=number - 1, hash=digest, user=user, role=role,
                          at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    if number == 1:
        entry = entry.replace(f"    prov:wasRevisionOf ag:version_0 ;\n", "")

    versions_file = path / genesis.VERSIONS_FILE
    with versions_file.open("a") as out:
        out.write(entry)

    log.info("%s ratified as version %d", world, number)
    log.info("  %s", digest)
    log.info("  by %s as %s", user, role.rsplit("#", 1)[-1])
    for f in covered:
        log.info("  covers %s", f.name)
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="agora-ratify",
        description="Mint a version of a world: fingerprint what it says, and record who "
                    "stands behind it.")
    p.add_argument("world", help="which world. Available: " + ", ".join(genesis.worlds()))
    p.add_argument("--user", help="the user ratifying this version, as a URI. Defaults to "
                                  "whoever ratified the previous one.")
    p.add_argument("--role", default=SOVEREIGN,
                   help="the capacity they acted in. Defaults to ag:Sovereign.")
    args = p.parse_args()
    sys.exit(0 if ratify(args.world, args.user, args.role) else 0)


if __name__ == "__main__":
    main()
