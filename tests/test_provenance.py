"""Who put the fact there — and the guard that the two engines still agree about it.

Public knowledge is five graphs: what a package asserted, what the sovereign ratified, what
RDFS entailed of each, and what the rules derived. The split exists so that "who put this here"
is answerable by looking rather than by knowing, and these hold it to that.

The test that matters most is the last one, and it is not about graphs at all. Two engines
compute a world — pyoxigraph for an agent, rdflib for the operator's tools — and the whole
family of bugs behind issues #27 and #58 is those two quietly disagreeing. One had already
happened when this file was written; see the docstring on the roster test.

See knowledge/decisions/who-put-the-fact-there.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from agent import genesis, ratified
from agent.ontology import (AG, ONTOLOGY_ENTAILED_GRAPH, ONTOLOGY_GRAPH, PROVENANCE_GRAPH,
                            WORLD_DERIVED_GRAPH, WORLD_ENTAILED_GRAPH,
                            WORLD_GRAPH)
from agent.store import Store, bindings
from agent.validate import conforms, graph_from

WORLDS = ["society", "simulation", "sensing"]


def _public(world: str) -> Store:
    st = Store()
    genesis.refresh_public(st, genesis.world_dir(world))
    return st


def _in_graph(st: Store, graph: str, sparql: str) -> list[dict]:
    return bindings(st.query(f"SELECT * WHERE {{ GRAPH <{graph}> {{ {sparql} }} }}"))


# --- each kind of fact lands where it says it does --------------------------------------------

@pytest.mark.parametrize("world", WORLDS)
def test_a_derived_capability_is_not_in_the_ratified_world(world):
    """`world.ttl` says in a comment that it declares no capability. That was the only thing
    saying so — AGENTS.md states the rule and a test asserted the derivation worked, but nothing
    stopped a capability being *written* there and nothing could tell one apart afterwards.
    Now the ratified graph simply does not contain them."""
    st = _public(world)
    assert not _in_graph(st, WORLD_GRAPH, "?a ag:hasCapability ?c")
    assert _in_graph(st, WORLD_DERIVED_GRAPH, "?a ag:hasCapability ?c")


@pytest.mark.parametrize("world", WORLDS)
def test_the_ratified_world_is_exactly_what_the_files_say(world):
    """Nothing computed leaks back into the sovereign's graph. This is what makes the world
    diffable against its own files — the property that would be lost for ever the moment
    something merged the derived graph back in for convenience."""
    st = _public(world)
    plain = Store()
    plain.put_graph(WORLD_GRAPH, "\n".join(
        p.read_text() for p in genesis.world_files(genesis.world_dir(world))), dataset=True)

    def count(store):
        return int(bindings(store.query(
            f"SELECT (COUNT(*) AS ?n) WHERE {{ GRAPH <{WORLD_GRAPH}> {{ ?s ?p ?o }} }}"))[0]["n"])

    assert count(plain) == count(st)


def test_computed_graphs_do_not_accumulate_across_starts():
    """`refresh_public` runs on every boot, and an agent may run for months between restarts.
    A closure or a derivation that appended rather than replaced would grow the belief base by
    restart count — and `belief_triples` is reported as flat (see domain/agent-metrics.md)."""
    st = _public("society")
    sizes = _sizes(st)
    genesis.refresh_public(st, genesis.world_dir("society"))
    assert _sizes(st) == sizes


def _sizes(st: Store) -> dict[str, int]:
    """Triples per public graph. Counted, not measured off the serialisation — a Turtle dump
    renumbers blank nodes, so its LENGTH differs between two identical graphs."""
    return {g: int(bindings(st.query(
        f"SELECT (COUNT(*) AS ?n) WHERE {{ GRAPH <{g}> {{ ?s ?p ?o }} }}"))[0]["n"])
        for g in st.public_graphs()}


# --- the split costs a reader nothing ----------------------------------------------------------

@pytest.mark.parametrize("world", WORLDS)
def test_an_ordinary_pattern_spans_every_public_graph(world):
    """A reader asks what the society knows and gets one answer, whichever graph holds it.

    `?agent ag:polls ?s . ?s a ag:Sensor` is the case in miniature: the first is the sovereign's
    and the second may be entailed, so the two live apart. Written inside a single `GRAPH` clause
    this returns NOTHING — silently, because an empty result is not an error. That is the trap
    the default graph exists to close, and it is why queries here name no graph at all.
    """
    st = _public(world)
    spanning = bindings(st.query(
        "SELECT ?agent WHERE { ?agent ag:polls ?s . ?s a ag:Sensor ; ag:senseMode ?m }"))
    assert spanning, "a pattern spanning the asserted/entailed split found nothing"

    narrowed = _in_graph(st, WORLD_GRAPH,
                         "?agent ag:polls ?s . ?s a ag:Sensor ; ag:senseMode ?m")
    assert len(narrowed) <= len(spanning)


def test_private_graphs_are_not_in_the_default_graph():
    """The default graph is PUBLIC knowledge, not everything. An agent's beliefs stay reachable
    only by naming their graph, which is what keeps a review's write boundary checkable."""
    from agent.ontology import beliefs_graph

    st = _public("society")
    genesis.birth(st, genesis.world_dir("society"), "fern")
    assert _in_graph(st, beliefs_graph("fern"), "?a ag:slowSleepS ?v")
    assert not bindings(st.query("SELECT * WHERE { ?a ag:slowSleepS ?v }"))


