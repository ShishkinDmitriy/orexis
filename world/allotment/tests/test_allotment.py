"""The allotment in the 0.2.0 runtime: three agents over one fake broker, trading water.

A dry plot's grower calls for a round, the supplier offers one to both growers, the grower tenders
a bid sized from its reading, the supplier clears the round when its window closes and tells the
winner its claim, the grower presents the claim and the supplier serves it through the valve over
the plot — every step a document one agent says to another, believed by both. The broker is a
fake: a publish reaches every client subscribed to a matching pattern, and a command to a valve is
held for the test to read."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.runtime import Runtime, boot
from agent.store import catalogue_of, graphs_of, rows
from agent.transport.mqtt.driver import Mqtt, matches

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AL = "http://example.org/orexis/world/allotment#"
MARKET = "http://example.org/orexis/market#"


class Clock:
    """One timeline for every agent: a test sets where it stands, and every read moves it on by a
    second, as a running agent's clock does."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        self.at += timedelta(seconds=1)
        return self.at


class Bus:
    """The broker: who subscribed to what, and every publish delivered to each subscriber."""

    def __init__(self, time):
        self.time, self.clients, self.published = time, [], []

    def client(self):
        bus = self

        class Client:
            def __init__(self):
                self.patterns, self.runtime = [], None
                bus.clients.append(self)

            def subscribe(self, pattern):
                self.patterns.append(pattern)

            def publish(self, topic, payload, retain=False):
                bus.published.append((topic, payload))
                for other in bus.clients:
                    if other.runtime is not None and any(matches(p, topic) for p in other.patterns):
                        other.runtime.deliver(topic, payload, bus.time.at)

        return Client()

    def commands(self, prefix="actuators/"):
        return [(t, json.loads(p)) for t, p in self.published if t.startswith(prefix)]

    def told(self, agent):
        return [p for t, p in self.published if t == f"agents/{agent}/inbox"]


def _allotment(monkeypatch):
    time = Clock(NOW)
    monkeypatch.setattr(clock, "now", time)
    bus = Bus(time)
    agents = {}
    for name in ("supplier", "rose_grower", "fern_grower"):
        client = bus.client()
        runtime = Runtime(boot(WORLD, name), name, transport=Mqtt(AL + name, client))
        client.runtime = runtime
        agents[name] = runtime
    return agents, bus, time


def _run(agents, rounds=3):
    for _ in range(rounds):
        for runtime in agents.values():
            runtime.run(passes=1, poll_s=0)


def _facts(runtime, predicate):
    q = f"SELECT ?s ?o WHERE {{ ?s <{MARKET}{predicate}> ?o }}"
    return {(r["s"].rsplit("#", 1)[-1].rsplit("/", 1)[-1], str(r["o"])) for r in
            rows(runtime.beliefs, q, graphs_of(runtime.beliefs, "http://example.org/orexis#BeliefGraph"))}


def test_each_agent_listens_on_its_own_topic_and_the_growers_on_their_probes(monkeypatch):
    agents, bus, _ = _allotment(monkeypatch)
    patterns = {name: sorted(c.patterns) for name, c in zip(agents, bus.clients)}
    assert patterns == {"supplier": ["agents/supplier/inbox"],
                        "rose_grower": ["agents/rose_grower/inbox", "sensors/rose_probe/reading"],
                        "fern_grower": ["agents/fern_grower/inbox", "sensors/fern_probe/reading"]}


def test_a_grower_s_world_is_hashed_within_what_the_market_s_texts_read(monkeypatch):
    """The market's `Calling` and `Tendering` read anything until #908 — a predicate list under
    `NOT EXISTS` with a `NOT EXISTS` nested in it — so a grower's read set was unreadable and every
    world of it hashed whole: a reading inside its band at a new instant was a surprise every pass,
    and the cone went with it. Read, the same number ten minutes on is the old present."""
    agents, _, time = _allotment(monkeypatch)
    rose = agents["rose_grower"]
    planner = rose.parts["planning"].planner
    heard: list = []
    planner.rerooted.connect(lambda event: heard.append(event) or [])
    rose.deliver("sensors/rose_probe/reading", b'{"value": 0.45}', time.at)
    rose.run(passes=1, poll_s=0)
    assert planner._read[1] is not None, "the growers' read set is readable: no text of the allotment reads anything"
    assert {MARKET + p for p in ("bidsIn", "calledBy", "calledOn", "answered", "clearedAt")} <= planner._read[1]
    assert {e.present for e in heard} == {"first"}
    heard.clear()
    time.at += timedelta(minutes=10)
    rose.deliver("sensors/rose_probe/reading", b'{"value": 0.45}', time.at)
    rose.run(passes=1, poll_s=0)
    assert heard and {e.present for e in heard} == {"ground"}, \
        f"the same reading at a new instant is the present the last pass stood in, not a surprise: {heard}"


