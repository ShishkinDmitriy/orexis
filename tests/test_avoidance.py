"""A want met by absence, end to end (#468, rebuilt on the sovereign's ruling): the world
ratifies the DESIRE itself in the asserted block — no capability, no derivation — its
`orexis:unmetWhen` points at the avoided pattern, the kernel lifts it into pursuit and
judges it binary, and the search steers out through the ordinary achiever path. Beside it,
the law: a ratified sh:Violation shape pruned at expansion, never-newly-enter."""

import shutil

import pytest

from conftest import build_agent

GARDENER = "http://example.org/orexis/world/loner#gardener"
WANT = "http://example.org/orexis/world/loner#never_naughty"
PATTERN = "http://example.org/orexis/world/loner#naughty_state"
ASSERTED = "http://example.org/orexis/graph/desire/asserted"
STATE_GRAPH = "http://example.org/orexis/graph/sensed"
MARKER = "<urn:naughty> <urn:p> <urn:o>"
MOISTURE = "http://example.org/orexis/water#SoilMoisture"


def _avoiding_world(tmp_path, both=False, shaped=False):
    """The loner world plus one ratified avoidance — the desire authored DIRECTLY, which is
    the whole point of the rebuild: what the sovereign ratifies is the want, not a statement
    something else expands.

    TWO AUTHORED FORMS of the avoided state (#499), and every behaviour below holds for
    both: a select whose rows mean entered, or a SHAPE describing the state — targeted on
    the marker node, conforming exactly when the marker stands — which the kernel compiles
    into that select. The want, and its polarity, are the same either way."""
    from agent import genesis

    dst = tmp_path / "avoiding"
    shutil.copytree(genesis.world_dir("loner"), dst)
    met_too = (f"<{WANT}> <http://example.org/orexis#metWhen> <{PATTERN}> .\n  "
               if both else "")
    avoided = (f'''<{PATTERN}> a <http://www.w3.org/ns/shacl#NodeShape> ;
      <http://www.w3.org/ns/shacl#targetNode> <urn:naughty> ;
      <http://www.w3.org/ns/shacl#property> [
          <http://www.w3.org/ns/shacl#path> <urn:p> ;
          <http://www.w3.org/ns/shacl#hasValue> <urn:o> ] .'''
               if shaped else
               f'''<{PATTERN}> <http://www.w3.org/ns/shacl#select>
      """SELECT (1 AS ?entered) WHERE {{ {MARKER} }}""" .''')
    (dst / "desire.ttl").write_text(f'''GRAPH <{ASSERTED}> {{
  <{GARDENER}> <http://example.org/orexis#holds> <{WANT}> .
  <{WANT}> a <http://example.org/orexis#Desire> ;
      <http://www.w3.org/2000/01/rdf-schema#label>
          "never let the naughty marker stand — the sentence somebody ratified" ;
      <http://example.org/orexis#unmetWhen> <{PATTERN}> .
  {met_too}{avoided}
}}
''')
    return dst


def _gardener(tmp_path, monkeypatch, world=None, shaped=False):
    from agent import genesis
    from orexis_agent_progression.store import Store

    dst = world or _avoiding_world(tmp_path, shaped=shaped)
    st = Store()
    genesis.refresh_public(st, dst)
    genesis.birth(st, dst, "gardener")
    return build_agent("gardener", st, monkeypatch), st


def _avoidance_row(agent):
    return next(g for g in agent.considering() if g.uri == WANT)


@pytest.mark.parametrize("shaped", [False, True], ids=["select", "shape"])
def test_a_ratified_avoidance_is_pursued_with_no_capability_in_the_room(tmp_path, monkeypatch, shaped):
    """The rebuild's whole claim: the want is pure ratified data, so no module exists for it
    and none is needed — the KERNEL lifts it into pursuit, because wanting is the kernel's —
    and its urgency is the pattern's own verdict, binary: held at zero, entered at one."""
    agent, st = _gardener(tmp_path, monkeypatch, shaped=shaped)

    assert not any(m.name == "aversion" for m in agent.modules), \
        "no capability composes for pure ratified data — that is the ruling, held"

    held = _avoidance_row(agent)
    assert held.state == "met", \
        "the marker is absent, so the want is met and asks for no attention"

    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")
    entered = _avoidance_row(agent)
    assert entered.state == "unmet", \
        "the marker standing is the pattern's own verdict"