# --- the store says what each graph is, not just what it is called -----------------------------

@pytest.mark.parametrize("world", WORLDS)
def test_every_public_graph_accounts_for_itself(world):
    """A sixth graph cannot be silent.

    `ag:PublicGraphShape` refuses a described graph that says neither where it came from nor what
    made it — but a graph nobody described at all is not a `prov:Entity`, so no shape targets it.
    That silence is what this catches, by walking the public set rather than waiting to be told.
    """
    st = _public(world)
    described = {r["g"] for r in _in_graph(
        st, PROVENANCE_GRAPH,
        "?g a prov:Entity ; ?p ?o FILTER(?p IN (prov:wasDerivedFrom, prov:wasGeneratedBy))")}
    public = set(st.public_graphs())
    assert public <= described, (
        f"undescribed: {public - described} — add it to agora/provenance.py")


def test_the_graph_names_could_be_opaque_and_nothing_would_be_lost():
    """The test the meta-graph exists to pass.

    Rename all five to `g1`..`g5` and every query in this repository still works, because nothing
    parses a graph IRI — they are constants referenced by name. So the names cannot be where the
    knowledge lives, and before the meta-graph it was: in them, and in a comment beside them.

    Here the roles are recovered **without reading a single IRI's text**: what a file produced
    versus what an activity produced, and which activity. A reader who had never seen this
    codebase could ask the same questions.
    """
    st = _public("society")
    from_files = {r["g"] for r in _in_graph(
        st, PROVENANCE_GRAPH, "?g a prov:Entity ; prov:wasDerivedFrom ?f")}
    computed = {r["g"] for r in _in_graph(
        st, PROVENANCE_GRAPH,
        "?g a prov:Entity ; prov:wasGeneratedBy [ prov:wasAssociatedWith ?agent ] ."
        "?agent a prov:SoftwareAgent")}

    # Every public graph accounts for itself, one way or the other.
    assert from_files | computed == set(st.public_graphs())

    # And a machine made the computed ones, while a PERSON stands behind what was read from
    # files — recovered from the kind of agent the activity was associated with, not from a name.
    # The world graph is legitimately both: read from files, and those files ratified by someone.
    by_a_person = {r["g"] for r in _in_graph(
        st, PROVENANCE_GRAPH,
        "?g a prov:Entity ; prov:wasGeneratedBy [ prov:qualifiedAssociation [ "
        "prov:hadRole ?role ] ]")}
    assert by_a_person and not (by_a_person & computed), (
        "what a person ratified and what a program computed must be distinguishable")

    activities = {r["a"] for r in _in_graph(
        st, PROVENANCE_GRAPH, "?g a prov:Entity ; prov:wasGeneratedBy ?a")}
    assert len(activities) == 3, "ratification, derivation and closure are distinct"