def _scopes(runtime):
    """Every scope the store holds, each as the set of its members' local names."""
    held: dict = {}
    for r in rows(runtime.beliefs, """SELECT ?m ?s WHERE {
            GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:ScopeGraph } GRAPH ?g { ?m planning:inScope ?s } }""", ()):
        held.setdefault(r["s"], set()).add(r["m"].rsplit("#", 1)[-1].rsplit("/", 1)[-1])
    return list(held.values())


def test_the_allotment_is_two_scopes_and_the_heating_it_imports_is_in_neither(monkeypatch):
    """The allotment imports the climate domain and holds no heater, so the heating's precondition
    binds a grower and a plot and nothing a heating is done with. Read as fillings, those made a
    scope per plot that admitted nothing and minted nothing, at an imaginarium a pass apiece — about
    as dear as a real scope's, measured (#913). A row leaving the heater unbound is no filling: two
    scopes, the market plumbing with the dosing, and `Serving` alone on `discharged`, since the
    documents and not any effect write the claims it reads."""
    agents, _, _ = _allotment(monkeypatch)
    for name, runtime in agents.items():
        scopes = _scopes(runtime)
        assert len(scopes) == 2, f"{name}: two scopes, not one per plot for a heating nothing can take: {scopes}"
        assert not [s for s in scopes if "Heating" in s], f"{name}: the heating is in no scope: {scopes}"
        assert {"Serving", "discharged"} <= min(scopes, key=len), f"{name}: Serving stands alone: {scopes}"
        assert {"Dosing", "Calling", "Tendering", "Presenting", "Offering", "Clearing"} <= max(scopes, key=len), \
            f"{name}: the market plumbing and the dosing are one scope: {scopes}"
        #  AND THE WAIT IN BOTH (#920): the planning package's own action, which no document of this
        #  world names and which touches no atom, is in every scope the partition makes.
        assert all("Wait" in s for s in scopes), f"{name}: the wait is in every scope: {scopes}"


def test_the_present_reading_and_its_foreseen_prediction_are_one_way_of_failing(monkeypatch):
    """Readable, the market's texts leave the allotment more than one scope, and the grower is no
    member of `Serving`'s — so the grower's IRI, which an observation names as whose it is and a
    prediction's copy does not, is not "a member of every scope", and keyed the present's trouble
    apart from the foreseen's: two want graphs under one name, two roots, and the plan placed from
    the foreseen ground twenty minutes out, where the test's rounds never reached it. The holder's
    own IRI is never part of a trouble's key (#908): one want, one open stretch, placed from the
    present. Found at four scopes, the grower a member of two; it holds at two (#913)."""
    agents, _, time = _allotment(monkeypatch)
    rose = agents["rose_grower"]
    scopes = _scopes(rose)
    assert len(scopes) > 1 and [s for s in scopes if "rose_grower" not in s], \
        f"the premise: a scope the grower is no member of, so the every-scope rule does not take it out of the key: {scopes}"
    rose.deliver("sensors/rose_probe/reading", b'{"value": 0.2}', time.at)
    rose.run(passes=1, poll_s=0)
    wants = [(r["g"], r["s"], r.get("e")) for store in rose.parts["planning"].planner.imaginaria.values()
             for r in rows(store, f"""SELECT ?g ?s ?e WHERE {{ GRAPH <{catalogue_of(store)}> {{
                 ?g a planning:WantGraph ; dcterms:temporal ?p . ?p orexis:start ?s OPTIONAL {{ ?p orexis:end ?e }} }} }}""", ())]
    assert len(wants) == 1 and wants[0][2] is None, f"one want graph over one open stretch, not one per ground: {wants}"
    assert datetime.fromisoformat(wants[0][1]) < NOW + timedelta(minutes=1), f"in trouble from the present: {wants}"
    committed = rows(rose.beliefs, f"""SELECT ?s WHERE {{ GRAPH <{catalogue_of(rose.beliefs)}> {{
        ?g a execution:CommittedStepGraph ; dcterms:temporal/orexis:start ?s }} }}""", ())
    assert committed and max(datetime.fromisoformat(r["s"]) for r in committed) < NOW + timedelta(minutes=2), \
        f"the plan is placed from the present, not from the foreseen ground at the reading's instant plus twenty minutes: {committed}"


