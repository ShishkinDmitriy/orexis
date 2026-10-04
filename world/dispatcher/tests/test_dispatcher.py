"""The dispatcher: one agent, two vans, two parcels on the courier's grid, and an aversion to two
vans on one cell (#567). What this world is held to is what was MEASURED on it, since the issue's
mechanism — a search that derives a want to resolve a conflict — is not built:

- the two vans are ONE scope, joined through the parcels, since a parcel standing where either van
  could stand is a filling value of both vans' Pick (a-scope-is-a-predicate-on-a-key, the two-vans
  seam); so every world a want's search opens admits the other van's moves too, and each is weighed;
- two parcels astray are two wants, each named for its parcel and planned alone, because the
  domain's shape says each block is about the parcel itself (a-parcel-astray-is-a-want-of-its-own);
  each carries the estimate bound to its parcel, so the other van's drive brings it no nearer and is
  opened only where it ties (#893); both are delivered in one pass;
- on a corridor, each plan drives its van through the shared cell at its third step, the two walk in
  lockstep, and the present holds two vans on that cell for one act — which nothing sees, since a
  desire is weighed in the planner's pass and the walk comes after it;
- two vans on one cell at a PASS'S START are seen: the aversion — the avoided state itself, under
  `planning:unmetWhen`, judged as a met-test is since #892 — reads unmet with a witness per van and
  the cell as the offending value, its want is minted carrying the same select, and a one-step plan
  parts them.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.ontology import STATE
from agent.planning.planner import Planner
from agent.runtime import UNFINISHED, Runtime, boot
from agent.store import graphs_of, rows

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
D = "http://example.org/orexis/world/dispatcher#"
DESIRE = "http://example.org/orexis/planning#DesireGraph"   # planning's word; the Planner is all planning exports

_MEMBERS_Q = "SELECT ?m ?s WHERE { GRAPH ?g { ?m planning:inScope ?s } }"
_WANTS_Q = "SELECT ?w ?d WHERE { GRAPH ?g { ?w a planning:Want ; prov:wasDerivedFrom ?d } }"
_PLANS_Q = """
SELECT ?want ?outcome (COUNT(?step) AS ?steps) WHERE {
  GRAPH ?p { ?p a planning:Plan ; planning:outcome ?outcome ; planning:for ?want .
             OPTIONAL { ?step a execution:Step ; execution:partOf ?p } } }
GROUP BY ?want ?outcome"""
_STEPS_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?want ?a ?van ?parcel ?to WHERE {
  GRAPH ?p { ?p planning:for ?want . ?step a execution:Step ; execution:partOf ?p ; planning:fills ?a .
             OPTIONAL { ?step courier:van ?van } OPTIONAL { ?step courier:parcel ?parcel } OPTIONAL { ?step courier:to ?to } } }"""
#  THE POSSIBLE WORLDS WEIGHED PER WANT — the figure measure-the-search tabulates; a candidate passed
#  over is weighed too and is not counted here.
_WEIGHED_Q = """
SELECT ?for (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?w .
    ?w a planning:PossibleGraph } }
GROUP BY ?for"""
#  OF THOSE, THE ONES REACHED BY A MOVE OF EACH VAN: the candidate a world is `planning:by` fills the van.
_BY_VAN_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?for ?van (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?w .
    ?w a planning:PossibleGraph ; planning:by ?c . ?c courier:van ?van } }
GROUP BY ?for ?van"""
#  WHAT EACH WANT'S ESTIMATE READ IN THE PRESENT GROUND.
_REMAINING_Q = """
SELECT ?for ?left WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?g ;
    planning:remaining ?left . ?g a planning:GroundGraph } }"""
_WORLDS_Q = "SELECT ?w WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph } }"
#  TWO VANS ON ONE CELL, in one graph's facts: the vans' kinds are public and the world's facts its own.
_SHARED_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT DISTINCT ?cell WHERE { GRAPH $w { ?a courier:at ?cell . ?b courier:at ?cell }
                              GRAPH ?h { ?a a courier:Van . ?b a courier:Van } FILTER(?a != ?b) }"""
