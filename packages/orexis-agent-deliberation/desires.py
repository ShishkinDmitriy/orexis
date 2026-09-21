"""Every desire this agent holds, as a collection — and the modality whose store holds them.

`Desires` is BOTH, and they sit together because the store it owns IS the collection: a
projection holding the desires and the records, rebuilt whenever a premise moves. The wants are
read straight off the store because the derivation WRITES there, and those writes stale this
projection; nothing writes a
declared desire at runtime — they are authored at genesis and projected, never rebuilt (#644) —
so this half reads and offers no `save`.

THERE IS NO `Desire` TYPE, and `desire.py` is gone with it. A desire is rows: the reads below
hand back a boolean or a uri, which is what every caller asked for, and nothing anywhere read
a label or an about off the frozen dataclass they used to build. See
knowledge/decisions/a-read-is-a-function-over-a-store.md.
"""

from __future__ import annotations


#  --- the desire modality ---------------------------------------------------------------------
#
#  In this file and not one of its own, because the two things here are one subject: the
#  desire is the kernel's shape for a want, and the desire modality is where an agent's wants
#  live — a class per modality, each owning a store the agent never sees, per
#  a-store-is-a-modality. The agent holds the MODALITIES and nothing holds the collection, by
#  the sovereign's ruling: nothing ever addresses it — `orexis-ask` names a modality and a
#  module asks for the one it means — and a holder no question needs is a namespace, not a
#  concept.

import logging

from assembly import loader
from orexis_agent_progression.store import Store, bindings
from orexis_agent_progression.ontology import DESIRE, RECORD, WANT

log = logging.getLogger("desires")

#  HOW MANY A `find_all` HANDS BACK unless the caller says otherwise — `wants.PAGE`'s reason,
#  and the same number: a collection whose size is the world's is one an author sizes by hoping.
PAGE = 100

#  BOTH KINDS ON PURPOSE, and it is said out loud here because it used to be said by entailment.
#  The planner keys this map by whatever node it is standing on, and that is USUALLY a want — the
#  derivation hands it the one derived under a desire — but not always: where a desire reads unmet
#  and nothing can be minted for it, the desire itself is what gets planned for. While `orexis:Want`
#  was a subclass, `?want a orexis:Desire` quietly matched both and nothing said so; the types are
#  disjoint now (a-kind-is-a-type-not-a-binding), so the query names the two it means.
#
#  What this agent wants and what each want is ABOUT — the kernel's words only. A want with no
#  `orexis:about` is one no action query could join a lever to, and it is simply absent from the
#  VALUES block; the obligations are not here at all, because an obligation's row names whom it is owed
#  to and joins on that. (This used to read the property off the met-shape, and the kernel
#  no longer knows a want has one — the-stake-is-sensings-want.)
_ABOUT_Q = """SELECT ?me ?want ?about WHERE {
  VALUES ?kind { orexis:Desire orexis:Want }
  ?me orexis:holds ?want .
  ?want a ?kind ; orexis:about ?about }"""

#  The two modality classes whose instances are wants. ConstraintGraph is a want's boundary
#  rather than a want — but gap, menu and validation all read the two together, and the record
#  files both under the desires store because what MAY be and what is PURSUED are the two
#  halves of one question no belief answers.
#  WHAT THIS MODALITY HOLDS, by kind: the desires (the agent's own, the promises), the wants (each
#  pursued child, the world's asserted ones) and the records (the picks, the obligations and
#  every debt under them) — the picks ARE wants by the sovereign's ruling and a debt is served
#  as the want it raises. Copied in by these kinds and read back by them.
HELD = (DESIRE, WANT, RECORD)


