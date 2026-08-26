"""An agent re-picking a belief — the room it has, the guards, and what it remembers.

Nothing is mocked. The store is a real belief base, the shapes are the real shapes, the rule is
the SPARQL the sensing package ships, and the path is the one a deployed agent runs when it
arises. See knowledge/decisions/a-belief-is-a-pick-within-a-range.md.
"""

from __future__ import annotations

import pytest

from agent import genesis
from packages.capability.review.graphs import evidence_graph, revisions_graph
from agent.ontology import STATE_GRAPH, WORLD_GRAPH, beliefs_graph, term
from onboarding.namespaces import SENSING
from packages.capability.review import RECKONING, REVIEW
from packages.capability.review.module import Range, world_ranges
from agent.store import bindings
from packages.capability.review.summary import RING, Summaries

from conftest import WORLDS_ROOT, build_agent, genesis_store

# Sensing's term, built from sensing's namespace. The kernel `term()` is still
# imported for review's own, which is the distinction this sweep exists to make visible.
SLOW = SENSING + "slowSleepS"
AUTHORED = 600.0   # fern's first pick
COMMITTED = 600.0  # and the floor it commits to
CEILING = 900.0    # the constitutional ceiling it may relax to

# The second revisable term the same package ships: the jolt threshold. The two rules read one
# window of evidence the opposite way round — a lively world earns a tight cadence and a COARSE
# delta, a still one a slow cadence and a FINE delta — so most cases below assert both, as a
# dict because SPARQL promises no row order.
DELTA = SENSING + "alarmDeltaFraction"
DELTA_AUTHORED = 0.25  # fern's first pick — the old family constant, now merely its opinion
DELTA_FINE = 0.1       # its mandate's floor: what a still world lets it call a jolt
DELTA_COARSE = 0.5     # its mandate's ceiling: what a lively world makes it call one


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", monkeypatch=monkeypatch)


def feed(agent, values, sensor=None):
    """Put readings through the ingest path, then close the window as an arising would."""
    sensor = sensor or agent.subscribing().sensors[0]
    for value in values:
        agent.reviewing().summaries.record(sensor.subject, sensor.observes, value)
    agent.reviewing().summaries.roll()
    agent.reviewing().publish_evidence(agent.reviewing().ranges())
    return agent.reviewing()


def window(agent) -> int:
    rows = bindings(agent.beliefs.query(
        "SELECT ?n WHERE { GRAPH ?g { sensing:SensingCapability sensing:reviewWindow ?n } }"))
    return int(rows[0]["n"])


# --- what may move, and how far ------------------------------------------------------------

def test_a_revisable_term_is_discovered_from_the_t_box_not_from_python(fern):
    """No registry and no import: the reviewer asks the merged ontology what may be re-picked,
    so a capability nobody here has read is reviewable on the same terms as this one."""
    assert SLOW in world_ranges(fern.beliefs.query)


def test_the_world_range_comes_from_the_constitution(fern):
    room = world_ranges(fern.beliefs.query)[SLOW]
    assert (room.floor, room.ceiling) == (10.0, 900.0)


def test_the_jolt_threshold_is_revisable_on_the_same_terms(fern):
    """The second term the sensing package declares, covered by the same machinery with no
    Python knowing its name: constitution from the family's figures, narrowed by the mandate.
    Revisable because the first 0.25 was an estimate measured on nothing, and correcting an
    estimate must cost a retained command, never a reflash."""
    room = world_ranges(fern.beliefs.query)[DELTA]
    assert (room.floor, room.ceiling) == (0.05, 0.5)
    narrowed = fern.reviewing().ranges()[DELTA]
    assert (narrowed.floor, narrowed.ceiling) == (DELTA_FINE, DELTA_COARSE)


def test_the_agents_own_commitment_narrows_it(fern):
    """The author's job is to constrain, not to guess. 10..900 is what any agent may do; 600..900
    is what this one will."""
    assert (fern.reviewing().ranges()[SLOW].floor,
            fern.reviewing().ranges()[SLOW].ceiling) == (COMMITTED, CEILING)


