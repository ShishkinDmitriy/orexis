"""The deducer: the module that holds an agent's regions and answers for its wants.

`desire:Deducing`'s body, with the grant gone. It reads the regions the desire modality
derived, answers the choir's questions about them — the band, the urgency, the bounds a board
should watch — and contributes this agent's stakes to what it is pursuing.

The arithmetic it uses is `agent/regions.py`; what it adds is the AGENT's side of it: which
subjects are mine, which properties I hold a stake in, and what to say about a reading.
"""

from __future__ import annotations

from datetime import datetime

from .desire import Desire
from .module import Module
from .ontology import AG, SENSED_GRAPH, beliefs_graph
from .regions import (Gap, Region, aims_of, desires_of, gaps_of, regions_of,
                      _SENSING, _AIMS_Q, _REGIONS_Q)
from .store import bindings

class Deducer(Module):
    """The agent's ends, and the only module entitled to say what a reading MEANS."""

    name = "desire"

    def __init__(self, agent):
        super().__init__(agent)
        self.regions = regions_of(agent.desires.query_union, self.me.uri)
        self._aims = aims_of(agent.desires.query_union, agent.id, self.me.uri)
        self.log.info("wants %s", ", ".join(
            f"{p.rsplit('#', 1)[-1]} in {r.low:g}..{r.high:g}"
            for p, r in sorted(self.regions.items())) or "nothing")

    # --- what any sibling may ask of me ---

    def region(self, observed_property: str) -> Region | None:
        """My region in one property, or None if I hold no desire in it.

        The seam every other capability reaches me through. `agent.deducer` reaches
        whoever wants, and this says what it wants — so a bid, a dose or a cadence can be
        computed against my ends without anything importing this package.
        """
        return self.regions.get(observed_property)

    def aim(self, observed_property: str) -> float | None:
        """The point I am steering this property toward, or None if I picked none.

        The pick inside the region — private, mine, and the value `water:hasTarget` used to be.
        A consumer that requires one (a bidder pricing a deficit) treats None as its own
        refusal; nothing here defaults to the region's centre, because a fabricated preference
        is still a fabricated belief.
        """
        return self._aims.get(observed_property)

    def on_belief_revised(self, belief_term: str, value) -> None:
        """An aim is a belief, so a review may move it — within the region, which is the same
        check boot makes. Re-read rather than patched, because the revision names a term and an
        aim is a structure: simplest correct answer is to ask the graph again."""
        self._aims = aims_of(self.agent.desires.query_union, self.agent.id, self.me.uri)

    # --- what I contribute to my siblings, through the contract every module has ---

    def _is_mine(self, subject_uri: str, observed_property: str) -> bool:
        """A desire is in one property of the one subject I advance. Both have to match.

        The subject test is what keeps me quiet about somebody else's pot; the property test is
        what keeps me from judging a temperature against a moisture region. Handed either, the
        honest answer is no opinion, and saying so is the difference between silence and a
        confident wrong verdict — 21.0 read as a moisture fraction lands far above any region and
        scores as perfectly comfortable.
        """
        return subject_uri == self.me.acts_for and observed_property in self.regions

    def annotate(self, subject_uri: str, observed_property: str, value: float) -> dict:
        """My verdict on my own subject, for my agent's public announcement.

        A band and never a number: a listener learns that I am in trouble, not how wet I am. The
        message carries the property alongside it (see `agent/observation.py`), so an agent that
        now holds several desires announces several verdicts and each one says what it is about.
        """
        if not self._is_mine(subject_uri, observed_property):
            return {}
        return {"band": self.regions[observed_property].band(value)}

    def bounds(self, subject_uri: str, observed_property: str) -> tuple[float, float] | None:
        """My region's edges — what a crossing-watching board is told to announce on leaving
        (#151). The REGION and not the survival envelope, deliberately: waking at the edge of
        comfort is what makes the announcement early enough to act on, and the envelope is
        where acting has already half-failed.
        """
        if subject_uri != self.me.acts_for:
            return None
        region = self.regions.get(observed_property)
        return (region.low, region.high) if region else None

    def urgency(self, subject_uri: str, observed_property: str,
                value: float | None) -> float | None:
        """How close this puts me to trouble. Sensing turns it into a cadence.

        NOT MINE TO COMPUTE ANY MORE, only mine to ANSWER FOR: how a want's badness is
        measured is a capability's contribution (a-desire-states-its-own-measure), so this
        asks the choir's other half — `Agent.desire_urgency`, where sensing answers for
        observation-backed wants from its own declaration — with `$value` the caller's number,
        because the choir is asked about readings it has not written yet and about PREDICTED
        ones. What shifted with the declaration is the anchor: distance from the AIM, with the
        centre only the no-pick fallback, so the cadence tightens toward the point the agent
        actually steers for. Callers changed nothing.

        Asked with None, the question is the urgency of NOT KNOWING (#137), and the answer is
        maximal: not knowing whether the pot is dying is at least as urgent as knowing it is
        uncomfortable, and the region cannot say otherwise without a number to judge. The first
        current reading ends this answer — ignorance decays into whatever the gap then says —
        which is "the first intention is always Observe" in its cadence-shaped form.
        """
        if not self._is_mine(subject_uri, observed_property):
            return None
        if value is None:
            return 1.0
        answer = self._measured(Desire(uri="urn:asked", urgency=1.0,
                                       observed_property=observed_property, value=value),
                                value)
        #  The defined fallback: a want nothing loaded measures is maximal — not knowing how
        #  bad IS how bad. `desires_of` logs it where the ranking runs.
        return 1.0 if answer is None else answer

    def _measured(self, desire: Desire, value: float | None = None) -> float | None:
        """The choir road: whichever capability measures this want, asked against the LIVE
        belief base. Handed into `desires_of` and `gaps_of` too, because a free function
        cannot hold the agent — one question, one asker, however many joins consume it."""
        return self.agent.desire_urgency(desire, self.agent.beliefs.query, SENSED_GRAPH,
                                         value)

    # --- the diff, asked of me rather than recomputed by whoever wants it ---

    def gaps(self) -> dict[str, Gap]:
        """Where every property I want stands against where I want it — stale rows included.

        Included on purpose: a stale row is "last I looked I was dry, and I cannot see any
        more", which a deliberator needs precisely because nothing else will mention it. Rows
        carry `at`, and `current()` is the same diff with my own freshness rule applied.
        """
        return gaps_of(self.agent.desires.query_union, self.agent.beliefs.query,
                       self.me.uri, self.agent.id, measure=self._measured)

    def current(self) -> dict[str, Gap]:
        """The diff I would act on: every row still inside my own freshness rule.

        The rule is sensing's — the cadence I commanded plus my grace, per property — asked
        through the provider exactly as bidding asks it, because a reading past what I allow
        for the rhythm I myself set is a sensor gone quiet, not a measurement. Issue #124's
        case in one sentence: a dead probe's last observation is upserted, never expires, and
        without this filter kept presenting a comfortable pot for however long the probe stayed
        dead. With no sensing at all nothing wrote these observations either, so every row
        passes vacuously and honestly.
        """
        sensing = self.agent.provider(_SENSING)
        if sensing is None:
            return self.gaps()
        out = {}
        for prop, gap in self.gaps().items():
            age = gap.age_s()
            if age is not None and age > sensing.stale_after_s(self.me.acts_for, prop):
                continue
            out[prop] = gap
        return out

    def reports(self) -> dict:
        """What this agent wants, how much of that it can currently see, and the worst of it.

        `desires` belongs in the health series because an agent whose regions silently went to
        zero — a world amended, a range withdrawn — is running and doing nothing, which is the
        failure that looks most like working. `desires_measured` counts the regions with a
        CURRENT reading behind them, so blind and gone-quiet finally have a line: the two
        numbers diverging is a desire this agent cannot see, whether because no instrument
        exists or because one died. `worst_gap` is computed over the current rows only — a
        frozen last reading must not present as a live verdict — so on a dead sensor it
        disappears rather than reassures, and `reading_age_s` on the same dashboard says why.
        """
        out: dict = {"desires": len(self.regions)}
        current = self.current()
        out["desires_measured"] = len(current)
        if current:
            out["worst_gap"] = round(max(abs(g.gap) for g in current.values()), 3)
        return out

    def desires(self, now: datetime | None = None) -> list[Desire]:
        """MY contribution to what this agent is pursuing: its stakes, and no duties.

        The choir hook for desires (`agent.pursuing()` merges every module's). Split from the debts
        when the ledger became its own capability: an agent may hold stakes and owe nothing, owe
        and hold no stake — `world/simulation`'s city is exactly that — or both, and none of
        those is the others' business. `desires_of` reads the whole shipped query and each module
        takes its own kind, so there is still one text and one definition.
        """
        return [g for g in desires_of(self.agent.desires.query_union,
                                    self.agent.beliefs.query, self.me.uri, self.agent.id, now,
                                    measure=self._measured)
                if not g.is_duty]

    def series(self) -> list[tuple[str, dict, dict]]:
        """WHERE the want sits, not merely that it exists (#61's argument, extended from the
        revisable picks to the deduced regions) — one row per property, the property as a TAG
        on the sovereign's own suggestion: `desired_low` grouped by `property` is one generic
        panel for any number of wants, where a suffixed field name is a string a dashboard can
        only match. Into this agent's OWN bucket — the operator sees them, rivals do not. A
        region that quietly moved (a world amended, an instrument narrowed, a flowering season
        ratified) and an aim drifting inside it are exactly the lines a sovereign wants."""
        rows = []
        for prop, region in sorted(self.regions.items()):
            local = prop.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            fields = {"desired_low": region.low, "desired_high": region.high}
            aim = self.aim(prop)
            if aim is not None:
                fields["aim"] = aim
            rows.append(("agent_desire", {"property": local}, fields))

        return rows
