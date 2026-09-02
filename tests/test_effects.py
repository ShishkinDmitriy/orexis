"""What a lever says it makes true, and the one number that must not fork (#238).

An action states its effect on its own node (an-action-is-one-node), which the package ships
and genesis loads: `sh:construct` for what applying it would add, `orexis:retracts` — ours — for what it removes. These hold the rules to what they claim, and hold the ACTUATOR to reading
its expectation out of the same rule a planner will read.
"""

from __future__ import annotations

import pytest

from agent import genesis
from orexis_agent_deliberation import effects
from orexis_agent_progression.ontology import ACTIONS_GRAPH, STATE_GRAPH, beliefs_graph
from orexis_agent_progression.store import bindings

from conftest import stake_of, MOISTURE, build_agent, genesis_store, predicted_readings

OBSERVING = "http://example.org/orexis/sensing#Observing"
DOSING = "http://example.org/orexis/actuation#Dosing"
_AG = "http://example.org/orexis#"
RESULT = "http://www.w3.org/ns/sosa/hasSimpleResult"
RESULT_TIME = "http://www.w3.org/ns/sosa/resultTime"


def _loner(readings):
    st = genesis_store(readings, world="loner")
    genesis.birth(st, genesis.world_dir("loner"), "gardener")
    return st


def _values(triples, predicate=RESULT):
    return [t.object.value for t in triples if t.predicate.value == predicate]


# --- the rules are found because a package shipped one, not because anything lists them ----

def test_a_package_that_ships_an_action_file_is_found_without_being_named():
    """The loader idiom, applied a fourth time. A way of acting is a node in a file in the
    package that owns the acting, and nothing in the kernel learns its name — the reason
    adding a capability is adding a directory."""
    from assembly import loader

    #  The parent directory is `orexis-capability-market` now, so the package's own `name` is
    #  what to compare — asked of the loader, which is the one thing that knows how to read it.
    by_path = {p.path: p.name for p in loader.packages()}
    shipped = {by_path[f.parent] for f in loader.action_files() if f.parent in by_path}
    assert {"sensing", "actuation", "market"} <= shipped
    assert all(p.name == "actions.ttl" for p in loader.action_files())


def test_the_rules_are_in_the_store_where_a_sovereign_can_read_them():
    """A schema belongs in the store — that is what the ontology graph already is — and this
    one has to be readable by a model deciding what it could do, not only by the planner. The
    menu stays computed, which is the standing rule and is about INSTANCES: a stored row can
    outlive the plumbing it was concluded from, and a rule about a means cannot."""
    st = _loner({("zz", MOISTURE): 0.10})

    for means in (OBSERVING, DOSING):
        rule = effects.rule_for(st, means)
        assert rule is not None, f"{means} states no effect"
        assert "CONSTRUCT" in rule["construct"]


# --- what looking makes true, and what it must NOT claim -----------------------------------

def test_looking_refreshes_the_reading_and_carries_its_value_unchanged():
    """Observe's whole effect: the same value, a new instant.

    The tempting error is a predicted reading INSIDE the region, since that is what the agent
    wants — and it would teach a planner that a thirsty plant can be watered by looking at it.
    So this asserts the value is carried through unchanged, at a value well outside the region,
    where a shape that invented an improvement would be obvious.
    """
    st = _loner({("zz", MOISTURE): 0.10})
    added, retracted = effects.apply(
        st, OBSERVING, me="<http://example.org/orexis/world/loner#gardener>",
        subject="<http://example.org/orexis/world/loner#zz>", about=f"<{MOISTURE}>",
        state=f"<{STATE_GRAPH}>")

    assert _values(added) == ["0.1"], "looking tells you what IS, and changes nothing"
    assert _values(added, RESULT_TIME), "and it tells you so NOW — the freshness half"
    assert retracted, "the reading it replaces goes, because the sensed graph upserts"


def test_the_retraction_takes_the_whole_node_the_writer_would_replace():
    """`orexis:retracts` exists because SHACL-AF has none, and it is not decoration: the sensed
    graph does DELETE-then-INSERT on ONE node per (subject, property). A retraction that took
    less than the writer takes would leave a possible world holding two results on one node —
    and then a shape asking whether ANY reading sits past an edge answers about the reading the
    plan just replaced.
    """
    st = _loner({("zz", MOISTURE): 0.10})
    _, retracted = effects.apply(
        st, OBSERVING, me="<http://example.org/orexis/world/loner#gardener>",
        subject="<http://example.org/orexis/world/loner#zz>", about=f"<{MOISTURE}>",
        state=f"<{STATE_GRAPH}>")

    held = {(t.subject.value, t.predicate.value) for t in retracted}
    assert len({s for s, _ in held}) == 1, "one node, which is what the writer keys on"
    assert {RESULT, RESULT_TIME} <= {p for _, p in held}, \
        "and all of it — a half-retracted node is the two-results bug in slow motion"