def test_a_graph_that_explains_nothing_is_refused():
    """The shape, exercised. Without this the shape could be silently wrong and nothing would
    say so — a constitution nobody tests is a comment with extra syntax."""
    st = _public("society")
    st.update(f"""INSERT DATA {{ GRAPH <{PROVENANCE_GRAPH}> {{
        <http://example.org/agora/graph/mystery> a prov:Entity }} }}""")
    data = graph_from(st, *st.public_graphs(), PROVENANCE_GRAPH)
    ok, report = conforms(data)
    assert not ok and "mystery" in report


def test_a_sixth_public_graph_needs_no_python():
    """The test the discovery exists to pass.

    A graph IRI is an INSTANCE. Code that listed five of them was doing what rule 1 forbids
    everywhere else — and the cost was not theoretical: the same five were written out in
    `ontology.py`, again in `provenance.py`, and again by hand in the `USING` clauses of every
    rule of every capability, so a capability author maintained a copy of a registry.

    Here a graph is declared public in the vocabulary alone. Nothing is imported, nothing is
    edited, and it turns up in the default graph of an ordinary query.
    """
    st = _public("society")
    before = set(st.public_graphs())

    st.update(f"""INSERT DATA {{ GRAPH <{ONTOLOGY_GRAPH}> {{
        <http://example.org/agora/graph/sixth> a ag:PublicGraph }} }}""")
    st.update("""INSERT DATA { GRAPH <http://example.org/agora/graph/sixth> {
        ag:fern_agent ag:somethingNew "yes" } }""")

    assert set(st.public_graphs()) - before == {"http://example.org/agora/graph/sixth"}
    # And an unqualified pattern reads it, which is the whole point: a reader asks what the
    # society knows and never learns which graph the answer came from.
    assert bindings(st.query('SELECT ?v WHERE { ag:fern_agent ag:somethingNew ?v }'))


def test_a_graph_typed_privately_stays_out_of_the_default_graph():
    """Membership is by declaration, never by exclusion.

    The tempting inversion — public means "not one of the private kinds" — fails in the
    dangerous direction: a new private graph nobody remembered to exclude leaks into every
    query. Declared membership fails the safe way round, with a graph nobody typed simply
    invisible until someone says what it is.
    """
    st = _public("society")
    st.update("""INSERT DATA { GRAPH <http://example.org/agora/graph/private> {
        ag:fern_agent ag:aSecret "shh" } }""")
    assert "http://example.org/agora/graph/private" not in st.public_graphs()
    assert not bindings(st.query('SELECT ?v WHERE { ag:fern_agent ag:aSecret ?v }'))
    assert _in_graph(st, "http://example.org/agora/graph/private", "?s ag:aSecret ?v")


def test_provenance_is_not_in_the_default_graph():
    """Deliberately not an `ag:PublicGraph`, and the reason is use versus mention.

    These are statements ABOUT the graphs, not facts IN the world. Merged into the default graph
    they would answer open patterns that mean something else entirely — `?device a ?class`, which
    `agora-wokwi` really asks, would start returning activities — and every graph IRI would become
    a subject in a society that otherwise contains only things a society has.
    """
    st = _public("society")
    assert not bindings(st.query("SELECT * WHERE { ?s a prov:Activity }"))
    assert _in_graph(st, PROVENANCE_GRAPH, "?s a prov:Activity")