@pytest.mark.parametrize("shaped", [False, True], ids=["select", "shape"])
def test_the_search_exits_an_avoided_state_by_the_cheapest_path(tmp_path, monkeypatch, shaped):
    """Steering out is the ordinary achiever path: a candidate world where the pattern no
    longer binds is MET by the same one text on the same one engine, joins the achievers,
    and cost decides between two exits."""
    from assembly import loader
    from orexis_agent_deliberation.planner import Planner

    def toy(name, cost):
        return f'''
toy:{name} a orexis:Action ;
    orexis:takes orexis:about, <urn:toy#lever> ;
    orexis:available """SELECT ?want ?about ?lever WHERE {{ VALUES (?want ?about) {{ $wants }} BIND($me AS ?lever) }}""" ;
    orexis:costs """SELECT ?cost WHERE {{ BIND({cost} AS ?cost) }}""" ;
    orexis:retracts """CONSTRUCT {{ <urn:naughty> ?p ?o }} WHERE {{
            <urn:naughty> ?p ?o }}""" ;
    sh:construct "CONSTRUCT {{}} WHERE {{}}" .
'''
    toys = tmp_path / "actions.ttl"
    toys.write_text("@prefix orexis: <http://example.org/orexis#> .\n"
                    "@prefix toy: <urn:toy#> .\n"
                    "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
                    + toy("Scour", 5.0) + toy("Cleanse", 3.0))
    #  WITHOUT THE DOSE (#579): the real dose is free and declares the region reached, so
    #  beside it no toy is ever the cheapest achiever — a tempting lever dearer than a free
    #  one is dropped before it is simulated, and a world never forked is never refused. The
    #  law is the thing under test and the toys are its levers; the other actions stay, since
    #  the world's bridges promise facts of theirs.
    real = tuple(p for p in loader.action_files() if "actuation" not in str(p))
    monkeypatch.setattr(loader, "action_files", lambda: real + (toys,))

    agent, st = _gardener(tmp_path, monkeypatch, shaped=shaped)
    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")

    plan = Planner(agent, agent.me).plan(_avoidance_row(agent))
    assert plan.outcome == "satisfied" and plan.steps, \
        "clearing the marker is achievable in one step, and the pass must say so"
    assert plan.steps[0].action == "urn:toy#Cleanse", \
        "two paths out differ only in cost, and the cheaper wins"


@pytest.mark.parametrize("shaped", [False, True], ids=["select", "shape"])
def test_an_avoided_state_nothing_can_exit_stays_hot_and_says_so(tmp_path, monkeypatch, shaped):
    """Soft means soft: nothing on the menu clears the marker, the search proposes nothing,
    and the want stays entered at full heat, visible to the ask. The outcome is NOTHING —
    equip me: no lever the gardener holds writes what the aversion reads, so none is
    simulated, and "my levers do not reach it" is what NOTHING says. (This read NOT_BETTER
    while relevance took every reading-replacing lever for writing anything and weighed the
    pump against a marker it could never touch; #554 made relevance read the retract as what
    it is, and the answer sharpened with it.)"""
    from orexis_agent_deliberation.planner import Planner

    agent, st = _gardener(tmp_path, monkeypatch, shaped=shaped)
    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")

    plan = Planner(agent, agent.me).plan(_avoidance_row(agent))
    assert plan.outcome == "no candidate" and not plan.steps, \
        "no lever writes what the aversion reads — said as what it is"
    assert _avoidance_row(agent).state == "unmet", "and the want stays unmet, never shrugged off"


def test_the_shape_form_agrees_with_the_judge(tmp_path, monkeypatch):
    """Parity for the negative twin, as `tests/test_violation.py` holds it for the positive
    one: the avoided state as a shape, judged by rudof on the same world — conforming is
    entered — beside the kernel's compiled conformance select, held and entered alike."""
    import rdflib

    from orexis_agent_deliberation.conformance import judge
    from orexis_agent_deliberation.planner import Planner

    SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    agent, st = _gardener(tmp_path, monkeypatch, shaped=True)
    seen = set()
    for standing in (False, True):
        if standing:
            st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")
        want = _avoidance_row(agent)
        p = Planner(agent, agent.me)
        node = p._begin(want)
        assert "FILTER EXISTS" in p._compiled.unmet, "compiled to the CONFORMANCE select"
        shape = p._compiled.base.cbd(rdflib.URIRef(PATTERN))
        results, _ = judge(p._border(node), shape)
        conforms = not list(results.subjects(rdflib.RDF.type, SH.ValidationResult))
        assert conforms == standing, "the judge says the marker conforms exactly when it stands"
        assert (want.state == "unmet") == conforms, \
            f"and the kernel's verdict follows: {want.state} with the judge conforming={conforms}"
        seen.add(conforms)
    assert seen == {True, False}


