"""Sensing — capabilities over one shared ingest path, split by WHO HOLDS THE CLOCK.

Which one an agent gets is decided by its **hardware**, and derived at genesis from the
device's own nature:

- **sensing:Polling** (`sensing:PolledProcedure` device) — the agent's own timer; it asks for each reading and the
  device replies. The simplest exchange and the most agent control, but it needs a device that
  is reachable at any moment. **Not implemented**: no rule grants it and no class here
  provides it, because a board that deep-sleeps cannot hear the request. The room is kept
  deliberately — see ontology.ttl.
- **sensing:Subscribing** (`sensing:ScheduledProcedure` device) — the agent states an interval and the device
  keeps to it. The agent still decides how often to look; what it delegates is the
  timekeeping, which is exactly what lets the device sleep in between.
- **sensing:Listening** (`sensing:PushProcedure` device) — the device announces on its own clock and takes no
  orders. The agent records what arrives, and that is all it can do.

What survives the whole range is the **freshness judgment**: however the reading arrived, the
agent decides how stale it may be before it stops trusting it, because that is about belief
rather than control. What does not survive is the interval — a listening agent is never asked
for one, since it could not apply it. That asymmetry is enforced by shapes.ttl, not by
convention.

Two things deliberately do NOT appear here:

- **A protocol.** How a device is spoken to is a driver's business (`transports/`), chosen per
  sensor from what the world says about it — so an agent may hold one sensor on a bus and
  another on a wire under a single attention policy.
- **What counts as trouble.** Sensing knows how to look and how fresh a number is; it has
  no band and no target, because those belong to whoever holds a stake in the subject. So it
  *asks* — `choir.annotations` for what to say about a reading
  publicly — and an agent with no stake simply gets no answer and watches at its slow cadence.
  That is why nothing here imports another capability.

Everything touched is discovered: which sensors (`sensing:polls`), what property they read
(`sosa:observes`), and where to announce a sensing (`mqtt:eventTopic`).

Vocabulary: capabilities/sensing/ontology.ttl. Rules: capabilities/sensing/shapes.ttl.
Derivation: capabilities/sensing/rules.ru. See knowledge/domain/sensing.md.
"""

from __future__ import annotations

import uuid
from dataclasses import replace as _replace
from datetime import timedelta, datetime, timezone
from pathlib import Path

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    #  Annotation-only (#455): named in hook signatures, constructed nowhere at import.
    from orexis_agent_deliberation.want import Want
from .driver import driver_for
from agent.module import Module, contributes
from orexis_agent_progression.ontology import HANDLE, SUBSCRIPTIONS, PREDICTED, REPREDICT, WITNESS
from orexis_agent_progression.ontology import STATE_GRAPH, picks_graph
from orexis_agent_progression.ontology import OREXIS

#  What a look is ABOUT — one of the parameters sensing:Observing declares it takes.
ABOUT = OREXIS + "about"
from orexis_agent_progression.store import bindings


from . import pointer
#  The picks are touched, not imported (#455): `beliefs` builds them on first attribute
#  access, so a sensing-only assembly never loads the layer that defines `Picks`.
from . import beliefs as picks
from .observation import Observations
from . import choir
from .regions import Gap, Region, aims_of, gaps_of, regions_of
from .wiring import sensors_of
from . import readings
from .scaling import scaling_for
from .terms import (NS, INSTRUMENTS_GRAPH, ANNOTATE, BOUNDS, READING_RECORDED, FRESHNESS, LISTENING, OBSERVING, PUSH, SCHEDULED, STALE_AFTER_S, WATCH_LIVE,
                    SUBSCRIBING)
from orexis_agent_progression.timer import Timer
from . import predictions
from orexis_agent_progression import clock
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import FORESEEN



#  What an instrument watches, asked of the world being judged. Not carried on the want:
#  a subject is the wiring's to say, and the wiring is public in every world the planner builds.
_WATCHED_BY = "SELECT ?subject WHERE { %s sensing:monitors ?subject } LIMIT 1"




# The constitutional bounds are stated in the ontology, not compiled in here — and they hang
# off the capability FAMILY, so every transport and every future sensing inherits them.
_BOUNDS_Q = """
SELECT ?min ?max ?relax WHERE {
  GRAPH ?g { sensing:SensingCapability sensing:minSleepS ?min ; sensing:maxSleepS ?max .
             OPTIONAL { sensing:SensingCapability sensing:relaxFactor ?relax } }
} LIMIT 1"""