class Projection(Store):
    """One rebuild's worth of store: the desires and the records PROJECTED, and nothing else left
    standing — nothing deduced (#644). Memory, no path — the imaginarium's construction, one
    lifecycle over. `Deducer` until the desires were seen to be re-derived from a pick.

    Two moves. Every public graph and every record a want lives in is copied in — the desires
    graph genesis authored, the pick record, the obligations, the promises, the pursued
    children — asked by CLASS of the classification each graph's owner wrote, and kept to
    this agent where the store knows whose it is; no name is constructed here (#705). Then
    the public premises that are NOT desire content are dropped, since a store answering
    "what do I want" must not answer with the topology beside it — leaving the desires, the
    world's asserted wants (`graph/desire/asserted`, a public graph a world's TriG may fill)
    and the records.
    """

    def __init__(self, beliefs):
        from orexis_agent_progression import clock
        from orexis_agent_progression.ontology import OREXIS, PUBLIC

        super().__init__()
        now = clock.now()
        publics = list(beliefs.graphs_of(PUBLIC, at=now))
        #  A PROJECTION, AND NO RULE (#644, a-desire-holds-always-and-an-outdated-graph-is-dropped):
        #  the desires — every Always desire, authored at genesis into the agent's own desires graph
        #  and holding at every instant — and the records sourced at a time: the picks, the
        #  debts, the promises, the wants pursued under a desire (#618). The packages' desire
        #  rules ran here on every rebuild until a desire was seen to be re-derived from a pick;
        #  they run at genesis now, and this build deduces nothing.
        #  A DEBT AND A PURSUED CHILD ARE GRAPHS OF THEIR OWN, holding during their periods
        #  (#645): every one the door hands at this instant is projected, under the untimed
        #  record it sits beneath, so a lapsed debt and a child past its instant are absent
        #  from this store as they are from every reader.
        #  ASKED BY CLASS, never named, and by what a graph HOLDS: every graph of desires (the
        #  desires, the promises), every graph of wants (each pursued child), the pick record,
        #  the obligations record and every debt's graph under it — whatever each is called.
        #  The owners classified them; this reads the classification. The world's asserted
        #  graph is a desire and a want graph too, and public: it rides in with the publics.
        records = [g for g in beliefs.graphs_of(*HELD, at=now) if g not in publics]
        #  BOTH ASSERTED GRAPHS: a world may ratify a desire or a want, and each is a public
        #  graph of its own kind since they were split. Asked by what they HOLD, which is the
        #  only thing this build needs to know about them.
        asserted = {g for g in publics
                    if g in set(beliefs.graphs_of(OREXIS + "DesireGraph"))
                    | set(beliefs.graphs_of(OREXIS + "WantGraph"))}
        #  AND THE CATALOGUE, so this store answers by kind as the belief base does: what it
        #  holds is asked for as desires, wants and records, never as everything — which
        #  needs the vocabulary's axioms too, since a pursued graph is a graph of wants by
        #  `rdfs:subClassOf` and the closure reads the graphs typed as the vocabulary's.
        #  Terms are not topology, and no read by these kinds reaches them.
        kept = asserted | set(beliefs.graphs_of(OREXIS + "OntologyGraph"))
        for iri in publics + records + [beliefs.catalogue]:
            for quad in beliefs.quads(iri):
                self._store.add(quad)
        for iri in publics:
            if iri not in kept:
                self.clear_graph(iri)


