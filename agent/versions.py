"""What version a world is, and whether it is still the version it says it is.

`ag:WorldVersion` has been documented as *"the chain is append-only"* since the vocabulary was
written. There was no chain: every world declared one node, `ag:version_1`, with no predecessor,
no author and no timestamp, and **nothing anywhere wrote one**. It was read in four places and
produced in none — so `metrics.py`'s `world_version`, whose whole purpose is catching *"a world
re-ratified while agents keep running the version they booted with"*, could never differ.

Three things make the chain real, and each is a choice worth knowing about.

**Snapshots store; deltas derive.** A version is the world as it stood, entire. Retraction needs
no vocabulary at all — a fern that moved pots is simply *absent* from the later snapshot, and
"who introduced this triple" is "the earliest version containing it", which is a computation
rather than a statement. That is what keeps reification and RDF-star out of this design, and it
is why there is no `ag:retracts`. The bodies live in git; what the store keeps is the lineage.

**The head is derived, not declared.** `ag:currentVersion` is computed by `vocabulary/agora/
rules.ru` as the version no other version revises, and lands in the derived graph with every
other computed fact. That is what lets `versions.ttl` be append-only in the literal sense —
ratifying only ever ADDS a node, and never rewrites a line saying which one is current. A file
that had to be edited to record its own head would not be a chain, it would be a pointer.

**The hash is over raw bytes.** See `content_hash`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .store import bindings

# `sha256:` is carried in the literal on purpose. A bare hex string is indistinguishable from any
# other hex string, and the day this changes algorithm the old values must still say what they
# were computed with — a hash whose function is forgotten is not evidence of anything.
_ALGORITHM = "sha256"


def content_hash(files: list[Path]) -> str:
    """A fingerprint of exactly what was ratified, over the RAW BYTES of each file.

    **Bytes rather than a canonical serialisation of the parsed graph**, and the reason is that
    the two answer different questions. A canonical hash asks *does this still mean the same*;
    this gate asks *is what is on disk what was ratified*. Only the second is what a ratification
    is for — under the first, someone could reformat every file, rewrite every comment, and the
    store would go on claiming to be version 3 when version 3 was a different document. Comments
    are part of what a sovereign authored, and a world is reviewed by reading it.

    It is also the simpler thing to be sure of. Canonicalising a graph containing blank nodes —
    and `prov:qualifiedAttribution [ … ]` is one — needs RDFC-1.0 and a correct implementation of
    it, which is a large dependency to take on in order to answer a weaker question.

    The file's NAME is hashed with its content, so renaming a world file is a change too. Order
    comes from the caller, which sorts; two worlds with the same files in a different filesystem
    order must not disagree about what they are.
    """
    digest = hashlib.new(_ALGORITHM)
    for path in files:
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"{_ALGORITHM}:{digest.hexdigest()}"


# The head of the chain and what it claims to cover. Read through `ag:currentVersion`, which is
# DERIVED — see the module note — so this works only against a store that has run the rules, and
# says nothing at all about a bare pile of Turtle. That is the right dependency: a version is a
# fact about a world that has been assembled, not about a directory.
_CURRENT_Q = """
SELECT ?version ?number ?hash WHERE {
  ?world a ag:World ; ag:currentVersion ?version .
  ?version ag:versionNumber ?number .
  OPTIONAL { ?version ag:contentHash ?hash }
} LIMIT 1"""

# Every version, so a chain can be walked or counted. Ordered by the number the author stated,
# which is what it is for — the structural order is `prov:wasRevisionOf` and the two must agree.
_CHAIN_Q = """
SELECT ?version ?number ?hash ?predecessor WHERE {
  ?version a ag:WorldVersion ; ag:versionNumber ?number .
  OPTIONAL { ?version ag:contentHash ?hash }
  OPTIONAL { ?version prov:wasRevisionOf ?predecessor }
} ORDER BY ?number"""


def current(query) -> dict | None:
    """The version in force: its IRI, its number, and the hash it claims to cover."""
    rows = bindings(query(_CURRENT_Q))
    return rows[0] if rows else None


def chain(query) -> list[dict]:
    """Every version this world has had, oldest first."""
    return bindings(query(_CHAIN_Q))


_ATTRIBUTION_Q = """
SELECT ?user WHERE {
  ?world a ag:World ; ag:currentVersion ?version .
  ?version prov:qualifiedAttribution [ prov:agent ?user ] .
} LIMIT 1"""


def attribution(query) -> str | None:
    """Who ratified the version in force, so the next one can inherit the same hand.

    Only the user, deliberately — the ROLE is not inherited. Someone ratifying in one capacity
    today says nothing about the capacity they will act in next time, and carrying it forward
    would quietly re-assert a claim nobody made. `agora-ratify` defaults the role explicitly
    instead, where it is visible.
    """
    rows = bindings(query(_ATTRIBUTION_Q))
    return rows[0]["user"] if rows else None


def drift(query, files: list[Path]) -> str | None:
    """What is wrong, if the files on disk are not the version the world claims. Else None.

    This is the whole gate, and it is deliberately a *description* rather than a boolean: the
    only useful thing to say about a failed ratification check is which of several different
    mistakes was made, and every one of them is fixed by a different action.
    """
    head = current(query)
    if head is None:
        return ("this world states no version at all — nothing has ever been ratified. "
                "Run `agora-ratify <world> --user <uri>` to mint the first one.")
    if not head.get("hash"):
        return (f"version {head['number']} records no ag:contentHash, so nothing can say whether "
                "these files are the ones it covers. Run `agora-ratify <world>`.")
    actual = content_hash(files)
    if actual != head["hash"]:
        return (f"the world files have changed since version {head['number']} was ratified.\n"
                f"  ratified: {head['hash']}\n"
                f"  on disk:  {actual}\n"
                "Run `agora-ratify <world>` to record a new version, or restore the files.")
    return None
