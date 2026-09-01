"""The SHALL NOT, end to end (#468): a world ratifies a state to avoid, the agent derives a
want met by absence, and the search steers out of it through the ordinary achiever road."""

import shutil

import pytest

from conftest import build_agent

NAUGHTY = "http://example.org/orexis/world/loner#naughty_state"
GARDENER = "http://example.org/orexis/world/loner#gardener"
WANT = "http://example.org/orexis#aversion.gardener.naughty_state"
STATE_GRAPH = "http://example.org/orexis/graph/sensed"
MARKER = "<urn:naughty> <urn:p> <urn:o>"


def _avoiding_world(tmp_path):
    """The loner world, plus one ratified avoidance: never let the naughty marker stand."""
    from agent import genesis

    dst = tmp_path / "avoiding"
    shutil.copytree(genesis.world_dir("loner"), dst)
    with open(dst / "world.ttl", "a") as f:
        f.write(f'''

# --- test fixture: a ratified avoidance (#468) ---
<{GARDENER}> <http://example.org/orexis/aversion#avoids> <{NAUGHTY}> .
<{NAUGHTY}> <http://www.w3.org/ns/shacl#select>
    """SELECT (1 AS ?entered) WHERE {{ GRAPH $state {{ {MARKER} }} }}""" ;
    <http://www.w3.org/2000/01/rdf-schema#comment>
    "never let the naughty marker stand — the sentence somebody ratified" .
''')
    return dst


def _gardener(tmp_path, monkeypatch):
    from agent import genesis
    from orexis_agent_progression.store import Store

    st = Store()
    genesis.refresh_public(st, _avoiding_world(tmp_path))
    genesis.birth(st, tmp_path / "avoiding", "gardener")
    return build_agent("gardener", st, monkeypatch), st


def _aversion_row(agent):
    return next(g for g in agent.pursuing() if g.uri == WANT)


def test_a_ratified_avoidance_grants_the_capability_and_raises_the_want(tmp_path, monkeypatch):
    """The statement is the premise, the grant and the want's content in one: stating it
    composes the module, derives the want, and the want's urgency is the pattern's own
    verdict — held at zero, entered at one — which is stage one working: an entered avoided
    state competes for attention in the common currency, and a held one asks for none."""
    agent, st = _gardener(tmp_path, monkeypatch)

    assert st.query(f"ASK {{ <{GARDENER}> <http://example.org/orexis#hasCapability> "
                    f"<http://example.org/orexis/aversion#Heeding> }}")["boolean"], \
        "the statement grants Heeding — nothing is declared by hand"
    assert any(m.name == "aversion" for m in agent.modules), "and the module composes"

    held = _aversion_row(agent)
    assert held.urgency == 0.0 and held.state == "met", \
        "the marker is absent, so the want is met and asks for no attention"

    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")
    entered = _aversion_row(agent)
    assert entered.urgency == 1.0 and entered.state == "entered", \
        "the marker standing is the pattern's own verdict, binary on purpose"


def test_the_search_exits_an_avoided_state_by_the_cheapest_road(tmp_path, monkeypatch):
    """Steering out is the ordinary achiever road: a candidate world where the pattern no
    longer binds is MET by the same one text, joins the achievers, and cost decides — two
    levers that both clear the marker differ only in their declared figure, and the cheaper
    must be the plan from either menu order."""
    from assembly import loader
    from orexis_agent_deliberation.planner import Planner

    def toy(name, cost):
        return f"""
toy:{name} a orexis:Action ;
    orexis:available \"\"\"SELECT ?want ?via WHERE {{ VALUES (?want ?about) {{ $wants }} BIND($me AS ?via) }}\"\"\" ;
    orexis:costs \"\"\"SELECT ?cost WHERE {{ BIND({cost} AS ?cost) }}\"\"\" ;
    orexis:retracts \"\"\"CONSTRUCT {{ <urn:naughty> ?p ?o }} WHERE {{
            GRAPH $state {{ <urn:naughty> ?p ?o }} }}\"\"\" ;
    sh:construct "CONSTRUCT {{}} WHERE {{}}" .
"""

    toys = tmp_path / "actions.ttl"
    toys.write_text("@prefix orexis: <http://example.org/orexis#> .\n"
                    "@prefix toy: <urn:toy#> .\n"
                    "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
                    + toy("Scour", 5.0) + toy("Cleanse", 3.0))
    real = loader.action_files()
    monkeypatch.setattr(loader, "action_files", lambda: real + (toys,))

    agent, st = _gardener(tmp_path, monkeypatch)
    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")

    plan = Planner(agent, agent.me).plan(_aversion_row(agent))
    assert plan.outcome == "satisfied" and plan.steps, \
        "clearing the marker is achievable in one step, and the pass must say so"
    assert plan.steps[0].act.action == "urn:toy#Cleanse", \
        "two roads out of the avoided state differ only in cost, and the cheaper wins"


def test_an_avoided_state_nothing_can_exit_stays_hot_and_says_so(tmp_path, monkeypatch):
    """Soft means soft: no lever clears the marker, so the search proposes nothing — the
    honest NOTHING, not a refusal — and the want stays entered at full heat, visible to the
    sovereign's ask, which is the evidence-producing posture: an aversion nobody can serve
    is a finding, never a silent shrug."""
    from orexis_agent_deliberation.planner import Planner

    agent, st = _gardener(tmp_path, monkeypatch)
    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")

    plan = Planner(agent, agent.me).plan(_aversion_row(agent))
    assert plan.outcome == "no candidate" and not plan.steps, \
        "no lever points at the avoided state — equip me, said honestly"
    assert _aversion_row(agent).urgency == 1.0, "and the want stays hot rather than shrugged off"