#  WHERE THINGS STAND, asked of what the agent BELIEVES by kind: a published plan's steps state the
#  positions they predict in graphs of their own (a-steps-prediction-is-two-graphs-it-names), and a
#  read over every graph took a van's predicted cell for its present one.
_AT_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?x ?cell WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?x courier:at ?cell } }"""
_ACTS_Q = "SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a a execution:Act } }"
#  WHAT A DESIRE'S WEIGHING IN A GROUND SAYS IS IN TROUBLE, and where: each witness's instance and
#  the value that offended — for the aversion, the van and the cell it shares.
_WITNESSES_Q = """
SELECT ?x ?cell WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:Weighing ; planning:for $d ; planning:weighs ?g ; planning:violation ?v .
               ?g a planning:GroundGraph . ?v planning:instance ?x ; planning:offending ?cell } }"""
#  WHICH POLARITY a want carries its met-test under, and what it points at.
_POLARITY_Q = "SELECT ?p ?o WHERE { GRAPH ?g { $w ?p ?o FILTER(?p IN (planning:metWhen, planning:unmetWhen)) } }"

#  THE CORRIDOR: van A drives parcel A along the second row, van B drives parcel B down the third
#  column, and the two shortest chains meet at c2_1 — each van's third step.
CORRIDOR = {"world.ttl": [("courier:destination :c0_3", "courier:destination :c3_1"),
                          ("courier:destination :c3_3", "courier:destination :c2_0")],
            "state.ttl": [(":van_a courier:at :c0_0 .", ":van_a courier:at :c0_1 ."),
                          (":parcel_a courier:at :c0_1 .", ":parcel_a courier:at :c1_1 ."),
                          (":van_b courier:at :c3_0 .", ":van_b courier:at :c2_3 ."),
                          (":parcel_b courier:at :c3_1 .", ":parcel_b courier:at :c2_2 .")]}
#  ONE VAN AND ITS PARCEL ALONE, either half of the shipped delivery.
HALF_A = {"world.ttl": [(':van_b a courier:Van ; rdfs:label "van B" .', ""),
                        (':parcel_b a courier:Parcel ; courier:destination :c3_3 ;\n    rdfs:label "the parcel owed at the top of the last column" .', "")],
          "state.ttl": [(":van_b courier:at :c3_0 .", ""), (":parcel_b courier:at :c3_1 .", "")]}
HALF_B = {"world.ttl": [(':van_a a courier:Van ; rdfs:label "van A" .', ""),
                        (':parcel_a a courier:Parcel ; courier:destination :c0_3 ;\n    rdfs:label "the parcel owed at the top of the first column" .', "")],
          "state.ttl": [(":van_a courier:at :c0_0 .", ""), (":parcel_a courier:at :c0_1 .", "")]}
#  BOTH VANS ON ONE CELL as the world is posed.
TOGETHER = {"state.ttl": [(":van_b courier:at :c3_0 .", ":van_b courier:at :c0_0 .")]}


def _local(iri: str | None) -> str | None:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1] if iri else None


def variant(tmp_path: Path, name: str, edits: dict) -> Path:
    """The dispatcher with its documents rewritten — a copy, since a world imports its domains by the tree's shape."""
    world = tmp_path / name / "world" / "dispatcher"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / name / "domains").symlink_to(WORLD.parents[1] / "domains")
    for file, pairs in edits.items():
        text = (world / file).read_text()
        for old, new in pairs:
            assert old in text, f"{file} no longer says {old!r}"
            text = text.replace(old, new)
        (world / file).write_text(text)
    return world


