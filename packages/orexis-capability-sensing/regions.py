"""Where a property should be held, and how far a reading is from there — sensing's arithmetic.

**Was `agent/regions.py`, the kernel's.** A region is deduced from what a subject STATES IT
NEEDS and met by an OBSERVATION sitting inside it; a gap is the signed distance of the latest
reading from the point steered for; the wants assembled here — a stake per property, a
freshness want per instrument — are exactly the wants whose premise is an observation. Every
one of those is a sentence in `sosa`, which is this package's vocabulary and not the kernel's:
the kernel knows that a want exists, ranks it, plans for it and commits to it, and never learns
what a reading is (the-stake-is-sensings-want). The AIM — the pick inside a region — is here too,
since a point in a property checked against a range is the same kind of sentence; what stayed
behind is the obligation (`agent/ower.py`), which is not about sensing.

`Region.urgency` is a reference definition and not the live one: how a want's badness is
measured is declared in `measures.ttl` and asked through the choir (`Module.desire_urgency`).
See knowledge/domain/desire.md and knowledge/decisions/a-desire-states-its-own-measure.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from orexis_agent_progression.ontology import STATE_GRAPH, beliefs_graph
from orexis_agent_progression.store import bindings

log = logging.getLogger("sensing")

#  `ObservedDesire` LIVED HERE and is `rows.py`'s now (#455): it subclasses the mind's
#  Desire, and a base class is an import — see the module `__getattr__` at the bottom,
#  which keeps every existing import path working.


# What this agent wants about observations: its stakes and its freshness wants, shipped as
# SPARQL so any consumer can run it. Read once at import: a malformed query is then an error
# the moment the package loads rather than the first time somebody asks.
DESIRES_QUERY = (Path(__file__).parent / "desires.rq").read_text()

# My own aims — the pick inside each region, one per property I chose to steer. PRIVATE, so the
# graph is named: an unqualified pattern reads public knowledge, and an aim is exactly what must
# never arrive that way.
_AIMS_Q = """
SELECT ?property ?value WHERE {{ GRAPH <{beliefs}> {{
  <{me}> sensing:aims ?aim .
  ?aim ssn:forProperty ?property ;
       schema:value ?value .
}} }}"""


def aims_of(query, agent_id: str, agent_uri: str) -> dict[str, float]:
    """One agent's aims, property -> value. Private, so the beliefs graph is named.

    Takes the id as well as the URI because the graph is named from the one and the subject from
    the other — the same two facts the module itself is handed at construction.
    """
    return {row["property"]: float(row["value"])
            for row in bindings(query(_AIMS_Q.format(
                beliefs=beliefs_graph(agent_id), me=agent_uri)))}


#  THE READING OF THE SENSED GRAPH — sosa and nothing else: what was read, of what,
#  by which instrument, when. What it does NOT ask is whether a reading is still evidence:
#  that is sensing's judgment (`sensing:staleAfterS` is sensing's word), made through the
#  freshness want it derives and the measure it declares, and never here. A stake judges the
#  number it has; not knowing is the epistemic want's business, and `want_about` answers
#  that one first. The instrument is `sosa:madeBySensor`, which the sensed writer stamps.
_READINGS_Q = """
SELECT ?subject ?property ?value ?at ?instrument WHERE {
  GRAPH $state {
    ?obs sosa:hasFeatureOfInterest ?subject ;
         sosa:observedProperty ?property ;
         sosa:hasSimpleResult ?value .
    OPTIONAL { ?obs sosa:resultTime ?at }
    OPTIONAL { ?obs sosa:madeBySensor ?instrument }
  }
}"""


# My own regions, read once at construction — through `orexis:metWhen`, since the desire became a
# node carrying its shape rather than being it. The only instance identifier named is my own
# URI, which is the single one a process is handed — everything else is a term.
#
# Not narrowed to the desire graph, deliberately, and this is the trap AGENTS.md names: a basic
# graph pattern inside one `GRAPH` clause must match entirely within that graph, and desire is a
# CLASS of graph precisely so that a second source may exist. An unqualified pattern reads every
# public graph, so a region contributed by something other than the deduction is simply seen.
#  The numbers are read out of the SHAPES the deduction emits (a-desire-is-a-shape), and that
#  is the whole reason those shapes are DECLARATIVE rather than sh:sparql: an edge is an
#  ordinary triple, so a gap costs one query per reading instead of a validator run. The path
#  is deep because a reified observation has to be reached through an inverse path and a
#  qualified shape — convoluted to read, and the price of not inventing a second way to say
#  what a graph should look like.
#
#  TWO NODE SHAPES per property, told apart by the FORCE they carry: the region, a violation of
#  which is a gap, and the envelope, a violation of which is the subject ending.
#
#  Within each, the edges live on the SIDE shapes, one number apiece (#242): the floor is what
#  the Below shape refuses to see a reading under (`sh:maxExclusive`) and the ceiling is what
#  the Above shape refuses to see one over (`sh:minExclusive`). That is one hop further than
#  reading a min and a max off a single node, and it buys a violation that says WHICH WAY it
#  went — which watering repairs and a fan does not. See orexis:violationIs.
_REGIONS_Q = """
SELECT ?property ?low ?high ?floor ?ceiling WHERE {
  <%s> orexis:holds ?desire .
  ?desire ssn:forProperty ?property ; orexis:metWhen ?shape .
  ?shape sh:property ?below , ?above .
  ?below orexis:violationIs orexis:Below ;
         sh:qualifiedValueShape/sh:property/sh:maxExclusive ?low .
  ?above orexis:violationIs orexis:Above ;
         sh:qualifiedValueShape/sh:property/sh:minExclusive ?high .
  OPTIONAL {
    <%s> orexis:holds ?envelope .
    ?envelope ssn:forProperty ?property ; sh:property ?underFloor , ?overCeiling .
    ?underFloor sh:severity sh:Warning ; orexis:violationIs orexis:Below ;
                sh:qualifiedValueShape/sh:property/sh:maxExclusive ?floor .
    ?overCeiling sh:severity sh:Warning ; orexis:violationIs orexis:Above ;
                 sh:qualifiedValueShape/sh:property/sh:minExclusive ?ceiling }
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
        """The FALLBACK target — where an agent with no other reason to prefer would aim.

        That sentence was always the admission that the centre stood in for the pick, and
        since a-desire-states-its-own-measure it stands in only where there is no pick: the
        declared measure reads the aim at query time and falls back to this exactly when the
        agent has picked nothing."""
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
        """How close this reading puts me to real trouble: 0.0 at the centre, 1.0 at the edge
        of what my subject survives.

        **A REFERENCE, no longer the live definition.** How a want's badness is measured is a
        capability's answer now, asked through the choir (`Module.desire_urgency`) — sensing's
        `measures.ttl` for observation-backed wants, measured from the AIM at query time with
        the centre only as the no-pick fallback — so the two agree exactly when no aim is
        picked, which is what the tests hold the declared query to. Nothing on the live path
        calls this any more: a want nothing measures scores a logged 1.0 rather than falling
        back here, because a silent second definition is the drift the declaration exists to
        prevent.

        **Measured from a point INSIDE the region and not from the edge**, which is a deliberate
        difference from the band. A step function would tell sensing to relax completely
        anywhere inside the region and then panic on the way out, and attention should rise as
        the edge approaches — an agent at the very edge of comfortable is already worth watching
        more closely than one sitting in the middle. So the band answers *am I in trouble* and
        this answers *how close am I getting*, and they are not each other's complement.

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
    """One row of the diff: where a property is against where it should be — and WHEN it was.

    `gap` is signed — negative below the point being steered for (the aim, or the centre while
    none is picked), positive above — and |gap| is the desire's own declared measure,
    normalised by the survival room on that side. One definition, asked of the same measure
    every other consumer runs, so the diff cannot disagree with the ranking.

    `at` is when the sensed side was measured. The row does not judge its own freshness,
    because how old is too old is the agent's rule — the cadence it commanded plus its grace —
    and a diff that quietly hid stale rows would hide exactly the case worth seeing: "last I
    looked I was dry, and I cannot see any more" is information, not noise. `age_s` is given so
    the judging is one comparison for whoever holds the policy.
    """

    observed_property: str
    value: float
    low: float
    high: float
    gap: float
    at: datetime | None = None
    #  The shape this diff is against, so a desire built from it can name its own node rather
    #  than rebuilding the IRI — a want minted by a rule is found by asking, never by spelling.
    region: str | None = None

    def age_s(self, now: datetime | None = None) -> float | None:
        """Seconds since the sensed side was true, or None for a reading with no timestamp."""
        if self.at is None:
            return None
        return ((now or datetime.now(timezone.utc)) - self.at).total_seconds()


def gaps_of(desires, beliefs, agent_uri: str, agent_id: str, measure=None) -> dict[str, Gap]:
    """The desired/sensed diff for one agent, property -> gap. Computed, never stored.

    A gap is a VERDICT — the same number is a crisis for one agent and nothing for another — so
    like a band it is recomputed on every asking and no graph holds it. What may be persisted is
    a summary of its history, which is review's pattern and not this function's business.

    Two handles since the dataset split (#298): `desires` answers what is WANTED and `beliefs`
    what IS, and the join is here — `desires.rq` and `readings.rq` are the two texts. The
    MAGNITUDE is nobody's arithmetic here: `measure` is the choir road the sensing module hands in
    (see `_measured_urgency`), so the diff and the ranking cannot disagree because both ask the
    same capability the same question. `agent_id` names the pick record the sign's aim is read
    from. A property with no observation yet is absent rather than zero: at birth every desire
    is unmeasured, and unmeasured must not read as satisfied.
    """
    subjects = _subjects_of(beliefs, agent_uri)
    known, _ = _known(beliefs)
    aims = aims_of(desires, agent_id, agent_uri)
    out: dict[str, Gap] = {}
    for row in _desired(desires, agent_uri):
        if row["kind"] != "stake":
            continue
        subject = next((s for s in subjects if (s, row["property"]) in known), None)
        item = known.get((subject, row["property"])) if subject else None
        if item is None or item.value is None:
            continue
        region = _region_of(row)
        urgency = _measured_urgency(measure, row, item.value)
        #  The SIGN is judged against the same point the measure judges distance from: the
        #  aim, or the centre while none is picked. Signed against the centre it disagreed
        #  with its own magnitude the moment a pick moved off-centre.
        target = aims.get(row["property"], region.centre)
        gap = 0.0 if item.value == target else             (urgency if item.value > target else -urgency)
        out[row["property"]] = Gap(
            observed_property=row["property"], value=item.value,
            low=region.low, high=region.high, gap=gap,
            at=item.at, region=row.get("desire"),
        )
    return out


def _measured_urgency(measure, row: dict, value: float | None) -> float:
    """One want's urgency: whichever capability measures such wants, asked through `measure`.

    It was `_stake_urgency` while a stake was the only kind anything declared a measure for.
    Freshness has one now — sensing's, since the want became sensing's — and it takes the same
    road, which is the point of the road: the kernel asks, a capability answers, and this
    function does not learn which kind it just asked about. `value` may be None, because the
    question *how urgent is not knowing* is exactly the one a freshness want asks.

    `measure` is the choir road, handed in by the sensing module — `(desire, value) -> float | None`,
    behind which `Agent.desire_urgency` asks every module and sensing answers for
    observation-backed wants against the live belief base. A free function cannot hold the
    agent, so the join takes the question as a parameter; the KERNEL evaluates nothing
    (a-desire-states-its-own-measure). `value` is the reading the caller already joined, so
    the number judged and the number on the row are one fact from one read.

    A want nothing measures scores 1.0, logged — the defined fallback: not knowing how bad is
    maximal, exactly as not knowing at all is. Logged only where a measure was actually ASKED:
    a caller that hands none in is not asking about these wants at all (the debts reader wants
    the obligation rows and computes the rest to throw away), and warning there says a package is
    missing when nothing is.
    """
    #  The INSTRUMENT rides along, because it is what tells the answerer which kind of want
    #  this is. A row that binds none is a stake and the want it makes says so by omission.
    #  Deferred (#455): the row type is `rows.py`'s now — a base class is an import — and a
    #  top-level import here would be the cycle (rows imports this file's helpers). Runs only
    #  where a measure was handed in, which only a running mind ever does.
    from .rows import ObservedDesire
    answer = measure(ObservedDesire(uri=row["desire"], urgency=1.0,
                            observed_property=row["property"], value=value,
                            instrument=row.get("instrument")),
                     value) if measure else None
    if answer is None:
        if measure is not None:
            log.warning("nothing loaded measures a want about %s — urgency reads 1.0",
                        row["property"])
        return 1.0
    return answer


#  `desires_of` LIVED HERE and is `rows.py`'s now (#455), for the same reason as the class
#  it constructs.


@dataclass(frozen=True)
class Known:
    """One current reading: the value and when it was taken. Whether it is still evidence is
    not on it — that is sensing's judgment, made through the freshness want and its measure."""

    value: float | None
    at: datetime | None


def _desired(desires, agent_uri: str) -> list[dict]:
    """The desire modality's rows about observations — `desires.rq`, this package's."""
    return bindings(desires(DESIRES_QUERY.replace("$me", f"<{agent_uri}>")))


def _known(beliefs) -> tuple[dict, dict]:
    """What is known, keyed twice: by (subject, property) for the stakes, and by
    (instrument, property) for the freshness wants, which name the instrument they are about."""
    by_pair, by_instrument = {}, {}
    for r in bindings(beliefs(_READINGS_Q.replace("$state", f"<{STATE_GRAPH}>"))):
        item = Known(value=float(r["value"]) if r.get("value") else None,
                     at=datetime.fromisoformat(r["at"]) if r.get("at") else None)
        by_pair[(r["subject"], r["property"])] = item
        if r.get("instrument"):
            by_instrument[(r["instrument"], r["property"])] = item
    return by_pair, by_instrument


def _subjects_of(beliefs, agent_uri: str) -> list[str]:
    return [r["s"] for r in bindings(beliefs(
        f"SELECT ?s WHERE {{ <{agent_uri}> orexis:actsFor ?s }}"))]


def _region_of(row: dict) -> Region:
    floor, ceiling = row.get("floor"), row.get("ceiling")
    return Region(observed_property=row["property"],
                  low=float(row["low"]), high=float(row["high"]),
                  floor=float(floor) if floor is not None else None,
                  ceiling=float(ceiling) if ceiling is not None else None)


def regions_of(query, agent_uri: str) -> dict[str, Region]:
    """Every region one agent holds, property -> region. Read, never computed here.

    A free function because it is the whole of what this module does with a store, and a test
    about what a world implies should not have to build an agent to ask. The arithmetic that
    produced these numbers is `desires.ru`, run on every rebuild of the desire modality; this
    only reads the answer.
    """
    out: dict[str, Region] = {}
    for row in bindings(query(_REGIONS_Q % (agent_uri, agent_uri))):
        floor, ceiling = row.get("floor"), row.get("ceiling")
        out[row["property"]] = Region(
            observed_property=row["property"],
            low=float(row["low"]), high=float(row["high"]),
            floor=float(floor) if floor is not None else None,
            ceiling=float(ceiling) if ceiling is not None else None,
        )
    return out


def __getattr__(name: str):
    """The Desire-shaped half lives in `rows` and loads on first touch (#455).

    A base class is an import: `ObservedDesire(Desire)` made importing this file load the
    deliberation layer, so a sensing-only assembly paid for row types only a running mind
    constructs. Forwarding keeps every import path as it was — `regions.ObservedDesire` and
    `regions.desires_of` resolve here, at the moment something touches them, which in any
    running agent is a moment the layer is already loaded.
    """
    if name in ("ObservedDesire", "desires_of"):
        from . import rows
        return getattr(rows, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