@pytest.mark.parametrize("world", WORLDS)
def test_a_file_is_identified_the_same_wherever_the_tree_sits(world):
    """`prov:wasDerivedFrom` wants an IRI, and an absolute path would bake one machine into the
    store — a world is at `/app/world/` in a container and `world/<name>/` on a host, so the same
    world would describe itself differently depending on where it was built."""
    derived = {r["f"] for r in _in_graph(
        _public(world), PROVENANCE_GRAPH, f"<{WORLD_GRAPH}> prov:wasDerivedFrom ?f")}
    assert derived
    for iri in derived:
        assert iri.startswith("http://example.org/agora/file/world/"), iri
        assert "/home/" not in iri and "/app/" not in iri


# --- sovereign is a role somebody held, not a kind of person -----------------------------------

@pytest.mark.parametrize("world", WORLDS)
def test_the_ratified_world_records_who_ratified_it_and_in_what_capacity(world):
    """`prov:agent` alone would say a user was involved. `prov:hadRole` says in what capacity —
    the only form that survives an installation having several users with different powers."""
    rows = _in_graph(_public(world), PROVENANCE_GRAPH, f"""
        <{WORLD_GRAPH}> prov:wasGeneratedBy ?act .
        ?act prov:qualifiedAssociation [ prov:agent ?user ; prov:hadRole ?role ] .""")
    assert rows, "the ratified graph names nobody"
    assert rows[0]["role"] == AG + "Sovereign"
    assert rows[0]["user"].startswith("http://example.org/agora/user/")


def test_there_is_no_sovereign_agent_only_a_sovereign_role():
    """The distinction the whole design turns on. `ag:Sovereign` is a `prov:Role`; if it were
    ever also typed as an agent, "who is the sovereign" would become a permanent property of a
    person rather than a fact about one ratification, and a second user could not exist."""
    st = _public("society")
    kinds = {r["t"] for r in bindings(st.query(f"SELECT ?t WHERE {{ <{AG}Sovereign> a ?t }}"))}
    assert "http://www.w3.org/ns/prov#Role" in kinds
    assert not {k for k in kinds if k.endswith(("Agent", "Person", "SoftwareAgent"))}


def test_the_world_references_a_user_and_declares_nothing_about_them():
    """A user is installation-level (AGENTS.md rule 3) and an agent is given only its world — so
    the URI is an identifier it never resolves, exactly as `ag:brokerHost` names a host it never
    introspects. Saying more here would be a world asserting facts about the installation."""
    st = _public("society")
    user = bindings(st.query(
        "SELECT ?u WHERE { ?w a ag:World ; prov:qualifiedAttribution [ prov:agent ?u ] }"))[0]["u"]
    said = bindings(st.query(f"SELECT ?p WHERE {{ <{user}> ?p ?o }}"))
    assert not said, f"the world declares {[r['p'] for r in said]} about a user it only references"


def test_the_world_states_the_capacity_and_the_loader_does_not_assume_it():
    """The role was briefly a literal in `provenance.py`, and that is not a detail.

    An installation has several users with different powers. With the capacity assumed, every
    user a world attributed became a sovereign on the way in — so a world could never say that
    one user OPERATES what another RATIFIED, and adding a second role would have meant editing
    code rather than a world.
    """
    from agent import provenance

    st = _public("society")
    user, role = provenance.attribution_of(st)
    assert role == AG + "Sovereign"
    # Copied, not invented: change what the world says and the description follows.
    assert f"prov:hadRole <{role}>" in provenance._turtle(
        genesis.world_dir("society"), (user, role))