def test_a_means_no_package_described_simply_has_no_effect():
    """None is an ordinary answer. Most levers state no effect yet, and one whose consequences
    nobody has written down still works — it is only one a planner cannot reason about. A
    caller that treated the absence as an error would make shipping a package a two-file
    obligation, which is the registry this layout exists to avoid."""
    st = _loner({("zz", MOISTURE): 0.10})

    assert effects.rule_for(st, "http://example.org/nowhere#Consult") is None
    assert effects.apply(st, "http://example.org/nowhere#Consult") == ([], [])


# --- the number that must not fork ---------------------------------------------------------

def test_the_dose_the_actuator_expects_is_the_dose_its_rule_predicts(monkeypatch):
    """THE constraint of #238, and the reason the rule exists rather than a third helper.

    `litres / conversion` was already written twice in Python — the bidder sizing its
    expectation, the actuator sizing its self-dose — before anything asked what a dose would DO.
    A copy inside the effect would have been the worst of the three: an agent that plans against
    one future and verifies against another reports false UNMET verdicts, and the failure looks
    like a device lying rather than like arithmetic disagreeing with itself.

    So the ledger's number is compared against the RULE's, computed here from the shipped text
    with no arithmetic of this test's own. Rewrite the rule's expression and this test moves
    with it; reintroduce a Python copy that disagrees and it fails.
    """
    gardener = build_agent("gardener", _loner({("zz", MOISTURE): 0.10}), monkeypatch)
    actuation = next(m for m in gardener.modules if m.name == "actuation")

    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    keeper = next(m for m in gardener.modules if m.name == "intention")
    watches = keeper.open_expectations(stake_of(gardener, MOISTURE).uri)
    assert len(watches) == 1, "a self-dose went out and opened exactly one expectation"

    litres = float(gardener.sent.to("actuators/pump/command")[0]["ml"]) / 1000.0
    predicted, _ = effects.apply(
        gardener.beliefs, DOSING, me=f"<{actuation.me.uri}>",
        subject=f"<{actuation.me.acts_for}>", about=f"<{MOISTURE}>",
        state=f"<{STATE_GRAPH}>", beliefs=f"<{beliefs_graph('gardener')}>",
        litres=repr(litres), value="0.1")
    from_rule = float(_values(predicted)[0])

    assert predicted_readings(gardener, watches[0].step) == [pytest.approx(from_rule, abs=1e-3)], \
        "the number the keeper holds the world to must be the number the rule predicted"


def test_the_prediction_is_a_function_of_value_litres_and_the_agents_own_belief(monkeypatch):
    """Three arguments and nothing else, which is what lets a planner ask the same question
    about a world that does not exist yet.

    The base is GIVEN rather than read, and that was a correction the runtime forced: an
    actuator decides on the reading it has just been handed, which is not in the sensed graph
    at the moment it decides — a rule reading the store for its base predicted from the
    PREVIOUS reading, or from nothing at all on the first one. Asked here at two bases and two
    doses, because a function of three arguments is not pinned by one case.
    """
    gardener = build_agent("gardener", _loner({("zz", MOISTURE): 0.10}), monkeypatch)
    actuation = next(m for m in gardener.modules if m.name == "actuation")

    def delta(value, litres):
        """The movement the rule predicts from where the sensed graph says the property
        stands — `value` is written there first, since the rule reads its base from the
        world it is asked about (the planner's imagined one, or this one)."""
        from conftest import write_reading
        write_reading(gardener, value, MOISTURE)
        predicted, _ = effects.apply(
            gardener.beliefs, DOSING, me=f"<{actuation.me.uri}>",
            subject=f"<{actuation.me.acts_for}>", about=f"<{MOISTURE}>",
            state=f"<{STATE_GRAPH}>", beliefs=f"<{beliefs_graph('gardener')}>",
            litres=repr(litres))
        return float(_values(predicted)[0]) - value

    assert delta(0.10, 0.12) == pytest.approx(delta(0.90, 0.12)), \
        "the same dose moves the property the same distance wherever it started"
    assert delta(0.10, 0.24) == pytest.approx(2 * delta(0.10, 0.12)), \
        "and twice the water moves it twice as far — the conversion is a ratio"
    assert delta(0.10, 0.12) > 0, "a dose of water raises moisture, which the belief states"


# --- when it lands, and how you would know (#247) ----------------------------