class SensingModule(Module):
    """Shared ingest: record what a sensor read, announce it, keep a freshness rule.

    Identical whether the reading was asked for or simply arrived.
    """

    # Which kind of device this module is for. The derivation grants the capability from the
    # sensor's sensing:senseMode; this is the same pairing, read from the other side.
    SENSE_MODE: str | None = None

    def __init__(self, agent):
        super().__init__(agent)
        # MINE, not the agent's. An agent may hold sensors of different modes, and it derives a
        # capability for each — but a module that took all of them would aim a cadence at a device
        # that takes no orders, and swallow readings from one it never re-aims. The derivation
        # split the capabilities; this splits the sensors the same way.
        wired = sensors_of(self.agent.beliefs.reader(PUBLIC), self.me.uri)
        self.sensors = tuple(s for s in wired
                             if self.SENSE_MODE is None or s.sense_mode == self.SENSE_MODE)
        unclaimed = [s.local_id for s in wired if s not in self.sensors]
        if unclaimed:
            self.log.debug("%s: not mine — %s", self.name, ", ".join(unclaimed))

        # one driver per sensor, chosen from its binding — not from anything the agent believes
        self.drivers = {s.uri: driver_for(s, self.publish) for s in self.sensors}
        for sensor in self.sensors:
            if self.drivers[sensor.uri] is None:
                self.log.warning("%s states no binding I can speak — it will never be read",
                                 sensor.local_id)

        # And one scaling, chosen the same way and for the same reason: what turns a raw
        # value into a quantity is a fact about the DEVICE, not about the agent watching it.
        # Today every sensor gets the identity member, because the firmware scales before it
        # publishes — the stage is not absent, it is set to identity. See issue #26.
        self.scalings = {s.uri: scaling_for(s) for s in self.sensors}
        for sensor in self.sensors:
            if self.scalings[sensor.uri] is None:
                self.log.warning("%s names a scaling this build does not carry — it will "
                                 "never be read", sensor.local_id)

        # Recording is one place for every capability that records — see observation.py.
        self.observations = Observations(agent, self.sensors)
        #  THE INTENDED BRANCHES (#639): every keyed fact a standing step predicts, as the
        #  keeper tells them — folded into the predictions from each step's landing, and what
        #  every reading of the key is compared with once, at arrival.
        self._predicted: dict = {}
        #  One deadline per (subject, property): when this agent stops trusting that reading.
        self._staleness: dict = {}
        #  THE REGIONS this agent holds — deduced by my own `desires.ru` from what its subject
        #  states it needs, read once here. They were the kernel's deducer's, and every
        #  question about them is a question about a reading, so they are mine now
        #  (the-stake-is-sensings-want). Every sensing module the agent composes reads the
        #  same ones, and `Agent.considering` folds a want seen twice into one by its node.
        self.regions: dict[str, Region] = regions_of(self.agent.beliefs.reader(PUBLIC), self.me.uri)
        #  And the AIM inside each — the agent's own pick, a belief, which a review may move.
        self._aims: dict[str, float] = aims_of(self.agent.desires.query, self.agent.id,
                                               self.me.uri)
        if self.regions:
            self.log.info("wants %s", ", ".join(
                f"{p.rsplit('#', 1)[-1]} in {r.low:g}..{r.high:g}"
                for p, r in sorted(self.regions.items())))
        #  What I have already written down, so publishing is a no-op until the answer moves.
        #  Nothing is published from HERE: `SubscribingModule` fills its cadence dicts after
        #  `super().__init__()` returns, so asking what rhythm is in force during construction
        #  reaches attributes that do not exist yet. `start()` is after everyone is built.
        self._published: dict[str, int] = {}
        #  Which declared measure answers for which property — resolved once and kept,
        #  because a property's KIND is public-graph stable and the planner asks per node.
        self._measures: dict[str, str | None] = {}
        #  And what each instrument watches, for the same reason: wiring is public-graph
        #  stable and the planner asks the freshness measure once per node.
        self._watching: dict[str, str] = {}


    def _answer(self, query, text: str) -> float | None:
        """Run one substituted measure against one world, or say nothing.

        Shared by both kinds because the failure story is the same for both: a package's bug
        must not take an agent down, and a caller reads silence as the maximal 1.0 rather
        than as no urgency.
        """
        try:
            rows = bindings(query(text))
        except Exception as exc:
            self.log.error("my measure would not run: %s", exc)
            return None
        if not rows or rows[0].get("urgency") is None:
            return None
        return float(rows[0]["urgency"])

    def _watched(self, query, instrument: str) -> str:
        """What that instrument is pointed at, as a term ready to substitute.

        Read from the world rather than from `me.acts_for`, and that difference is the whole
        of why the loner's water butt is watched at all: an agent may poll an instrument
        aimed at something it does not act for, and a measure asking about its own subject
        would have judged the butt's freshness by the plant's readings.
        """
        if instrument not in self._watching:
            rows = bindings(query(_WATCHED_BY % f"<{instrument}>"))
            self._watching[instrument] = (f"<{rows[0]['subject']}>" if rows
                                          else "<urn:nobody>")
        return self._watching[instrument]

    def stale_after_s(self, subject_uri: str) -> int:
        """How old a reading of this subject may be before I stop trusting it.

        A method rather than a number because the answer depends on who holds the clock. Where
        the agent sets the interval it must be relative to that interval; where the device keeps
        its own, an absolute is the only thing the agent can state.
        """
        raise NotImplementedError

    def publish_horizon(self, sensor=None) -> None:
        """Write down how old a reading of mine may be — `stale_after_s`, per sensor, as a fact.

        The number was process state until #240: `sent_cadence` and `acked_cadence` are dicts on
        this module, so the horizon they yield died with the process and no query could ask for
        it. That was tolerable while only Python judged freshness. It stopped being tolerable
        when freshness became a WANT, because a want is a shape and a shape cannot run a method.

        What is published is the ANSWER, not the inputs. A shape that recomputed cadence-plus-
        grace would be a second definition of the same figure, free to drift from this one the
        first time the fallback chain changed; a shape carrying a baked constant would be wrong
        within a tick, since the cadence is re-commanded whenever urgency moves. Publishing what
        the method returns leaves exactly one definition and nothing to disagree with it.

        Idempotent and cheap: the store is only touched when the answer actually moves, which is
        when a cadence is commanded or acknowledged rather than on every reading.
        """
        for aimed in ([sensor] if sensor is not None else self.sensors):
            horizon = int(self.stale_after_s(aimed.subject, aimed.observes))
            #  AND WHETHER THE WATCH IS LIVE (#512), the same way and for the same reason:
            #  a held claim waits for it, and a wait the keeper keeps is a select over
            #  beliefs, which a method cannot be.
            live = bool(self.watch_is_live(aimed.subject, aimed.observes))
            if self._published.get(aimed.uri) == (horizon, live):
                continue
            self._published[aimed.uri] = (horizon, live)
            self.agent.beliefs.update(f"""
                DELETE {{ GRAPH <{INSTRUMENTS_GRAPH}> {{
                    <{aimed.uri}> <{STALE_AFTER_S}> ?was ; <{WATCH_LIVE}> ?live }} }}
                WHERE  {{ GRAPH <{INSTRUMENTS_GRAPH}> {{
                    <{aimed.uri}> <{STALE_AFTER_S}> ?was .
                    OPTIONAL {{ <{aimed.uri}> <{WATCH_LIVE}> ?live }} }} }} ;
                DELETE WHERE {{ GRAPH <{INSTRUMENTS_GRAPH}> {{ <{aimed.uri}> <{WATCH_LIVE}> ?l }} }} ;
                INSERT DATA {{ GRAPH <{INSTRUMENTS_GRAPH}> {{
                    <{aimed.uri}> <{STALE_AFTER_S}> {horizon} ;
                                  <{WATCH_LIVE}> {"true" if live else "false"} }} }}""")

    @contributes(SUBSCRIPTIONS)
    def subscriptions(self) -> list[str]:
        # exactly my own sensors, and only where their binding listens at all — never a
        # wildcard, so the access grant stays visible in the subscription itself
        return [t for s in self.sensors if self.drivers[s.uri]
                for t in self.drivers[s.uri].subscriptions(s)]

    def start(self) -> None:
        """Say what I will treat as stale, before anything asks. A listening agent's horizon is
        constant and still has to be written down: a want that cannot find the number reads a
        reading of any age as fresh, which is the silent direction to fail."""
        self.publish_horizon()
        #  AND WHICH STEPS STAND (#639): a tell this module was not there to hear is gone, and
        #  the keeper's ledger is not — so the intended branches are asked for before the
        #  predictions below are written, and the ladder shows them from the first.
        if (keeper := self.agent.keeper) is not None:
            for p in keeper.predicted():
                self._intend(p)
        #  AND WHICH OF MY READINGS ARE ALREADY COLD (#598). A timer does not survive a
        #  restart and a belief does, so the horizon on every standing reading is re-armed
        #  here — and one already past it is marked at once, rather than waiting a whole
        #  horizon for a deadline that should have landed while the process was down.
        for sensor in self.sensors:
            self.watch_staleness(sensor.subject, sensor.observes)

    def stop(self) -> None:
        for timer in self._staleness.values():
            timer.stop()
        self._staleness.clear()
        self.observations.close()

    # --- a reading is stale, or it is not (#598) ---------------------------------------

    def watch_staleness(self, subject_uri: str, observed_property: str) -> None:
        """Arm the deadline that says this reading has stopped being evidence about now.

        A reading's age used to be arithmetic: the freshness measure and the want derived from
        it both asked `?at + horizon > NOW()` of every candidate world, which is the REAL now
        inside a search and therefore an answer about a world nobody is in. The fact is
        written instead, by this deadline landing on the loop, and every reader asks a triple.

        One timer per (subject, property), replaced by each new reading — the sensed graph
        upserts one node per pair, so a fresh reading takes the old node and its
        `sensing:staleSince` with it, and the deadline that was counting for the old one has
        nothing left to mark.
        """
        key = (subject_uri, observed_property)
        if (running := self._staleness.pop(key, None)) is not None:
            running.stop()
        reading = readings.current_reading(self.agent.beliefs.reader(PUBLIC), subject_uri,
                                           observed_property)
        if reading is None or reading.result_time is None:
            return                      # nothing to go cold; the want reads unmeasured
        try:
            horizon = float(self.stale_after_s(subject_uri, observed_property))
        except Exception:               # noqa: BLE001 — a rhythm nobody can state
            horizon = None
        if not horizon:
            #  NOT KNOWING IS MAXIMAL (#342): a sensor whose horizon this agent cannot state
            #  is not one whose readings can be shown to be current, so the reading is cold
            #  on arrival rather than fresh for ever.
            self.went_stale(subject_uri, observed_property)
            return
        left = horizon - (reading.age_s() or 0.0)
        if left <= 0:
            self.went_stale(subject_uri, observed_property)
            return
        timer = Timer(left, lambda: self.went_stale(subject_uri, observed_property),
                      repeat=False)
        self._staleness[key] = timer
        timer.start()
        #  AND WHAT I PREDICT (#642): the same horizon is the first window, the one the next
        #  reading is held to, and the drifts say what the reading may be at every horizon the
        #  packages list — written as graphs holding during their windows.
        predictions.write(self.agent, self.me.uri, subject_uri, observed_property, reading, horizon,
                          float(getattr(self.beliefs, "grace_s", 0) or 0),
                          intended=self._intended(subject_uri, observed_property))

    def went_stale(self, subject_uri: str, observed_property: str) -> None:
        """The horizon ran out: write it on the reading, and say so upward.

        Waking the seam is the half that makes this more than bookkeeping. A want about
        knowing becomes unmet the moment its reading goes cold, and until now nothing noticed
        until the agent happened to deliberate for another reason.
        """
        from orexis_agent_deliberation import reviser

        self._staleness.pop((subject_uri, observed_property), None)
        #  NOW() BELONGS HERE, and nowhere a search can reach it: this is the sense of time
        #  itself, on the loop, writing down what it noticed. `tests/test_clockless.py` holds
        #  the rules, measures and shapes deliberation evaluates to asking no clock at all.
        self.agent.beliefs.update(f"""
INSERT {{ GRAPH <{STATE_GRAPH}> {{ ?obs sensing:staleSince ?now }} }}
WHERE {{ GRAPH <{STATE_GRAPH}> {{
  ?obs sosa:hasFeatureOfInterest <{subject_uri}> ;
       sosa:observedProperty <{observed_property}> .
  FILTER NOT EXISTS {{ ?obs sensing:staleSince ?was }} }}
  BIND(NOW() AS ?now) }}""")
        #  The first prediction's window closed with no reading (#642): it is gone, and what
        #  remains predicts from a reading that is now stale — a missed expected event is what
        #  staleness is, said once.
        predictions.drop_first(self.agent, subject_uri, observed_property)
        for want in self.wants_about(observed_property, subject_uri):
            if want.is_epistemic:
                reviser.wake(self.agent, want.uri)

    @contributes(HANDLE)
    def handle(self, topic: str, payload: bytes) -> bool:
        """Offer the message to EVERY sensor that owns this channel, not just the first.

        One board carrying two peripherals is one MQTT client with one credential, so it
        publishes one message and its sensors share a topic — each taking its own value out by
        pointer. Returning after the first match meant the second sensor never saw a message
        and reported nothing, silently: the topic was handled, so nothing upstream complained.

        The return value still means *this channel was mine*, which is true the moment any
        sensor owns it — including when the payload turned out to be unreadable. That is a
        statement about addressing, not about success.

        **One message is one instant.** The values in it were produced together — a DHT11
        answers with a single 40-bit frame and cannot be asked for temperature alone — so the
        arrival is stamped ONCE here and carried down, rather than each write asking the clock
        for itself. Stamping per write recorded a difference that never happened: the gap was
        however long this loop took, which #88's live run put at 25ms between two halves of one
        physical read. Arrival is the honest instant available to us; the moment a device
        timestamps its own readings, that is better and is `sosa:phenomenonTime` (#101).
        """
        mine = False
        at = clock.now()
        acknowledged = None  # message-level, like the instant: one board, one rhythm
        doc = self.parse(payload)
        if doc is not None and isinstance(doc.get("sleep_s"), (int, float)):
            acknowledged = int(doc["sleep_s"])
        if doc is not None and doc.get("wake") == "alarm":
            # The world spoke (#151): this reading exists because the value crossed a
            # commanded threshold, not because the heartbeat came due. Worth a line, because
            # it is the one arrival that means something happened rather than time passed.
            self.log.info("alarm wake on %s — the world crossed a commanded limit and said so",
                          topic)
        for sensor in self.sensors:
            driver = self.drivers[sensor.uri]
            if driver is None or not driver.owns(sensor, topic):
                continue
            if not mine and acknowledged is not None:
                self.on_cadence_ack(sensor, acknowledged)
            mine = True
            raw = driver.parse(sensor, payload)
            # The last stage: a raw value is what the device sent, a quantity is what it action.
            # A binding whose scaling this build lacks is treated exactly as an unreadable
            # payload — the sensor is reported unread rather than recorded unscaled, because
            # a number nobody could interpret is worse in the store than a gap.
            scaling = self.scalings[sensor.uri]
            value = None if raw is None or scaling is None else scaling.apply(sensor, raw)
            if value is None:
                # Named, because on a shared topic "unreadable payload" alone cannot say WHICH
                # sensor found nothing — and one sensor missing its field while its neighbours
                # read fine is the exact failure a pointer makes possible.
                self.log.warning("%s: nothing at %s in the payload on %s", sensor.local_id,
                                 sensor.reading_pointer or "/value", topic)
            else:
                self.ingest(sensor, value, at)
                self.record_prior_if_any(sensor, doc, at)
        return mine

    def record_prior_if_any(self, sensor, doc, at: datetime) -> None:
        """A crossing report may carry the last value seen while the world was still quiet.

        The series store cannot say "nothing happened", so it interpolates: a heartbeat at 0.15
        and an alarm half an hour later at 1.00 are drawn as a straight line, and every consumer
        reads a gradual soak where there was a jump of twenty-five seconds. The device knows
        which it was — it looked a hundred times in that window and every look but the last two
        was in-window — and an alarm says so. Recording it puts the corner where it belongs.

        The prior sits at the READING'S OWN POINTER one level down, so a sensor that reads
        `/moisture` finds its prior at `/prev/moisture` and a shared topic keeps working: three
        sensors on one message each find their own, exactly as they do for the live value.
        Absent for a heartbeat, and absent when the window broke on the device's first look —
        there is no prior sample then, and inventing one would be worse than the interpolation.
        """
        if not isinstance(doc, dict) or doc.get("wake") != "alarm":
            return
        prev = doc.get("prev")
        if not isinstance(prev, dict):
            return
        age = prev.get("age_s")
        if not isinstance(age, (int, float)):
            return
        try:
            raw = pointer.resolve(sensor.reading_pointer or "/value", prev)
        except (pointer.PointerError, TypeError, ValueError):
            # A prior that cannot be read is simply absent, exactly as the live value would be.
            # resolve() RAISES on a missing key rather than returning None, and treating it as a
            # falsy result would have let the exception out of handle() and dropped the whole
            # message — including the alarm the prior was only ever decorating.
            return
        if raw is None:
            return
        scaling = self.scalings[sensor.uri]
        value = None if scaling is None else scaling.apply(sensor, raw)
        if value is None:
            return
        self.observations.record_prior(self.log, sensor, value,
                                       at - timedelta(seconds=float(age)))

    def ingest(self, sensor, value: float, at: datetime | None = None) -> None:
        """Record what the sensor read, then re-aim if this capability can.

        `at` is when the message carrying this value arrived, so that every value out of one
        message shares one instant. Optional because a caller with no message in hand — a test,
        or a future path that synthesises a reading — has nothing better than now to offer.
        """
        self.observations.record(self.log, sensor, value, at)
        #  AND WHEN I WILL STOP TRUSTING IT (#598): the reading is evidence until the horizon
        #  runs out, and what says so is a fact this arms the deadline for. The upsert took the
        #  previous node and its `staleSince` with it, so the reading standing here is fresh.
        self.watch_staleness(sensor.subject, sensor.observes)
        self.on_reading(sensor, value, at)

    def on_reading(self, sensor, value: float, at=None) -> None:
        """What this capability does after recording. Subscribing re-aims; listening does not.

        `at` is the reading's instant, threaded through because a TREND is two readings and the
        time between them — and the store upserts observations, so the previous one survives
        nowhere but here."""

    def on_cadence_ack(self, sensor, acknowledged_s: int) -> None:
        """The board said which cadence this message was taken under (#135). Subscribing keeps
        it — the freshness rule follows the cadence IN FORCE, not the one requested — and
        listening ignores it, since a device that takes no orders has nothing to receipt."""

    def watch_is_live(self, subject_uri: str, observed_property: str) -> bool:
        """Whether a dose landing NOW would be seen at the fast cadence.

        The #132 question, answered where the clamps live. The base answer is True: a
        listening device pushes on its own clock and its watch is always as live as it gets —
        holding a claim for a rhythm nobody can tighten would hold it forever. Subscribing
        overrides with the #135 stamp: live means the board has ACKNOWLEDGED a cadence at or
        under my fast end, which is proof it heard the tightening rather than hope that it did.
        """
        return True

    def quiet(self) -> list[tuple[str, str]]:
        """Every sensor of mine that has delivered once and then gone silent past my rule.

        Answered by the base class for BOTH clocks: subscribing's limit is relative to the
        cadence in force and listening's is absolute, but `stale_after_s` already dispatches
        that, so the question is one question. A sensor that has NEVER delivered is deliberately
        not here — that is a different fault, said by `readings_total` sitting at zero — and the
        age comes off the metrics clock, which counts arrivals wherever they entered.
        """
        out = []
        for sensor in self.sensors:
            age = self.observations.reading_age_s(sensor.local_id)
            if age is None:
                continue
            limit = self.stale_after_s(sensor.subject, sensor.observes)
            if age > limit:
                #  The SENSOR is the key — one silence per sensor, however long it lasts.
                #  The line renders the age and therefore changes on every look; keying on it
                #  is what made one fault look like a fault-and-recovery per tick.
                out.append((sensor.local_id,
                            f"{sensor.local_id}: nothing for {age:.0f}s, past the "
                            f"{limit}s I allow"))
        return out

    @contributes(READING_RECORDED)
    def on_reading_recorded(self, subject_uri: str, observed_property: str, value: float) -> None:
        """Every reading is a look that happened, and a number for every want about it.

        Two things the kernel used to do by property and now does by want, because the ledger
        keys on the want and which wants a property carries is this package's to say
        (the-stake-is-sensings-want): the standing Observe for each is satisfied — the look
        is this module's act, and the reading arriving is the look done — and every standing
        step that predicted this reading is answered by it (#639): in the band it predicted,
        met; outside it at or after the step's landing, unmet; before the landing, nothing.
        Idempotent across two sensing modules on one agent: the second finds nothing
        standing, and an expectation answered once is claimed.
        """
        if (keeper := self.agent.keeper) is None:
            return
        for want in self.wants_about(observed_property, subject_uri):
            keeper.satisfy(OBSERVING, want.uri, "a reading arrived — the look happened")
        types = {r["t"] for r in bindings(self.agent.beliefs.query(f"""
SELECT ?t WHERE {{ GRAPH <{STATE_GRAPH}> {{
  ?o sosa:hasFeatureOfInterest <{subject_uri}> ; sosa:observedProperty <{observed_property}> ; a ?t }} }}""", self.agent.beliefs.graphs_of(PUBLIC)))}
        self._compare(keeper, subject_uri, observed_property, types)
        #  AND WHETHER THE MIND SHOULD HEAR OF IT (#632): the bands the reading IS against the
        #  bands the first prediction said it may be in — the one the next reading is held to, the first of the
        #  key, still standing here since the ladder is rewritten after this is told. The
        #  reviser holds the rule; this module hands it the two sets in its own words.
        if subject_uri == self.me.acts_for and (stake := self.stake_about(observed_property)) is not None:
            from orexis_agent_deliberation import reviser
            bands = self._bands()
            actual = frozenset(types & bands)
            expected = self._expected_bands(subject_uri, observed_property, bands)
            said = (f"{observed_property.rsplit('#', 1)[-1]} read "
                    f"{', '.join(sorted(b.rsplit('#', 1)[-1] for b in actual)) or 'nothing'} where "
                    f"{', '.join(sorted(b.rsplit('#', 1)[-1] for b in (expected or ()))) or 'nothing'} was expected")
            reviser.observed(self.agent, stake.uri, expected, actual, said)

    # --- which want a reading is about: this package's to say --------------------------

    def wants_about(self, observed_property: str, subject_uri: str | None = None) -> list:
        """Every want this agent holds about a property — its stake, if it acts for the
        subject, and the freshness want of each instrument that reads it.

        AS THE CONTAINER PRESENTS THEM (#618): while a want derived under a root stands, the
        agent is considering THAT, under its own name, and an actor holding a reading must key
        its commitment, its expectation and its mark on the name the ledger holds."""
        return [w for w in self.agent.considering()
                if getattr(w, "observed_property", None) == observed_property
                and (w.is_epistemic or subject_uri in (None, self.me.acts_for))]

    def want_about(self, observed_property: str):
        """WHICH of a property's wants is the one to act on — the rule, stated once: an unmet
        epistemic want first, then the stake, then whatever is left.

        KNOWING FIRST, then the number, and the order is a rule rather than a ranking. A
        property carries two wants — the region it should sit in, and that its instrument
        has spoken recently — and taking whichever is HOTTER would decide between two
        different questions by a number that means the same thing in both. No lever moves a
        number you cannot see, so an actuator asking whether to dose a pot nobody has looked
        at lately is told to look; once the reading is current the stake answers. This was
        the deliberator's `desire_about`; the actors' door is `execution.pursue_for(want)`.
        """
        mine = self.wants_about(observed_property)
        return (next((d for d in mine if d.is_epistemic and not d.is_met), None)
                or next((d for d in mine if not d.is_epistemic), None)
                or next(iter(mine), None))

    def stake_about(self, observed_property: str):
        """The region want about a property, or None — what a bidder or an actuator commits
        to, and what the keeper's rows for their acts pursue."""
        return next((d for d in self.wants_about(observed_property) if not d.is_epistemic), None)

    def awaiting_feedback(self, subject_uri: str, observed_property: str) -> bool:
        """Is something of mine in flight for this property — a step standing or an expectation
        still open — so that the world owes a movement I must be looking to see?

        THE CADENCE'S WHOLE INPUT, and it used to be a number. A reading was scored by the
        declared measure and the sleep interpolated between the slow and fast bounds by it, so
        a board watched harder the nearer a reading sat to trouble. That is gone with the
        measure, and the sovereign's ruling names what the cadence was always for: *sense
        frequently when we executed something and wait for feedback.* It is progression's
        question, not an observation's — which is why it is asked of the KEEPER and of nothing
        else, and why the two answers it used to merge fold into one. The keeper's own was an
        open expectation; the market's was a claim held with a step standing to present it,
        contributed through sensing's choir because the cadence was the only reader. Neither
        needs a hook: `standing` takes the action as an OPTION, so this asks whether anything
        stands without naming a word of the market's.

        BOUNDED BY THE PATIENCE, which both halves carried for the same reason: a step nothing
        resolves must not hold the fast cadence for ever, and an expectation is bounded by its
        own deadline. A dead sensor cannot pin the board awake.

        What ATTENTION should properly be is the sovereign's to decide; this is the unlink.
        """
        keeper = self.agent.keeper
        if keeper is None or subject_uri != self.me.acts_for:
            return False
        now = clock.now()
        for want in self.wants_about(observed_property):
            if keeper.expecting(want.uri):
                return True
            if any(s.age_s(now) <= keeper.beliefs.patience_s
                   for s in keeper.standing(want=want.uri)):
                return True
        return False

    def sense_now(self) -> None:
        """Ask for a reading now, if my hardware allows it. Listening cannot.

        Best-effort even where it is allowed: a device that sleeps between readings only hears
        this if the nudge happens to land inside its waking window. It is the seed of
        sensing:Polling, not a substitute for it — a real polling module would need a device that
        is always listening, and would then drive every reading this way.
        """

    #  ---- the region, and what a reading means against it -------------------------------
    #
    #  These were the kernel's deducer's: the band, the urgency, the bounds a board should watch,
    #  the gaps, the stakes contributed to what the agent pursues. Every one of them is a
    #  verdict on an OBSERVATION, and the kernel no longer knows what one is.

    def region(self, observed_property: str) -> Region | None:
        """The agent's region in one property, or None if it holds no stake in it.

        Whoever wants, and this says what it wants — so a bid, a dose or a cadence can be
        computed against the agent's ends without anything importing this package: through
        `agent.providers(SENSING)`, or through the choir hooks below.
        """
        return self.regions.get(observed_property)

    def aim(self, observed_property: str) -> float | None:
        """The point the agent is steering this property toward, or None if it picked none.

        A consumer that requires one (a bidder pricing a deficit) treats None as its own
        refusal; nothing here defaults to the region's centre, because a fabricated preference
        is still a fabricated belief.
        """
        return self._aims.get(observed_property)

    def on_belief_revised(self, belief_term: str, value) -> None:
        """An aim is a belief, so a review may move it — within the region, which is the same
        check boot makes. Re-read rather than patched: the revision names a term and an aim is
        a structure, so the simplest correct answer is to ask the graph again."""
        self._aims = aims_of(self.agent.desires.query, self.agent.id, self.me.uri)

    def _is_mine(self, subject_uri: str, observed_property: str) -> bool:
        """A stake is in one property of the one subject the agent advances. Both have to
        match: handed a temperature against a moisture region the honest answer is no opinion,
        and 21.0 read as a moisture fraction would score as perfectly comfortable."""
        return subject_uri == self.me.acts_for and observed_property in self.regions

    @contributes(ANNOTATE)
    def annotate(self, subject_uri: str, observed_property: str, value: float) -> dict:
        """The verdict on the agent's own subject, for its public announcement — a band and
        never a number: a listener learns that it is in trouble, not how wet it is."""
        if not self._is_mine(subject_uri, observed_property):
            return {}
        return {"band": self.regions[observed_property].band(value)}

    @contributes(BOUNDS)
    def bounds(self, subject_uri: str, observed_property: str) -> tuple[float, float] | None:
        """The region's edges — what a crossing-watching board is told to announce on leaving
        (#151). The REGION and not the survival envelope, deliberately: waking at the edge of
        comfort is what makes the announcement early enough to act on."""
        if subject_uri != self.me.acts_for:
            return None
        region = self.regions.get(observed_property)
        return (region.low, region.high) if region else None

    @contributes(PREDICTED)
    def predicted(self, predicted, standing: bool) -> None:
        """The keeper says which branch the agent intends (#639): an expectation opened on a step
        that predicts a reading of one of my keys, or closed. Kept here, folded into the
        predictions of the key from the step's landing on — the ladder is rewritten at
        once, so the sovereign reading the predictions sees the intended branch while the
        step stands and the drift's own after — and compared with every reading of the key
        at arrival. Only a `sosa:Observation` is mine to judge; a number a caller stated is
        held to the band it falls in, and the number stays in the residual."""
        SOSA = "http://www.w3.org/ns/sosa/"
        key = dict(predicted.key)
        subject_uri, observed_property = key.get(SOSA + "hasFeatureOfInterest"), key.get(SOSA + "observedProperty")
        if predicted.keyed_class != SOSA + "Observation" or subject_uri is None or observed_property is None:
            return
        if standing:
            self._intend(predicted)
        else:
            self._predicted.pop(predicted.intention, None)
        if any(x.subject == subject_uri and x.observes == observed_property for x in self.sensors):
            self.watch_staleness(subject_uri, observed_property)

    def _intend(self, predicted) -> None:
        """Keep one intended branch — its bands stated by the step, or read off the number a
        caller stated. A number no band of mine holds cannot be judged, and the expectation can
        only lapse; said once."""
        SOSA = "http://www.w3.org/ns/sosa/"
        key = dict(predicted.key)
        if not predicted.bands:
            bands = self._bands_for(key.get(SOSA + "hasFeatureOfInterest"),
                                    key.get(SOSA + "observedProperty"), predicted.value)
            if not bands:
                self.log.warning("no band of mine holds %s for %s: the expectation can only lapse",
                                 predicted.value, predicted.intention.rsplit("#", 1)[-1])
                return
            predicted = _replace(predicted, bands=bands)
        self._predicted[predicted.intention] = predicted

    def _intended(self, subject_uri: str, observed_property: str) -> list:
        SOSA = "http://www.w3.org/ns/sosa/"
        return [p for p in self._predicted.values()
                if dict(p.key).get(SOSA + "hasFeatureOfInterest") == subject_uri
                and dict(p.key).get(SOSA + "observedProperty") == observed_property]

    def _bands_for(self, subject_uri: str | None, observed_property: str | None,
                   value: float | None) -> frozenset:
        """The band a number falls in, for a subject I act for: the member class the world
        minted for the subject and property under the family the region says — and the
        family beside it, as a reading carries both."""
        if value is None or subject_uri != self.me.acts_for:
            return frozenset()
        region = self.regions.get(observed_property)
        if region is None:
            return frozenset()
        family = ("BelowRegion" if value < region.low else
                  "AboveRegion" if value > region.high else "InRegion")
        rows = bindings(self.agent.beliefs.query(f"""
SELECT ?b WHERE {{ ?b rdfs:subClassOf sensing:{family} ;
                   sensing:ofSubject <{subject_uri}> ; sensing:ofProperty <{observed_property}> }}""", self.agent.beliefs.graphs_of(PUBLIC)))
        if not rows:
            return frozenset()
        return frozenset({rows[0]["b"], NS + family})

    def _bands(self) -> frozenset:
        """Every band class the vocabulary declares — the three families and each member the
        world minted under them — read once: what of a reading's types is a band."""
        if not hasattr(self, "_band_classes"):
            families = (NS + "BelowRegion", NS + "InRegion", NS + "AboveRegion")
            rows = bindings(self.agent.beliefs.query(f"""
SELECT ?b WHERE {{ VALUES ?f {{ {' '.join(f'<{f}>' for f in families)} }} ?b rdfs:subClassOf ?f }}""", self.agent.beliefs.graphs_of(PUBLIC)))
            self._band_classes = frozenset(r["b"] for r in rows) | frozenset(families)
        return self._band_classes

    def _expected_bands(self, subject_uri: str, observed_property: str, bands: frozenset):
        """The bands the first prediction of this key says it may be in — the types of the
        first prediction standing for it — or None where no prediction stands."""
        graphs = predictions.graphs_of(self.agent.beliefs, self.agent.id,
                                       subject_uri.rsplit("#", 1)[-1], observed_property)
        if not graphs:
            return None
        rows = bindings(self.agent.beliefs.query(f"""
SELECT ?t WHERE {{ GRAPH <{graphs[0]}> {{ ?o sosa:observedProperty <{observed_property}> ; a ?t }} }}""", self.agent.beliefs.graphs_of(PUBLIC)))
        return frozenset(r["t"] for r in rows) & bands

    def _compare(self, keeper, subject_uri: str, observed_property: str, types: set) -> None:
        """One comparison per standing step this reading is about (#639): the reading IS the
        band the step predicted — every class the step stated is on it — or it is not. A
        reading dated at or before the expectation opened is the before. What is answered is
        the keeper's to carry on: residual, suspicion, advance or drop."""
        mine = self._intended(subject_uri, observed_property)
        if not mine:
            return
        reading = readings.current_reading(self.agent.beliefs.reader(PUBLIC), subject_uri, observed_property)
        if reading is None or reading.result_time is None:
            return
        for p in mine:
            if reading.result_time <= p.since:
                continue
            band = ", ".join(sorted(b.rsplit("#", 1)[-1] for b in p.bands))
            if p.bands <= types:
                keeper.answered(p.intention, True, f"answered as the step predicted: the reading "
                                              f"of {observed_property.rsplit('#', 1)[-1]} is {band}")
            elif reading.result_time >= p.lands_at:
                keeper.answered(p.intention, False, f"the step landed and the reading of "
                                               f"{observed_property.rsplit('#', 1)[-1]} is not {band} — "
                                               f"the world did not answer as the graph promised")

    @contributes(REPREDICT)
    def repredict(self) -> None:
        """A premise a prediction reads has moved (#643): every reading I hold is predicted
        again from where it stands, through the same path a reading arriving takes — the
        horizon re-armed, the ladder rewritten."""
        for sensor in self.sensors:
            if readings.current_reading(self.agent.beliefs.reader(PUBLIC), sensor.subject, sensor.observes) is not None:
                self.watch_staleness(sensor.subject, sensor.observes)

    @contributes(WITNESS)
    def witnessed(self, keyed_class: str, key: dict) -> float | None:
        """What the world shows now for a predicted observation — the current reading of the
        property on the subject the key names, for the residual the keeper writes at a
        verdict (#518). Only a `sosa:Observation` is sensing's to witness."""
        SOSA = "http://www.w3.org/ns/sosa/"
        if keyed_class != SOSA + "Observation":
            return None
        subject_uri = key.get(SOSA + "hasFeatureOfInterest")
        observed_property = key.get(SOSA + "observedProperty")
        if subject_uri is None or observed_property is None:
            return None
        reading = self.current_reading(subject_uri, observed_property)
        return float(reading.value) if reading is not None else None

    def gaps(self) -> dict[str, Gap]:
        """Where every property the agent wants stands against where it wants it — stale rows
        included. A dry pot read an hour ago is "last I looked I was dry, and I cannot see any
        more", which a deliberator needs precisely because nothing else will mention it."""
        return gaps_of(self.agent.desires.query, self.agent.beliefs.reader(PUBLIC),
                       self.me.uri, self.agent.id)

    def current(self) -> dict[str, Gap]:
        """The gaps whose reading is still evidence — the eyes that are open: a gap whose
        property has a MET freshness want. Issue #124's case holds by the same path: a dead
        probe's last observation is upserted and never expires, but its freshness want goes
        cold, and the gap stops counting as seen."""
        fresh = {getattr(d, "observed_property", None) for d in self.agent.considering()
                 if d.is_epistemic and d.is_met}
        return {prop: gap for prop, gap in self.gaps().items() if prop in fresh}

    def desires(self, now: datetime | None = None) -> list[Want]:
        """My contribution to what the agent is considering: its stakes and its freshness wants,
        the two kinds whose premise is an observation. The obligations are the ledger's."""
        from .rows import desires_of  # deferred (#455): same reason as ObservedWant above
        return desires_of(self.agent.desires.query, self.agent.beliefs.reader(PUBLIC),
                          self.me.uri)

    def reports(self) -> dict:
        """What the agent wants, how much of that it can currently see, and the worst of it —
        in the health series, because an agent whose regions silently went to nothing looks
        exactly like a content one on every other panel."""
        out: dict = {"desires": len(self.regions),
                     "sensed_write_failures": self.observations.sensed_failures}
        current = self.current()
        out["desires_measured"] = len(current)
        if current:
            out["worst_gap"] = round(max(abs(g.gap) for g in current.values()), 3)
        return out

    def series(self) -> list[tuple[str, dict, dict]]:
        """WHERE each want sits — one row per property, the property as a TAG, into the
        agent's own bucket (#61's argument extended to the regions): a region that quietly
        moved and an aim drifting inside it are exactly the lines a sovereign wants."""
        rows = []
        for prop, region in sorted(self.regions.items()):
            local = prop.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            fields = {"desired_low": region.low, "desired_high": region.high}
            aim = self.aim(prop)
            if aim is not None:
                fields["aim"] = aim
            rows.append(("agent_desire", {"property": local}, fields))
        #  And the health of every sensor this module hears — the counters that were the
        #  kernel's `Metrics` (metrics-are-an-aspect).
        return rows + self.observations.health_rows()

    def current_reading(self, subject_uri: str, observed_property: str):
        """The newest reading of one property of one subject, whatever its age — the door every
        other capability comes through, now that what a reading looks like is this package's."""
        return readings.current_reading(self.agent.beliefs.reader(PUBLIC), subject_uri, observed_property)

    def value_in(self, query, graph: str, subject_uri: str, observed_property: str):
        """What a property reads in the world `query` answers about, at `graph` — the planner's
        question about a candidate world, and an actor's when it sizes a step there."""
        return readings.value_in(query, graph, subject_uri, observed_property)

    def fresh_reading(self, subject_uri: str, observed_property: str):
        """The latest reading of one property, or None if it is older than I trust."""
        reading = readings.current_reading(self.agent.beliefs.reader(PUBLIC), subject_uri, observed_property)
        if reading is None:
            return None
        return reading if reading.is_fresh(self.stale_after_s(subject_uri, observed_property)) else None

    def sensor_for(self, subject_uri: str, observed_property: str):
        """Which of my sensors watches this property of this subject, if any.

        Two sensors may answer — two probes in one pot reporting the same property — and the
        first is returned. That case is a `sh:Warning` at validation rather than an error,
        because "these are one thing measured twice" is a legitimate wiring; see
        knowledge/decisions/one-agent-many-sensors.md.
        """
        return next((s for s in self.sensors
                     if s.subject == subject_uri and s.observes == observed_property), None)


