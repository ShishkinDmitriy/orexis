"""What each public graph IS, said in the store rather than in a comment.

Public knowledge is five graphs and the difference between them is load-bearing: one holds what
a sovereign ratified, another what a rule computed, another what RDFS entailed. That was true
before this module and **unreadable** — the knowledge lived in the names, in `ontology.py`'s
comments, and in a decision record. A shape could not check it, an agent could not query it, and
anyone with a SPARQL client saw five graphs and no way to ask which held computed facts.

Which is the filename mistake one level up. A graph IRI is an identifier, not a description, and
the proof is that renaming all five to `g1`..`g5` would leave every query in this repository
working — nothing parses these strings, they are constants referenced by name. **After this
module, the store still knows what each one is.** `tests/test_provenance.py` holds it to that.

**PROV-O only, and nothing invented.** `prov:` is already in `store.PREFIXES` and every
observation already carries `prov:wasGeneratedBy`, so this is the existing habit rather than a
new vocabulary. There is no `ag:Ratified`, no `ag:DerivedGraph`, no term of ours at all.

**Sovereign is a role, not an identity.** An installation has several users — one authors a
world, another operates it with fewer powers — so "the sovereign" is not a person to be named
but a capacity someone acted in, on one occasion. `prov:qualifiedAssociation` says exactly that:
the ratification activity has an association carrying `prov:agent` (which user) and
`prov:hadRole ag:Sovereign` (in what capacity). There is no `ag:Sovereign` *agent* and there must
not be one.

**And none of it is evidence.** The ratified graph asserting who ratified it is circular: the
attribution is a claim the files make about themselves, and anyone who can edit the file can edit
the claim. It is legible, queryable and shapeable, which is worth having — but it is testimony,
not proof, and the record says so where someone deciding whether to trust it will read it.

See knowledge/decisions/who-put-the-fact-there.md.
"""

from __future__ import annotations

from pathlib import Path

from . import loader
from .config import REPO_ROOT
from .ontology import (ONTOLOGY_ENTAILED_GRAPH, ONTOLOGY_GRAPH, PROVENANCE_GRAPH,
                       WORLD_DERIVED_GRAPH, WORLD_ENTAILED_GRAPH, WORLD_GRAPH)

# A file, as something a graph can be derived FROM. Minted under our own namespace rather than
# `file:` on purpose: an absolute path bakes one machine into the store, and the world sits at
# `/app/world/` in a container and `world/<name>/` on a host — so the same world would describe
# itself differently depending on where it was built, and two agents could not be compared.
_FILE = "http://example.org/agora/file/"
_ACTIVITY = "http://example.org/agora/activity/"

# The two things that compute a graph. Named so the graphs they produce can point at them, and
# so `prov:used` can say what each one read.
CLOSURE = _ACTIVITY + "closure"  # agora/inference.py
DERIVATION = _ACTIVITY + "derivation"  # every package's rules.ru
RATIFICATION = _ACTIVITY + "ratification"  # a user authored the world files


def file_iri(path: Path, world: Path | None = None) -> str:
    """A stable identifier for a file, independent of where the tree happens to sit.

    Package files are named relative to the repository root, which they are always inside. A
    world's files are named `world/<name>/<file>` from the world directory's own name instead —
    a mounted world is at an absolute path with no relationship to this checkout, and computing
    `../../..` from it would put the build machine's layout into the graph.
    """
    if world is not None:
        return f"{_FILE}world/{world.name}/{path.name}"
    try:
        return _FILE + path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        # Outside the repository entirely — a test tree, or an oddly installed package. Its own
        # name is the most that can honestly be said about where it came from.
        return _FILE + path.name


# Who a world says ratified it. The world REFERENCES a user and declares nothing about them, so
# this reads an identifier and copies it — it does not learn a name, a key or a type, and must
# not invent one. A world that names nobody simply has no association, which is honest: the
# shape asks a graph to say where it came from, not who to blame.
_SOVEREIGN_Q = "SELECT ?user WHERE { ?w a ag:World ; prov:wasAttributedTo ?user } LIMIT 1"