def test_a_user_named_without_a_capacity_gets_no_association():
    """A bare `prov:wasAttributedTo` says who was involved and not in what capacity, and the
    capacity is the whole distinction. Silence is a better answer than a guess."""
    from agent import provenance

    st = _public("society")
    st.update(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?w prov:qualifiedAttribution ?a }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?w prov:wasAttributedTo <urn:someone> }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?w a ag:World ; prov:qualifiedAttribution ?a }} }}""")
    assert provenance.attribution_of(st) is None


# --- the guard that matters --------------------------------------------------------------------

@pytest.mark.parametrize("world", WORLDS)
def test_both_engines_derive_the_same_world(world):
    """pyoxigraph builds an agent's belief base; rdflib builds what the operator's tools read.
    They must agree about what every agent can do, and they have not always.

    **This caught a live one.** After the closure was materialised, `agent/ratified.py` still
    re-ran the derivation rules on rdflib — which had no closure of its own, so a device typed as
    a KIND of actuator was not observably an actuator there. `roster()` therefore stopped
    deriving `ag:Actuation` for the supplier, and `agora-compose` would have written a compose
    file with the signing keys silently unmounted: the supplier could no longer co-sign a dose,
    and every voucher redemption would have failed. Nothing noticed, because compose.yaml is
    committed and regenerating it is not a gate.

    The fix was to stop deriving twice — rdflib now reads what the store computed. This test is
    what would have caught it, and what will catch the next one.
    """
    st = _public(world)
    from_store = {(r["id"], r["cap"]) for r in bindings(st.query(
        "SELECT ?id ?cap WHERE { ?a a ag:Agent ; ag:localId ?id ; ag:hasCapability ?cap }"))}

    ds = ratified.dataset(world)
    from_rdflib = {(r["id"], r["cap"]) for r in ratified.rows(ds, f"""
        SELECT ?id ?cap WHERE {{
          ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{AG}hasCapability> ?cap }}""")}

    assert from_store == from_rdflib, (
        f"{world}: the two engines disagree about what agents can do — "
        f"only in the store: {from_store - from_rdflib}; "
        f"only in rdflib: {from_rdflib - from_store}")


# --- nobody should narrow a query back to one graph --------------------------------------------

_SOURCES = {
    "agent": sorted(p for p in Path(genesis.__file__).parent.rglob("*.py")),
    "onboarding": sorted(Path(genesis.__file__).parent.parent.glob("onboarding/*.py")),
}

# The graphs a SELECT must not single out, and who is allowed to anyway.
_SPLIT = (WORLD_GRAPH, WORLD_DERIVED_GRAPH, WORLD_ENTAILED_GRAPH,
          ONTOLOGY_GRAPH, ONTOLOGY_ENTAILED_GRAPH)
# inference.py writes the closure and must say where; genesis.py and validate.py name graphs to
# load, clear and flatten them, which is not reading across the split.
_MAY_NAME_A_GRAPH = {"inference.py", "genesis.py", "validate.py", "ontology.py", "ratified.py"}


@pytest.mark.parametrize("group", sorted(_SOURCES))
def test_every_source_group_is_still_found(group):
    """The guard on the guard, borrowed from test_store.py — moving a tree has twice emptied a
    glob and taken cases off a scan without failing anything."""
    assert _SOURCES[group], f"the {group} glob is stale and this guard checks nothing"


@pytest.mark.parametrize(
    "path", sorted(p for g in _SOURCES.values() for p in g), ids=lambda p: p.name)
def test_no_select_narrows_itself_to_one_public_graph(path):
    """A `SELECT` that wraps `GRAPH <…/world>` around its patterns is asking a narrower question
    than its author meant, and the way it fails is an empty result rather than an error.

    Updates are exempt and must name a graph: a `DELETE`/`INSERT` has to say what it writes to.
    Only string literals are read, so the prose explaining any of this cannot trip the scan —
    the same reason `test_inference.py` parses rather than greps.
    """
    if path.name in _MAY_NAME_A_GRAPH:
        pytest.skip("names graphs to write, load or flatten them, not to read across the split")

    tree = ast.parse(path.read_text())
    literals = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    for text in literals:
        if "SELECT" not in text.upper() or "GRAPH <" not in text:
            continue
        if any(w in text.upper() for w in ("INSERT", "DELETE")):
            continue
        for graph in _SPLIT:
            assert graph not in text, (
                f"{path.name}: a SELECT names <{graph}> and so reads only part of public "
                "knowledge. Drop the GRAPH clause — store.query already merges the five.")