def test_the_first_pick_is_not_a_bound(fern):
    """The whole correction. What genesis wrote is a value inside the range, not an end of it —
    so a review may move below it when its own commitment allows."""
    assert fern.reviewing().current(SLOW) == AUTHORED
    room = fern.reviewing().ranges()[SLOW]
    assert room.floor <= AUTHORED <= room.ceiling


def test_a_commitment_leaving_no_room_fixes_the_figure():
    """How an author says 'not up for review' — by leaving nowhere to go, rather than a flag."""
    assert Range(SLOW, 900.0, 900.0).fixed
    assert not Range(SLOW, 600.0, 900.0).fixed


def test_a_world_that_widens_a_mandate_will_not_validate():
    """The check that only became possible when the mandate went public.

    Both ends of this comparison used to sit in different graphs — the constitution in the
    vocabulary, the range in a private beliefs file — so nothing could hold them together and the
    reviewer's intersection was the only defence. A sovereign granting more room than the society
    allows is now refused before anything starts, which is where a governance error belongs.
    """
    from agent.ontology import PROVENANCE_GRAPH
    from agent.store import Store
    from agent.validate import conforms, graph_from

    path = genesis.world_dir("simulation")

    def built():
        """Exactly what `orexis-validate` builds: the public graphs plus everyone's beliefs."""
        st = Store()
        genesis.refresh_public(st, path)
        everyone = [genesis.agent_id_of(p) for p in sorted(path.glob(genesis.BELIEFS_GLOB))]
        for agent_id in everyone:
            genesis.birth(st, path, agent_id)
        return st, everyone

    def judged(st, everyone):
        """Exactly what orexis-validate judges since #312: the wants and the pick records
        arrive through each agent's desire modality, and only through it."""
        from agent import effects
        from conftest import desires_build

        data = graph_from(st, *st.public_graphs(), PROVENANCE_GRAPH)
        for a in everyone:
            for triple in desires_build(st, a).construct(
                    "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
                data.add(effects._triple(triple))
        return data

    st, everyone = built()
    assert conforms(judged(st, everyone))[0], "the shipped world should validate"

    st, everyone = built()
    st.update(f"""
DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?c review:notAbove ?a }} }}
INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?c review:notAbove 99999 }} }}
WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?c review:onTerm ?t ; review:notAbove ?a }} }}""")
    assert not conforms(judged(st, everyone))[0]


def test_a_mandate_never_widens_what_the_constitution_allows(fern):
    """A mandate is intersected, so one looser than the constitution is the constitution.

    Written into the WORLD graph, which is where a mandate lives now — a world may narrow what
    the society allows and never widen it. `ag:MandateWithinTheConstitutionShape` refuses this at
    validation; the intersection here is the second line of defence, for a world already running.
    """
    fern.beliefs.update(f"""
DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?c review:notAbove ?a }} }}
INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?c review:notAbove 99999 }} }}
WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?c review:onTerm <{SLOW}> ; review:notAbove ?a }} }}""")
    assert fern.reviewing().ranges()[SLOW].ceiling == CEILING


# --- what the shipped rule concludes ---------------------------------------------------------

def test_a_thin_window_proposes_nothing(fern):
    """Two identical readings are a coincidence. A rule with nothing to say returns no rows —
    an unsatisfied pattern rather than a sentinel."""
    feed(fern, [0.5] * 3)
    assert fern.reviewing().proposals() == []


def test_a_steady_probe_relaxes_the_cadence_and_sharpens_the_jolt(fern):
    """The trade: nothing is happening, so the board may sleep — and precisely because it
    sleeps, the ULP watch is the only watcher left, and a fine delta there costs nothing."""
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    assert dict(fern.reviewing().proposals()) == {SLOW: CEILING, DELTA: DELTA_FINE}


def test_a_frozen_probe_tightens_instead_of_relaxing(fern):
    """The case the obvious rule gets exactly backwards: an instrument that has not moved to the
    last bit is likelier broken than the world it measures is perfectly still. The delta takes
    the floor with the still case — a flat line fires no delta whatever its size, and if the
    instrument revives with a jolt, the fine threshold reports it at once."""
    feed(fern, [0.412] * (window(fern) + 2))
    assert dict(fern.reviewing().proposals()) == {SLOW: COMMITTED, DELTA: DELTA_FINE}


def test_a_moving_probe_tightens_the_cadence_and_coarsens_the_jolt(fern):
    """The trade, the other way: the tight cadence already carries the news, so a fine delta
    would only spend the battery announcing routine liveliness."""
    feed(fern, [0.3, 0.7] * (window(fern) // 2 + 1))
    assert dict(fern.reviewing().proposals()) == {SLOW: COMMITTED, DELTA: DELTA_COARSE}


# --- the asymmetry, tested on the rule's own aggregation ---------------------------------------

def _evidence(agent, spreads):
    """Seed one Evidence node per spread, as several sensors would produce.

    Written straight into the evidence graph because no ratified world gives one agent two
    sensors yet — this exercises the shipped rule's aggregation rather than a stand-in for it.
    """
    agent.reviewing().publish_evidence(agent.reviewing().ranges())
    n = window(agent) + 2
    agent.beliefs.update("INSERT DATA { GRAPH <%s> { %s } }" % (
        evidence_graph(agent.id),
        "".join(f'[] a review:Evidence ; review:sampleSpread "{s:.6f}"^^xsd:decimal ; '
                f'review:sampleCount {n} . ' for s in spreads)))


def test_relaxing_needs_every_sensor_to_agree(fern):
    _evidence(fern, [0.001, 0.001])
    assert dict(fern.reviewing().proposals()) == {SLOW: CEILING, DELTA: DELTA_FINE}


def test_one_moving_sensor_is_enough_to_tighten(fern):
    """The cost of watching a still pot too closely is some battery; the cost of the reverse is
    a dead plant. So relaxing needs unanimity and tightening needs one dissenter — and the SAME
    dissenter coarsens the jolt threshold, because the delta is the agent's and one twitchy
    channel wakes the whole board."""
    _evidence(fern, [0.001, 0.9])
    assert dict(fern.reviewing().proposals()) == {SLOW: COMMITTED, DELTA: DELTA_COARSE}


def test_one_frozen_sensor_is_enough_to_tighten(fern):
    _evidence(fern, [0.001, 0.0])
    assert dict(fern.reviewing().proposals()) == {SLOW: COMMITTED, DELTA: DELTA_FINE}


# --- applying, refusing, reverting -------------------------------------------------------------

def test_a_revision_moves_the_belief_and_the_module_takes_it_up(fern):
    subscribing = fern.subscribing()
    assert subscribing.beliefs.slow_sleep_s == AUTHORED
    assert subscribing.alarm_beliefs.delta_fraction == DELTA_AUTHORED

    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewing().review()

    assert fern.reviewing().current(SLOW) == CEILING
    assert fern.reviewing().current(DELTA) == DELTA_FINE
    # Re-read, not patched: the module holds a frozen dataclass and must have refreshed it —
    # both of them, since one arising settled both terms.
    assert subscribing.beliefs.slow_sleep_s == CEILING
    assert subscribing.alarm_beliefs.delta_fraction == DELTA_FINE


def test_a_value_outside_the_range_is_refused_not_clamped(fern):
    """A rule proposing out of range is wrong about something, and quietly correcting it would
    hide that."""
    room = fern.reviewing().ranges()[SLOW]
    assert not fern.reviewing().settle(room, 2000.0)
    assert fern.reviewing().current(SLOW) == AUTHORED
    assert fern.reviewing().refused == 1


def test_a_revision_the_shapes_refuse_is_put_back(fern):
    """Legitimacy is the boot check re-run, so a belief the agent could not have started with is
    one it cannot reach by changing its mind either."""
    from agent.validate import validate_agent

    assert not fern.reviewing().settle(Range(SLOW, 0.0, 5.0), 1.0)  # under the constitutional floor
    assert fern.reviewing().current(SLOW) == AUTHORED
    assert fern.reviewing().refused == 1
    # And it is still startable, which is what reverting exists to preserve.
    validate_agent(fern.beliefs, fern.id, fern.me.uri, fern.me.capabilities,
                   desires=fern.desires)


# --- memory, which is also the schedule ---------------------------------------------------------

def test_a_decision_to_change_nothing_is_recorded(fern):
    """Without it the same question is re-argued at every arising, and the agent can never
    notice it has declined eleven times and the problem is elsewhere. The frozen probe holds
    the cadence it proposes (declined) while the jolt threshold moves to the floor (taken) —
    one arising, two terms, two different outcomes on the record."""
    feed(fern, [0.412] * (window(fern) + 2))  # frozen -> the cadence rule proposes what it holds
    fern.reviewing().review()
    assert fern.reviewing().declined == 1
    assert {r["term"]: r["outcome"] for r in _decisions(fern)} == {
        SLOW: "declined", DELTA: "taken"}


def test_a_settled_term_is_not_re_argued_before_it_is_due(fern):
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewing().review()
    taken = fern.reviewing().revisions
    assert taken == 2  # one arising settled both terms

    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewing().review()
    assert fern.reviewing().revisions == taken  # still due later, so nothing was re-decided
    assert len(_decisions(fern)) == 2


def test_every_decision_says_why_and_when_to_look_again(fern):
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewing().review()
    recorded = {r["term"]: r for r in _decisions(fern)}[SLOW]
    assert float(recorded["from"]) == AUTHORED and float(recorded["to"]) == CEILING
    assert recorded["why"] and recorded["due"] > recorded["at"]


def test_the_next_arising_is_never_sooner_than_the_stated_floor(fern):
    assert fern.reviewing().interval_s == 300  # what fern's beliefs state
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewing().review()
    assert fern.reviewing().next_wake_s() >= 300


# --- the write boundary ----------------------------------------------------------------------

def test_a_review_writes_only_its_own_beliefs_and_never_the_world_or_the_record(fern):
    """The graph types made load-bearing. A review reads the world as constraint and `:sensed`
    as evidence, and changes neither — which is what the tripartite split is FOR."""
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    before = (fern.beliefs.get_graph(WORLD_GRAPH), fern.beliefs.get_graph(STATE_GRAPH))

    fern.reviewing().review()

    assert fern.reviewing().current(SLOW) == CEILING, "it should have changed something"
    assert (fern.beliefs.get_graph(WORLD_GRAPH), fern.beliefs.get_graph(STATE_GRAPH)) == before


def test_a_review_touches_no_other_agents_beliefs(fern):
    """It cannot reach one — but the fixture births every agent in the world, so unlike a
    deployed store this one actually contains somebody else's to reach for."""
    other = fern.beliefs.get_graph(beliefs_graph("tomato"))
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewing().review()
    assert fern.beliefs.get_graph(beliefs_graph("tomato")) == other


def _decisions(agent) -> list[dict]:
    return bindings(agent.beliefs.query(f"""
SELECT ?term ?from ?to ?why ?outcome ?at ?due WHERE {{ GRAPH <{revisions_graph(agent.id)}> {{
  ?r a review:Revision ; review:revisedTerm ?term ; review:fromValue ?from ; review:toValue ?to ;
     review:becauseOf ?why ; review:outcome ?outcome ; review:atTime ?at ; review:dueAt ?due }} }}"""))


def test_an_agent_given_no_room_has_no_review_at_all(monkeypatch):
    """The mandate is the switch, and it is in the world where anyone can read it.

    This used to be the absence of `review:reviewIntervalS` in a private beliefs file — a public
    ability switched by a fact no peer, no shape and no operator could see. Now an agent the
    world grants no room derives no capability, loads no module, keeps no summaries and never
    arises: the mechanism is *absent* rather than idle, which is a different and better thing.

    The supplier is the case in the shipped world rather than a contrived one — it holds no
    revisable setting, so there is nothing to give it room on.
    """
    supplier = build_agent("supplier", monkeypatch=monkeypatch)
    assert not supplier.me.can(RECKONING)
    assert "review" not in {m.name for m in supplier.modules}
    assert supplier.provider(REVIEW) is None


def test_upkeep_still_runs_for_an_agent_that_reviews_nothing(monkeypatch):
    """Compacting is not a choice, so it did not become optional when reviewing did.

    It used to run on the reviewer's clock, which was safe only while every agent had one. An
    agent with no mandate would otherwise have stopped compacting silently — and silently is the
    whole difficulty of #45, which is open precisely because nobody has watched one happen.
    """
    supplier = build_agent("supplier", monkeypatch=monkeypatch)
    assert supplier.upkeep.max_bytes_per_triple > 0
    assert supplier.upkeep.consider() is False  # in memory: nothing to compact, and it looked


# --- what the equipment allows, which is the third source ------------------------------------
#
# `ranges()` has documented three narrowing sources since it was written — constitution, mandate,
# hardware — and the third existed only in the docstring. These are it. The world used is
# `sensing`, because it is the only one with hardware to state a limit; a simulated device has no
# physical floor, and that is the honest reason `simulation` narrows nothing.

def _sensing_with(update: str = ""):
    """The sensing world, optionally mutated, re-derived exactly as genesis derives it.

    Cleared before re-running: a rule's conclusion is not idempotent when its premise changed,
    and leaving the old one beside the new is how `test_capabilities` once read BOTH sensing
    capabilities and called it a pass.
    """
    from assembly import loader
    from agent.ontology import WORLD_DERIVED_GRAPH

    st = genesis_store(world="sensing")
    if update:
        st.update(update)
    st.clear_graph(WORLD_DERIVED_GRAPH)
    for rule in loader.rule_files():
        st.update(genesis.substitute(rule.read_text(), st))
    return st


_ONE = """  <http://example.org/orexis/world/sensing#{sensor}> ssn-system:hasSystemCapability [
      a ssn-system:SystemCapability ;
      ssn-system:hasSystemProperty [ a ssn-system:Frequency , schema:PropertyValue ; schema:value {seconds} ; schema:unitCode unit:SEC ] ] ."""


def _states(**floors: int) -> str:
    """One update however many devices it speaks about: each carries its own PREFIX block, so
    two of them concatenated is a syntax error rather than two statements."""
    body = "\n".join(_ONE.format(sensor=s, seconds=n) for s, n in floors.items())
    return f"""
PREFIX ag: <http://example.org/orexis#>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX sensing: <http://example.org/orexis/sensing#>
INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
{body}
}} }}"""


def _limit(st):
    rows = bindings(st.query("""
SELECT ?floor WHERE { ?a review:limitedTo ?l . ?l review:onTerm ?t ; review:notBelow ?floor }"""))
    return [float(r["floor"]) for r in rows]


def test_what_a_board_can_honour_reaches_the_agent_that_polls_it():
    """The limit is stated on the DEVICE and needed by the AGENT, and only the agent holds a
    belief to narrow. So the derivation carries it across `sensing:polls` — which is why this
    is a rule at genesis and not a query at review time: an agent is never given the wiring."""
    assert _limit(_sensing_with()) == [2.0]   # the KY-015's datasheet sampling period


def test_a_device_that_states_nothing_narrows_nothing(monkeypatch):
    """The capacitive probe declares no Frequency, because an ADC read has no meaningful floor.
    Absence is the ordinary case and must not be read as zero — a floor of zero would widen the
    range rather than leave it alone."""
    st = _sensing_with()
    room = build_agent("fern", st=st, monkeypatch=monkeypatch).reviewing().ranges()[SLOW]
    assert room.floor == 10.0, "the constitution's floor, untouched by a device that stated none"


def test_a_board_slower_than_the_constitution_narrows_the_range(monkeypatch):
    """The case the mechanism exists for, and the one no shipped device exercises: nothing in
    this repository is slower than the society's own floor of ten seconds. Stated here rather
    than invented in a world, because a hardware fact nobody measured is worse than none."""
    st = _sensing_with(_states(air_temp_fern=60))
    room = build_agent("fern", st=st, monkeypatch=monkeypatch).reviewing().ranges()[SLOW]
    assert room.floor == 60.0, "the board's floor should have raised the agent's"
    assert room.ceiling == 900.0, "and left the ceiling where the constitution put it"


def test_an_agent_polling_two_boards_is_held_to_the_slower():
    """MAX, not MIN. An agent reads all its sensors on one wake, so it can go no faster than its
    slowest device — taking the minimum would ask the slow board for a cadence it never keeps,
    which is the exact failure this exists to prevent, reached from the other side."""
    st = _sensing_with(_states(air_temp_fern=45, moisture_sensor_fern=90))
    assert _limit(st) == [90.0]


def test_the_floor_is_the_equipments_and_the_mandate_cannot_lower_it(monkeypatch):
    """Two sources, one arithmetic: whichever binds tighter wins, and a mandate that reaches
    past the hardware does not get its way. The shape refuses that world at validation; this is
    what the runtime does with one that slipped through anyway."""
    st = _sensing_with(_states(air_temp_fern=120))
    room = build_agent("fern", st=st, monkeypatch=monkeypatch).reviewing().ranges()[SLOW]
    assert room.floor == 120.0, "sensing's fern commits notBelow 10, and the board says 120"


# --- the picks are visible outside the container (#61) ------------------------------------------

def test_the_report_says_toward_what_not_merely_that(fern):
    """belief_revisions said an agent changed its mind; this says where the belief now sits.
    One field per revisable term it holds, into its own bucket — the range is the governance
    surface, and the only evidence a range was mis-authored is what agents do inside it."""
    reviewing = fern.reviewing()
    assert reviewing.reports()["picked_sensing_slowSleepS"] == AUTHORED
    assert reviewing.reports()["picked_sensing_alarmDeltaFraction"] == DELTA_AUTHORED
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    reviewing.review()
    assert reviewing.reports()["picked_sensing_slowSleepS"] == CEILING
    assert reviewing.reports()["picked_sensing_alarmDeltaFraction"] == DELTA_FINE


def test_a_taken_revision_is_a_marker_over_the_series(fern):
    """The picked_* fields show WHERE a belief sits; the event shows the MOMENT it moved and
    why, beside the intention story (#125)."""
    fern.metrics.take_events()
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewing().review()
    events = fern.metrics.take_events()
    assert {(kind, tags["term"]) for _, kind, _, tags in events} == {
        ("belief-taken", "slowSleepS"), ("belief-taken", "alarmDeltaFraction")}
    slow = next(text for _, _, text, tags in events if tags["term"] == "slowSleepS")
    assert "600" in slow and "900" in slow


def test_a_decline_is_counted_but_never_a_marker(fern):
    """Declining is the routine outcome of most arisings — a marker per arising would bury
    the markers that mean something, and the count is the right voice for the routine. The
    frozen window declines the cadence and takes the jolt threshold, and only the taken one
    leaves a mark."""
    fern.metrics.take_events()
    feed(fern, [0.412] * (window(fern) + 2))
    fern.reviewing().review()
    assert fern.reviewing().declined == 1
    assert [(kind, tags) for _, kind, _, tags in fern.metrics.take_events()] == [
        ("belief-taken", {"term": "alarmDeltaFraction"})]


def test_a_refusal_is_a_marker_because_it_is_a_bug_signal(fern):
    fern.metrics.take_events()
    room = fern.reviewing().ranges()[SLOW]
    assert not fern.reviewing().settle(room, 2000.0)
    assert [kind for _, kind, _, _ in fern.metrics.take_events()] == ["belief-refused"]
