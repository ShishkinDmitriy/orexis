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
from datetime import datetime, timezone
from pathlib import Path

from agent.module import Module
from agent.ontology import SENSED_GRAPH, beliefs_graph
from agent.store import bindings

from .graphs import obligations_graph
from .terms import DEDUCING, KERNEL, NS

# What this package asks OF others, by family — their namespaces, never their Python. The
# freshness rule lives with whoever holds the clock, and this module asks it exactly as
# bidding does.
_SENSING = "http://example.org/agora/sensing#SensingCapability"

# The diff between desired and sensed, shipped as SPARQL so any consumer can run it — see the
# file's own header. Read once at import: a malformed query is then an error the moment the
# package loads rather than the first time somebody asks.
GAP_QUERY = (Path(__file__).parent / "gap.rq").read_text()

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
#  is the whole reason those shapes are DECLARATIVE rather than sh:sparql: `sh:minInclusive` is
#  an ordinary triple, so a gap costs one query per reading instead of a validator run. The
#  path is deep because a reified observation has to be reached through an inverse path and a
#  qualified shape — convoluted to read, and the price of not inventing a second way to say
#  what a graph should look like.
#
#  Two shapes per property, told apart by the FORCE they carry: the region a violation of which
#  is a gap, and the envelope a violation of which is the subject ending.
_REGIONS_Q = """
SELECT ?property ?low ?high ?floor ?ceiling WHERE {
  <%s> ag:holds ?shape .
  ?shape ssn:forProperty ?property ;
         sh:property ?want .
  ?want sh:severity ag:ShouldBecome ;
        sh:qualifiedValueShape/sh:property/sh:minInclusive ?low ;
        sh:qualifiedValueShape/sh:property/sh:maxInclusive ?high .
  OPTIONAL {
    <%s> ag:holds ?envelope .
    ?envelope ssn:forProperty ?property ; sh:property ?tolerate .
    ?tolerate sh:severity sh:Warning ;
              sh:qualifiedValueShape/sh:not/sh:property/sh:minInclusive ?floor ;
              sh:qualifiedValueShape/sh:not/sh:property/sh:maxInclusive ?ceiling }
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

    def age_s(self, now: datetime | None = None) -> float | None:
        """Seconds since the sensed side was true, or None for a reading with no timestamp."""
        if self.at is None:
            return None
        return ((now or datetime.now(timezone.utc)) - self.at).total_seconds()


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
        at=datetime.fromisoformat(row["at"]) if row.get("at") else None,
    ) for row in bindings(query(substituted))}


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
        self.regions = regions_of(agent.store.query, self.me.uri)
        self._aims = aims_of(agent.store.query, agent.id, self.me.uri)
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
        self._aims = aims_of(self.agent.store.query, self.agent.id, self.me.uri)

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

    # --- obligations: the desires this agent did not source (#218 remade) ----------------

    def _uri_of(self, agent_id: str) -> str | None:
        """The counterparty's node, from the one thing a claim carries: its id. Public wiring,
        so a debt names an agent the world declares and never a string somebody sent me."""
        rows = bindings(self.agent.store.query(
            f'SELECT ?a WHERE {{ ?a a <http://example.org/agora#Agent> ; '
            f'<http://example.org/agora#localId> "{agent_id}" }} LIMIT 1'))
        return rows[0]["a"] if rows else None

    def owe(self, to_agent_id: str, claim_jti: str) -> str | None:
        """Record what the society just made this agent owe. Returns the obligation's IRI.

        Raised when a claim is ISSUED, not when it is presented: the debt exists from the
        moment the society allocated it, and the holder's silence afterwards is the holder's
        business. Idempotent by the claim's own jti — single-use there, single-use here — so a
        replay raises nothing new.

        Written to a graph of this agent's own, so a restarting host still knows what it owes:
        the issued claims used to live in a module dict that died with the process.
        """
        to_agent = self._uri_of(to_agent_id)
        if to_agent is None:
            # Whom I may owe is TOPOLOGY (the ACL shape): an obligation to an agent this
            # world does not declare is not a debt, it is a forgery, and refusing here means
            # no forged presentation can ever raise a want.
            self.log.warning("asked to owe %s, whom this world does not declare — refused",
                             to_agent_id)
            return None
        uri = f"{KERNEL}obligation.{claim_jti}"
        graph = obligations_graph(self.agent.id)
        if bindings(self.agent.store.query(
                f"SELECT ?o WHERE {{ GRAPH <{graph}> {{ <{uri}> ?p ?o }} }} LIMIT 1")):
            return None
        self.agent.store.update(f"""INSERT DATA {{ GRAPH <{graph}> {{
            <{uri}> a <{KERNEL}Obligation> ;
                <http://www.w3.org/ns/prov#wasDerivedFrom> "{claim_jti}" ;
                <{KERNEL}owedTo> <{to_agent}> ;
                <{KERNEL}forClaim> "{claim_jti}" ;
                <{KERNEL}presented> false ;
                <{KERNEL}owedAt> "{datetime.now(timezone.utc).isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}""")
        self.log.info("owed to %s for claim %s", to_agent_id, claim_jti)
        return uri

    def demanded(self, claim_jti: str) -> None:
        """The holder presented: an obligation nobody had asked for is now asked for.

        The step this capability's `presented` flag exists for — an unpresented claim
        requires nothing of me, a presented one requires acting now — and the reason urgency
        here is a step rather than a curve until claims may be held over time.
        """
        graph = obligations_graph(self.agent.id)
        self.agent.store.update(f"""
            DELETE {{ GRAPH <{graph}> {{ ?o <{KERNEL}presented> ?was }} }}
            INSERT {{ GRAPH <{graph}> {{ ?o <{KERNEL}presented> true }} }}
            WHERE  {{ GRAPH <{graph}> {{ ?o <{KERNEL}forClaim> "{claim_jti}" ;
                                         <{KERNEL}presented> ?was }} }}""")

    def discharge(self, claim_jti: str) -> None:
        """The dose is out: the debt is paid, and says when. Never deleted — a debt paid and
        a debt forgotten must not look alike, which is the same reason a resolved intention
        stays in its ledger."""
        graph = obligations_graph(self.agent.id)
        self.agent.store.update(f"""INSERT {{ GRAPH <{graph}> {{
                ?o <{KERNEL}dischargedAt> "{datetime.now(timezone.utc).isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}
            WHERE {{ GRAPH <{graph}> {{ ?o <{KERNEL}forClaim> "{claim_jti}" .
                     FILTER NOT EXISTS {{ ?o <{KERNEL}dischargedAt> ?done }} }} }}""")

    def owed(self, presented_only: bool = False) -> list[dict]:
        """What still stands, newest first — what an agent owes, askable by the sovereign."""
        extra = f'?o <{KERNEL}presented> true .' if presented_only else ""
        return bindings(self.agent.store.query(f"""
SELECT ?o ?to ?jti ?presented ?at WHERE {{ GRAPH <{obligations_graph(self.agent.id)}> {{
  ?o a <{KERNEL}Obligation> ; <{KERNEL}owedTo> ?to ; <{KERNEL}forClaim> ?jti ;
     <{KERNEL}presented> ?presented ; <{KERNEL}owedAt> ?at .
  {extra}
  FILTER NOT EXISTS {{ ?o <{KERNEL}dischargedAt> ?done }} }} }} ORDER BY DESC(?at)"""))

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
        return gaps_of(self.agent.store.query, self.me.uri)

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