def test_a_dry_plot_is_watered_by_a_claim_bought_on_the_supplier_s_venue(monkeypatch):
    agents, bus, time = _allotment(monkeypatch)
    rose, supplier = agents["rose_grower"], agents["supplier"]
    rose.deliver("sensors/rose_probe/reading", b'{"value": 0.2}', time.at)
    agents["fern_grower"].deliver("sensors/fern_probe/reading", b'{"value": 0.45}', time.at)
    _run(agents)
    assert bus.told("supplier"), "the dry grower called for a round"
    assert ("water", "true") in _facts(rose, "open"), "the supplier offered a round, and the grower believes it"
    assert ("water", "true") in _facts(agents["fern_grower"], "open"), "offered to every bidder on the venue"
    assert any(b"Bid" in p for p in bus.told("supplier")), "the dry grower tendered"
    assert not bus.commands(), "nothing is served before the round clears"

    time.at += timedelta(seconds=31)
    _run(agents)
    (claim, holder), = _facts(rose, "heldBy")
    assert holder == AL + "rose_grower", "the round cleared, and the rose won the lot"
    assert _facts(rose, "amountL") == {(claim, "0.5")}, \
        "0.2 against a middle of 0.45 at two litres a fraction asks half a litre, all the lot"
    assert _facts(rose, "pricePerL") >= {(claim, "3")}, "pay-as-bid: the claim costs what the rose bid"
    assert _facts(supplier, "presented") == {(claim, "true")}, "the rose presented it"
    assert bus.commands() == [("actuators/rose_valve/command", {"dose_ml": 500})], "and the supplier served it"
    assert _facts(rose, "discharged") == {(claim, "true")}, "and told the rose it was discharged"
    assert not _facts(rose, "holdsClaimOn"), "so the rose holds it no longer"

    time.at += timedelta(minutes=5)
    rose.deliver("sensors/rose_probe/reading", b'{"value": 0.45}', time.at)
    _run(agents)
    assert rose.parts["execution"].executor.walking() == [], "the reading answered the presentation"
    assert len(bus.commands()) == 1, "one dose, and nothing more once the plot is watered"


def test_one_lot_goes_to_the_dearer_bid_and_the_other_grower_calls_again(monkeypatch):
    """Both plots dry, one lot of half a litre. The rose asks half a litre at three a litre, the
    fern four tenths at two: pay-as-bid gives the whole lot to the rose. The fern's tender is never
    answered, so past its patience its intention fails, it calls again, and the next round is its
    alone."""
    agents, bus, time = _allotment(monkeypatch)
    agents["rose_grower"].deliver("sensors/rose_probe/reading", b'{"value": 0.2}', time.at)
    agents["fern_grower"].deliver("sensors/fern_probe/reading", b'{"value": 0.25}', time.at)
    _run(agents)
    time.at += timedelta(seconds=31)
    _run(agents)
    assert bus.commands() == [("actuators/rose_valve/command", {"dose_ml": 500})], "the rose won the first lot"
    assert not _facts(agents["fern_grower"], "heldBy") - _facts(agents["rose_grower"], "heldBy"), \
        "the fern won nothing, and knows only of the rose's claim"
    agents["rose_grower"].deliver("sensors/rose_probe/reading", b'{"value": 0.45}', time.at)

    time.at += timedelta(seconds=120)
    _run(agents)
    #  THE SECOND ROUND CLEARS WHEN ITS PERIOD ENDS, and where that falls on this clock depends on how
    #  many times the agents read it — every read is a second — so the test waits for the round, a
    #  round's length at a time, and not for a count of reads.
    for _ in range(3):
        time.at += timedelta(seconds=31)
        _run(agents)
        if len(bus.commands()) > 1:
            break
    assert bus.commands() == [("actuators/rose_valve/command", {"dose_ml": 500}),
                              ("actuators/fern_valve/command", {"dose_ml": 400})], \
        "the fern called again, won the second round alone, and was served four tenths of a litre"
