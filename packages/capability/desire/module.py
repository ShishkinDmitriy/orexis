"""desire:Deducing — the region this agent is trying to hold, one per property it has a stake in.

**This is the middle letter of BDI, and it is the one the project had least of.** Belief had a
whole store, and desire was three decimals in a beliefs file: a target and two band edges,
denominated in soil moisture and in nothing else. So an agent could want exactly one thing, and
the air temperature and humidity this society senses fed nothing that could want anything.

What it holds now is a REGION per property — where to keep it — and the ENVELOPE outside it,
where the subject does not merely sit badly but ends. Both are deduced, at genesis, by
`rules.ru`, from ranges the world already states. Nothing here is authored, and that is the
point: `water:hasTarget 0.55` was one decimal in a private file against which `0.95` would have
validated exactly as well, and the region is what a pick like that answers to.

**Three questions this module answers for its siblings, and none of them imports it.**

    band(property, value)     LOW / OK / HIGH — the verdict that travels in an announcement
    urgency(property, value)  0.0 to 1.0 — what perception turns into a cadence
    region(property)          the numbers themselves, for whoever needs to aim rather than judge

They used to come from `market:Bidding`, which meant an agent had to be a BIDDER to have an
opinion about its own state — and could only have one, about the one property a bid is priced
in. A stake is not a market position. An agent that acts for a plant in a world with no economy
at all still knows when that plant is in trouble; it simply has nobody to ask for help.

Vocabulary: packages/capability/desire/ontology.ttl. Rules: its shapes.ttl. Derivation: its
rules.ru. See knowledge/decisions/desire-is-deduced-from-the-ranges-the-world-states.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent.module import Module
from agent.ontology import SENSED_GRAPH
from agent.store import bindings

from .terms import DEDUCING

# The diff between desired and sensed, shipped as SPARQL so any consumer can run it — see the
# file's own header. Read once at import: a malformed query is then an error the moment the
# package loads rather than the first time somebody asks.
GAP_QUERY = (Path(__file__).parent / "gap.rq").read_text()

# My own regions, read once at construction. The only instance identifier named is my own URI,
# which is the single one a process is handed — everything else is a term.
#
# Not narrowed to the desire graph, deliberately, and this is the trap AGENTS.md names: a basic
# graph pattern inside one `GRAPH` clause must match entirely within that graph, and desire is a
# CLASS of graph precisely so that a second source may exist. An unqualified pattern reads every
# public graph, so a region contributed by something other than the deduction is simply seen.
_REGIONS_Q = """
SELECT ?property ?low ?high ?floor ?ceiling WHERE {
  <%s> desire:desires ?desire .
  ?desire ssn:forProperty ?property ;
          schema:minValue ?low ;
          schema:maxValue ?high .
  OPTIONAL { ?desire desire:toleratedMin ?floor ; desire:toleratedMax ?ceiling }
} ORDER BY ?property"""


@dataclass(frozen=True)
class Region:
    """Where one property should be held, and how much room there is outside before it ends."""

    observed_property: str
    low: float
    high: float
    floor: float | None = None    # the survival envelope, when the world states one
    ceiling: float | None = None

    @property
    def centre(self) -> float:
        """The point of the region — where an agent with no other reason to prefer would aim."""
        return (self.low + self.high) / 2

    def band(self, value: float) -> str:
        """A reading judged against MY region. Never stored — always recomputed.

        The same three words a moisture band has always used, now said about any property and
        derived from a range rather than from two hand-picked decimals. The same 0.30 is LOW for
        a fern and OK for a succulent because their plants need different things, which is
        exactly what it meant before; what has changed is that the difference is now stated
        publicly by the plants rather than implicitly by two numbers nobody could check.
        """
        if value < self.low:
            return "LOW"
        if value > self.high:
            return "HIGH"
        return "OK"

    def urgency(self, value: float) -> float:
        """How close this reading puts me to real trouble: 0.0 at the point of my region, 1.0 at
        the edge of what my subject survives.

        **Measured from the CENTRE and not from the edge**, which is a deliberate difference from
        the band. A step function would tell perception to relax completely anywhere inside the
        region and then panic on the way out, and attention should rise as the edge approaches —
        an agent at the very edge of comfortable is already worth watching more closely than one
        sitting in the middle. So the band answers *am I in trouble* and this answers *how close
        am I getting*, and they are not each other's complement.

        **Asymmetric for free, and that is the whole reason the envelope is carried.** The scale
        on each side is the distance from the centre to the survival bound on THAT side, so how
        bad it is to be 0.05 out depends on how much room there is in that direction. A
        Zamioculcas comes back from bone dry and does not come back from a rotted rhizome; with
        the two figures in hand, the wet side reads as sharper than the dry one without a line of
        code knowing anything about roots.

        With no envelope stated the region's own edge is the scale — cruder, honestly reached,
        and the answer degrades rather than failing. A region with no width at all is
        all-or-nothing trouble, which is the same reading `market:Bidding` gave a bandless agent.
        """
        centre = self.centre
        if value == centre:
            return 0.0
        if value < centre:
            outer = self.floor if self.floor is not None else self.low
        else:
            outer = self.ceiling if self.ceiling is not None else self.high
        room = abs(outer - centre)
        if room <= 0:
            return 1.0
        return min(1.0, abs(value - centre) / room)


@dataclass(frozen=True)
class Gap:
    """One row of the diff: where a property is against where it should be.

    `gap` is signed — negative below the region's point, positive above — and |gap| is the
    module's `urgency`, normalised by the survival room on that side. See gap.rq, which is the
    definition; this is only its Python shape.
    """

    observed_property: str
    value: float
    low: float
    high: float
    gap: float


def gaps_of(query, agent_uri: str) -> dict[str, Gap]:
    """The desired/sensed diff for one agent, property -> gap. Computed, never stored.

    A gap is a VERDICT — the same number is a crisis for one agent and nothing for another — so
    like a band it is recomputed on every asking and no graph holds it. What may be persisted is
    a summary of its history, which is review's pattern and not this function's business.

    A property with no observation yet is absent rather than zero: at birth every desire is
    unmeasured, and unmeasured must not read as satisfied.
    """
    substituted = (GAP_QUERY
                   .replace("$me", f"<{agent_uri}>")
                   .replace("$sensed", f"<{SENSED_GRAPH}>"))
    return {row["property"]: Gap(
        observed_property=row["property"],
        value=float(row["value"]),
        low=float(row["low"]), high=float(row["high"]),
        gap=float(row["gap"]),
    ) for row in bindings(query(substituted))}


def regions_of(query, agent_uri: str) -> dict[str, Region]:
    """Every region one agent holds, property -> region. Read, never computed here.

    A free function because it is the whole of what this module does with a store, and a test
    about what a world implies should not have to build an agent to ask. The arithmetic that
    produced these numbers is in `rules.ru` and ran at genesis; this only reads the answer.
    """
    out: dict[str, Region] = {}
    for row in bindings(query(_REGIONS_Q % agent_uri)):
        floor, ceiling = row.get("floor"), row.get("ceiling")
        out[row["property"]] = Region(
            observed_property=row["property"],
            low=float(row["low"]), high=float(row["high"]),
            floor=float(floor) if floor is not None else None,
            ceiling=float(ceiling) if ceiling is not None else None,
        )
    return out


class DesireModule(Module):
    """The agent's ends, and the only module entitled to say what a reading MEANS."""

    CAPABILITY = DEDUCING
    name = "desire"

    def __init__(self, agent):
        super().__init__(agent)
        self.regions = regions_of(agent.store.query, self.me.uri)
        self.log.info("wants %s", ", ".join(
            f"{p.rsplit('#', 1)[-1]} in {r.low:g}..{r.high:g}"
            for p, r in sorted(self.regions.items())) or "nothing")

    # --- what any sibling may ask of me ---

    def region(self, observed_property: str) -> Region | None:
        """My region in one property, or None if I hold no desire in it.

        The seam every other capability reaches me through. `agent.provider(DESIRE)` finds
        whoever wants, and this says what it wants — so a bid, a dose or a cadence can be
        computed against my ends without anything importing this package.
        """
        return self.regions.get(observed_property)

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

    def urgency(self, subject_uri: str, observed_property: str, value: float) -> float | None:
        """How close this puts me to trouble. Perception turns it into a cadence."""
        if not self._is_mine(subject_uri, observed_property):
            return None
        return self.regions[observed_property].urgency(value)

    # --- the diff, asked of me rather than recomputed by whoever wants it ---

    def gaps(self) -> dict[str, Gap]:
        """Where every property I want stands against where I want it. Fresh on every call."""
        return gaps_of(self.agent.store.query, self.me.uri)

    def reports(self) -> dict:
        """How many things this agent wants, and how far it sits from the worst of them.

        `desires` belongs in the health series because an agent whose regions silently went to
        zero — a world amended, a range withdrawn — is running and doing nothing, which is the
        failure that looks most like working. `worst_gap` is the same diff every other consumer
        reads, disclosed as |gap| so the series is comparable across agents whose properties are
        in different units. Absent while nothing has been observed, and the absence is itself a
        reading: this agent wants things it has not yet seen.
        """
        out: dict = {"desires": len(self.regions)}
        gaps = self.gaps()
        if gaps:
            out["worst_gap"] = round(max(abs(g.gap) for g in gaps.values()), 3)
        return out