def test_a_want_saying_met_and_unmet_at_once_is_refused(tmp_path, monkeypatch):
    """The never-both gate: two verdicts on one want is a want two readers disagree about,
    and orexis:MetTestShape refuses it at validation rather than letting the disagreement
    surface at 3am as a planner and a row answering differently."""
    import rdflib

    from agent.validate import conforms

    data = rdflib.Graph()
    data.parse(data=f'''
@prefix orexis: <http://example.org/orexis#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
<{GARDENER}> orexis:holds <{WANT}> .
<{WANT}> a orexis:Desire ;
    orexis:metWhen <{PATTERN}> ;
    orexis:unmetWhen <{PATTERN}> .
<{PATTERN}> sh:select """SELECT (1 AS ?entered) WHERE {{ {MARKER} }}""" .
''', format="turtle")
    ok, report = conforms(data)
    assert not ok, "a want carrying both met-tests must be refused"
    assert "never both" in report, "and refused for the reason the shape states"


# --- the law beside it: pruned at expansion, never-newly-enter ---------------------------

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


def _toy_pair(tempting_cost: float = 1.0, honest_cost: float = 2.0):
    """The tempting lever predicts the aim exactly AND plants the marker; the honest one
    predicts a touch worse and stays clean — and is dearer, so without the law the tempting
    one wins on BOTH ranking axes. Only the pruning can explain an honest plan."""
    def toy(name, cost, value, mark):
        marked = "<urn:naughty> <urn:p> <urn:o> ." if mark else ""
        return f'''
toy:{name} a orexis:Action ;
    orexis:takes orexis:about, <urn:toy#lever> ;
    orexis:available """SELECT ?want ?about ?lever WHERE {{ VALUES (?want ?about) {{ $wants }} BIND($me AS ?lever) }}""" ;
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
            + toy("Tempting", tempting_cost, 0.18, True) + toy("Honest", honest_cost, 0.16, False))


def _lawful_gardener(tmp_path, monkeypatch, toys_text):
    from assembly import loader
    from agent import genesis
    from orexis_agent_progression.store import Store

    toys = tmp_path / "actions.ttl"
    toys.write_text(toys_text)
    #  WITHOUT THE DOSE (#579), as the other fixture: the real dose is free and declares the
    #  region reached, so beside it no toy is the cheapest achiever.
    real = tuple(p for p in loader.action_files() if "actuation" not in str(p))
    monkeypatch.setattr(loader, "action_files", lambda: real + (toys,))

    dst = _avoiding_world(tmp_path)
    with open(dst / "world.ttl", "a") as f:
        f.write(LAW)
    st = Store()
    genesis.refresh_public(st, dst)
    genesis.birth(st, dst, "gardener")
    return build_agent("gardener", st, monkeypatch), st


def test_the_law_prunes_at_expansion_and_the_next_legal_plan_wins(tmp_path, monkeypatch):
    """A valid plan contains no state that NEWLY matches a violation-severity shape, checked
    at EXPANSION — the tempting candidate (better urgency, lower cost, plants the marker) is
    discarded before the met-test can crown it, and the next legal plan wins by construction
    rather than by fallback code."""
    from orexis_agent_deliberation.planner import Planner

    agent, st = _lawful_gardener(tmp_path, monkeypatch, _toy_pair())
    stake = next(g for g in agent.considering()
                 #  the REGION want — the epistemic twin is Observe's to achieve
                 if not g.is_epistemic
                 and getattr(g, "observed_property", None) == MOISTURE)
    plan = Planner(agent, agent.me).plan(stake)

    assert plan.steps, "the stake is achievable — one lever is legal"
    assert plan.steps[0].action == "urn:toy#Honest", \
        "better on BOTH ranking axes and still not taken: the law prunes at expansion"


def test_an_agent_already_inside_the_forbidden_state_keeps_its_exit(tmp_path, monkeypatch):
    """Never-NEWLY-enter: the base already stands in the forbidden state, its violation is
    not news, and the exit must survive the pruning — or the agent that most needs a plan is
    the one refused every one. The envelope-at-the-gates argument, honoured from the
    planner's side."""
    from orexis_agent_deliberation.planner import Planner

    exit_toy = ("@prefix orexis: <http://example.org/orexis#> .\n"
                "@prefix toy: <urn:toy#> .\n"
                "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
                '''
toy:Exit a orexis:Action ;
    orexis:takes orexis:about, <urn:toy#lever> ;
    orexis:available """SELECT ?want ?about ?lever WHERE { VALUES (?want ?about) { $wants } BIND($me AS ?lever) }""" ;
    orexis:retracts """CONSTRUCT { <urn:naughty> ?p ?o } WHERE {
            <urn:naughty> ?p ?o }""" ;
    sh:construct "CONSTRUCT {} WHERE {}" .
''')
    agent, st = _lawful_gardener(tmp_path, monkeypatch, exit_toy)
    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")

    plan = Planner(agent, agent.me).plan(_avoidance_row(agent))
    assert plan.outcome == "satisfied" and plan.steps, \
        "the recovery must be plannable from inside the forbidden state"
    assert plan.steps[0].action == "urn:toy#Exit", "and it is the exit itself"
