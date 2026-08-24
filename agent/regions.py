"""What an agent wants, as arithmetic: the region, the gap, and the wants it ranks.

**The kernel's.** This was the desire package's, granted to an agent that acts for a subject
stating what it needs — and the store those wants live in was built for every agent regardless,
by `Agent.__init__`, three lines above the modules. The same contradiction the keeper and the
deliberator each turned out to have: a modality for everyone, a reader for some. A mind is not
plug-in-able.

What is HERE is the arithmetic, which has one form: intersecting stated ranges, measuring the
signed distance to an aim, ranking a stake against a duty in one unit-free currency. What is
NOT here is the question the capability was actually named for — where a region COMES from.
Working it out from the ranges the world states is one answer and asking something else is
another, and that seam is real; it is a pick now rather than a grant, like the deliberator's.

See knowledge/decisions/desire-is-deduced-from-the-ranges-the-world-states.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta, timezone

from .desire import Desire
from .ontology import AG, INSTRUMENTS_GRAPH, SENSED_GRAPH, beliefs_graph, obligations_graph
from .store import bindings

_SENSING = "http://example.org/orexis/sensing#SensingCapability"

log = logging.getLogger("desire")

# The diff between desired and sensed, shipped as SPARQL so any consumer can run it — see the
# file's own header. Read once at import: a malformed query is then an error the moment the
# package loads rather than the first time somebody asks.
DESIRES_QUERY = (Path(__file__).parent / "desires.rq").read_text()
READINGS_QUERY = (Path(__file__).parent / "readings.rq").read_text()

# My own aims — the pick inside each region, one per property I chose to steer. PRIVATE, so the
# graph is named: an unqualified pattern reads public knowledge, and an aim is exactly what must
# never arrive that way.
_AIMS_Q = """
SELECT ?property ?value WHERE {{ GRAPH <{beliefs}> {{
  <{me}> ag:aims ?aim .
  ?aim ssn:forProperty ?property ;
       schema:value ?value .
}} }}"""

# My own regions, read once at construction — through `ag:metWhen`, since the desire became a
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
#  went — which watering repairs and a fan does not. See ag:violationIs.
_REGIONS_Q = """
SELECT ?property ?low ?high ?floor ?ceiling WHERE {
  <%s> ag:holds ?desire .
  ?desire ssn:forProperty ?property ; ag:metWhen ?shape .
  ?shape sh:property ?below , ?above .
  ?below sh:severity ag:ShouldBecome ; ag:violationIs ag:Below ;
         sh:qualifiedValueShape/sh:property/sh:maxExclusive ?low .
  ?above sh:severity ag:ShouldBecome ; ag:violationIs ag:Above ;
         sh:qualifiedValueShape/sh:property/sh:minExclusive ?high .
  OPTIONAL {
    <%s> ag:holds ?envelope .
    ?envelope ssn:forProperty ?property ; sh:property ?underFloor , ?overCeiling .
    ?underFloor sh:severity sh:Warning ; ag:violationIs ag:Below ;
                sh:qualifiedValueShape/sh:property/sh:maxExclusive ?floor .
    ?overCeiling sh:severity sh:Warning ; ag:violationIs ag:Above ;
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
    MAGNITUDE is nobody's arithmetic here: `measure` is the choir road the deducer hands in
    (see `_measured_urgency`), so the diff and the ranking cannot disagree because both ask the
    same capability the same question. `agent_id` names the pick record the sign's aim is read
    from. A property with no observation yet is absent rather than zero: at birth every desire
    is unmeasured, and unmeasured must not read as satisfied.
    """
    subjects = _subjects_of(beliefs, agent_uri)
    known, _ = _known(beliefs)
    aims = aims_of(desires, agent_id, agent_uri)
    out: dict[str, Gap] = {}
    for row in _desired(desires, agent_uri, agent_id=None):
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

    `measure` is the choir road, handed in by the deducer — `(desire, value) -> float | None`,
    behind which `Agent.desire_urgency` asks every module and sensing answers for
    observation-backed wants against the live belief base. A free function cannot hold the
    agent, so the join takes the question as a parameter; the KERNEL evaluates nothing
    (a-desire-states-its-own-measure). `value` is the reading the caller already joined, so
    the number judged and the number on the row are one fact from one read.

    A want nothing measures scores 1.0, logged — the defined fallback: not knowing how bad is
    maximal, exactly as not knowing at all is. Logged only where a measure was actually ASKED:
    a caller that hands none in is not asking about these wants at all (the debts reader wants
    the duty rows and computes the rest to throw away), and warning there says a package is
    missing when nothing is.
    """
    #  The INSTRUMENT rides along, because it is what tells the answerer which kind of want
    #  this is. A row that binds none is a stake and the want it makes says so by omission.
    answer = measure(Desire(uri=row["desire"], urgency=1.0,
                            observed_property=row["property"], value=value,
                            instrument=row.get("instrument")),
                     value) if measure else None
    if answer is None:
        if measure is not None:
            log.warning("nothing loaded measures a want about %s — urgency reads 1.0",
                        row["property"])
        return 1.0
    return answer


def desires_of(desires, beliefs, agent_uri: str, agent_id: str,
             now: datetime | None = None, measure=None) -> list[Desire]:
    """Everything an agent is pursuing, hottest first — its stakes and its debts in one list.

    Both sources appear because an obligation is a desire someone else sourced and urgency is
    the common currency — a litre owed and a pot drying rank against each other rather than
    running down two paths that never meet. Two handles since the dataset split (#298):
    `desires.rq` asks the desire modality what is pursued, `readings.rq` asks the belief
    modality what is known, and the judging — distance, staleness, lapse — happens here,
    where the clock is. One clock, deliberately: the deadline and the urgency used to be
    judged by two (the store's NOW and Python's), and two clocks that normally agree are
    still two clocks.

    A want whose reading is missing or too old is maximally urgent: not knowing whether the
    pot is dying outranks knowing it is uncomfortable, which is why the first intention is
    always to look. Staleness is judged against the horizon `publish_horizon` wrote — a store
    with none published does not judge staleness at all, the honest outcome of not knowing
    what rhythm is being kept.
    """
    now = now or datetime.now(timezone.utc)
    subjects = _subjects_of(beliefs, agent_uri)
    known, by_instrument = _known(beliefs)
    out = []
    for row in _desired(desires, agent_uri, agent_id):
        if row["kind"] == "duty":
            #  Lapsed is judged HERE, against the same clock the urgency uses — one reader,
            #  one now, so a debt cannot be maximally hot and still count as open because two
            #  clocks disagreed.
            demanded = row.get("presented") == "true"
            lapsed = bool(row.get("expires")) and now >= datetime.fromisoformat(row["expires"])
            out.append(Desire(uri=row["desire"], urgency=_duty_urgency(row, now),
                            claim=row["claim"], owed_to=row["owedTo"],
                            state="lapsed" if lapsed else
                                  ("demanded" if demanded else "standing"),
                            pursuable=demanded and not lapsed))
            continue
        if row["kind"] == "freshness":
            subject = None
            item = by_instrument.get((row.get("instrument"), row["property"]))
        else:
            subject = next((s for s in subjects if (s, row["property"]) in known), None)
            item = known.get((subject, row["property"])) if subject else None
        value = item.value if item else None
        stale = _is_stale(item, now)
        if row["kind"] == "freshness":
            #  MEASURED like everything else since the want moved into sensing, where the
            #  reading and the horizon both live. The number it comes back with is the one
            #  this branch used to compute — maximal while nothing current is known, zero
            #  otherwise — and the difference is that the planner can now ask the same
            #  question of a world nobody is in yet, which is what lets a look be preferred
            #  to standing still instead of being recognised by a special case.
            #
            #  The STATE stays here, because it is a different question and one this side
            #  holds the clock for: which of the two ways of not knowing this is. The measure
            #  reads the same published horizon, so the two cannot disagree about whether a
            #  reading is current — one fact, two readers, rather than two definitions.
            urgency = _measured_urgency(measure, row, value)
            #  READ OFF THE MEASURE, so the label and the number cannot part company. It used
            #  to come off `_is_stale`, which declines to judge at all where no horizon has
            #  been published — so a want the measure scored maximal reported `met`, which is
            #  the disagreement the reification was supposed to have ended. Anything the
            #  measure does not call current is not current; WHICH kind of not-current it is
            #  is the reading's to say, and that distinction is worth keeping because the two
            #  are different faults (never looked, against looked and let it go cold).
            state = "met" if urgency < 1.0 else \
                ("unmeasured" if value is None else "stale")
        else:
            region = _region_of(row)
            if value is None:
                urgency, state = 1.0, "unmeasured"
            elif stale:
                #  A stale want is as urgent as an unread one, and for the same reason: the
                #  number in hand is not evidence about now. Scaling it by the distance the
                #  LAST reading showed would rank an agent by something it no longer knows.
                urgency, state = 1.0, "stale"
            else:
                #  Whichever capability MEASURES such wants, asked through the choir road the
                #  caller handed in — the same question the planner asks of a candidate
                #  world, which is the whole point of one measure. The STATE stays the
                #  region's: met is the shape's verdict, urgency is the measure's, and since
                #  the measure is anchored at the aim the two genuinely differ —
                #  met-and-urgent is an agent inside its region and off its pick, a true
                #  situation, not a contradiction.
                urgency = _measured_urgency(measure, row, value)
                state = "unmet" if value < region.low or value > region.high else "met"
        out.append(Desire(uri=row["desire"], urgency=urgency, state=state,
                        observed_property=row["property"], value=value,
                        #  Only a freshness row binds one, which is what makes it the
                        #  discriminator rather than a decoration.
                        instrument=row.get("instrument")))
    return sorted(out, key=lambda g: -g.urgency)


@dataclass(frozen=True)
class _Known:
    """One current reading and how it may be judged: the value, when it was taken, and the
    staleness horizon whoever monitors that pair published."""

    value: float | None
    at: datetime | None
    horizon: float | None


def _desired(desires, agent_uri: str, agent_id: str | None) -> list[dict]:
    """The desire modality's rows — `desires.rq`, with the duty branch reaching this agent's
    obligations graph only when an id is given to name it by."""
    text = DESIRES_QUERY.replace("$me", f"<{agent_uri}>")
    text = text.replace("$owed", f"<{obligations_graph(agent_id)}>" if agent_id
                        else "<urn:nobody:owes>")
    return bindings(desires(text))


def _known(beliefs) -> tuple[dict, dict]:
    """The belief modality's rows — `readings.rq` — keyed twice: by (subject, property) for
    the stakes, and by (instrument, property) for the freshness wants, whose subject only the
    belief side knows."""
    text = (READINGS_QUERY.replace("$sensed", f"<{SENSED_GRAPH}>")
            .replace("$instruments", f"<{INSTRUMENTS_GRAPH}>"))
    by_pair, by_instrument = {}, {}
    for r in bindings(beliefs(text)):
        item = _Known(value=float(r["value"]) if r.get("value") else None,
                      at=datetime.fromisoformat(r["at"]) if r.get("at") else None,
                      horizon=float(r["horizon"]) if r.get("horizon") else None)
        by_pair[(r["subject"], r["property"])] = item
        if r.get("instrument"):
            by_instrument[(r["instrument"], r["property"])] = item
    return by_pair, by_instrument


def _subjects_of(beliefs, agent_uri: str) -> list[str]:
    return [r["s"] for r in bindings(beliefs(
        f"SELECT ?s WHERE {{ <{agent_uri}> ag:actsFor ?s }}"))]


def _region_of(row: dict) -> Region:
    floor, ceiling = row.get("floor"), row.get("ceiling")
    return Region(observed_property=row["property"],
                  low=float(row["low"]), high=float(row["high"]),
                  floor=float(floor) if floor is not None else None,
                  ceiling=float(ceiling) if ceiling is not None else None)


def _is_stale(item, now: datetime) -> bool:
    return (item is not None and item.horizon is not None and item.at is not None
            and item.at + timedelta(seconds=item.horizon) < now)


def _duty_urgency(row: dict, now: datetime) -> float:
    """The fraction of the claim's redeem window that has run, clamped.

    Here rather than in the query because the store's engine binds NOTHING for
    `duration / duration` — measured, and pinned by a test, because an unsupported operation
    that returns unbound instead of failing is how a whole column silently reads zero.
    """
    if not row.get("expires"):
        return 0.0                        # a market with no redeem channel; nobody is waiting
    owed_at = datetime.fromisoformat(row["at"])
    window = (datetime.fromisoformat(row["expires"]) - owed_at).total_seconds()
    if window <= 0:
        return 1.0
    return max(0.0, min(1.0, (now - owed_at).total_seconds() / window))


def aims_of(query, agent_id: str, agent_uri: str) -> dict[str, float]:
    """One agent's aims, property -> value. Private, so the beliefs graph is named.

    Takes the id as well as the URI because the graph is named from the one and the subject from
    the other — the same two facts the module itself is handed at construction.
    """
    return {row["property"]: float(row["value"])
            for row in bindings(query(_AIMS_Q.format(
                beliefs=beliefs_graph(agent_id), me=agent_uri)))}


def regions_of(query, agent_uri: str) -> dict[str, Region]:
    """Every region one agent holds, property -> region. Read, never computed here.

    A free function because it is the whole of what this module does with a store, and a test
    about what a world implies should not have to build an agent to ask. The arithmetic that
    produced these numbers is in `rules.ru` and ran at genesis; this only reads the answer.
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

