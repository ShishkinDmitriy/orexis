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
new vocabulary. There is no `orexis:Ratified`, no `orexis:DerivedGraph`, no term of ours at all.

**Sovereign is a role, not an identity.** An installation has several users — one authors a
world, another operates it with fewer powers — so "the sovereign" is not a person to be named
but a capacity someone acted in, on one occasion. `prov:qualifiedAssociation` says exactly that:
the ratification activity has an association carrying `prov:agent` (which user) and
`prov:hadRole` (in what capacity). There is no `orexis:Sovereign` *agent* and there must not be one.

**And the world states the capacity, not this module.** The role was briefly a literal here,
which reads as a detail and is not one: with the capacity assumed, a world could never say that
alice OPERATES what dimonina RATIFIED, because every user it attributed became a sovereign on the
way in. A world says `prov:qualifiedAttribution [ prov:agent … ; prov:hadRole … ]` and this
copies both. Adding a second role is then a world edit rather than a code change, which is the
whole point of there being more than one.

**And none of it is evidence.** The ratified graph asserting who ratified it is circular: the
attribution is a claim the files make about themselves, and anyone who can edit the file can edit
the claim. It is legible, queryable and shapeable, which is worth having — but it is testimony,
not proof, and the record says so where someone deciding whether to trust it will read it.