MOISTURE = "http://example.org/orexis/water#SoilMoisture"
LAW = f'''

# --- test fixture: the hard MUST NOT — law, not a want ---
<http://example.org/orexis/world/loner#no_naughty_law>
    a <http://www.w3.org/ns/shacl#NodeShape> ;
    <http://www.w3.org/ns/shacl#targetNode> <{GARDENER}> ;
    <http://www.w3.org/ns/shacl#severity> <http://www.w3.org/ns/shacl#Violation> ;
    <http://www.w3.org/ns/shacl#sparql> [
        <http://www.w3.org/ns/shacl#message> "the naughty marker may not stand — ratified as law" ;
        <http://www.w3.org/ns/shacl#select> """SELECT $this WHERE {{ {MARKER} }}""" ] .
'''


def _lawful_gardener(tmp_path, monkeypatch, toys_text):
    from assembly import loader
    from agent import genesis
    from orexis_agent_progression.store import Store

    toys = tmp_path / "actions.ttl"
    toys.write_text(toys_text)
    real = loader.action_files()
    monkeypatch.setattr(loader, "action_files", lambda: real + (toys,))

    dst = _avoiding_world(tmp_path)
    with open(dst / "world.ttl", "a") as f:
        f.write(LAW)
    st = Store()
    genesis.refresh_public(st, dst)
    genesis.birth(st, dst, "gardener")
    return build_agent("gardener", st, monkeypatch), st


def _toy_pair():
    """The tempting lever predicts the aim exactly AND plants the marker; the honest one
    predicts a touch worse and stays clean. The tempting one is cheaper too, so without the
    law it wins on BOTH ranking axes — only the pruning can explain an honest plan."""
    def toy(name, cost, value, mark):
        marked = "<urn:naughty> <urn:p> <urn:o> ." if mark else ""
        return f'''
toy:{name} a orexis:Action ;
    orexis:available """SELECT ?want ?via WHERE {{ VALUES (?want ?about) {{ $wants }} BIND($me AS ?via) }}""" ;
    orexis:costs """SELECT ?cost WHERE {{ BIND({cost} AS ?cost) }}""" ;
    sh:construct """CONSTRUCT {{
            ?obs a <http://www.w3.org/ns/sosa/Observation> ;
                 <http://www.w3.org/ns/sosa/hasFeatureOfInterest> $subject ;
                 <http://www.w3.org/ns/sosa/observedProperty> $about ;
                 <http://www.w3.org/ns/sosa/resultTime> ?now ;
                 <http://www.w3.org/ns/sosa/hasSimpleResult> {value} .
            {marked}
        }} WHERE {{ BIND(BNODE() AS ?obs) BIND(NOW() AS ?now) }}""" .
'''
    return ("@prefix orexis: <http://example.org/orexis#> .\n"
            "@prefix toy: <urn:toy#> .\n"
            "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
            + toy("Tempting", 1.0, 0.18, True) + toy("Honest", 2.0, 0.16, False))


def test_the_law_prunes_at_expansion_and_the_next_legal_plan_wins(tmp_path, monkeypatch):
    """Item 4, ruled and built: a valid plan contains no state that NEWLY matches a
    violation-severity shape, checked at EXPANSION — the tempting candidate (better urgency,
    lower cost, plants the marker) is discarded before the met-test can crown it, and the
    next legal plan wins by construction rather than by fallback code."""
    from orexis_agent_deliberation.planner import Planner

    agent, st = _lawful_gardener(tmp_path, monkeypatch, _toy_pair())
    stake = next(g for g in agent.pursuing()
                 #  the REGION want, not the freshness one — both are about moisture, and the
                 #  epistemic twin is achieved by Observe, which is not what this test is for
                 if not g.is_epistemic
                 and getattr(g, "observed_property", None) == MOISTURE)
    plan = Planner(agent, agent.me).plan(stake)

    assert plan.steps, "the stake is achievable — one lever is legal"
    assert plan.steps[0].act.action == "urn:toy#Honest", \
        "the tempting road is better on BOTH ranking axes and still may not be taken: " \
        "the law prunes it at expansion, and the honest plan wins with no fallback"


def test_an_agent_already_inside_the_forbidden_state_keeps_its_exit(tmp_path, monkeypatch):
    """Never-NEWLY-enter, the clause that makes the hard gate safe: the base already stands
    in the forbidden state, its violation is not news, and the exit plan must survive the
    pruning — or the agent that most needs a plan is the one refused every one. The same
    argument that made the envelope a warning at the gates, honoured from the planner's
    side."""
    from orexis_agent_deliberation.planner import Planner

    exit_toy = ("@prefix orexis: <http://example.org/orexis#> .\n"
                "@prefix toy: <urn:toy#> .\n"
                "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
                '''
toy:Exit a orexis:Action ;
    orexis:available """SELECT ?want ?via WHERE { VALUES (?want ?about) { $wants } BIND($me AS ?via) }""" ;
    orexis:retracts """CONSTRUCT { <urn:naughty> ?p ?o } WHERE {
            GRAPH $state { <urn:naughty> ?p ?o } }""" ;
    sh:construct "CONSTRUCT {} WHERE {}" .
''')
    agent, st = _lawful_gardener(tmp_path, monkeypatch, exit_toy)
    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")

    plan = Planner(agent, agent.me).plan(_aversion_row(agent))
    assert plan.outcome == "satisfied" and plan.steps, \
        "the recovery must be plannable from inside the forbidden state"
    assert plan.steps[0].act.action == "urn:toy#Exit", "and it is the exit itself"