class SubscribingModule(SensingModule):
    """sensing:Subscribing — derived from being wired to a device that keeps to a given interval.

    The standing request is the whole mechanism: the interval is published *retained*, so a
    device that is asleep now receives it the instant it wakes and subscribes. That is why
    this works against hardware the agent cannot otherwise reach.
    """

    CAPABILITY = SUBSCRIBING
    SENSE_MODE = SCHEDULED
    name = "subscribing"

    def __init__(self, agent):
        self.beliefs = agent.desires.read(picks.SUBSCRIBING_PICKS)
        # The jolt threshold is the agent's own pick, not the family's figure — it has to be,
        # because a review rewrites the agent's graph and nothing else. Optional, and absence
        # is a statement: no pick means band-only alarms.
        self.alarm_beliefs = agent.desires.read_optional(picks.ALARM_PICKS)
        super().__init__(agent)
        self.min_sleep_s, self.max_sleep_s, self.relax_factor = self._bounds()
        # The interval in force, which the freshness rule reads, and the whole last message,
        # which decides whether to send again. Two dicts because they answer different
        # questions: "how long may this board sleep" and "does it already know all this".
        self.sent_cadence: dict[str, int] = {}
        self.sent: dict[str, tuple] = {}
        # The trend: last reading seen and the slope it made with the one before, per
        # (subject, property). Module memory and nowhere else — the store upserts observations,
        # so history for a slope survives only here. Dies with the process; two readings
        # rebuild it, and until then there is simply no trend bound (#133).
        self._last_seen: dict[tuple[str, str], tuple[float, datetime]] = {}
        self._trend: dict[tuple[str, str], float] = {}
        # What the board SAID it is running, per channel (#135) — testimony, against
        # `sent_cadence`'s intent. The freshness rule prefers it, and the pair disagreeing on
        # two consecutive readings is the detector #37 never had: a cleared retained command
        # arrives here as a board acking its compile-time default.
        self.acked_cadence: dict[str, int] = {}
        self._ack_disputed: dict[str, tuple[int | None, int]] = {}

    def stale_after_s(self, subject_uri: str, observed_property: str) -> int:
        """The interval I asked for, plus slack. NOT an absolute.

        I chose this cadence, so refusing a reading that arrived exactly when I asked for it
        would be refusing my own instruction — which is what a fixed limit did, silently, every
        time a comfortable plant let the cadence relax past it.

        Per sensor, and therefore per property: two sensors on one subject can be running at
        different cadences, and holding the slower one's reading to the faster one's clock
        would report a healthy board as quiet.
        """
        sensor = self.sensor_for(subject_uri, observed_property)
        cadence = None
        if sensor is not None:
            key = sensor.command_topic or sensor.local_id
            # The board's own testimony beats my intent (#135): freshness follows the cadence
            # IN FORCE, and what is in force is what the board says it is running — a command
            # it never received, or clamped to its own floor, must not make its honest rhythm
            # read as gone-quiet, nor a stale reading as current.
            cadence = self.acked_cadence.get(key)
            if cadence is None:
                cadence = self.sent_cadence.get(sensor.local_id)
        if cadence is None:
            # Not aimed yet. Assume the slowest I would ask for, so a first reading is not
            # rejected for arriving on a schedule I have not set.
            cadence = self.beliefs.slow_sleep_s
        return int(cadence) + self.beliefs.grace_s

    def _bounds(self) -> tuple[int, int, float]:
        rows = bindings(self.agent.beliefs.query(_BOUNDS_Q, self.agent.beliefs.graphs_of(PUBLIC)))
        if not rows:
            raise RuntimeError("the ontology states no cadence bounds — re-run orexis-seed")
        # A relax factor at or below 1 could never release at all, which is a vocabulary slip
        # and not a policy anyone can mean; treated as "no slew" rather than as a frozen board.
        relax = float(rows[0].get("relax") or 0.0)
        return int(rows[0]["min"]), int(rows[0]["max"]), relax if relax > 1.0 else 0.0

    def start(self) -> None:
        """Ask for a look, and command an OPENING cadence instead of waiting to be told one.

        The cadence used to be computed only when a reading arrived, so at birth — a desired
        state, an empty sensed graph, the moment of maximum uncertainty — the board ran its own
        default until the first reading happened by. Now each sensor is aimed at once, from
        what the agent already holds: a fresh reading earns the gap's ordinary answer, and
        nothing (or something stale) asks the choir the OTHER question — how urgent is not
        knowing — which desire answers with the maximum for a property it wants held (#137).
        The burst relaxes by itself: the first current reading replaces ignorance's answer with
        the gap's, through the same recomputation every reading triggers.

        Scope, honestly: the ignorance ask happens here and not in the per-reading group
        recompute, because a real board reports every pointer in one message — its properties
        become measured together — and the one case that differs (a peer whose pointer never
        yields) is a broken payload, already visible as desires_measured diverging (#124).
        """
        super().start()
        self.sense_now()
        for sensor in self.sensors:
            reading = self.fresh_reading(sensor.subject, sensor.observes)
            value = reading.value if reading is not None else None
            self.set_cadence(sensor,
                             self.cadence_for(sensor.subject, sensor.observes, value),
                             choir.annotations(self.agent, sensor.subject, sensor.observes,
                                                    value) if value is not None else None)

    def on_reading(self, sensor, value: float, at=None) -> None:
        # The trend first, so the cadence computed below already knows it. Kept in module
        # memory and nowhere else: the store upserts observations (one per subject-property),
        # so the previous reading this slope needs would otherwise be gone — and a slope is a
        # verdict-adjacent quantity anyway, derived from my own readings, recomputed freely,
        # stored never. Dies with the process, rebuilt after two readings; the fallback while
        # it is unknown is simply no trend bound, which is the pre-#133 behaviour.
        self._note_trend(sensor.subject, sensor.observes, value, at)
        # The verdict travels with the cadence because it is the same message and the same
        # audience. Collected the way every cross-capability opinion is collected — whoever
        # holds a stake contributes, sensing passes it on without reading it. An agent with
        # no stake in this property contributes nothing and the device is told only a cadence.
        self.set_cadence(sensor,
                         self.cadence_for(sensor.subject, sensor.observes, value),
                         choir.annotations(self.agent, sensor.subject, sensor.observes, value))

    def watch_is_live(self, subject_uri: str, observed_property: str) -> bool:
        sensor = self.sensor_for(subject_uri, observed_property)
        if sensor is None:
            return False
        # A alarm-armed board IS a live watch (#151): a dose landing moves the value across
        # the commanded band edge and the board announces within its watching period, however
        # long the heartbeat. The thresholds must actually have gone out — the same dedup
        # memory that proves the channel has been spoken to proves what was said.
        if sensor.alarm and sensor.local_id in self.sent_cadence:
            return True
        acked = self.acked_cadence.get(sensor.command_topic or sensor.local_id)
        return acked is not None and acked <= self.beliefs.fast_sleep_s

    def on_cadence_ack(self, sensor, acknowledged_s: int) -> None:
        """Keep the board's testimony, answer it, and dispute it when it contradicts my intent.

        **An acked reading is a board waiting to be released (#152).** The board's post-publish
        wait now ends when my answer arrives, not when a timer expires — so silence is no longer
        an option, and the memory of what the channel was last told stops excusing one. Clearing
        it here means the set_cadence this reading is about to trigger always speaks, even when
        nothing changed: the reply IS the release. A reading without the field — old firmware,
        a test ingesting directly — keeps the old economy, because nobody is waiting for it.

        One mismatched ack is expected noise from pre-release firmware: the live response to the
        PREVIOUS reading lands in its fixed window, so the wake after a re-aim acks the old value
        once. (A releasing board sleeps exactly what it was answered, so its acks agree.) Two
        consecutive identical mismatches is the real thing — a command the board never received
        (#37's cleared-retained case) or one its firmware clamped — so that is when it is said
        out loud; the re-send it used to have to arrange happens by itself now.
        """
        key = sensor.command_topic or sensor.local_id
        self.sent.pop(key, None)
        self.acked_cadence[key] = int(acknowledged_s)
        #  The board's own testimony beats my intent, so it moves the published horizon as well
        #  — a rhythm clamped to a device's floor makes readings stale later, not sooner.
        self.publish_horizon(sensor)
        for peer in self._aimed_with(sensor):
            self.observations.cadence_acked(peer.local_id, int(acknowledged_s))
        commanded = self.sent_cadence.get(sensor.local_id)
        if commanded is not None and int(acknowledged_s) != int(commanded):
            dispute = (commanded, int(acknowledged_s))
            if self._ack_disputed.get(key) == dispute:
                self.log.warning(
                    "%s acknowledges %ss where %ss was commanded, twice running — the retained "
                    "command was cleared or clamped",
                    sensor.local_id, acknowledged_s, commanded)
            self._ack_disputed[key] = dispute
        else:
            self._ack_disputed.pop(key, None)

    def _note_trend(self, subject_uri: str, observed_property: str,
                    value: float, at) -> None:
        """Two readings and the time between them: the slope, in units per second."""
        at = at or clock.now()
        key = (subject_uri, observed_property)
        previous = self._last_seen.get(key)
        if previous is not None:
            prev_value, prev_at = previous
            dt = (at - prev_at).total_seconds()
            if dt > 0:
                self._trend[key] = (value - prev_value) / dt
        self._last_seen[key] = (value, at)

    def cadence_for(self, subject_uri: str, observed_property: str,
                    value: float | None = None) -> int:
        """How long the board may sleep: fast while something of mine is in flight for this
        property, slow otherwise.

        BINARY, AND THAT IS THE CHANGE. The sleep used to be interpolated between the two
        bounds by how urgent a reading was — `slow + (fast - slow) * urgency` — so a board
        watched harder the nearer the soil sat to its floor, and #133 added a second ask on
        the value PREDICTED at the end of the sleep, tighten-only, so a window could not open
        moments before a trend crossed into trouble. Both are gone with the measure, and what
        the sovereign's ruling puts in their place is the thing the cadence was always for:
        *sense frequently when we executed something and wait for feedback.* A board that
        watched a dry pot harder while nothing was being done about it was spending readings
        on a number no faster sampling would change.

        The trend is still MEASURED (`_note_trend`) because the predictions read it; nothing
        here asks it, because there is no longer a question to ask of a predicted value —
        whether a step is in flight is not something a slope foretells.

        Nothing in flight, or no stake in this property at all, is the same answer: the slow
        cadence, which is the honest reading of "the world owes me no movement here". That is
        why the property is passed — a thermometer on a pot the agent bids water for must not
        be paced by what the soil is doing. `value` is kept in the signature and unread: every
        caller has one in hand, and `watch_closely` reads it: this is asked from inside the
        pipeline that is about to store the reading, so the store cannot answer for it.
        """
        b = self.beliefs
        sleep_s = b.fast_sleep_s \
            if self.watch_closely(subject_uri, observed_property, value) else b.slow_sleep_s
        return int(round(min(self.max_sleep_s, max(self.min_sleep_s, sleep_s))))

    def watch_closely(self, subject_uri: str, observed_property: str,
                      value: float | None = None) -> bool:
        """Two facts, either of which earns the fast cadence — and neither is a measure.

        NOTHING READ YET is the first. An agent with a stake in a property and no current
        reading of it is not calm, it is BLIND, and the first intention is always to look:
        the opening burst before any reading exists, and the return to it when a probe goes
        quiet. This used to arrive as "not knowing is maximally urgent", which was the graded
        answer standing in for a fact — whether anything current is known is not a degree.

        SOMETHING IN FLIGHT is the second, and it is the sovereign's own: *sense frequently
        when we executed something and wait for feedback.*

        What is NOT here is how bad the reading is. A board used to watch a dry pot harder
        while nothing was being done about it, which spent readings on a number no faster
        sampling would change.
        """
        if not self._is_mine(subject_uri, observed_property):
            #  NO STAKE IN THIS PROPERTY OF THIS SUBJECT, so neither fact can apply: a
            #  thermometer on a pot the agent bids water for must not be paced by the soil,
            #  and an agent with no region here has nothing it is blind ABOUT.
            return False
        #  THE READING IN HAND FIRST, because this is asked from inside the pipeline that is
        #  about to store one: a store lookup here answers about the world BEFORE this reading
        #  and would leave a board bursting for ever. `value` is what the caller just read, or
        #  what `start` found on record; None with nothing on record is blind.
        if value is None and self.current_reading(subject_uri, observed_property) is None:
            return True
        return self.awaiting_feedback(subject_uri, observed_property)

    def _aimed_with(self, sensor):
        """Every sensor this one shares a command channel with, itself included.

        A cadence is a property of the BOARD, not of a property being measured: one device
        sleeps once, however many things it reads on waking. So the unit being aimed is the
        channel, and a sensor with no channel is alone in a group of one — nothing is sent for
        it and nothing is merged with it.
        """
        if not sensor.command_topic:
            return (sensor,)
        return tuple(s for s in self.sensors if s.command_topic == sensor.command_topic)

    def set_cadence(self, sensor, sleep_s: int, verdict: dict | None = None) -> None:
        """Standing policy for the CHANNEL this sensor is on, not for the sensor alone.

        Deduplicated on the whole message rather than on the interval alone. It used to skip
        when the cadence was unchanged, which is right for a cadence and wrong the moment
        anything else rides along: a pot drying from OK to LOW inside one cadence band would
        have kept the old verdict on its device indefinitely, because the only thing being
        compared had not moved.

        **What the memory means changed with #152.** It used to ask "does the board already
        know all this", across readings — the right economy while the board's post-publish wait
        was a fixed window that expired on its own. A board that waits to be RELEASED must be
        answered every time, so an acked reading clears the channel's memory before this runs
        (see on_cadence_ack) and the question left for `self.sent` is "have I answered THIS
        arrival yet": one board carrying several sensors triggers this once per sensor per
        message, the group recompute gives every call the same answer, and one release goes out
        instead of three copies of it.

        Keyed on the command topic, because one board carrying several peripherals has several
        sensors and ONE place to be instructed. Keyed per sensor, each would compute its own
        interval from its own urgency and publish it retained to the same topic — soil moisture
        asking for 30s and a thermometer with no stake asking for 900s, last writer winning, on
        every message. The board would be aimed by whichever sensor spoke last.

        So the TIGHTEST wins: if anything on this board is urgent, the board watches closely,
        and the properties that are not urgent are read more often than they need to be — which
        costs a reading and is the only safe direction to be wrong in.

        **The verdict travels with it, from the same sensor.** Verdicts used to be MERGED, on the
        reasoning that they are about different properties and the device shows all of them. That
        was true while exactly one module annotated exactly one property: every band that could
        arrive was a moisture band, and `dict.update` never collided with anything. It stopped
        being true when an agent could want more than one thing — two sensors on one board now
        both produce a `band`, the merge keeps whichever was computed last, and the board would
        display the comfort of one property while the other was the reason it is being read every
        thirty seconds. Taking the verdict of whichever sensor set the cadence makes the message
        internally consistent: one interval, and the reason for it.
        """
        group = self._aimed_with(sensor)
        if len(group) > 1:
            # Recompute the others from the last reading each of them has, so the answer does
            # not depend on which sensor happened to trigger this. A sensor that has not read
            # yet contributes nothing rather than a guess.
            claims = [(int(sleep_s), dict(verdict or {}))]
            for peer in group:
                if peer.local_id == sensor.local_id:
                    continue
                reading = readings.current_reading(self.agent.beliefs.reader(PUBLIC), peer.subject, peer.observes)
                if reading is None:
                    continue
                claims.append((
                    self.cadence_for(peer.subject, peer.observes, reading.value),
                    choir.annotations(self.agent, peer.subject, peer.observes, reading.value)))
            # Keyed on the interval alone: `min` over the pairs would compare the dicts on a tie
            # and raise. Ties go to the earliest claim, which is the triggering sensor's.
            sleep_s, verdict = min(claims, key=lambda claim: claim[0])

        key = sensor.command_topic or sensor.local_id
        # Fast attack, slow release (#139). Tightening goes through untouched — hesitating in
        # that direction costs a plant — but a RELAXATION is bounded per commanded step: the
        # next sleep may exceed the last by at most the family's relaxFactor, so one
        # comfortable reading cannot cliff a burst-tight cadence straight to the slow end. The
        # release runs geometrically over a few dense readings, exactly the window the trend
        # needs two of them to establish (#133), and confidence is earned rather than assumed.
        # Every WATCHED channel on this board is told its band (#151), beside the cadence and
        # in the same retained breath: a map of pointer -> [low, high], the tightest bounds any
        # module with a stake holds — desire's region edges, ordinarily — so the board watches
        # everything its agent wants held, per channel, while both of them sleep. A channel
        # that promised nothing gets no band, a board with no watched channels gets no map,
        # and old firmware ignores keys it does not know.
        alarm = {}
        for peer in self._aimed_with(sensor):
            if not peer.alarm:
                continue
            held = choir.bounds(self.agent, peer.subject, peer.observes)
            if held is not None:
                limits = [round(held[0], 3), round(held[1], 3)]
                # The DEVIATION half: a move of more than this since the board's last report is
                # worth waking for even INSIDE the band — the stranger watering a comfortable
                # pot, the leak still in-range. The board arms the intersection of the band and
                # last±delta, so this costs it nothing but arithmetic. The fraction is this
                # agent's own revisable pick; no pick, band-only alarm.
                if self.alarm_beliefs is not None and self.alarm_beliefs.delta_fraction > 0:
                    limits.append(round(
                        self.alarm_beliefs.delta_fraction * (held[1] - held[0]), 3))
                alarm[peer.reading_pointer or "/value"] = limits
        if alarm:
            verdict = {**(verdict or {}), "alarm": alarm}

        last = self.sent_cadence.get(sensor.local_id)
        if self.relax_factor and last is not None and sleep_s > last:
            sleep_s = min(int(sleep_s), max(int(last) + 1, int(last * self.relax_factor)))
        message = (int(sleep_s), tuple(sorted((verdict or {}).items())))
        if self.sent.get(key) == message:
            return
        driver = self.drivers[sensor.uri]
        if driver is None:
            return
        if not driver.set_cadence(sensor, sleep_s, verdict):
            # Nothing went out, so nothing is recorded and nothing is claimed (#103): an agent
            # that logged "cadence now Ns" over an unsendable instruction believed, reported
            # and freshness-judged a rhythm no board was keeping — every link locally correct,
            # only the composition a lie. The shapes refuse the wiring that reaches here; this
            # is the runtime half, for the world that validated before they did.
            self.log.warning("%s: keeps a schedule but states no channel to be told one — "
                             "it runs whatever it was flashed with", sensor.local_id)
            return
        # A release that repeats the standing answer is the ordinary heartbeat now, not news —
        # info only when something moved, or the log would restate the cadence every reading.
        changed = self.sent_cadence.get(sensor.local_id) != sleep_s
        self.sent[key] = message
        for aimed in group:
            self.sent_cadence[aimed.local_id] = sleep_s
            #  The horizon moved with the rhythm, so what a shape reads moves with it too.
            self.publish_horizon(aimed)
        (self.log.info if changed else self.log.debug)(
            "%s: cadence now %ss%s", sensor.local_id, sleep_s,
            f", showing {verdict}" if verdict else "")

    def sense_now(self) -> None:
        """Best-effort nudge — lands only if the device is awake to hear it."""
        for sensor in self.sensors:
            if self.drivers[sensor.uri]:
                self.drivers[sensor.uri].sense_now(sensor)

    @contributes(OBSERVING)
    def look(self, act, judgment, intention: str) -> bool:
        """Carry out a committed look: nudge the driver that watches this row's lever.

        The actor for `sensing:Observe` (knowledge/domain/actor.md) — the FAMILY is named, so the
        listening module is offered the same row and declines, and this one answers True
        only where a driver exists to nudge. The look is satisfied by the reading arriving,
        whoever caused it, exactly as before: `on_reading_recorded` here resolves it, per want.
        """
        nudged = False
        for sensor in self.sensors:
            if act.value_of(ABOUT) in (sensor.observes, sensor.uri) and self.drivers[sensor.uri]:
                self.drivers[sensor.uri].sense_now(sensor)
                nudged = True
        return nudged

    def on_belief_revised(self, belief_term: str, value) -> None:
        """Take up a re-picked interval at once, rather than at the next restart.

        Re-read rather than patched, so there is exactly one path by which this module learns
        what it believes. Then re-aim every board from the reading I already hold: the
        alternative is waiting out the OLD cadence, which after a relaxation is up to a quarter
        of an hour of the agent knowingly running a policy it has just abandoned.
        """
        super().on_belief_revised(belief_term, value)   # the aim, re-read
        # Compared whole. This used to strip the namespace off and match on the local name,
        # which was a latent bug rather than a shortcut: two packages may each declare a
        # `slowSleepS` in their own namespace, and the stripped form cannot tell them apart —
        # so a revision of somebody else's belief would have been taken up as this module's.
        # A block's terms are full IRIs, so there is nothing to strip.
        if belief_term in picks.ALARM_PICKS.terms.values():
            # A re-picked jolt threshold, and the re-aim below re-arms every watched channel
            # with the new delta — the whole reason the pick is a belief and not a compile-time
            # figure: correcting the estimate reaches the board on its next wake, not at the
            # next reflash.
            self.alarm_beliefs = self.agent.desires.read_optional(picks.ALARM_PICKS)
        elif belief_term not in picks.SUBSCRIBING_PICKS.terms.values():
            return
        else:
            self.beliefs = self.agent.desires.read(picks.SUBSCRIBING_PICKS)
        for sensor in self.sensors:
            reading = readings.current_reading(self.agent.beliefs.reader(PUBLIC), sensor.subject, sensor.observes)
            if reading is not None:
                self.set_cadence(
                    sensor,
                    self.cadence_for(sensor.subject, sensor.observes, reading.value),
                    choir.annotations(self.agent, sensor.subject, sensor.observes, reading.value))


class ListeningModule(SensingModule):
    """sensing:Listening — derived from being wired to a push-mode sensor.

    No interval, because the device would not take one. The agent keeps its freshness rule,
    which now works as a *detector* rather than a control: if the board goes quiet, readings
    go stale and the agent stops acting on them instead of quietly using old numbers.
    """

    @contributes(OBSERVING)
    def look(self, act, judgment, intention: str) -> bool:
        """A look, declined: a listening device takes no orders, so there is nothing to nudge.
        Contributed rather than left to the family's other member, because the family must
        answer for every look handed to it (#523), and an agent that ONLY listens has no other
        member — its look stands, and what ends it is the reading the device sends when it
        will. False is "not now", said every time."""
        return False

    CAPABILITY = LISTENING
    SENSE_MODE = PUSH
    name = "listening"

    def __init__(self, agent):
        self.beliefs = agent.desires.read(picks.LISTENING_PICKS)
        super().__init__(agent)

    def stale_after_s(self, subject_uri: str, observed_property: str) -> int:
        """Absolute: this device keeps its own clock, so there is no interval to be relative to."""
        return self.beliefs.max_age_s
