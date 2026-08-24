"""What every capability module is.

The contract is deliberately small: say which topics you want, handle the ones that are
yours, and start/stop cleanly. A module reads its parameters from the agent's beliefs, its
wiring from the agent's `Self`, and nothing else — in particular it never reaches for another
agent, and never writes a topic or an identifier that is not in the graph.

It does not reach for another *module* by name either. Where one capability needs something
only another can supply, it asks the agent for whoever provides a **capability family**
(`agent.provider`) or invites every sibling to contribute (`annotate`, `urgency`). Both are
resolved through the T-Box, so no capability package ever imports another's Python — which is
what lets one be added or removed without touching the rest.

See knowledge/decisions/capability-packages.md.
"""

from __future__ import annotations

from datetime import datetime

from .desire import Desire

import json
import logging
import threading


class Module:
    """Base class. Subclasses set CAPABILITY to the ontology term that activates them."""

    CAPABILITY: str = ""
    name: str = "module"

    def __init__(self, agent):
        self.agent = agent  # the runtime.Agent hosting this module
        self.me = agent.me  # my wiring, from the world
        self.log = logging.getLogger(f"{agent.id}.{self.name}")

    # --- lifecycle ---

    def subscriptions(self) -> list[str]:
        """Topics this module needs. All of them come from the graph."""
        return []

    def handle(self, topic: str, payload: bytes) -> bool:
        """Return True if this module took the message. Others are offered it regardless.

        It used to say "so no other module sees it", which was true and was the defect: the
        runtime returned on the first module that claimed a topic, and a second module
        subscribed to the same one never saw the message. Returning True is a report, not a
        claim — what it decides is whether the runtime warns that nobody wanted this.
        """
        return False

    def on_reading_recorded(self, subject_uri: str, observed_property: str, value: float) -> None:
        """This agent's sensing recorded something new. Most modules do not care."""

    def on_belief_revised(self, belief_term: str, value) -> None:
        """One of my agent's beliefs has been re-picked. Take it up, if it is one of mine.

        A module reads its block once, at construction, into a frozen dataclass — which is right,
        because a belief changing under a running module would otherwise be a belief nobody could
        reason about. So a revision is announced rather than discovered, and acting on it is the
        module's own business. Most never hold a revisable figure and can ignore this.

        Note what is NOT here: a hook for contributing what to review. That is declared in the
        package's `ontology.ttl` and asked of it in its `review.rq`, so a capability needs no
        Python at all to be reviewable. See orexis/review.py.
        """

    def start(self) -> None:
        """Called once the connection is up."""

    def stop(self) -> None:
        """Release timers and threads."""

    # --- what I can contribute to my siblings ---
    #
    # These exist so that a capability which HOLDS a judgment need not be imported by one that
    # merely needs it. Sensing knows how to look; it does not know what counts as trouble,
    # because trouble is a fact about a stake, and the stake belongs to whoever holds the band.
    # So sensing asks, and whoever can, answers.
    #
    # Both are asked about a (subject, property) pair rather than a subject. A stake is held in
    # a property — a band is a band of moisture — so a module handed a temperature must be able
    # to say it has no opinion, instead of judging it against the only scale it owns.

    def annotate(self, subject_uri: str, observed_property: str, value: float) -> dict:
        """What I can add to my agent's public announcement about a reading.

        Voluntary disclosure: this is the agent saying what it makes of its own state, so
        only a module that actually holds an opinion contributes one.
        """
        return {}

    def series(self) -> list[tuple[str, dict, dict]]:
        """Tagged rows for this agent's own bucket: (measurement, tags, fields), zero or more.

        Where `reports()` contributes FIELDS to the one agent-health point, this contributes
        POINTS with their own dimensions — for figures that exist per something a person
        groups a dashboard by. A property is a tag, not a suffix baked into a field name:
        `desired_low` tagged `property=SoilMoisture` groups; `desired_low_SoilMoisture` is a
        string Grafana can only ever match. Same tick, same writer, same bucket; the `agent`
        tag is added by the writer."""
        return []

    def reports(self) -> dict:
        """Fields this module wants in its agent's own health series. Most have none.

        Here rather than in `metrics.py` because the kernel must not name a capability: a build
        without a package would otherwise import one that is not there, and the reporting code
        would carry a list of every capability that ever wanted a number. A module that is not
        loaded contributes no fields, and the ABSENCE of its lines is itself a reading — it says
        this agent was never granted that ability, rather than that it has had nothing to say.
        """
        return {}

    def bounds(self, subject_uri: str, observed_property: str) -> tuple[float, float] | None:
        """Where this module wants the property HELD — the band a crossing-watching board
        should announce on leaving (#151). None means no stake and no opinion, like urgency;
        desire answers with its region's edges, and the board then literally watches the
        agent's desire while both of them sleep.
        """
        return None

    def take(self, row, desire, intention: str) -> bool:
        """Carry out one committed step, if I am the one who can. True if I did.

        The choir's doing hook (knowledge/domain/actor.md): execution has planned, written the
        head row to the ledger as `intention`, and now hands it to every module the means'
        `ag:takenBy` names. `row` is the affordance the step is — means, property, lever and,
        for a duty, whom it is owed to; `desire` is the want it serves. What to DO with them is
        this module's own, and the sizing stays where it always was — `value_bid`, `dose_for`,
        `redeem` — because an actor takes a step and never decides one.

        **False means "not now", never "no."** A bid with no round open, a dose with no fresh
        reading, a serve with no claim in hand: decline, and the intention stands for the
        trigger that changes the answer, which runs execution again and finds it standing.
        Most modules take nothing and answer False to everything.
        """
        return False

    def desires(self, now: "datetime | None" = None) -> list["Desire"]:
        """What this module contributes to what the agent is pursuing. Empty by default.

        A choir hook, like `annotate` and `series`: desires are the AGENT's, assembled from
        whichever of its modules hold wants, because no single module can see all of them any
        more. Desire contributes stakes and owing contributes debts, and an agent may have
        either without the other — a plant wants for itself and owes nobody, a pure seller owes
        and wants nothing for itself. Ranking them against each other is `agent.pursuing()`, which
        is where a currency common to both belongs.
        """
        return []

    def notices(self) -> list[tuple[str, str]]:
        """(subject, property) pairs this module notices are unknown or too stale to act on.

        The choir again (#208), for NOTICING: whoever is positioned to see that something
        warrants a decision reports it, and only reports — the deliberator turns gaps into
        moves and the keeper commits them, because deciding and remembering stay singular or
        every module becomes its own little welded chain. Sensing's are the archetype: a
        property with no observation, or a freshest reading past what the agent trusts —
        judgments it already computes for freshness and quiet(). Default: nothing to notice.

        Named for the act and not the object, the hard way: the first name was `gaps()`, and
        desire already HAD a `gaps()` — the rich desired/sensed diff, a dict — so the choir
        collected property IRIs as if they were pairs and the keeper's tick died unpacking a
        string, per tick, on every agent with a stake. Two hooks may not share a name with
        different contracts; the collision test seeds an observation first, which is the
        condition the original test missed.
        """
        return []

    def quiet(self) -> list[str]:
        """What this module has stopped hearing that it expected to hear — one line each.

        The self-liveness half of #53: the freshness rule already refuses a stale reading
        whenever something ASKS, but a fault that stops the asking is invisible to it. The
        watchdog asks this on its own clock, so the agent says "nothing from X for Ys, past
        what I allow" instead of waiting to be queried. Most modules expect nothing on a
        schedule and answer nothing; the strings are prose for a log, never parsed.
        """
        return []

    def urgency(self, subject_uri: str, observed_property: str,
                value: float | None) -> float | None:
        """How close this reading puts me to my own trouble: 0.0 (fine) to 1.0 (trouble).

        None means I have no stake in this subject and this property, and therefore no
        opinion. Sensing uses it to decide how closely to watch — attention follows need,
        and need is not sensing's to define.

        `value` may itself be None, and the question changes with it: not "how bad is this
        number" but "how urgent is it that I have no current number at all". Ignorance is a
        need like any other (#137) — a module with a stake in the property answers it, one
        with none stays silent, and the same max-of-answers resolves the choir either way.
        """
        return None

    def desire_urgency(self, desire, query, sensed: str,
                       value: float | None = None) -> float | None:
        """How urgent one DESIRE is, in the WORLD `query` answers about. None: no opinion.

        The other half of `urgency` above, and the reason it exists apart: that hook judges a
        reading against live beliefs, and a planner needs the same judgement about a world
        NOBODY IS IN YET — a candidate its effects predicted. So the world is a parameter:
        `query` is a store's query surface (the agent's belief base, or the planner's
        imaginarium) and `sensed` names the graph that world's readings live in. `value` is a
        caller-supplied number to judge where one is in hand — the choir is asked about
        readings not yet written and about predicted ones — and absent, the module judges
        what `sensed` holds.

        HOW a want's badness is measured is deliberately not the kernel's to say
        (a-desire-states-its-own-measure): the kernel asks this question and holds no measure
        vocabulary, no measure graph, no evaluator. A capability that owns the question
        answers from its own declaration — sensing does, for observation-backed wants — and a
        desire nobody answers for is maximally urgent, logged, at the call sites that rank.
        """
        return None

    @classmethod
    def measures(cls, query, observed_property: str) -> bool:
        """Would I have a measure for a want about this property? The same question as
        `desire_urgency`, asked of the CLASS and before any agent exists.

        It exists because the sovereign's gate must ask it (`orexis-validate`), and a gate
        cannot build an agent: an agent holds credentials that onboarding has not minted yet,
        and building one to interrogate it would put the runtime inside the check that runs
        before the runtime is allowed to exist. So the class answers from the same declaration
        the instance reads — one resolution, two callers — and the kernel still holds no
        measure vocabulary of its own: it asks, and whoever declares one answers.

        `query` is a store's query surface over the ratified world, which is all a KIND test
        needs. False by default, and False is the honest answer for every module that judges
        no wants — the choir shape again, with the roll called earlier than usual.
        """
        return False

    # --- helpers every module wants ---

    @staticmethod
    def parse(payload: bytes) -> dict | None:
        try:
            doc = json.loads(payload)
            return doc if isinstance(doc, dict) else None
        except (ValueError, TypeError):
            return None

    def publish(self, topic: str, payload: dict, retain: bool = False) -> None:
        self.agent.publish(topic, payload, retain)


class Timer:
    """A cancellable repeating timer — used by modules that act on their own schedule."""

    def __init__(self, interval_s: float, fn):
        self.interval_s = interval_s
        self.fn = fn
        self._timer: threading.Timer | None = None
        self._stopped = False

    def start(self) -> None:
        if self._stopped:
            return
        self._timer = threading.Timer(self.interval_s, self._fire)
        self._timer.daemon = True
        self._timer.start()

    def _fire(self) -> None:
        try:
            self.fn()
        finally:
            self.start()

    def stop(self) -> None:
        self._stopped = True
        if self._timer:
            self._timer.cancel()
