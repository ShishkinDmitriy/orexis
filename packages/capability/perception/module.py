"""Perception — capabilities over one shared ingest path, split by WHO HOLDS THE CLOCK.

Which one an agent gets is decided by its **hardware**, and derived at genesis from the
device's own nature:

- **perception:Polling** (`perception:PolledProcedure` device) — the agent's own timer; it asks for each reading and the
  device replies. The simplest exchange and the most agent control, but it needs a device that
  is reachable at any moment. **Not implemented**: no rule grants it and no class here
  provides it, because a board that deep-sleeps cannot hear the request. The room is kept
  deliberately — see ontology.ttl.
- **perception:Subscribing** (`perception:ScheduledProcedure` device) — the agent states an interval and the device
  keeps to it. The agent still decides how often to look; what it delegates is the
  timekeeping, which is exactly what lets the device sleep in between.
- **perception:Listening** (`perception:PushProcedure` device) — the device announces on its own clock and takes no
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
- **What counts as trouble.** Perception knows how to look and how fresh a number is; it has
  no band and no target, because those belong to whoever holds a stake in the subject. So it
  *asks* — `agent.urgency` for how closely to watch, `agent.annotations` for what to say
  publicly — and an agent with no stake simply gets no answer and watches at its slow cadence.
  That is why nothing here imports another capability.

Everything touched is discovered: which sensors (`perception:polls`), what property they read
(`sosa:observes`), and where to announce a perception (`mqtt:eventTopic`).

Vocabulary: capabilities/perception/ontology.ttl. Rules: capabilities/perception/shapes.ttl.
Derivation: capabilities/perception/rules.ru. See knowledge/domain/sensing.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

from agent.scaling import scaling_for
from agent.driver import driver_for
from agent.module import Module
from agent.observation import Observations
from agent.store import bindings

from .beliefs import LISTENING_BLOCK, SUBSCRIBING_BLOCK
from .terms import LISTENING, PUSH, SCHEDULED, SUBSCRIBING

# The constitutional bounds are stated in the ontology, not compiled in here — and they hang
# off the capability FAMILY, so every transport and every future perception inherits them.
_BOUNDS_Q = """
SELECT ?min ?max ?relax WHERE {
  GRAPH ?g { perception:PerceptionCapability perception:minSleepS ?min ; perception:maxSleepS ?max .
             OPTIONAL { perception:PerceptionCapability perception:relaxFactor ?relax } }
} LIMIT 1"""


class PerceptionModule(Module):
    """Shared ingest: record what a sensor read, announce it, keep a freshness rule.

    Identical whether the reading was asked for or simply arrived.
    """

    # Which kind of device this module is for. The derivation grants the capability from the
    # sensor's perception:senseMode; this is the same pairing, read from the other side.
    SENSE_MODE: str | None = None

    def __init__(self, agent):
        super().__init__(agent)
        # MINE, not the agent's. An agent may hold sensors of different modes, and it derives a
        # capability for each — but a module that took all of them would aim a cadence at a device
        # that takes no orders, and swallow readings from one it never re-aims. The derivation
        # split the capabilities; this splits the sensors the same way.
        self.sensors = tuple(s for s in self.me.sensors
                             if self.SENSE_MODE is None or s.sense_mode == self.SENSE_MODE)
        unclaimed = [s.local_id for s in self.me.sensors if s not in self.sensors]
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

        # Recording is not perception's to define — see agent/observation.py.
        self.observations = Observations(agent)

    def stale_after_s(self, subject_uri: str) -> int:
        """How old a reading of this subject may be before I stop trusting it.

        A method rather than a number because the answer depends on who holds the clock. Where
        the agent sets the interval it must be relative to that interval; where the device keeps
        its own, an absolute is the only thing the agent can state.
        """
        raise NotImplementedError

    def subscriptions(self) -> list[str]:
        # exactly my own sensors, and only where their binding listens at all — never a
        # wildcard, so the access grant stays visible in the subscription itself
        return [t for s in self.sensors if self.drivers[s.uri]
                for t in self.drivers[s.uri].subscriptions(s)]

    def stop(self) -> None:
        self.observations.close()

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
        at = datetime.now(timezone.utc)
        acknowledged = None  # message-level, like the instant: one board, one rhythm
        doc = self.parse(payload)
        if doc is not None and isinstance(doc.get("sleep_s"), (int, float)):
            acknowledged = int(doc["sleep_s"])
        for sensor in self.sensors:
            driver = self.drivers[sensor.uri]
            if driver is None or not driver.owns(sensor, topic):
                continue
            if not mine and acknowledged is not None:
                self.on_cadence_ack(sensor, acknowledged)
            mine = True
            raw = driver.parse(sensor, payload)
            # The last stage: a raw value is what the device sent, a quantity is what it means.
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
        return mine

    def ingest(self, sensor, value: float, at: datetime | None = None) -> None:
        """Record what the sensor read, then re-aim if this capability can.

        `at` is when the message carrying this value arrived, so that every value out of one
        message shares one instant. Optional because a caller with no message in hand — a test,
        or a future path that synthesises a reading — has nothing better than now to offer.
        """
        self.observations.record(self.log, sensor, value, at)
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

    def quiet(self) -> list[str]:
        """Every sensor of mine that has delivered once and then gone silent past my rule.

        Answered by the base class for BOTH clocks: subscribing's limit is relative to the
        cadence in force and listening's is absolute, but `stale_after_s` already dispatches
        that, so the question is one question. A sensor that has NEVER delivered is deliberately
        not here — that is a different fault, said by `readings_total` sitting at zero — and the
        age comes off the metrics clock, which counts arrivals wherever they entered.
        """
        out = []
        for sensor in self.sensors:
            age = self.agent.metrics.reading_age_s(sensor.local_id)
            if age is None:
                continue
            limit = self.stale_after_s(sensor.subject, sensor.observes)
            if age > limit:
                out.append(f"{sensor.local_id}: nothing for {age:.0f}s, past the "
                           f"{limit}s I allow")
        return out

    def sense_now(self) -> None:
        """Ask for a reading now, if my hardware allows it. Listening cannot.

        Best-effort even where it is allowed: a device that sleeps between readings only hears
        this if the nudge happens to land inside its waking window. It is the seed of
        perception:Polling, not a substitute for it — a real polling module would need a device that
        is always listening, and would then drive every reading this way.
        """

    def fresh_reading(self, subject_uri: str, observed_property: str):
        """The latest reading of one property, or None if it is older than I trust."""
        reading = self.agent.beliefs.current_reading(subject_uri, observed_property)
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


class SubscribingModule(PerceptionModule):
    """perception:Subscribing — derived from being wired to a device that keeps to a given interval.

    The standing request is the whole mechanism: the interval is published *retained*, so a
    device that is asleep now receives it the instant it wakes and subscribes. That is why
    this works against hardware the agent cannot otherwise reach.
    """

    CAPABILITY = SUBSCRIBING
    SENSE_MODE = SCHEDULED
    name = "subscribing"

    def __init__(self, agent):
        self.beliefs = agent.beliefs.read(SUBSCRIBING_BLOCK)
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
        rows = bindings(self.agent.store.query(_BOUNDS_Q))
        if not rows:
            raise RuntimeError("the ontology states no cadence bounds — re-run agora-seed")
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
        self.sense_now()
        for sensor in self.sensors:
            reading = self.fresh_reading(sensor.subject, sensor.observes)
            value = reading.value if reading is not None else None
            self.set_cadence(sensor,
                             self.cadence_for(sensor.subject, sensor.observes, value),
                             self.agent.annotations(sensor.subject, sensor.observes,
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
        # holds a stake contributes, perception passes it on without reading it. An agent with
        # no stake in this property contributes nothing and the device is told only a cadence.
        self.set_cadence(sensor,
                         self.cadence_for(sensor.subject, sensor.observes, value),
                         self.agent.annotations(sensor.subject, sensor.observes, value))

    def watch_is_live(self, subject_uri: str, observed_property: str) -> bool:
        sensor = self.sensor_for(subject_uri, observed_property)
        if sensor is None:
            return False
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
        for peer in self._aimed_with(sensor):
            self.agent.metrics.cadence_acked(peer.local_id, int(acknowledged_s))
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
        at = at or datetime.now(timezone.utc)
        key = (subject_uri, observed_property)
        previous = self._last_seen.get(key)
        if previous is not None:
            prev_value, prev_at = previous
            dt = (at - prev_at).total_seconds()
            if dt > 0:
                self._trend[key] = (value - prev_value) / dt
        self._last_seen[key] = (value, at)

    def cadence_for(self, subject_uri: str, observed_property: str,
                    value: float | None) -> int:
        """How long the board may sleep: the closer to my own trouble, the closer I watch —
        and no longer than the trend allows.

        Trouble is not perception's to define, so it is asked for. An agent with no stake in
        the subject — or none in *this property* of it — gets no answer and watches at its slow
        cadence, which is the honest reading of "nothing here is urgent to me". That second
        case is why the property is passed: a thermometer on a pot the agent bids water for
        must not have its cadence driven by how dry the soil is.

        THE TREND BOUND (#133). Urgency answers where the state IS; a sleep granted on that
        alone can begin moments before the trend crosses into trouble, and nobody hears for
        the whole window. So the candidate sleep is checked against where the state is
        HEADING: predict the value at the end of the sleep from the measured slope, ask the
        same stakeholder how urgent THAT would be, and if the answer is worse, grant the
        cadence that answer earns instead. One step of lookahead, tighten-only — a favourable
        trend relaxes nothing, because reading more often than needed costs a reading and is
        the only safe direction to be wrong in, and a relaxation earned by a trend would be a
        prediction trusted further than any prediction here deserves. The safety margin is
        implicit: urgency is evaluated at the END of the sleep, so the granted window always
        ends at or before the predicted trouble, never astride it.

        No slope yet — fewer than two readings, or a fresh restart — means no bound, which is
        the pre-#133 behaviour, honestly reached. The declared `dryRatePerTick` is deliberately
        NOT the fallback the issue suggested: it is a domain term perception may not name, and
        its tick is undefined for a real pot. Evidence or nothing.
        """
        b = self.beliefs
        urgency = self.agent.urgency(subject_uri, observed_property, value)
        if urgency is None:
            return min(self.max_sleep_s, max(self.min_sleep_s, b.slow_sleep_s))

        def granted(u: float) -> float:
            return b.slow_sleep_s + (b.fast_sleep_s - b.slow_sleep_s) * u

        sleep_s = granted(urgency)
        slope = self._trend.get((subject_uri, observed_property))
        if slope and value is not None:
            predicted = value + slope * sleep_s
            ahead = self.agent.urgency(subject_uri, observed_property, predicted)
            if ahead is not None and ahead > urgency:
                sleep_s = granted(ahead)
        return int(round(min(self.max_sleep_s, max(self.min_sleep_s, sleep_s))))

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
                reading = self.agent.beliefs.current_reading(peer.subject, peer.observes)
                if reading is None:
                    continue
                claims.append((
                    self.cadence_for(peer.subject, peer.observes, reading.value),
                    self.agent.annotations(peer.subject, peer.observes, reading.value)))
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
        last = self.sent_cadence.get(sensor.local_id)
        if self.relax_factor and last is not None and sleep_s > last:
            sleep_s = min(int(sleep_s), max(int(last) + 1, int(last * self.relax_factor)))
        message = (int(sleep_s), tuple(sorted((verdict or {}).items())))
        if self.sent.get(key) == message:
            return
        driver = self.drivers[sensor.uri]
        if driver is None:
            return
        driver.set_cadence(sensor, sleep_s, verdict)
        # A release that repeats the standing answer is the ordinary heartbeat now, not news —
        # info only when something moved, or the log would restate the cadence every reading.
        changed = self.sent_cadence.get(sensor.local_id) != sleep_s
        self.sent[key] = message
        for aimed in group:
            self.sent_cadence[aimed.local_id] = sleep_s
        (self.log.info if changed else self.log.debug)(
            "%s: cadence now %ss%s", sensor.local_id, sleep_s,
            f", showing {verdict}" if verdict else "")

    def sense_now(self) -> None:
        """Best-effort nudge — lands only if the device is awake to hear it."""
        for sensor in self.sensors:
            if self.drivers[sensor.uri]:
                self.drivers[sensor.uri].sense_now(sensor)

    def on_belief_revised(self, belief_term: str, value) -> None:
        """Take up a re-picked interval at once, rather than at the next restart.

        Re-read rather than patched, so there is exactly one path by which this module learns
        what it believes. Then re-aim every board from the reading I already hold: the
        alternative is waiting out the OLD cadence, which after a relaxation is up to a quarter
        of an hour of the agent knowingly running a policy it has just abandoned.
        """
        # Compared whole. This used to strip the namespace off and match on the local name,
        # which was a latent bug rather than a shortcut: two packages may each declare a
        # `slowSleepS` in their own namespace, and the stripped form cannot tell them apart —
        # so a revision of somebody else's belief would have been taken up as this module's.
        # A block's terms are full IRIs, so there is nothing to strip.
        if belief_term not in SUBSCRIBING_BLOCK.terms.values():
            return
        self.beliefs = self.agent.beliefs.read(SUBSCRIBING_BLOCK)
        for sensor in self.sensors:
            reading = self.agent.beliefs.current_reading(sensor.subject, sensor.observes)
            if reading is not None:
                self.set_cadence(
                    sensor,
                    self.cadence_for(sensor.subject, sensor.observes, reading.value),
                    self.agent.annotations(sensor.subject, sensor.observes, reading.value))


class ListeningModule(PerceptionModule):
    """perception:Listening — derived from being wired to a push-mode sensor.

    No interval, because the device would not take one. The agent keeps its freshness rule,
    which now works as a *detector* rather than a control: if the board goes quiet, readings
    go stale and the agent stops acting on them instead of quietly using old numbers.
    """

    CAPABILITY = LISTENING
    SENSE_MODE = PUSH
    name = "listening"

    def __init__(self, agent):
        self.beliefs = agent.beliefs.read(LISTENING_BLOCK)
        super().__init__(agent)

    def stale_after_s(self, subject_uri: str, observed_property: str) -> int:
        """Absolute: this device keeps its own clock, so there is no interval to be relative to."""
        return self.beliefs.max_age_s
