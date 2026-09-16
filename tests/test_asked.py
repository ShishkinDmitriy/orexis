"""A rule asked about a world it does not name (#666) — held to the world it used to name.

The gate before the mechanism. Every action in the tree, in every world that loads it, is run
twice: once against a MATERIALISED world, which is what the search has always built, and once
against the same world held as the node's ADDS and RETRACTS with its patterns rewritten. The
two must answer the same thing, triple for triple, or the rewriting is wrong — and a rewriting
that is wrong returns an empty result rather than an error, which is the failure this whole
area keeps producing.

REFUSING IS NOT FAILING. A text the scanner cannot normalise raises `Refused` and the caller
materialises, which is today's behaviour exactly. So the assertions here are about texts it
ACCEPTS; what it refuses is reported, because a refusal is a performance fact somebody should
be able to see rather than a silent fallback.
"""

from __future__ import annotations

import pytest
import pyoxigraph as ox

from orexis_agent_deliberation import asked, effects, relevance
from orexis_agent_deliberation.asked import Refused
from orexis_agent_progression.ontology import STATE_GRAPH, beliefs_graph
from orexis_agent_progression.store import NAMESPACES, Raw, bindings

from conftest import genesis_store

ADDS, RETRACTS = "urn:asked:adds", "urn:asked:retracts"
LANDS = Raw('"2026-09-16T12:00:00+00:00"^^xsd:dateTime')
GONE = ox.NamedNode("urn:orexis:gone")


# --- the scanner, on its own -------------------------------------------------------------

def test_a_statement_expands_its_predicate_object_list():
    """`;` and `,` are abbreviation, and a pattern is what a rewrite acts on."""
    triples = asked._triples("?o sosa:hasFeatureOfInterest ?s ; sosa:observedProperty ?p, ?q .")
    assert triples == [("?o", "sosa:hasFeatureOfInterest", "?s"),
                       ("?o", "sosa:observedProperty", "?p"),
                       ("?o", "sosa:observedProperty", "?q")]


def test_a_literal_holding_a_separator_is_not_a_separator():
    """The scanner is blind inside quotes and IRIs — which is what makes it a scanner rather
    than a chain of replacements (#500)."""
    triples = asked._triples('?x rdfs:label "a ; b , c ." ; skos:note <urn:a;b> .')
    assert triples == [("?x", "rdfs:label", '"a ; b , c ."'), ("?x", "skos:note", "<urn:a;b>")]


@pytest.mark.parametrize("body,why", [
    ("?x ?p [ a ?c ] .", "a blank node property list"),
    ("?x rdfs:label .", "not a triple"),
])
def test_what_the_scanner_will_not_say_it_refuses(body, why):
    """Loudly, and to the caller, which materialises. Silence here would be a world read in
    half."""
    with pytest.raises(Refused):
        asked._triples(body)


def test_a_property_path_is_refused_rather_than_rewritten():
    """A closure cannot alternate between two graphs, and no rewriting of the pattern gives it
    one — the imaginarium materialises that predicate instead."""
    with pytest.raises(Refused):
        asked.resolved("?s (hanoi:on)+ ?about .", ADDS, RETRACTS, {"hanoi:on"})


def test_a_pattern_whose_predicate_cannot_move_is_left_alone():
    """Rewriting what cannot differ costs a union and buys nothing: measured, rewriting every
    pattern runs 1.32-1.72x where rewriting what moves runs 1.08-1.22x."""
    out = asked.resolved("?me orexis:actsFor ?s .", ADDS, RETRACTS, {"sosa:observedProperty"})
    assert "UNION" not in out and "orexis:actsFor" in out


# --- and against every rule the tree ships -----------------------------------------------

def _worlds():
    return [("loner", "gardener", {("zz", "http://example.org/orexis/water#SoilMoisture"): 0.04}),
            ("hanoi", "hanoi", None),
            ("greenhouse", "grower",
             {("bed", "http://example.org/orexis/water#SoilMoisture"): 0.20,
              ("bed", "http://example.org/orexis/water#AirTemperature"): 12.0,
              ("outside", "http://example.org/orexis/water#AirTemperature"): 21.0,
              ("water_butt", "http://example.org/orexis/water#StoredLitres"): 15.0})]


def _agent(monkeypatch, world, agent_id, readings):
    from agent import genesis, runtime
    monkeypatch.setenv("OREXIS_WORLD", world)
    monkeypatch.setenv("INFLUX_BUCKET", f"test-{world}")
    monkeypatch.setenv("INFLUX_TOKEN", "t")
    st = genesis_store(readings, world=world)
    if world == "hanoi":
        H, W = "http://example.org/orexis/hanoi#", "http://example.org/orexis/world/hanoi#"
        below, triples = H + "PegA", []
        for d in reversed(["disk_1", "disk_2", "disk_3"]):
            triples.append(f"<{W}{d}> <{H}on> <{below}>"); below = W + d
        st.update("INSERT DATA { GRAPH <%s> { %s } }" % (STATE_GRAPH, " . ".join(triples) + " . "))
    genesis.classify_own_graphs(st, agent_id)
    return runtime.Agent(agent_id, st=st), st


