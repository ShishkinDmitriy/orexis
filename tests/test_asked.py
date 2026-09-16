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

from orexis_agent_deliberation import asked, effects
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
    """THE GATE. Every action this world loads has its OWN effect taken, and then every rule
    text is asked about the world that effect reached — once against that world materialised,
    which is what the search has always built, and once against it held as a diff. The two
    must answer identically.

    THE STEP IS THE ACTION'S OWN, and that is what this gate is for. Asked about a synthetic
    diff — a quad taken out of the readings by hand — the rewriting looked right on every rule
    in the tree while the search planned the dose and not the heating: a world nobody's rule
    would ever reach proves nothing about the worlds they do. Each action's construct and
    retraction make the world here, and every rule is asked about all of them, so the pairs
    are the ones a pass actually forms.

    IT RUNS PRODUCTION'S OWN REWRITING (`Imaginarium._asked`), never a copy of it: a gate that
    re-implements what it checks agrees with itself and with nothing else.
    """
    from orexis_agent_deliberation.imaginarium import Imaginarium
    from orexis_agent_progression.store import bind as bind_text

    agent, st = _agent(monkeypatch, world, agent_id, readings)
    im = Imaginarium(agent.beliefs, beliefs_graph(agent_id), STATE_GRAPH,
                     *agent.beliefs.recorded_graphs())
    binds = dict(me=agent.me.uri, subject=agent.me.acts_for or "urn:nobody",
                 about="urn:nothing", via="urn:nothing", want="urn:nothing",
                 beliefs=beliefs_graph(agent_id), litres=0.0, lands=LANDS,
                 claim=Raw('"urn:nobody"'), wants=Raw("(<urn:nothing> <urn:nothing>)"))
    rules = {}
    for row in bindings(agent.beliefs.query("SELECT ?a WHERE { ?a a orexis:Action }")):
        rule = effects.rule_for(agent.beliefs, row["a"])
        if rule is not None:
            rules[row["a"]] = rule

    #  ONE WORLD PER ACTION, reached by that action's own effect — plus the root, so a rule is
    #  also held to the world a pass starts in.
    worlds = {"the present": STATE_GRAPH}
    for action, rule in rules.items():
        added, retracted = effects.apply(im, action, when=None, state=STATE_GRAPH, **binds)
        if not added and not retracted:
            continue
        worlds[action.rsplit("#")[-1]] = im.reached(
            STATE_GRAPH, (_Step(action),), added, retracted)

    checked, refused, wrong = 0, set(), []
    for where, node in worlds.items():
        for action, rule in rules.items():
            for kind in ("available", "construct", "retracts"):
                text = rule.get(kind)
                if not text:
                    continue
                bound = bind_text(text, state=node, **binds)
                rewritten = im._asked(bound)
                if rewritten is bound:
                    #  The present is not a diff, so nothing is rewritten there and there is
                    #  nothing to hold. Anywhere else, an unchanged text is a refusal.
                    if node is not STATE_GRAPH:
                        refused.add(f"{action.rsplit('#')[-1]}.{kind}")
                    continue
                im.world(node)                       # today's road: the world, every triple
                graphs = [*im._store.public_graphs(), *im._store.recorded_graphs()]
                if _run(im, bound, graphs) != _run(im, rewritten, graphs):
                    wrong.append(f"{action.rsplit('#')[-1]}.{kind} in the world {where} reached")
                checked += 1
    assert checked, f"{world}: no rule was checked — the gate is measuring nothing"
    with capsys.disabled():
        print(f"\n  {world}: {len(worlds)} worlds x {len(rules)} actions, {checked} asks held, "
              f"{len(refused)} texts refused")
        for why in sorted(refused):
            print(f"      refused  {why}")
    assert not wrong, "answered differently when the world is a diff:\n  " + "\n  ".join(wrong)


class _Step:
    """What `reached` names a world by — an action and a lever, as an affordance row has."""

    def __init__(self, action):
        self.action, self.via, self.about = action, "urn:nothing", None


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
