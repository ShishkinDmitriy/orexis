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

from orexis_agent_progression.ontology import BELIEF_REVISED, QUIET, REPORTS, SEND, SERIES
from orexis_agent_progression.ontology import DESIRES, DESIRE_URGENCY

from datetime import datetime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    #  Annotation-only (#455): the base Module names Want in hook SIGNATURES and never
    #  touches it — a contract annotation is free, where an import would make every module
    #  that subclasses this load the deliberation layer at assembly.
    from orexis_agent_deliberation.want import Want

import json
import logging

from assembly.contribute import answer as assembly_answer, contributes
from assembly.inject import Handle, injections_of


#  THE MECHANISM IS ASSEMBLY'S. `@contributes` marks a function with the point it fills and the
#  resolver finds it on a class, an instance or a module; what stays here is the BDI-shaped
#  points themselves and their defaults (the-assembly-is-not-the-mind).


class Module:
    """Base class. Subclasses set CAPABILITY to the ontology term that activates them."""

    CAPABILITY: str = ""
    name: str = "module"

    def answer(self, term: str):
        """Whatever fills one point on me, as a bound method — or None if I fill none."""
        return assembly_answer(self, term)

    def __init__(self, agent):
        self.agent = agent  # the runtime.Agent hosting this module
        self.me = agent.me  # my wiring, from the world
        self.log = logging.getLogger(f"{agent.id}.{self.name}")

        #  WHAT THIS MODULE DECLARED IT NEEDS — a value-less class annotation, the same
        #  convention dataclasses use. Handles, not objects: the service is built on first
        #  touch, so a module needing another module's service is never built before it exists,
        #  and nothing is imported until an agent reaches for it. `X | None` means the module
        #  can work without one (an-injected-service-is-reached-by-term).
        for name, (key, optional) in injections_of(type(self)).items():
            if optional and not agent.offers(key):
                setattr(self, name, None)     # `X | None` and nothing offers X
            else:
                setattr(self, name, Handle(key, agent.service))

    # --- lifecycle ---

    @contributes(BELIEF_REVISED)
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

    @contributes(SERIES)
    def series(self) -> list[tuple[str, dict, dict]]:
        """Tagged rows for this agent's own bucket: (measurement, tags, fields), zero or more.

        Where `reports()` contributes FIELDS to the one agent-health point, this contributes
        POINTS with their own dimensions — for figures that exist per something a person
        groups a dashboard by. A property is a tag, not a suffix baked into a field name:
        `desired_low` tagged `property=SoilMoisture` groups; `desired_low_SoilMoisture` is a
        string Grafana can only ever match. Same tick, same writer, same bucket; the `agent`
        tag is added by the writer."""
        return []

    @contributes(REPORTS)
    def reports(self) -> dict:
        """Fields this module wants in its agent's own health series. Most have none.

        Here rather than in `metrics.py` because the kernel must not name a capability: a build
        without a package would otherwise import one that is not there, and the reporting code
        would carry a list of every capability that ever wanted a number. A module that is not
        loaded contributes no fields, and the ABSENCE of its lines is itself a reading — it says
        this agent was never granted that ability, rather than that it has had nothing to say.
        """
        return {}

    @contributes(DESIRES)
    def desires(self, now: "datetime | None" = None) -> list["Want"]:
        """What this module contributes to what the agent is pursuing. Empty by default.

        A choir hook, like `annotate` and `series`: desires are the AGENT's, assembled from
        whichever of its modules hold wants, because no single module can see all of them any
        more. Sensing contributes stakes and owing contributes debts, and an agent may have
        either without the other — a plant wants for itself and owes nobody, a pure seller owes
        and wants nothing for itself. Ranking them against each other is `agent.pursuing()`, which
        is where a currency common to both belongs.
        """
        return []

    @contributes(QUIET)
    def quiet(self) -> list[tuple[str, str]]:
        """What this module has stopped hearing that it expected to hear — `(key, line)` each.

        The self-liveness half of #53: the freshness rule already refuses a stale reading
        whenever something ASKS, but a fault that stops the asking is invisible to it. The
        watchdog asks this on its own clock, so the agent says "nothing from X for Ys, past
        what I allow" instead of waiting to be queried. Most modules expect nothing on a
        schedule and answer nothing; the lines are prose for a log, never parsed.

        THE KEY IS WHY THIS IS A PAIR, and it was learned the expensive way. The watchdog
        tells a new silence from a continuing one by set difference, and it used to difference
        the LINES — which carry the elapsed seconds, so every look rendered a different string
        for the same unbroken fault. One sensor down read as a fresh fault plus a recovery
        every sixty seconds, forever: `nothing for 337s` beside `heard again — was: nothing for
        277s`, while nothing had been heard for seven minutes. The contributor names the thing
        that went quiet, because only it knows; the watchdog compares keys and prints lines,
        and "never parsed" stays true.
        """
        return []

    @contributes(DESIRE_URGENCY)
    def desire_urgency(self, judgment, query, state: str,
                       value: float | None = None) -> float | None:
        """How urgent one DESIRE is, in the WORLD `query` answers about. None: no opinion.

        The other half of `urgency` above, and the reason it exists apart: that hook judges a
        reading against live beliefs, and a planner needs the same judgement about a world
        NOBODY IS IN YET — a candidate its effects predicted. So the world is a parameter:
        `query` is a store's query surface (the agent's belief base, or the planner's
        imaginarium) and `state` names the graph that world's state lives in. `value` is a
        caller-supplied number to judge where one is in hand — the choir is asked about
        readings not yet written and about predicted ones — and absent, the module judges
        what `state` holds.

        HOW a want's badness is measured is deliberately not the kernel's to say
        (a-desire-states-its-own-measure): the kernel asks this question and holds no measure
        vocabulary, no measure graph, no evaluator. A capability that owns the question
        answers from its own declaration — sensing does, for observation-backed wants — and a
        desire nobody answers for is maximally urgent, logged, at the call sites that rank.
        """
        return None

    @staticmethod
    def parse(payload: bytes) -> dict | None:
        try:
            doc = json.loads(payload)
            return doc if isinstance(doc, dict) else None
        except (ValueError, TypeError):
            return None

    def publish(self, topic: str, payload: dict, retain: bool = False,
                not_after=None) -> bool:
        """Put something on the wire — asked of whoever holds the connection (`send`). True if
        it left. The kernel has no mailbox; the transport that reaches the society is a
        capability.

        `not_after` is the moment the message stops meaning anything — an
        [act](knowledge/domain/act.md)'s window, where one is being carried out. Given one, a
        transport with no live session REFUSES rather than queueing: a queue faithfully
        delivers a message the agent no longer means, which is the whole argument of
        knowledge/decisions/publishing-is-a-goal-and-the-protocol-is-a-primitive.md. Without
        one — a cadence command, a status reply, an announcement — queueing is right and
        nothing changes.
        """
        return any(self.agent.ask(SEND, topic, payload, retain, not_after))