class _Clock:
    """One timeline: every read moves it on by a second, as a running agent's clock does."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        self.at += timedelta(seconds=1)
        return self.at


def _pass(world: Path, budget: int = 128):
    """One pass of the Planner over the booted world, from the present. The one imaginarium."""
    planner = Planner(boot(world, "dispatcher"), "dispatcher", budget=budget)
    planner.plan(NOW)
    (im,) = planner.imaginaria.values()
    return im


def _wants(im) -> dict[str, str]:
    return {_local(r["w"]): _local(r["d"]) for r in rows(im, _WANTS_Q, ())}


def _plans(im) -> dict[str, tuple[str, int]]:
    return {_local(r["want"]): (_local(r["outcome"]), int(r["steps"])) for r in rows(im, _PLANS_Q, ())}


def _steps(im) -> dict[str, set[tuple]]:
    out: dict[str, set] = {}
    for r in rows(im, _STEPS_Q, ()):
        out.setdefault(_local(r["want"]), set()).add((_local(r["a"]), _local(r.get("van")), _local(r.get("parcel")), _local(r.get("to"))))
    return out


def _weighed(im) -> dict[str, int]:
    return {_local(r["for"]): int(r["n"]) for r in rows(im, _WEIGHED_Q, ())}


def _by_van(im) -> dict[str, dict[str, int]]:
    out: dict[str, dict] = {}
    for r in rows(im, _BY_VAN_Q, ()):
        out.setdefault(_local(r["for"]), {})[_local(r["van"])] = int(r["n"])
    return out


def _remaining(im) -> dict[str, float]:
    return {_local(r["for"]): float(r["left"]) for r in rows(im, _REMAINING_Q, ())}


def _shared(store, graphs) -> dict[str, list[str]]:
    """Per graph among `graphs`, the cells two vans stand on in it — only those holding one."""
    found = {_local(g): sorted(_local(r["cell"]) for r in rows(store, _SHARED_Q, (), w=g)) for g in graphs}
    return {g: cells for g, cells in found.items() if cells}


def _at(store) -> dict[str, str]:
    return {_local(r["x"]): _local(r["cell"]) for r in rows(store, _AT_Q, ()) if r["x"].startswith(D)}


def _run(world: Path, passes: int = 1):
    """The runtime over the booted world for `passes`, every step taken traced as (step, van A's cell,
    van B's cell, the cells two vans share) read off the beliefs the moment it was taken."""
    time = _Clock(NOW)
    clock.now = time
    beliefs = boot(world, "dispatcher")
    runtime = Runtime(beliefs, "dispatcher", budget=128)
    runtime.time = time
    executor = runtime.parts["execution"].executor
    trace: list[tuple] = []

    def traced(event):
        at = _at(beliefs)
        trace.append((_local(event.step), at.get("van_a"), at.get("van_b"), _shared(beliefs, graphs_of(beliefs, STATE))))
        return []
    executor.step_taken.connect(traced)
    outcome = runtime.run(passes=passes, poll_s=0)
    return runtime, outcome, trace


@pytest.fixture
def ticking(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)


def test_the_boot_says_what_each_graph_is_and_two_vans_are_one_scope(ticking):
    """One scope, and both vans in it with both parcels: nothing van A does reads a fact of van B, but a
    parcel is a filling value of either van's Pick, so the parcels join the vans — by key as by predicate."""
    beliefs = boot(WORLD, "dispatcher")
    assert len(graphs_of(beliefs, DESIRE)) == 1 and len(graphs_of(beliefs, STATE)) == 1
    assert _at(beliefs) == {"van_a": "c0_0", "parcel_a": "c0_1", "van_b": "c3_0", "parcel_b": "c3_1"}
    members: dict[str, set] = {}
    for r in rows(beliefs, _MEMBERS_Q, ()):
        members.setdefault(_local(r["m"]), set()).add(r["s"])
    scopes = {s for ss in members.values() for s in ss}
    assert len(scopes) == 1, f"two vans in one courier vocabulary are one scope: {scopes}"
    assert {"van_a", "van_b", "parcel_a", "parcel_b", "Drive", "Pick", "Drop", "at", "carriedBy"} <= set(members)


def test_apart_two_parcels_are_two_wants_planned_alone_and_each_estimate_is_its_parcels(ticking, tmp_path):
    """Two wants, one per parcel, each a five-step plan over its own van and both delivered in one pass.
    EACH WANT'S ESTIMATE IS ITS PARCEL'S: in the present ground it reads what the van alone reads,
    three drives, where the desire's select — every parcel — read six (#893). What the one scope
    still costs is the other van's moves: every world a want's search opens admits them, a candidate
    admitted is weighed, and the estimate can refuse to OPEN a world and never to weigh it — so each
    want weighs worlds the other van's drive reached, and more worlds than the van alone. Measured:
    37 and 37 against 13, where the desire's estimate cost 61 and 64. The day the vans are two scopes
    the other van's worlds go, and the finding in measure-the-search is to be rewritten."""
    im = _pass(WORLD)
    assert _wants(im) == {"every_parcel_delivered.pursued.parcel_a": "every_parcel_delivered",
                          "every_parcel_delivered.pursued.parcel_b": "every_parcel_delivered"}
    plans, steps = _plans(im), _steps(im)
    assert plans == {"every_parcel_delivered.pursued.parcel_a": ("Satisfied", 5),
                     "every_parcel_delivered.pursued.parcel_b": ("Satisfied", 5)}
    assert {van for _, van, _, _ in steps["every_parcel_delivered.pursued.parcel_a"] if van} == {"van_a"}
    assert {van for _, van, _, _ in steps["every_parcel_delivered.pursued.parcel_b"] if van} == {"van_b"}
    assert _shared(im, [r["w"] for r in rows(im, _WORLDS_Q, ())]) == {}, "apart, no world the search visits holds two vans on a cell"
    paid, left, by_van = _weighed(im), _remaining(im), _by_van(im)
    halves, halves_left = {}, {}
    for name, edits in (("a", HALF_A), ("b", HALF_B)):
        half = _pass(variant(tmp_path, name, edits))
        (want,) = _plans(half)
        assert _plans(half)[want] == ("Satisfied", 5)
        halves[want] = _weighed(half)[want]
        halves_left[want] = _remaining(half)[want]
    assert set(halves) == set(plans)
    assert left == halves_left, f"a want's estimate is its parcel's drives, as the van alone reads them: {left} against {halves_left}"
    assert all(len(by_van[w]) == 2 for w in halves), f"the one scope admits the other van's moves to every search: {by_van}"
    assert all(halves[w] < paid[w] < 4 * halves[w] for w in halves), \
        f"each want weighs the other van's worlds and no longer the product: {paid} against {halves} alone"
    runtime, outcome, trace = _run(WORLD)
    assert outcome == UNFINISHED and len(trace) == 10, "a desire holds the agent, and both chains are walked in one pass"
    assert _at(runtime.beliefs) == {"van_a": "c0_3", "parcel_a": "c0_3", "van_b": "c3_3", "parcel_b": "c3_3"}


def test_corridor_each_plan_crosses_the_shared_cell_and_the_present_holds_two_vans_on_it_unseen(ticking, tmp_path):
    """Each plan drives its van to c2_1 at its third step, and the aversion is judged in no possible
    world — a desire is weighed in grounds alone. Walked in lockstep, the present holds both vans on
    c2_1 for one act, and no want is minted from the aversion: the derivation ran before the walk, and
    the next pass finds the parcels delivered. This is the measurement #567's mechanism waits on, held
    so it is rewritten when that is built. With the desire's estimate each search forked the other van
    far enough that four of 118 worlds held two vans on one cell; with each want's own (#893) none of
    the worlds visited does, and the two vans meet on the cell only when the plans are walked."""
    corridor = variant(tmp_path, "corridor", CORRIDOR)
    im = _pass(corridor)
    plans, steps = _plans(im), _steps(im)
    assert plans == {"every_parcel_delivered.pursued.parcel_a": ("Satisfied", 5),
                     "every_parcel_delivered.pursued.parcel_b": ("Satisfied", 5)}
    assert ("Drive", "van_a", None, "c2_1") in steps["every_parcel_delivered.pursued.parcel_a"]
    assert ("Drive", "van_b", None, "c2_1") in steps["every_parcel_delivered.pursued.parcel_b"]
    assert _shared(im, [r["w"] for r in rows(im, _WORLDS_Q, ())]) == {}, "no world the searches visit holds two vans on one cell"
    assert "no_cell_holds_two_vans" not in _weighed(im), "and the aversion, a desire, is weighed in no possible world"
    runtime, outcome, trace = _run(corridor)
    assert outcome == UNFINISHED and len(trace) == 10
    met = [(step, shared) for step, _, _, shared in trace if shared]
    assert len(met) == 1 and list(met[0][1].values()) == [["c2_1"]], f"both vans on c2_1 for one act: {trace}"
    assert _at(runtime.beliefs) == {"van_a": "c3_1", "parcel_a": "c3_1", "van_b": "c2_0", "parcel_b": "c2_0"}
    planner = runtime.parts["planning"].planner
    minted = {w for im in planner.imaginaria.values() for w, d in _wants(im).items() if d == "no_cell_holds_two_vans"}
    assert minted == set(), f"nothing judged the present between the two walks: {minted}"


def test_two_vans_on_one_cell_at_a_pass_start_mint_the_aversions_want_and_a_drive_parts_them(ticking, tmp_path):
    """The aversion, the avoided state under `planning:unmetWhen` (#892): both vans on c0_0 as posed, it
    reads unmet with a witness per van, each offending with c0_0, one want is minted under it — about
    both, named for neither, carrying the same select under the same term — and a one-step plan, a
    drive, satisfies it; run, the vans stand apart."""
    together = variant(tmp_path, "together", TOGETHER)
    im = _pass(together)
    assert {(_local(r["x"]), _local(r["cell"])) for r in rows(im, _WITNESSES_Q, (), d=D + "no_cell_holds_two_vans")} == \
        {("van_a", "c0_0"), ("van_b", "c0_0")}, "the avoided state is judged in the present: a row per van, the cell offending"
    assert _wants(im)["no_cell_holds_two_vans.pursued"] == "no_cell_holds_two_vans"
    assert [(_local(r["p"]), _local(r["o"])) for r in rows(im, _POLARITY_Q, (), w=D + "no_cell_holds_two_vans.pursued")] == \
        [("unmetWhen", "no_cell_holds_two_vans.pursued.avoided")]
    assert _plans(im)["no_cell_holds_two_vans.pursued"] == ("Satisfied", 1)
    assert {a for a, *_ in _steps(im)["no_cell_holds_two_vans.pursued"]} == {"Drive"}
    assert _weighed(im)["no_cell_holds_two_vans.pursued"] == 4, "what the met-test form cost, measured: " + str(_weighed(im))
    runtime, outcome, trace = _run(together)
    at = _at(runtime.beliefs)
    assert at["van_a"] != at["van_b"], at