@pytest.mark.parametrize("world,agent_id,readings", _worlds())
def test_every_rule_answers_the_same_whether_the_world_is_materialised_or_a_diff(
        monkeypatch, world, agent_id, readings, capsys):
    """THE GATE. For every action this world loads, the same rule text run against a world the
    imaginarium materialised and against that world held as a diff must answer identically."""
    from orexis_agent_deliberation.imaginarium import Imaginarium

    agent, st = _agent(monkeypatch, world, agent_id, readings)
    im = Imaginarium(agent.beliefs, beliefs_graph(agent_id), STATE_GRAPH,
                     *agent.beliefs.recorded_graphs())
    moves = _moves(agent.beliefs)
    binds = dict(me=agent.me.uri, subject=agent.me.acts_for or "urn:nobody",
                 about="urn:nothing", via="urn:nothing", want="urn:nothing",
                 beliefs=beliefs_graph(agent_id), litres=0.0, lands=LANDS,
                 claim=Raw('"urn:nobody"'),
                 #  The VALUES block an availability select takes, as the afforder fills it:
                 #  one (want, about) pair. What it binds does not matter here — the two runs
                 #  are handed the same one, and what is being compared is whether the world
                 #  being a diff changes the answer.
                 wants=Raw("(<urn:nothing> <urn:nothing>)"))

    checked, refused = 0, []
    for row in bindings(agent.beliefs.query("SELECT ?a WHERE { ?a a orexis:Action }")):
        rule = effects.rule_for(agent.beliefs, row["a"])
        if rule is None:
            continue
        for kind in ("available", "construct", "retracts"):
            text = rule.get(kind)
            if not text:
                continue
            try:
                pair = _both(im, text, binds, moves)
            except Refused as why:
                refused.append(f"{row['a'].rsplit('#')[-1]}.{kind}: {why}")
                continue
            named, unnamed = pair
            assert named == unnamed, \
                f"{row['a']} {kind} answers differently when the world is a diff"
            checked += 1
    assert checked, f"{world}: no rule was checked — the gate is measuring nothing"
    with capsys.disabled():
        print(f"\n  {world}: {checked} texts held to parity, {len(refused)} refused")
        for why in refused:
            print(f"      refused  {why}")


def _moves(store) -> set:
    """The predicates some action writes, spelled as a rule spells them."""
    out = set()
    for iri in relevance.actions_of(store.query):
        rule = effects.rule_for(store, iri)
        if rule is None:
            continue
        for kind in ("construct", "retracts"):
            written = relevance.writes_of_construct(rule[kind]) if rule.get(kind) else None
            if written is relevance.ANYTHING:
                return _ANY
            out |= {str(p) for p in (written or ())}
    #  Both spellings, since a rule names a predicate either way and this resolves no prefix.
    return out | {_short(p) for p in out}


class _Any(set):
    def __contains__(self, item):        # every predicate moves: the safe direction
        return True


_ANY = _Any()


def _short(iri: str) -> str:
    for prefix, ns in NAMESPACES.items():
        if iri.startswith(str(ns)):
            return f"{prefix}:{iri[len(str(ns)):]}"
    return iri


def _both(im, text: str, binds: dict, moves) -> tuple:
    """The rule's answer against a materialised world, and against the same world as a diff."""
    from orexis_agent_progression.store import bind as bind_text

    #  A step's own diff, taken against the world as it stands, is what a node holds.
    added, retracted = [], []
    for quad in list(im.quads(STATE_GRAPH))[:1]:
        retracted.append(ox.Triple(quad.subject, quad.predicate, quad.object))
    world = "urn:asked:world"
    im._store.clear_graph(world); im._store.clear_graph(ADDS); im._store.clear_graph(RETRACTS)
    im._store.update(f"INSERT {{ GRAPH <{world}> {{ ?s ?p ?o }} }} WHERE "
                     f"{{ GRAPH <{STATE_GRAPH}> {{ ?s ?p ?o }} }}", forget=False)
    im._store.remove_quads([ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(world))
                            for t in retracted], forget=False)
    im._store.add_quads([ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(ADDS))
                         for t in added], forget=False)
    im._store.add_quads({ox.Quad(t.subject, t.predicate, GONE, ox.NamedNode(RETRACTS))
                         for t in retracted}, forget=False)

    #  TODAY: the default graph is public knowledge and the agent's own — the BASE's readings
    #  among them — and `GRAPH $state` names the materialised world. That is `Store.construct`.
    everything = [*im._store.public_graphs(), *im._store.recorded_graphs()]
    named = _run(im, bind_text(text, state=world, **binds),
                 [g for g in everything if g != STATE_GRAPH] + [world])
    #  PROPOSED: the same default graph with the BASE's readings in it, and the patterns doing
    #  the rest. Nothing names a world.
    body, head = _where(text)
    rewritten = head + "{" + asked.resolved(body, ADDS, RETRACTS, moves) + "}"
    unnamed = _run(im, bind_text(rewritten, state=STATE_GRAPH, **binds), everything)
    return named, unnamed


def _where(text: str) -> tuple[str, str]:
    """A query split into everything up to its WHERE's brace, and the body inside it."""
    i = text.index("WHERE"); j = text.index("{", i); depth = 0
    for k in range(j, len(text)):
        depth += (text[k] == "{") - (text[k] == "}")
        if depth == 0:
            return text[j + 1:k], text[:j]
    raise Refused("unbalanced WHERE")


def _run(im, query: str, graphs: list) -> set:
    """A rule's answer as a comparable set — blank node identity dropped, as a diff drops it."""
    out = im._store._store.query(query, prefixes=NAMESPACES,
                                 default_graph=[ox.NamedNode(g) for g in graphs])
    names = list(getattr(out, "variables", []) or [])
    rows = list(out)
    if rows and hasattr(rows[0], "subject"):                       # a CONSTRUCT's triples
        return {(_t(r.subject), _t(r.predicate), _t(r.object)) for r in rows}
    return {tuple((str(v), _t(r[v])) for v in names if r[v] is not None) for r in rows}


def _t(term) -> str:
    return "_:b" if isinstance(term, ox.BlankNode) else str(term)
