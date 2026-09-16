"""What an agent is trying to bring about, in the one shape a deliberator ranges over.

Here and not in a package because a desire is a MENTAL STATE, and those are the kernel's — the
same reason the obligation's premises and `progression:Intention` moved into the orexis namespace when the mind
was named (the-mind-is-six-graphs). Two packages need this type and neither may import the
other: `desire` produces desires, `deliberation` consumes them, and the only thing they are
allowed to share is a kernel word.

**Two sources, one currency.** A desire is either a stake — a property of the subject this agent
acts for, wanted inside a region — or an obligation, a claim someone else holds against it. They are
deliberately the same type: an agent's whole conduct is wants it pursues through affordances,
and a deliberator that had to ask which kind it was holding would be the second decision path
this design exists to avoid. What differs is only where the urgency came from, and that is
recorded in the graph rather than in a flag anyone branches on. See
knowledge/decisions/an-obligation-is-a-desire-someone-else-sourced.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Desire:
    """One thing wanted, and how badly.

    `urgency` is unit-free in both cases and that is the whole point of the type: a stake's
    comes from the survival envelope (how much room is left before the subject ends), an obligation's
    from the redeem window (how much time is left before the claim expires), and the two become
    comparable without either knowing how the other was computed. "My plant is dying" and "I owe
    fern a litre" finally rank against each other.
    """

    uri: str  # the desire's own node: a shape this agent holds, or an obligation
    urgency: float  # 0 = content, 1 = at the edge of what it can bear or of its deadline

    # What it currently reads, where whoever contributed the want has a number for it — a
    # stake's reading, filled by sensing. None when nothing has been observed, which is a gap
    # and not a zero. WHAT the want is about is not on this type: a want is its node, and a
    # package that needs the property of one it holds walks to it in its own words
    # (the-stake-is-sensings-want; sensing's `ObservedDesire` carries `observed_property`).
    value: float | None = None

    # A obligation's two: the claim it came from and whom it is owed to. A stake has neither, which
    # is what `is_obligation` reads — no kind field, because a flag that can disagree with the data
    # beside it is a flag that eventually does.
    claim: str | None = None
    owed_to: str | None = None

    #  When the want stops being satisfiable — `orexis:expiresAt`, carried onto the Desire so
    #  the planner can hold a candidate plan's landing time to the room left. #472: the
    #  obligation's binding is `orexis:Within`, and this is the deadline that binding reads —
    #  a legacy record from before the word behaves identically, because the deadline is the
    #  fact and the binding restates it. None for a stake, and None for a debt whose market
    #  stated no window: such a debt has no landing to miss.
    expires: datetime | None = None

    # An EPISTEMIC want's one: the instrument whose reading is wanted current. Present exactly
    # where the want is about knowing rather than about a number, which is what `is_epistemic`
    # reads — the same discipline as `is_obligation` above, and for the same reason: it is not a flag
    # saying what kind this is, it is the premise, and a want derived from an instrument is a
    # want about that instrument by construction.
    #
    # It is here because two wants can now be about ONE property — fern holds a region in its
    # moisture AND wants its probe to have spoken recently — and everything that used to ask
    # "the want about this property" had exactly one answer and now has two. Whose the
    # instrument IS stays out of the kernel: this is an IRI handed over, and the capability
    # that derived the want is the one that knows what to do with it.
    instrument: str | None = None

    # Whether anything is being asked of this agent YET. A obligation nobody has presented stands and
    # may be hot, and still must not be acted on: the holder is waiting for its own watch to be
    # live, and a host that doses early spends the water where nothing is looking. Always true
    # for a stake — a plant does not ask.
    pursuable: bool = True

    #  What state the desire is in, in its own kind's vocabulary: `met`, `unmet` or `unmeasured`
    #  for a stake, `met`, `stale` or `unmeasured` for an epistemic want — where it is read off
    #  the MEASURE, so a want scored maximal can never report as met, which it did while the
    #  label came from a staleness test that declines to judge at all without a published
    #  horizon — and `standing` or `demanded` for an obligation. Carried rather than inferred from
    #  urgency, and that distinction is not academic — urgency is 0 only exactly at the point
    #  being steered for, so "urgency > 0" counts a barrel sitting comfortably inside 1-5 as
    #  unmet. It read that way on the bench for about ten minutes and made a calm society look
    #  stuck. The split is now structural: the met-SHAPE governs the state and the MEASURE
    #  governs the urgency, and they are different questions on the desire's own node.
    state: str | None = None

    #  THE ROOT THIS WANT IS DERIVED UNDER (#618), or None for a root and for anything not
    #  derived from a want. An `orexis:Always` want is never pursued itself: the row the
    #  container presents in its place carries the root's own measure and names the root
    #  here, so a mark or a lookup by either name meets the same want.
    derived_from: str | None = None

    #  THE INSTANT AN `orexis:At` WANT HOLDS AT (#619), or None. A want derived under a root
    #  from a predicted crossing: judged as the world will be THEN, late past it, and its
    #  room is the stretch to it — which the container computes into `urgency` when it
    #  presents the want, since a time room is the kernel's arithmetic as a debt's is.
    holds_at: datetime | None = None

    #  WHEN THE READING THIS ROW JUDGES WAS TAKEN, or None where nothing was read — filled by
    #  whoever holds the reading (sensing). A pass for a want met at an instant drifts the
    #  reading's AGE at its root (#619, #625): the present is the world as it was OBSERVED, a
    #  drift that counted from the pass's clock would leave those seconds undrifted, and this
    #  engine cannot turn the stretch between two instants into a number (AGENTS, the traps).
    read_at: datetime | None = None

    #  NO measure field, deliberately, and one briefly existed: a desire does not carry how
    #  its badness is scored, because that is a capability's answer and not the mind's
    #  structure (a-desire-states-its-own-measure). Whoever needs the number asks the choir —
    #  `Agent.desire_urgency(desire, query, sensed)` — of whichever world is being judged,
    #  and sensing answers for observation-backed wants from its own declaration. A obligation's
    #  fraction-of-window stays kernel Python behind a pinned engine limit (this store binds
    #  nothing for duration division — tests/test_desires.py), with the market's own
    #  declaration as its recorded future home.

    @property
    def is_met(self) -> bool:
        """Nothing is wanted here right now. False for an obligation, which is never *met* — it is
        discharged, and a discharged debt is history rather than a desire."""
        return self.state == "met"

    @property
    def is_obligation(self) -> bool:
        return self.claim is not None

    @property
    def is_epistemic(self) -> bool:
        """Is this a want about my KNOWLEDGE of something rather than about the thing?

        The two are repaired by different means — no lever moves a number you cannot see —
        and, since a property may carry one of each, whoever asks "what should I do about
        this property" has to say which of the two it means. An actuator means the number.
        """
        return self.instrument is not None


#  --- the desire modality ---------------------------------------------------------------------
#
#  In this file and not one of its own, because the two things here are one subject: the
#  desire is the kernel's shape for a want, and the desire modality is where an agent's wants
#  live — a class per modality, each owning a store the agent never sees, per
#  a-store-is-a-modality. The agent holds the MODALITIES and nothing holds the collection, by
#  the sovereign's ruling: nothing ever addresses it — `orexis-ask` names a modality and a
#  module asks for the one it means — and a holder no question needs is a namespace, not a
#  concept.

from assembly import loader
from orexis_agent_progression.ontology import DESIRE_ASSERTED_GRAPH
from orexis_agent_progression.store import Store

#  The two modality classes whose instances are wants. ConstraintGraph is a want's boundary
#  rather than a want — but gap, menu and validation all read the two together, and the record
#  files both under the desires store because what MAY be and what is PURSUED are the two
#  halves of one question no belief answers.
class Projection(Store):
    """One rebuild's worth of store: the roots and the records PROJECTED, and nothing else left
    standing — nothing deduced (#644). Memory, no path — the imaginarium's construction, one
    lifecycle over. `Deducer` until the roots were seen to be re-derived from a pick.

    Two moves. Every public graph and every record a want lives in is copied in — the roots
    graph genesis authored, the pick record, the obligations, the promises, the pursued
    children — reached by the one construction from an agent's own id the rules allow. Then
    the public premises that are NOT desire content are dropped, since a store answering
    "what do I want" must not answer with the topology beside it — leaving the roots, the
    world's asserted wants (`graph/desire/asserted`, a public graph a world's TriG may fill)
    and the records.
    """

    def __init__(self, beliefs):
        from orexis_agent_progression.ontology import obligations_graph, promises_graph, roots_graph
        from .ontology import pursued_graph

        super().__init__()
        publics = list(beliefs.public_graphs())
        #  A PROJECTION, AND NO RULE (#644, a-root-holds-always-and-an-outdated-graph-is-dropped):
        #  the roots — every Always desire, authored at genesis into the agent's own roots graph
        #  and holding at every instant — and the records sourced at a time: the picks, the
        #  debts, the promises, the wants pursued under a root (#618). The packages' desire
        #  rules ran here on every rebuild until a root was seen to be re-derived from a pick;
        #  they run at genesis now, and this build deduces nothing.
        #  A DEBT AND A PURSUED CHILD ARE GRAPHS OF THEIR OWN, holding during their periods
        #  (#645): every one the door hands at this instant is projected, under the untimed
        #  record it sits beneath, so a lapsed debt and a child past its instant are absent
        #  from this store as they are from every reader.
        timed = [g for g in beliefs.recorded_graphs()
                 if g.startswith(obligations_graph(beliefs.agent_id) + "/")
                 or g.startswith(pursued_graph(beliefs.agent_id) + "/")]
        records = [roots_graph(beliefs.agent_id), beliefs.graph, obligations_graph(beliefs.agent_id),
                   promises_graph(beliefs.agent_id), pursued_graph(beliefs.agent_id), *timed]
        for iri in publics + records:
            for quad in beliefs.quads(iri):
                self._store.add(quad)
        for iri in publics:
            if iri != DESIRE_ASSERTED_GRAPH:
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
    freshness wants and asserted root desires come to exist — from the world, the records,
    and the packages' `desires.ru`. The pick record and the obligations record are projected in
    beside them, because the picks ARE wants by the sovereign's ruling and an obligation is this
    agent's debts record, served as the wants they raise.
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
        self.query = built.query
        self.query_union = built.query_union
        self.construct = built.construct
        self.quads = built.quads

    def read(self, picks):
        """Fill one capability's picks FROM THE DESIRE MODALITY — where they belong,
        because a pick is a want (#297's sort, knowledge/domain/pick.md). Served from
        this store's rebuilt copy, so a re-pick reaches a module the moment the rebuild runs
        and never before: the record is the belief base's, the read surface is this one."""
        from .beliefs import read_picks
        return read_picks(self.query_union, self._beliefs.agent_uri, self._beliefs.graph,
                          self._beliefs.agent_id, picks)

    def read_optional(self, picks):
        """The picks, or None where the agent said nothing at all — `Beliefs.read_optional`'s
        contract, served from this modality's copy."""
        from .beliefs import read_picks_optional
        return read_picks_optional(self.query_union, self._beliefs.agent_uri,
                                   self._beliefs.graph, self._beliefs.agent_id, picks)
