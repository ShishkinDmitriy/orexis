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

from .ontology import AG
from .store import Store, bindings

#  The two modality classes whose instances are wants. ConstraintGraph is a want's boundary
#  rather than a want — but gap, menu and validation all read the two together, and the record
#  files both under the desires store because what MAY be and what is PURSUED are the two
#  halves of one question no belief answers.
_DESIRE_MODALITIES_Q = f"""
SELECT DISTINCT ?g WHERE {{
  {{ ?g a <{AG}DesireGraph> }} UNION {{ ?g a <{AG}ConstraintGraph> }}
}}"""


def desire_graphs(source: Store) -> list[str]:
    """Every graph the catalog types with a desire modality, public or this agent's own.

    Asked with the union default, because "what are this store's graphs" is a question about
    the whole store — the classification of an agent's own graphs is deliberately outside the
    public default, and listing names here would be rule 1's trap.
    """
    return sorted(r["g"] for r in bindings(source.query_union(_DESIRE_MODALITIES_Q)))


class _Copy(Store):
    """One rebuild's worth of store: the desire-modality graphs, copied. Memory, no path —
    the same construction the imaginarium uses, for the same reason: nothing to clean up."""

    def __init__(self, source):
        super().__init__()
        for iri in desire_graphs(source):
            for quad in source.quads(iri):
                self._store.add(quad)


class Desires:
    """The desire modality: what this agent pursues, owning a store the agent never sees.

    A modality is a class that owns its store, and its store's nature is ITS decision
    (a-store-is-a-modality). This one's choices: in memory, rebuilt and never edited —
    `rebuild()` replaces the store wholesale, so a want whose premise has ceased is absent
    afterwards without anyone having retracted it (#263's discipline, structural) — and
    READ-ONLY on the surface: the class exposes queries and no writer, so a write attempt
    fails at the call site, whatever the store underneath could do.

    Rebuilt from the belief modality, which remains the home of record while the reader
    migration lands: genesis derives into it, a volume persists it, and this copy is the
    read surface. What selects a graph is what it IS — `ag:DesireGraph` or
    `ag:ConstraintGraph`, asserted in the public catalog for the shared graphs and in the
    classification graph for the agent's own — so a package that declares a new
    desire-modality graph is copied without the kernel learning its name. The picks ride
    along already: `ag:BeliefsGraph` is typed `ag:DesireGraph`, which the sovereign's ruling
    made literal.
    """

    def __init__(self, beliefs):
        self._beliefs = beliefs
        self.rebuild()

    def rebuild(self) -> None:
        """Recompute the store from its premises — the ONLY way this modality ever changes.

        Called after anything that moves a premise: a re-derivation, an endowment, a
        recorded re-pick. A fresh store rather than an edit; the read surface is rebound, so
        every holder of `agent.desires` sees the new state and nobody holds a stale handle.
        """
        copy = _Copy(self._beliefs)
        self.query = copy.query
        self.query_union = copy.query_union
        self.construct = copy.construct
        self.quads = copy.quads

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
