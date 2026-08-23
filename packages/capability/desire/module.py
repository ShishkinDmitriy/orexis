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
    urgency(property, value)  0.0 to 1.0 — what sensing turns into a cadence
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent.desire import Desire
from agent.module import Module
from agent.ontology import INSTRUMENTS_GRAPH, SENSED_GRAPH, beliefs_graph
from agent.store import bindings

from .graphs import obligations_graph
from .terms import DELIBERATION, DEDUCING, KERNEL, NS

# What this package asks OF others, by family — their namespaces, never their Python. The
# freshness rule lives with whoever holds the clock, and this module asks it exactly as
# bidding does.
_SENSING = "http://example.org/orexis/sensing#SensingCapability"

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

# My own regions, read once at construction. The only instance identifier named is my own URI,
# which is the single one a process is handed — everything else is a term.
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
  <%s> ag:holds ?shape .
  ?shape ssn:forProperty ?property ;
         sh:property ?below , ?above .
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
        the band. A step function would tell sensing to relax completely anywhere inside the
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
    """One row of the diff: where a property is against where it should be — and WHEN it was.

    `gap` is signed — negative below the region's point, positive above — and |gap| is the
    module's `urgency`, normalised by the survival room on that side. See gap.rq, which is the
    definition; this is only its Python shape.

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


def gaps_of(desires, beliefs, agent_uri: str) -> dict[str, Gap]:
    """The desired/sensed diff for one agent, property -> gap. Computed, never stored.

    A gap is a VERDICT — the same number is a crisis for one agent and nothing for another — so
    like a band it is recomputed on every asking and no graph holds it. What may be persisted is
    a summary of its history, which is review's pattern and not this function's business.

    Two handles since the dataset split (#298): `desires` answers what is WANTED and `beliefs`
    what IS, and the join is here — `desires.rq` and `readings.rq` are the two texts, and the
    arithmetic that used to be repeated between the queries and the module lives once, in
    `Region`. A property with no observation yet is absent rather than zero: at birth every
    desire is unmeasured, and unmeasured must not read as satisfied.
    """
    subjects = _subjects_of(beliefs, agent_uri)
    known, _ = _known(beliefs)
    out: dict[str, Gap] = {}
    for row in _desired(desires, agent_uri, agent_id=None):
        if row["kind"] != "stake":
            continue
        item = next((known[(s, row["property"])] for s in subjects
                     if (s, row["property"]) in known), None)
        if item is None or item.value is None:
            continue
        region = _region_of(row)
        urgency = region.urgency(item.value)
        gap = 0.0 if item.value == region.centre else             (urgency if item.value > region.centre else -urgency)
        out[row["property"]] = Gap(
            observed_property=row["property"], value=item.value,
            low=region.low, high=region.high, gap=gap,
            at=item.at, region=row.get("desire"),
        )
    return out


def desires_of(desires, beliefs, agent_uri: str, agent_id: str,
             now: datetime | None = None) -> list[Desire]:
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
            item = by_instrument.get((row.get("instrument"), row["property"]))
        else:
            item = next((known[(s, row["property"])] for s in subjects
                         if (s, row["property"]) in known), None)
        value = item.value if item else None
        stale = _is_stale(item, now)
        if row["kind"] == "freshness":
            #  Nothing to be far FROM, so the only urgencies are the epistemic ones: knowing
            #  nothing, or knowing something too old to be about now.
            urgency = 1.0 if value is None or stale else 0.0
            state = "unmeasured" if value is None else ("stale" if stale else "met")
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
                urgency = region.urgency(value)
                state = "unmet" if value < region.low or value > region.high else "met"
        out.append(Desire(uri=row["desire"], urgency=urgency, state=state,
                        observed_property=row["property"], value=value))
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


class DesireModule(Module):
    """The agent's ends, and the only module entitled to say what a reading MEANS."""

    CAPABILITY = DEDUCING
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

        The seam every other capability reaches me through. `agent.provider(DESIRE)` finds
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
        return self.regions[observed_property].urgency(value)

    # --- the diff, asked of me rather than recomputed by whoever wants it ---

    def gaps(self) -> dict[str, Gap]:
        """Where every property I want stands against where I want it — stale rows included.

        Included on purpose: a stale row is "last I looked I was dry, and I cannot see any
        more", which a deliberator needs precisely because nothing else will mention it. Rows
        carry `at`, and `current()` is the same diff with my own freshness rule applied.
        """
        return gaps_of(self.agent.desires.query_union, self.agent.beliefs.query, self.me.uri)

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
                                    self.agent.beliefs.query, self.me.uri, self.agent.id, now)
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