def _turtle(world: Path, sovereign: str | None = None) -> str:
    """The description, as Turtle. One `prov:Entity` per public graph, each accounting for
    itself — see `ag:PublicGraphShape`, which refuses one that does not."""
    ontology_files = " , ".join(f"<{file_iri(p)}>" for p in loader.ontology_files())
    world_files_ = " , ".join(
        f"<{file_iri(p, world)}>" for p in sorted(world.glob("*.ttl")))
    rules = [file_iri(p) for p in loader.rule_files()]

    lines = [
        "@prefix prov: <http://www.w3.org/ns/prov#> .",
        "@prefix ag:   <http://example.org/agora#> .",
        "",
        "# --- asserted: read from files, and the chain stops there (see the module note) ---",
        f"<{ONTOLOGY_GRAPH}> a prov:Entity ; prov:wasDerivedFrom {ontology_files} .",
    ]
    if world_files_:
        lines.append(f"<{WORLD_GRAPH}> a prov:Entity ; prov:wasDerivedFrom {world_files_} .")
        if sovereign:
            # A qualified association, because the interesting part is the ROLE. `prov:agent`
            # alone would say a user was involved; `prov:hadRole` says in what capacity, which is
            # the only form that survives an installation having several users with different
            # powers. The user is referenced and never typed here — the world did not say it was
            # a Person, and this module describes what happened rather than adding to it.
            lines += [
                f"<{WORLD_GRAPH}> prov:wasGeneratedBy <{RATIFICATION}> .",
                f"<{RATIFICATION}> a prov:Activity ; prov:qualifiedAssociation [",
                f"    a prov:Association ; prov:agent <{sovereign}> ; prov:hadRole ag:Sovereign ] .",
            ]
    else:
        # A world with no Turtle at all cannot be described as derived from anything, and the
        # shape would then refuse it — which is the correct outcome and worth reaching honestly.
        lines.append(f"<{WORLD_GRAPH}> a prov:Entity .")

    lines += [
        "",
        "# --- derived: a rule computed it, and the rules are the software agents that did ---",
        f"<{WORLD_DERIVED_GRAPH}> a prov:Entity ; prov:wasGeneratedBy <{DERIVATION}> .",
        f"<{DERIVATION}> a prov:Activity ;",
        "    prov:used <%s> , <%s> , <%s> , <%s> ;" % (
            ONTOLOGY_GRAPH, ONTOLOGY_ENTAILED_GRAPH, WORLD_GRAPH, WORLD_ENTAILED_GRAPH),
        "    prov:wasAssociatedWith " + (" , ".join(f"<{r}>" for r in rules) or "<%s>" % DERIVATION)
        + " .",
    ]
    lines += [f"<{r}> a prov:SoftwareAgent ." for r in rules]

    lines += [
        "",
        "# --- entailed: RDFS said it. The activity names what it closed over, which is the",
        "#     whole difference from the graph above: no author, and nothing that could have",
        "#     been decided otherwise.",
        f"<{ONTOLOGY_ENTAILED_GRAPH}> a prov:Entity ; prov:wasGeneratedBy <{CLOSURE}> .",
        f"<{WORLD_ENTAILED_GRAPH}> a prov:Entity ; prov:wasGeneratedBy <{CLOSURE}> .",
        f"<{CLOSURE}> a prov:Activity ;",
        f"    prov:used <{ONTOLOGY_GRAPH}> , <{WORLD_GRAPH}> ;",
        f"    prov:wasAssociatedWith <{file_iri(Path(__file__).parent / 'inference.py')}> .",
        f"<{file_iri(Path(__file__).parent / 'inference.py')}> a prov:SoftwareAgent .",
    ]
    return "\n".join(lines) + "\n"


def sovereign_of(st) -> str | None:
    """The user a world says ratified it, or None if it names nobody."""
    from .store import bindings

    rows = bindings(st.query(_SOVEREIGN_Q))
    return rows[0]["user"] if rows else None


def describe(st, world: Path) -> None:
    """Replace the meta-graph with an account of what was just loaded.

    Runs last in `refresh_public`, because it describes the result. Replaced rather than added
    to, for the same reason the closure is recomputed: it is a function of the files, and a
    description that accumulated would soon be describing a world that no longer exists.
    """
    st.put_graph(PROVENANCE_GRAPH, _turtle(world, sovereign_of(st)))
