"""What an agent is trying to bring about, in the one shape a deliberator ranges over.

Here and not in a package because a desire is a MENTAL STATE, and those are the kernel's — the
same reason `ag:Obligation` and `ag:Intention` moved into the agora namespace when the mind
was named (the-mind-is-six-graphs). Two packages need this type and neither may import the
other: `desire` produces desires, `deliberation` consumes them, and the only thing they are
allowed to share is a kernel word.

**Two sources, one currency.** A desire is either a stake — a property of the subject this agent
acts for, wanted inside a region — or a duty, a claim someone else holds against it. They are
deliberately the same type: an agent's whole conduct is wants it pursues through affordances,
and a deliberator that had to ask which kind it was holding would be the second decision path
this design exists to avoid. What differs is only where the urgency came from, and that is
recorded in the graph rather than in a flag anyone branches on. See
knowledge/decisions/an-obligation-is-a-desire-someone-else-sourced.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Desire:
    """One thing wanted, and how badly.

    `urgency` is unit-free in both cases and that is the whole point of the type: a stake's
    comes from the survival envelope (how much room is left before the subject ends), a duty's
    from the redeem window (how much time is left before the claim expires), and the two become
    comparable without either knowing how the other was computed. "My plant is dying" and "I owe
    fern a litre" finally rank against each other.
    """

    uri: str  # the desire's own node: a shape this agent holds, or an obligation
    urgency: float  # 0 = content, 1 = at the edge of what it can bear or of its deadline

    # A stake's two: what is wanted, and what it currently reads. `value` is None when nothing
    # has been observed, which is a gap and not a zero — see gap.rq.
    observed_property: str | None = None
    value: float | None = None

    # A duty's two: the claim it came from and whom it is owed to. A stake has neither, which
    # is what `is_duty` reads — no kind field, because a flag that can disagree with the data
    # beside it is a flag that eventually does.
    claim: str | None = None
    owed_to: str | None = None

    # Whether anything is being asked of this agent YET. A duty nobody has presented stands and
    # may be hot, and still must not be acted on: the holder is waiting for its own watch to be
    # live, and a host that doses early spends the water where nothing is looking. Always true
    # for a stake — a plant does not ask.
    pursuable: bool = True

    #  What state the desire is in, in its own kind's vocabulary: `met`, `unmet` or `unmeasured`
    #  for a stake, `standing` or `demanded` for a duty. Carried rather than inferred from
    #  urgency, and that distinction is not academic — urgency is 0 only exactly at a region's
    #  centre, so "urgency > 0" counts a barrel sitting comfortably inside 1-5 as unmet. It
    #  read that way on the bench for about ten minutes and made a calm society look stuck.
    state: str | None = None

    @property
    def is_met(self) -> bool:
        """Nothing is wanted here right now. False for a duty, which is never *met* — it is
        discharged, and a discharged debt is history rather than a desire."""
        return self.state == "met"

    @property
    def is_duty(self) -> bool:
        return self.claim is not None


#  --- the desire modality ---------------------------------------------------------------------
#
#  In this file and not one of its own, because the two things here are one subject: the
#  desire is the kernel's shape for a want, and the desire modality is where an agent's wants
#  live — a class per modality, each owning a store the agent never sees, per
#  a-store-is-a-modality. The agent holds the MODALITIES and nothing holds the collection, by
#  the sovereign's ruling: nothing ever addresses it — `agora-ask` names a modality and a
#  module asks for the one it means — and a holder no question needs is a namespace, not a
#  concept.

from . import loader
from .ontology import DESIRE_ASSERTED_GRAPH, DESIRE_DERIVED_GRAPH
from .store import Store

#  The two modality classes whose instances are wants. ConstraintGraph is a want's boundary
#  rather than a want — but gap, menu and validation all read the two together, and the record
#  files both under the desires store because what MAY be and what is PURSUED are the two
#  halves of one question no belief answers.
class _Derivation(Store):
    """One rebuild's worth of store: the wants DERIVED, the records PROJECTED, and nothing
    else left standing. Memory, no path — the imaginarium's construction, one lifecycle over.

    Four moves, in order. The premises are copied in — every public graph, plus the two
    records the rules and the projections read: the pick record and the obligations record,
    both reached by the one construction from an agent's own id the rules allow. The
    packages' `desires.ru` rules run against them, `$derived` bound to this store's own derived
    graph and `$given` to the premises, exactly the substitution genesis performs for its
    rules. The world's asserted block (`graph/desire/asserted`, a public graph a world's TriG
    may fill) is already among the copied publics and simply stays. Last, the public premises
    that are NOT desire content are dropped — a store answering "what do I want" must not
    answer with the topology it derived that from — leaving the derived wants, the asserted
    wants, and the two records.
    """

    def __init__(self, beliefs):
        from packages.capability.desire.graphs import obligations_graph

        super().__init__()
        publics = list(beliefs.public_graphs())
        records = [beliefs.graph, obligations_graph(beliefs.agent_id)]
        for iri in publics + records:
            for quad in beliefs.quads(iri):
                self._store.add(quad)
        given = "\n".join(f"USING <{g}>" for g in publics + records)
        for rule in loader.desires_rule_files():
            text = rule.read_text()
            out = []
            for line in text.splitlines():
                if not line.lstrip().startswith("#"):
                    line = (line.replace("$derived", f"<{DESIRE_DERIVED_GRAPH}>")
                                .replace("$given", given)
                                .replace("$me", f"<{beliefs.agent_uri}>"))
                out.append(line)
            self.update("\n".join(out))
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
    beside them, because the picks ARE wants by the sovereign's ruling and a duty is this
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
        built = _Derivation(self._beliefs)
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