class Desires:
    """The desire modality: what this agent pursues, owning a store the agent never sees.

    A modality is a class that owns its store, and its store's nature is ITS decision
    (a-store-is-a-modality). This one's choices: in memory, DERIVED and never edited —
    `rebuild()` re-runs the want-derivation wholesale, so a want whose premise has ceased is
    absent afterwards because the derivation no longer implies it (#263's discipline, live) —
    and READ-ONLY on the surface: the class exposes queries and no writer, so a write attempt
    fails at the call site, whatever the store underneath could do.

    Since #312 there is no copy and no selection: genesis derives no wants, the belief base
    holds no desire-modality graphs, and this build is the one place the regions, envelopes,
    freshness wants and asserted desires come to exist — from the world, the records,
    and the packages' `desires.ru`. The pick record and the obligations record are projected in
    beside them, because the picks ARE wants by the sovereign's ruling and an obligation is this
    agent's debts record, served as the wants they raise.

    AND IT IS NOT A COLLECTION. It carried three finders — `find_all`, `find_first_by_uri`,
    `find_first_by_want` — which made it a repository by the convention
    `a-read-is-a-function-over-a-store` retired, the second and last thing to follow it.
    They are functions over a store now (below), as the wants' went first, and what is left is
    a modality: a store, the rebuild that is the only way it changes, and the questions it can
    be asked. The convention has no instances.
    """

    def __init__(self, beliefs):
        self._beliefs = beliefs
        self.rebuild()

    def rebuild(self) -> None:
        """Re-derive the store from its premises — the ONLY way this modality ever changes.

        Called after anything that moves a premise: an obligation transition, a recorded
        re-pick, an endowment. A fresh store rather than an edit; the read surface is
        rebound, so every holder of `agent.desires` sees the new state and nobody holds a
        stale handle.
        """
        built = Projection(self._beliefs)
        #  Held so a read may memoise against it. The memo dies with the projection it was
        #  computed from, which is exactly when it should: a rebuild IS the invalidation.
        self._built = built
        self.quads = built.quads
        #  THE READ SURFACE IS THE COPY'S: a `query` handed out before a rebuild keeps
        #  answering from the copy it was made over — replaced, never edited. It asks the
        #  modality's store over what it holds (`HELD`), the kinds stated here, once, by the
        #  modality that owns the store — a modality's store is its decision.
        self.query = lambda sparql, substitutions=None: built.query(
            sparql, built.graphs_of(*HELD), substitutions)
        self.construct = lambda sparql, substitutions=None: built.construct(
            sparql, built.graphs_of(*HELD), substitutions)

    def read(self, picks):
        """Fill one capability's picks FROM THE DESIRE MODALITY — where they belong,
        because a pick is a want (#297's sort, knowledge/domain/pick.md). Served from
        this store's rebuilt copy, so a re-pick reaches a module the moment the rebuild runs
        and never before: the record is the belief base's, the read surface is this one."""
        from .beliefs import read_picks
        return read_picks(self.query, self._beliefs.agent_uri, self._beliefs.graph,
                          self._beliefs.agent_id, picks)

    def read_optional(self, picks):
        """The picks, or None where the agent said nothing at all — `Beliefs.read_optional`'s
        contract, served from this modality's copy."""
        from .beliefs import read_picks_optional
        return read_picks_optional(self.query, self._beliefs.agent_uri,
                                   self._beliefs.graph, self._beliefs.agent_id, picks)

    # --- what it can be asked -----------------------------------------------------------
    #
    #  A MODALITY AND NOT A COLLECTION: the store it owns is a projection holding the desires
    #  and the records, rebuilt whenever a premise moves, and the rebuild is the only way it
    #  changes. The wants are read straight off the belief base because the derivation WRITES
    #  there and those writes stale this projection; nothing writes a declared desire at
    #  runtime — they are authored at genesis and projected, never rebuilt (#644) — so this
    #  offers no `save`.

    def abouts(self, agent_uri: str) -> dict[str, tuple[str, ...]]:
        """What each thing this agent holds is ABOUT, node -> the IRIs it names.

        HERE BECAUSE THIS MODALITY OWNS THE STORE IT READS. It was `wants_of` on the service
        that looped the templates into a world, in a
        file named for the service that consumes the answer rather than for the collection that
        has it — which is why "why does the menu select for wants?" was a fair question with
        no good answer. Whoever asks a world what it affords needs to know what this agent holds;
        being told is not the
        same as fetching it, and a menu that fetched it knew a query text about somebody else's
        contents.

        BOTH KINDS, spanning this collection and the wants. The planner keys the map by whatever
        node it is standing on, usually a want and sometimes a desire, so the map holds both —
        which is the one question here that is not answerable from `find_all` alone.

        SEVERAL PER NODE, because a want may be (#566): a greenhouse bed is comfortable when its
        soil and its air are both in their regions, and that is ONE want about two properties —
        the first shipped want whose plan needs two different levers. Every want the plant worlds
        hold names exactly one, and reads the same through the tuple.
        """
        def compute():
            out: dict[str, list[str]] = {}
            for r in bindings(self.query(_ABOUT_Q, {"me": agent_uri})):
                out.setdefault(r["want"], []).append(r["about"])
            return {w: tuple(sorted(a)) for w, a in out.items()}

        #  REMEMBERED AGAINST THE PROJECTION, so a rebuild is the invalidation — and a rebuild is
        #  what every write that could change this answer already triggers. The service memoised
        #  it instead, which made that service stateful and forced its callers to keep one each.
        return self._built.remember(("abouts", agent_uri), compute)


#  ---- asking a store about its desires -------------------------------------------------
#
#  ONE QUESTION, AND IT IS THE ONLY ONE ANYTHING ASKS. There were three finders on a
#  repository, then three functions handing back a `Desire` — a frozen dataclass of uri, label,
#  about and points, built from a query and thrown away, since nothing anywhere read a label or
#  an about off one. A repository earns its place where domain objects are loaded, changed and
#  written back; nothing here is, so there is no `Desire` type and `desire.py` is gone.
#
#  TWO OF THE THREE WENT WITH IT, each for its own reason. `find_desires` had no caller but a
#  test, whose invariant — everything held is in exactly one collection — is structural since
#  the types became disjoint, and which asks the store itself now. `desire_behind` answered
#  "which desire was this want derived from", which is the WANT's own `prov:wasDerivedFrom`
#  and is on the row `find_wants` already reads: a want question asked in the desires.


def holds_desire(store, uri: str) -> bool:
    """Is this node one of the desires — as against a want, or a name the store does not hold?

    AN ASK, because that is the question. It was a find returning a row that the one caller
    tested for None, which built three fields to read none of them. The types are disjoint
    (a-kind-is-a-type-not-a-binding), so being typed one IS the answer: it was
    `orexis:bindsWhen orexis:Always` while `orexis:Want` was a subclass and the type alone
    could not tell the two apart.
    """
    return bool(store.query(f"ASK {{ <{uri}> a orexis:Desire }}")["boolean"])