See knowledge/decisions/who-put-the-fact-there.md.
"""

from __future__ import annotations

from pathlib import Path

from assembly import loader
from orexis_agent_deliberation.ontology import DERIVATIONS_GRAPH
from .config import REPO_ROOT
from orexis_agent_progression.ontology import (DESIRE_ASSERTED_GRAPH, ACTIONS_GRAPH, ONTOLOGY_ENTAILED_GRAPH,
                       ONTOLOGY_GRAPH, WORLD_DERIVED_GRAPH, WORLD_ENTAILED_GRAPH, WORLD_GRAPH)
from orexis_agent_progression.ontology import PUBLIC

# A file, as something a graph can be derived FROM. Minted under our own namespace rather than
# `file:` on purpose: an absolute path bakes one machine into the store, and the world sits at
# `/app/world/` in a container and `world/<name>/` on a host — so the same world would describe
# itself differently depending on where it was built, and two agents could not be compared.
_FILE = "http://example.org/orexis/file/"
_ACTIVITY = "http://example.org/orexis/activity/"

# The two things that compute a graph. Named so the graphs they produce can point at them, and
# so `prov:used` can say what each one read.
CLOSURE = _ACTIVITY + "closure"  # orexis/inference.py
DERIVATION = _ACTIVITY + "derivation"  # every package's rules.ru
RATIFICATION = _ACTIVITY + "ratification"  # a user authored the world files
#  Who does it: the kernel, named by its file like every rule is. A computed graph must
#  say what made it, and "the runtime" is not an answer a reader can follow to a line.
_KERNEL_AGENT = _FILE + "agent/genesis.py"


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


# Who a world says authored it, and IN WHAT CAPACITY. Both come from the world; neither is
# assumed here. The role used to be a literal in this module, which was the wrong place for it
# twice over: an installation has several users with different powers, so a world attributing
# someone had no way to say alice OPERATES what dimonina RATIFIED — and the machine was asserting
# a capacity only the world can know.
#
# The world REFERENCES a user and declares nothing else about them, so this reads two identifiers
# and copies them: no name, no key, no type, and nothing invented. A world that names nobody, or
# that names someone without saying in what capacity, simply gets no association — the shape asks
# a graph to say where it came from, not who to blame.
_ATTRIBUTION_Q = """
SELECT ?user ?role WHERE {
  ?w a orexis:World ; prov:qualifiedAttribution ?att .
  ?att prov:agent ?user ; prov:hadRole ?role .
} LIMIT 1"""


def _turtle(world: Path, attribution: tuple[str, str] | None = None,
            derived_graphs: tuple[str, ...] = (WORLD_DERIVED_GRAPH,)) -> str:
    """The description, as Turtle. One `prov:Entity` per public graph, each accounting for
    itself — see `orexis:PublicGraphShape`, which refuses one that does not."""
    ontology_files = " , ".join(f"<{file_iri(p)}>" for p in loader.ontology_files())
    world_files_ = " , ".join(
        f"<{file_iri(p, world)}>" for p in sorted(world.glob("*.ttl")))
    rules = [file_iri(p) for p in loader.rule_files()]

    lines = [
        "@prefix prov: <http://www.w3.org/ns/prov#> .",
        "@prefix orexis:   <http://example.org/orexis#> .",
        "",
        "# --- asserted: read from files, and the chain stops there (see the module note) ---",
        f"<{ONTOLOGY_GRAPH}> a prov:Entity ; prov:wasDerivedFrom {ontology_files} .",
    ]
    #  The actions, from the packages that own the acting (#238). Asserted from files
    #  exactly as the vocabulary is, and described here for the same reason: a public graph
    #  that cannot say where it came from is the silence `orexis:PublicGraphShape` refuses. A build
    #  where no package states an action still has the graph — empty, and honest about being
    #  derived from nothing rather than absent and unexplained.
    action_files = " , ".join(f"<{file_iri(p)}>" for p in loader.action_files())
    lines.append(f"<{ACTIONS_GRAPH}> a prov:Entity"
                 + (f" ; prov:wasDerivedFrom {action_files} ." if action_files else " ."))
    #  And what those rules READ and WRITE, computed from the same files by
    #  `genesis.describe_derivations` so the scope partition is a function of the store
    #  (scope-actions). Derived from the rule files, which is what it is a reading of.
    lines.append(f"<{DERIVATIONS_GRAPH}> a prov:Entity"
                 + (f" ; prov:wasDerivedFrom {' , '.join(f'<{r}>' for r in rules)} ." if rules else " ."))
    if world_files_:
        lines.append(f"<{WORLD_GRAPH}> a prov:Entity ; prov:wasDerivedFrom {world_files_} .")
        #  The asserted-desire graph is fed by the same ratified files — a world's TriG block
        #  is where a root desire comes from (#312) — and replaced from them on every start
        #  exactly as the world graph is, so it accounts for itself the same way. Described
        #  even when no world states one: an empty graph honest about its source, exactly as
        #  the effects graph is.
        lines.append(
            f"<{DESIRE_ASSERTED_GRAPH}> a prov:Entity ; prov:wasDerivedFrom {world_files_} .")
        if attribution:
            user, role = attribution
            # A qualified association, because the interesting part is the ROLE. `prov:agent`
            # alone would say a user was involved; `prov:hadRole` says in what capacity, which is
            # the only form that survives an installation having several users with different
            # powers. Both are COPIED from what the world stated — the capacity someone acted in
            # is a fact about the world, and a loader that assumed it could never represent a
            # second user. The user is referenced and never typed here — the world did not say it
            # was a Person, and this module describes what happened rather than adding to it.
            lines += [
                f"<{WORLD_GRAPH}> prov:wasGeneratedBy <{RATIFICATION}> .",
                f"<{RATIFICATION}> a prov:Activity ; prov:qualifiedAssociation [",
                f"    a prov:Association ; prov:agent <{user}> ; prov:hadRole <{role}> ] .",
            ]
    else:
        # A world with no Turtle at all cannot be described as derived from anything, and the
        # shape would then refuse it — which is the correct outcome and worth reaching honestly.
        lines.append(f"<{WORLD_GRAPH}> a prov:Entity .")

    # Every graph a rule writes into, not just the world's. A package may own one — desire does —
    # and a public graph that could not account for itself would be exactly the silence
    # `orexis:PublicGraphShape` and `tests/test_provenance.py` exist to refuse. Which graphs those
    # are is asked of the rules (see `genesis.write_targets`) rather than listed here, so the
    # kernel still names no package.
    lines += [
        "",
        "# --- derived: a rule computed it, and the rules are the software agents that did ---",
    ] + [
        f"<{g}> a prov:Entity ; prov:wasGeneratedBy <{DERIVATION}> ." for g in derived_graphs
    ] + [
        f"<{DERIVATION}> a prov:Activity ;",
        "    prov:used <%s> , <%s> , <%s> , <%s> ;" % (
            ONTOLOGY_GRAPH, ONTOLOGY_ENTAILED_GRAPH, WORLD_GRAPH, WORLD_ENTAILED_GRAPH),
        "    prov:wasAssociatedWith " + (" , ".join(f"<{r}>" for r in rules) or "<%s>" % DERIVATION)
        + " .",
    ]
    lines += [f"<{r}> a prov:SoftwareAgent ." for r in rules]

    #  What an agent says its OWN graphs are (the-mind-is-six-graphs): public, because a
    #  modality-scoped query must resolve `?d a orexis:DesireGraph` without naming an instance —
    #  and public means it accounts for itself here like every other public graph. Generated
    #  by the kernel from the vocabulary's graph classes and the one identifier the process
    #  is given, which is why the classification activity used the ontology and nothing else.

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


def attribution_of(st) -> tuple[str, str] | None:
    """The user a world says authored it and the capacity they acted in, or None.

    None for a world that names nobody, and equally for one that names someone without saying in
    what capacity — a bare `prov:wasAttributedTo` is not enough, because the capacity is the part
    that distinguishes ratifying from operating. Silence is a better answer than a guess.
    """
    from orexis_agent_progression.store import bindings

    rows = bindings(st.query(_ATTRIBUTION_Q, st.graphs_of(PUBLIC)))
    return (rows[0]["user"], rows[0]["role"]) if rows else None


def describe(st, world: Path, derived_graphs: tuple[str, ...] = (WORLD_DERIVED_GRAPH,)) -> None:
    """Replace the catalogue's account of what was just loaded.

    Runs last in `refresh_public`, because it describes the result. Replaced rather than added
    to, for the same reason the closure is recomputed: it is a function of the files, and a
    description that accumulated would soon be describing a world that no longer exists.

    `derived_graphs` is passed in rather than worked out here: the caller has already resolved
    which graphs the rules write into, and asking twice would mean two places that could
    disagree about what a derivation produced.
    """
    import rdflib
    catalogue = st.catalogue
    #  INTO THE CATALOGUE, where everything said about a graph lives, and replaced there: every
    #  row in PROV's words is this account's — a want's `prov:wasDerivedFrom` is in the want's
    #  own graph, never here — so the previous account is exactly the PROV rows.
    st.update(f"""
DELETE {{ GRAPH <{catalogue}> {{ ?s ?p ?o }} }}
WHERE  {{ GRAPH <{catalogue}> {{ ?s ?p ?o }}
         FILTER(STRSTARTS(STR(?p), "http://www.w3.org/ns/prov#")
                || (isIRI(?o) && STRSTARTS(STR(?o), "http://www.w3.org/ns/prov#"))) }}""")
    account = rdflib.Graph().parse(data=_turtle(world, attribution_of(st), derived_graphs), format="turtle")
    st.update(f"INSERT DATA {{ GRAPH <{catalogue}> {{\n{account.serialize(format='nt')}\n}} }}")
