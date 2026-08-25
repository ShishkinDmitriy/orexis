"""actuation:Actuation — redeem a claim against real hardware.

There is no "armed" flag and no dry-run mode. This capability actuates; that is what it is
for. An installation that must NOT move water does not disarm the module — it declares
devices that do not move water, and derivation gives its agent a different capability. What a
thing does belongs in the model, not in an environment variable that can disagree with it.


Held by the resource owner, never by the winner: a claim is a *claim on the owner*, and the
owner is the one with the valves. This module decides nothing. It maps a claim's subject to
the device that serves it (`actuation:actuates`), converts litres into open-seconds with that
device's own calibration (`actuation:mlPerSecond`), caps the dose at the device's own limit
(`actuation:maxDoseMl`) regardless of what cleared, co-signs, and publishes to the device's own
command topic. Every one of those is read from the world.

Single-use is enforced here by `jti`; the device enforces its own fail-safe watchdog. Two
independent limits, because the interesting failures are the ones where one of them is wrong.

Vocabulary: capabilities/actuation/ontology.ttl. Rules: capabilities/actuation/shapes.ttl.
Derivation: capabilities/actuation/rules.ru.
See knowledge/domain/executor.md.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass

import uuid

from agent import effects, signing
from agent.commitment import Commitment
from agent.module import Module, Timer
from agent.ontology import SENSED_GRAPH
from agent.store import bindings

from .beliefs import ACTUATION_PICKS
from .terms import ACTUATION, DOSING
from .wiring import actuator_for, actuators_of

SENSING = "http://example.org/orexis/sensing#SensingCapability"  # whoever can look, asked by family

# What this package asks OF others, by family or by IRI — namespaces, never Python.

# My own conversion belief for a SELF-dose (#190), keyed by the valuation term the resource
# chain names: my actuator draws from my own source, the source's class states its good, and
# the good's valuation for this property is the term my belief is held in — the same
# discovery the bidder makes through its venue, made through the pipe instead, because a
# self-actuating agent may have no venue at all.
#  SOSA, spelled once: the effect rule answers in observations, and this file has to
#  recognise the result predicate to invert it.
_SOSA = "http://www.w3.org/ns/sosa/"

_CONVERSION_Q = """
SELECT ?v WHERE {
  <%s> ag:actsFor ?subject ; actuation:hasActuator ?lever .
  ?lever actuation:actuates ?subject ; actuation:drawsFrom ?source .
  ?source market:offeredBy <%s> ; market:supplies ?good .
  ?term market:ofGood ?good ; market:aboutProperty <%s> .
  GRAPH <%s> { <%s> ?term ?v }
} LIMIT 1"""

# How often the module looks for doses nobody confirmed. Not the deadline — that is per dose
# and derived — only how coarsely it is noticed. A sweep is cheap and lateness is not urgent.
SWEEP_S = 5.0


#  A litre below which a dose is nothing. The market keeps the same figure for a bid; two
#  packages that may not import each other each say what "nothing" is for their own act.
EPS = 1e-9


@dataclass(frozen=True)
class Command:
    jti: str
    plant: str
    scope: str
    ml: float
    seconds: float
    auction_id: str


class ActuationModule(Module):
    CAPABILITY = ACTUATION
    name = "actuation"

    def __init__(self, agent):
        super().__init__(agent)
        self.actuators = actuators_of(agent.beliefs.query, self.me.uri)
        self.settled: set[str] = set()
        # Commanded and not yet confirmed: jti -> (deadline, plant, ml). A dose leaves here on
        # the device's report, or on the sweep deciding nobody is going to send one.
        self.pending: dict[str, tuple[float, str, float]] = {}
        self.confirmed = 0
        self.unconfirmed = 0
        self.grace_s = agent.desires.read(ACTUATION_PICKS).dose_grace_s
        self._sweep = Timer(SWEEP_S, self._expire)
        # v1 in-process: the settlement side holds both keys and co-signs. The device opens
        # only for a token signed by BOTH the host and clearing.
        self.host_key = self.clearing_key = None
        try:
            self.host_key = signing.load_private("host")
            self.clearing_key = signing.load_private("clearing")
        except Exception:
            self.log.warning("no signing keys (run orexis-keygen) — devices will reject commands")

    def _subject_of(self, winner_id: str) -> str:
        """The winner's SUBJECT — where its dose goes. A claim names the buying AGENT.

        This used to hand `claim.sub` straight to `actuator_for`, which matches actuators by
        the SUBJECT they actuate — and it worked for every claim ever redeemed because a pot
        and the agent acting for it share a localId (fern's pot is "fern"). The first buyer
        named unlike its subject broke it: the dealer is "supplier", its barrel is "barrel1",
        and the city owned a perfectly good valve it could not find. The walk the id
        coincidence was standing in for is one triple: whoever bears the claim's name, the
        dose goes to what it acts for. Falls back to the name itself, because a world may
        author a claim's sub as a subject directly and the coincidence path must keep working.
        """
        rows = bindings(self.agent.beliefs.query(
            f'SELECT ?sid WHERE {{ ?a ag:localId "{winner_id}" ; ag:actsFor ?s . '
            f'?s ag:localId ?sid }} LIMIT 1'))
        return rows[0]["sid"] if rows else winner_id

    def _subject_uri_of(self, winner_id: str) -> str | None:
        """The same walk, answering with the subject's IRI — what a rule's `$subject` needs.

        `_subject_of` answers with a LOCAL ID because `actuator_for` matches on one, and for
        months `redeem` handed that id to the effect rule wrapped in angle brackets: `<fern>`
        is not an IRI, the timing query failed to parse, `_select` swallowed it, and every
        served claim fell back to `cmd.seconds` — the one figure #247 made single-source, two
        figures again on exactly the market path (#351). None where nothing bears the name,
        and the caller keeps the wire's own duration, which is what it did by accident before.
        """
        rows = bindings(self.agent.beliefs.query(
            f'SELECT ?s WHERE {{ {{ ?a ag:localId "{winner_id}" ; ag:actsFor ?s }} '
            f'UNION {{ ?s ag:localId "{winner_id}" . FILTER NOT EXISTS {{ ?s ag:actsFor ?x }} }} }} '
            f'LIMIT 1'))
        return rows[0]["s"] if rows else None

    def command_for(self, claim) -> tuple[Command, object]:
        device = actuator_for(self.actuators, self._subject_of(claim.sub))
        if device is None:
            raise ValueError(f"I own no actuator that serves {claim.sub!r}")
        ml = min(claim.amount_l * 1000.0, device.max_dose_ml)  # the device's own cap
        return Command(
            jti=claim.jti, plant=claim.sub, scope=claim.scope,
            ml=round(ml, 1), seconds=round(ml / device.ml_per_second, 2),
            auction_id=claim.auction_id,
        ), device

    def on_reading_recorded(self, subject_uri: str, observed_property: str,
                            value: float) -> None:
        """The Actuate rung's trigger (#190): a fresh look at my own subject, whose gap the
        deliberator answers with the cheaper rung.

        Everything the market path earns, a self-dose keeps: the WHETHER is the
        deliberator's (the menu offers Actuate only where the lever and the source are both
        mine and no market offers the source as its lot); the amortisation is the keeper's
        (an adoption absorbed within patience means no dose, and an open expectation means
        my last dose has not answered — the same two guards a bidder runs); and the act
        itself goes through `redeem` on a SELF-CLAIM — signed by both keys, verified in the
        device, confirmed on the status channel, counted when silent. An unconfirmed
        self-dose is not a delivered one either; the REA event stands, it merely fulfils no
        exchange.
        """
        if subject_uri != self.me.acts_for:
            return
        if actuator_for(self.actuators, self._subject_of(self.me.agent_id)) is None:
            return
        #  THROUGH EXECUTION, never a decision of this module's own: the reading just
        #  recorded is what the agent believes (`Observations.record` writes before it
        #  announces), the search decides against it, the keeper commits, and `take` below
        #  is handed the row. A standing Actuate is not re-taken here — a dose is an act
        #  whose sizing moves with every reading, so it is re-planned, and an impulse within
        #  patience is absorbed before anything is written.
        from agent import execution

        execution.pursue_about(self.agent, observed_property)

    def size(self, observed_property: str, value: float) -> float | None:
        """The planner's question, answered by the one who would pour: `dose_for`."""
        return self.dose_for(observed_property, value)

    def take(self, row, desire, intention: str) -> bool:
        """Carry out a committed self-dose: size it from the reading in hand and command it.

        The actor for `actuation:Actuate` (knowledge/domain/actor.md). Everything the market path
        earns, a self-dose keeps: the act goes through `redeem` on a SELF-CLAIM — signed by
        both keys, verified in the device, confirmed on the status channel, counted when
        silent — and opens an expectation on the end. An unconfirmed self-dose is not a
        delivered one either; the REA event stands, it merely fulfils no exchange.
        """
        if row.action != DOSING:
            return False
        observed_property = row.observed_property
        reading = self.agent.beliefs.current_reading(self.me.acts_for, observed_property)
        if reading is None:
            return False
        value = reading.value
        keeper = self.agent.keeper
        if keeper is not None:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if any(now < w.deadline for w in keeper.open_expectations(observed_property)):
                return False  # my own dose has not answered yet — the #167 guard, rung 2
        litres = self.dose_for(observed_property, value)
        if litres is None or litres <= EPS:
            if keeper is not None:
                keeper.drop(DOSING, observed_property,
                            "the dose sized to nothing from the reading in hand")
            return False
        jti = uuid.uuid4().hex
        cmd = self.redeem(Commitment(sub=self.me.agent_id, scope="actuate:self",
                                      amount_l=litres,
                                auction_id=f"self-{jti[:8]}", jti=jti))
        if keeper is not None:
            #  THE INTENTION STANDS until the world answers (#353). It is to the END — a wetter
            #  pot — not to the command, so the watch opens on the standing row and the keeper
            #  resolves it at the verdict. While it stands, `adopt` absorbs the next impulse by
            #  the ordinary rule, which is the 584-dose guard with no hook and no second read
            #  of the ledger. A watch that cannot open (no baseline, no direction) is resolved
            #  at once: a row that could never be judged must not stand for ever.
            #  A dose RAISES what it doses — that is this package's own effect rule, `$value +
            #  litres / conversion` — so the watch is told so here; and how long a reading
            #  takes to arrive is my sensing's cadence, asked of it rather than by the keeper.
            sensing = self.agent.provider(SENSING)
            try:
                seeing = float(sensing.stale_after_s(self.me.acts_for, observed_property)) if sensing else None
            except Exception:
                seeing = None
            opened = keeper.expect(
                intention, observed_property,
                f"self-dosed {litres}L ({cmd.ml:.0f} ml commanded) — the graph says this "
                f"raises what I am short of, so show me",
                expected_delta=self._expected_delta(observed_property, litres, value),
                rises=True, seeing_s=seeing,
                lands_after_s=effects.lands_after(
                    self.agent.beliefs, DOSING, me=f"<{self.me.uri}>",
                    subject=f"<{self.me.acts_for}>", litres=repr(float(litres))))
            if opened and sensing is not None:
                sensing.sense_now()   # the freshest before on record
            if not opened:
                keeper.satisfy(DOSING, observed_property,
                               f"the dose is commanded — {cmd.ml:.0f} ml on its way, and no "
                               f"watch could be opened on the end")
        return True

    def dose_for(self, observed_property: str, value: float) -> float | None:
        """How much I would pour, given where this property stands — the size of ONE act.

        Public, and asked by the planner as well as taken by the actor, because a planner that
        computed its own dose would be simulating a different act from the one that would
        actually happen. It would predict a world nobody was going to reach, and be wrong in
        the direction that looks like the device lying: the same single-source argument #238
        made for the magnitude of an effect and #247 for its timing, arriving a third time at
        the quantity itself.

        None where the agent cannot size a dose at all — no aim to steer toward, no stated
        conversion, or a vessel it has watched run dry.
        """
        desire = self.agent.deducer
        aim = desire.aim(observed_property) if desire is not None else None
        conversion = self._conversion_for(observed_property)
        if aim is None or conversion is None:
            return None
        litres = round((aim - value) * conversion, 3)
        stock = self._stock_of_my_source()
        if stock is not None:
            # The witness meters rung 2 exactly as it meters the host's rounds: pour at most
            # what the vessel holds, and refuse when it is spent. The other 584-dose finding:
            # self-claims never meet clearing's allocation ledger, so without a witness the
            # butt's capacityL bounded nothing — a source with no witness still doses blind,
            # the mains precedent, but a FINITE bottle deserves a level sensor and the world
            # that has one is now honest about running dry.
            if stock <= EPS:
                self.log.warning("the vessel is spent (%.3f L) — no self-dose; wanting "
                                 "continues, the means is gone until something refills it",
                                 stock)
                return None
            litres = min(litres, round(stock, 3))
        return litres

    def _stock_of_my_source(self) -> float | None:
        """My freshest reading of the source my lever draws from — None when I am blind.

        The hosting module's `_stock_of`, at rung 2: the same witness pattern, the same
        freshest-regardless-of-age honesty, the same None-means-blind for a mains-like
        source nobody watches.
        """
        rows = bindings(self.agent.beliefs.query(f"""
SELECT ?source ?p WHERE {{
  <{self.me.uri}> ag:actsFor ?subject ; actuation:hasActuator ?lever ;
      sensing:polls ?s .
  ?lever actuation:actuates ?subject ; actuation:drawsFrom ?source .
  ?s sensing:monitors ?source ; sosa:observes ?p }} LIMIT 1"""))
        if not rows:
            return None
        reading = self.agent.beliefs.current_reading(rows[0]["source"], rows[0]["p"])
        return reading.value if reading is not None else None

    def _expected_delta(self, observed_property: str, litres: float,
                        value: float) -> float | None:
        """How far this dose should move the property — asked of the EFFECT RULE, not computed.

        `litres / conversion` used to be written here, and separately in the bidder, and the
        rule for #238 would have made a third copy. That is the arrangement the planning record
        names as the whole risk: an agent that plans against one future and verifies against
        another reports false UNMET verdicts, and the failure LOOKS like a device lying rather
        than like arithmetic disagreeing with itself. So the rule is the single source and this
        runs it: the number the planner will use to decide whether dosing helps is the number
        the keeper will later hold the world to.

        The subtraction is not a second formula — it inverts the rule's own answer, which is
        stated as a predicted READING because that is what an effect can honestly say about a
        valve. None whenever the rule declines to predict: no conversion belief, or no lever
        reaching this subject. The keeper takes None and falls back to the
        exact-crossing verdict, exactly as it did when the conversion belief was missing.
        """
        added, _ = effects.apply(
            self.agent.beliefs, DOSING,
            me=f"<{self.me.uri}>", subject=f"<{self.me.acts_for}>",
            property=f"<{observed_property}>", sensed=f"<{SENSED_GRAPH}>",
            beliefs=f"<{self.agent.beliefs.graph}>",
            litres=repr(float(litres)), value=repr(float(value)))
        #  `.value` and not `str()`: a pyoxigraph term stringifies to its N-Triples form, angle
        #  brackets and datatype included, so comparing `str(predicate)` to an IRI silently
        #  never matches and every expectation comes back None. It cost a test run to notice,
        #  which is cheap only because the test was pinning a number rather than a shape.
        for triple in added:
            if triple.predicate.value == f"{_SOSA}hasSimpleResult":
                return float(triple.object.value) - value
        return None

    def _conversion_for(self, observed_property: str) -> float | None:
        rows = bindings(self.agent.beliefs.query(_CONVERSION_Q % (
            self.me.uri, self.me.uri, observed_property,
            self.agent.beliefs.graph, self.me.uri)))
        return float(rows[0]["v"]) if rows and rows[0].get("v") is not None else None

    def redeem(self, claim) -> Command:
        if claim.jti in self.settled:
            raise ValueError(f"replay: jti {claim.jti} already redeemed")
        cmd, device = self.command_for(claim)
        payload = asdict(cmd)
        if self.host_key is not None and self.clearing_key is not None:
            data = signing.canonical(payload)
            payload["match_sig"] = signing.sign(self.host_key, data)  # the seller authorises
            payload["val_sig"] = signing.sign(self.clearing_key, data)  # clearing validated
        self.publish(device.command_topic, payload)
        self.settled.add(claim.jti)  # single-use either way: a dry run still spends the jti
        # Commanded is not delivered. The deadline is THIS dose's own duration plus the slack
        # this agent believes the bus needs — relative and not absolute, for the reason
        # `sensing:readingGraceS` is: an agent cannot ask a valve for a ninety-second pour and
        # then call it late at thirty.
        #
        # The duration is ASKED OF THE EFFECT (#247) rather than taken from the command, so the
        # figure a planner will wait on and the figure this deadline uses cannot become two
        # figures. `cmd.seconds` is what goes on the wire and stays the device's instruction;
        # the rule computes the same `min(litres, cap) / rate` from the same world, and
        # `test_effects` fails if they ever disagree. None keeps the old arrangement whole,
        # which is what a lever with no stated timing deserves.
        if device.status_topic:
            subject = self._subject_uri_of(claim.sub)
            lands = effects.lands_after(
                self.agent.beliefs, DOSING, me=f"<{self.me.uri}>",
                subject=f"<{subject}>", litres=repr(float(claim.amount_l))) if subject else None
            self.pending[cmd.jti] = (
                time.monotonic() + (cmd.seconds if lands is None else lands) + self.grace_s,
                cmd.plant, cmd.ml)
        self.log.info("%s: open %.2fs (~%.0f ml) -> %s", cmd.plant, cmd.seconds, cmd.ml,
                      device.command_topic)
        return cmd

    # --- did it actually flow? -------------------------------------------------------------

    def subscriptions(self) -> list[str]:
        """Exactly my own valves' status channels — never a wildcard, and only where the world
        states one. A device wired without a status channel is a real deployment; what it costs
        is stated in `reports()`."""
        return [a.status_topic for a in self.actuators if a.status_topic]

    def start(self) -> None:
        self._sweep.start()

    def stop(self) -> None:
        self._sweep.stop()

    def handle(self, topic: str, payload: bytes) -> bool:
        """A device saying what it dispensed. Matched by `jti`, which is what makes it *this*
        dose's report and not the previous one's.

        Silence is the device's refusal — `firmware/simulated-valve` publishes here after
        dispensing and says nothing when it rejects a command — so this is only ever the happy
        path. The unhappy one is a deadline passing in `_expire`.
        """
        if topic not in self.subscriptions():
            return False
        try:
            report = json.loads(payload)
        except (ValueError, TypeError):
            self.log.warning("unreadable status on %s", topic)
            return True  # mine, and unreadable — saying so is the point
        jti = report.get("jti")
        waiting = self.pending.pop(jti, None)
        if waiting is None:
            # A report for a dose I am not waiting on. Not an error: a restarted agent has
            # forgotten what it commanded, and the device is right to report anyway.
            self.log.info("status for %s, which I was not waiting on", jti)
            return True
        self.confirmed += 1
        _, plant, ml = waiting
        self.log.info("%s: confirmed %.0f ml (jti %s)", plant, report.get("ml", ml), jti)
        return True

    def _expire(self) -> None:
        """Doses nobody confirmed. Reported and counted — never re-sent, and never un-spent.

        The issue that asked for this suggested not treating an unconfirmed claim as spent.
        That is the wrong way round, for two reasons:

        - **The device refuses replays itself.** `firmware/simulated-valve` keeps its own spent
          set, so a re-sent command is refused rather than poured. Un-spending buys nothing
          and only removes this agent's own guard.
        - **The failures are not symmetric.** If the water flowed and the report was lost,
          re-sending risks pouring twice; if it did not flow, the plant misses this round and
          bids again in the next one. Over-watering is irreversible and a missed round is not,
          so the safe direction is to keep the jti spent and say loudly that nobody confirmed.

        What this produces is a number, `doses_unconfirmed`, which is the honest thing an agent
        can offer: it does not know whether the water flowed, and it stops pretending it does.
        """
        now = time.monotonic()
        for jti in [j for j, (due, _, _) in self.pending.items() if due <= now]:
            _, plant, ml = self.pending.pop(jti)
            self.unconfirmed += 1
            self.log.warning(
                "%s: no confirmation that %.0f ml flowed (jti %s) — the claim stays spent, "
                "because a lost report and an unopened valve look identical from here",
                plant, ml, jti)

    def reports(self) -> dict:
        """What this capability adds to its agent's own health series.

        `doses_unconfirmed` is the field worth watching: it is the difference between a valve
        that dispensed and one that never heard, which was invisible before. An agent whose
        valves state no status channel reports zeroes for ever, which is itself a reading.
        """
        return {"doses_confirmed": self.confirmed, "doses_unconfirmed": self.unconfirmed}

    def redeem_all(self, claims) -> list[Command]:
        out = []
        for claim in claims:
            try:
                out.append(self.redeem(claim))
            except ValueError as exc:
                self.log.error("cannot redeem for %s: %s", claim.sub, exc)
        return out