def _lands(store, litres, me, subject):
    return effects.lands_after(store, DOSING, me=f"<{me}>", subject=f"<{subject}>",
                               litres=repr(float(litres)))


def test_the_deadline_and_the_command_cannot_be_two_different_durations(monkeypatch):
    """The divergence guard, and the whole reason timing moved onto the effect.

    `cmd.seconds` is what goes on the wire — the device's instruction — and the rule computes
    the duration a waiter holds the world to. They are the same physics said twice, and #238's
    lesson is what happens when two copies drift: an agent plans against one future and
    verifies against another, and the failure LOOKS like a device lying rather than like
    arithmetic disagreeing with itself. Here the disagreement would be a clock instead of a
    number, and it would arrive as a dose called late that was never late.

    Across a RANGE, including past the device's cap: the cap is where two implementations of
    "how long is this dose" most easily part company, since one of them may forget it.
    """
    from orexis_capability_market.clearing import Claim

    agent = build_agent("gardener", _loner({("zz", MOISTURE): 0.10}), monkeypatch)
    actuation = next(m for m in agent.modules if m.name == "actuation")
    subject = agent.me.acts_for

    for litres in (0.05, 0.1, 0.37, 0.5, 2.0, 9.0):
        cmd, _ = actuation.command_for(
            Claim(sub="gardener", scope="actuate:self", amount_l=litres, debit=0.0,
                  auction_id="a", jti=f"j{litres}"))
        stated = _lands(agent.beliefs, litres, agent.me.uri, subject)
        assert stated is not None, "a device with a calibration can always be timed"
        assert abs(stated - cmd.seconds) < 0.01, (
            f"{litres}L: the wire says {cmd.seconds}s and the rule says {stated}s")


def test_a_dose_is_timed_by_the_valve_and_not_by_whose_pot_it_fills():
    """Written after the first version of the rule joined through `orexis:actsFor` and answered
    only for self-doses — so every market dose fell back to the local computation, and the
    single source held for the half that needed it least. How long a valve stays open is a fact
    about the VALVE."""
    st = genesis_store({})
    genesis.birth(st, genesis.world_dir("simulation"), "supplier")
    supplier = "http://example.org/orexis/world/simulation#supplier"

    for pot in ("fern", "tomato", "succulent"):
        stated = _lands(st, 0.3, supplier, f"http://example.org/orexis/world/simulation#{pot}")
        assert stated is not None, f"the host's valve on {pot} is a valve it can time"
        assert stated > 0


def test_looking_lands_at_once_because_looking_changes_nothing():
    """Zero is the honest answer, not a shrug. The pot is exactly as wet after the reading as
    before it, so the world-change completes instantly and emptily — what a look delays is
    KNOWLEDGE, which is what the confirmation route says instead."""
    st = genesis_store({})
    genesis.birth(st, genesis.world_dir("simulation"), "fern")
    fern = "http://example.org/orexis/world/simulation#fern"
    assert effects.lands_after(st, "http://example.org/orexis/sensing#Observing", me=f"<{fern}_agent>",
                               subject=f"<{fern}>") == 0.0


def test_a_served_claim_is_timed_by_the_rule_and_not_by_the_wire(monkeypatch, caplog):
    """#351. The self-dose path bound `$subject` to the agent's own `acts_for`, a URI; the
    served-claim path bound it to `_subject_of(claim.sub)`, a LOCAL ID — `<fern>` is not an
    IRI, the timing query failed to parse, `_select` swallowed it, and every market dose fell
    back to `cmd.seconds`. Silent, because a swallowed rule error is an empty result.

    So: the host serves a buyer's claim, the log is clean, and the deadline it holds the
    valve to is the rule's figure plus its grace — the same assertion the self-dose makes.
    """
    import logging
    import time

    from orexis_capability_market.clearing import Claim

    monkeypatch.setenv("OREXIS_WORLD", "simulation")
    st = genesis_store({}, world="simulation")
    agent = build_agent("supplier", st, monkeypatch)
    actuation = next(m for m in agent.modules if m.name == "actuation")
    fern = "http://example.org/orexis/world/simulation#fern"

    with caplog.at_level(logging.ERROR, logger="effects"):
        before = time.monotonic()
        cmd = actuation.redeem(Claim(sub="fern", scope="water", amount_l=0.3, debit=0.1,
                                     auction_id="a1", jti="served-1"))
    assert "would not run" not in caplog.text, "the timing query must parse on the served path"
    stated = _lands(agent.beliefs, 0.3, agent.me.uri, fern)
    assert stated is not None
    deadline, _, _ = actuation.pending[cmd.jti]
    assert abs((deadline - before) - (stated + actuation.grace_s)) < 0.5, \
        "the served claim is held to the rule's landing time, not the wire's"
