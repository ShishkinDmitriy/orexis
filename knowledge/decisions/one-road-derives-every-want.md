---
type: Decision
title: One road derives every want, and a package writes instances and predictions - never wants
description: >-
  A desire is one and universal - all my properties inside their ranges, no debt of mine
  overdue. Its wants are minted by one road for every kind of desire: the desire's met-test,
  compiled to the select whose rows are its violations, run now and at the start of each
  prediction the agent holds, yields the instances in trouble and when; those are clustered by
  scope, and one want is minted per cluster, holding at the earliest crossing. A package that
  knows an instance arrived - a claim, a reading - writes the instance and what it predicts of
  it, and never the want. The forest stands, and it is a forest of WANTS under a desire, not of
  derived desires. The per-instance desire level was drawn and struck.
status: accepted
timestamp: 2026-09-18T15:00:00Z
---

# Three roads, and why there were three

A want is what a search is handed; a desire is what it is derived from. Three things derived
them, and no two the same way:

| road | class → instance | ∀t → an instant | who minted |
|---|---|---|---|
| sensing | a genesis rule, one desire per (subject, property) | `crossing_row_of` over the predictions | the pursuit road |
| the market | by hand, in `owe`, when a claim arrived | by hand — the claim's expiry as the graph's period | the ledger |
| a ratified want | not at all — authored as one want | unmet now | nobody |

The reason is not a choice anybody made. Two different operations were fused in each road at a
different time: **decomposition** — which instances a universal is about — and **witnessing** —
the instant at which the universal is about to fail. Sensing could decompose at genesis because
the roster is ratified at birth; the market could not, because a debt arrives afterwards, so it
skipped the tree and minted the leaf itself. Decomposition existed only as a genesis-time rule,
and that is the whole of why the ledger grew a road of its own.

# The road

**A desire is one, and universal.** *All the properties of what I act for are inside their
ranges.* *No debt I owe is overdue.* One per premise, declared by a package's `desires.ru` at
genesis or ratified by a world, never pursued, and carrying a met-test — a SHACL shape whose
target is the class it quantifies over
([a-desire-is-universal-and-a-want-is-existential](/decisions/a-desire-is-universal-and-a-want-is-existential.md)).

**Judging is one select, and it is already compiled.** The met-test compiled by `report_select`
is the SELECT whose rows are `?this` — the focus node that failed — and `?_constraint`, which
property or side of it. That select IS the decomposition: run against a world, its rows are the
instances in trouble. Run it now, over the graphs holding now, and at the start of each prediction the
agent holds — sensing's drift, the ledger's *undischarged at its deadline* — and each row's
first instant is its witness, the t₀ at which *always* would stop being true. Decomposition and
witnessing are one query per desire, which is why neither needs a rule of its own.

**Cluster by scope, mint one want per cluster.** Two troubled instances some action can move
together belong in one want — a plan for soil and air in one cone, which is what the greenhouse
already has as one want about two properties (#566). Two in different scopes are two wants, two
cones, plans concatenated. So a [scope](/domain/scope.md) is what decides the GRAIN of the wants
under a desire, and a [cone](/domain/cone.md) is the search each want gets; `cone.md` already
says a scope *counts cones without being one*, and this is the mechanism that count exists for.
Every shipped world is one scope, so every desire today mints at most one want covering all its
troubled instances — which is the greenhouse's want, generalised.

The want holds AT the cluster's earliest witness. An instance whose own crossing is later is in
range at that instant, so the conjunction the met-test asks is satisfiable, and a plan that
reaches it has fixed what needed fixing by when it was needed.

**A package writes instances and predictions.** The ledger, on a claim: the debt, and a
prediction that it is undischarged at its deadline. Sensing, on a reading: the reading, and what
the drift predicts of it. Neither writes a want. *No overdue debts* gets the met-test it never
had — overdue was unaskable because it wanted the clock, and a prediction at the deadline is an
instant a reader can ask at. The road does the rest, for both, the same way.

# What was refused

**A per-instance desire level.** The first draft of this had *this debt not overdue, throughout
its window* as a desire node between the universal and the want — a `hold-during` with the
debt's window as its period. The sovereign struck it: the instance is the WANT's grain, not the
desire's. A desire is one; what is per-instance is what gets minted under it. Cleaner, and it
removes a stored node that only ever restated a row of the violation select.

**The ledger's own road.** `owe` stops minting. The twenty-one `is_obligation` branches become
the choir judging a want by its redeem window — still subjective, still the market's measure
([a-situated-instance-is-kept-only-when-it-is-testimony](/decisions/a-situated-instance-is-kept-only-when-it-is-testimony.md))
— and no longer a second deriver reaching the same graph family by a different door.

**Sensing's per-property desires as THE decomposition.** They are one way of declaring — a
genesis rule that pre-splits *all properties in range* per property because the roster is
known. Under one road they are legitimate and unnecessary: one universal desire yields the same
wants, and yields a soil-and-air want where per-property desires could not. Collapsing them is
not required by this record and is its natural consequence.

**Decomposition at rebuild.** A runtime instance arrives by a WRITE — a claim, a reading — and
the road reads it on the next pass. Re-running derivations on every rebuild of the desire
modality was tried and refused when a root was re-derived from a pick (#644); enumerating a
universal's instances is a read, not a re-derivation, and the scar stands.

# The forest stands, and it is a forest of wants

[a-desire-is-a-forest-of-derived-roots](/decisions/a-desire-is-a-forest-of-derived-roots.md)
settled that an agent's desires are several trees, a root per premise, decomposed per instance,
per property and per side. What this record changes is what the nodes below a root ARE: not
derived desires, but WANTS. A root is a desire; everything under it is minted by the road above
from the instances the world presents, and is gone when met. `desire.md`'s own heading had it
right before this record did — *a desire is the top of one tree of wants*.

# What is left

Stage one is built. `witnesses_of` runs the desire's report select — `?this`, which constraint,
and `?_about` where the constraint's block states it — now and at each prediction's start, and
returns the rows with their first instants; `_clusters` groups them by scope; `mint` names one
want per cluster, about exactly those, suffixed for what it is about only where that is narrower
than the desire, so a desire about one property mints `<desire>.pursued` exactly as before.
`Want.about` is a tuple. Measured on the greenhouse: a dry, warm bed mints a want about the soil
alone and plans a dose alone; a cold, dry bed mints one want about both.

Two things were learned building it. **`GROUP_CONCAT` over an IRI binds nothing** on this
engine — no column, no error — and over `STR(?x)` it binds; the trap AGENTS.md records, arriving
through aggregation, and pinned in `test_wants.py`. And **the per-block `orexis:about` is an
authoring convention**: sensing's region shape and the greenhouse's state it per constraint,
and a shape that does not falls back to the desire's whole `orexis:about`, which is what every
want was before.
**Stage two is built: the ledger writes debts and predictions.** *No overdue debts* carries a
met-test whose two violations are each about the debt itself (`orexis:about sh:this`, on a
`sh:sparql` constraint so that a serve's discharge reads met in the imagined world): a lapse in
view and unpaid, or presented and unpaid. `owe` writes the debt and a `market:lapsesAt`
prediction holding from the deadline, then ASKS the road, which mints one want per debt at its
own deadline; `discharge` and the sweep drop the prediction; the ledger speaks for the road's
want by its claim's window; the host answers foresight for that root as every deadline it has
been given; a debt written before the ledger predicted is endowed its prediction at boot. A
debt with no deadline and nobody asking is nothing to pursue until its holder asks, and the
want minted then holds at no instant. The `is_obligation` sites stood at first, branching on
the choir's judgment; they were collapsed one slice at a time afterwards — the serve's
affordance names the want it is owed for (#697), a debt is reported under its root (#698),
the tick marks what may be acted on (#700), and the kernel's `Judgment` carries no market
word, the market's `OwedJudgment` carrying the claim and whom it is owed to. #675 is done.

Stage two taught three things. **A root met now with nothing foreseen derives nothing** — the
road's fallback, one want about everything the desire is about, is for a root unmet now whose
select yields no rows, and it minted a want under a met root the first time the road ran
without a pass's judgment in hand; the road is told the verdict where a pass stands on the
root and reads it off the select where a package asks. **A root's shape lives in the roots
graph**, not in public knowledge, and the container compiling it from the public graphs alone
found no target, raised, and read the root unmet every pass — silently, since an error reads
as the loud direction. And **a package's answer reaches the choir only through a module the
choir asks**: the ledger is held by hosting and is not one, so its foresight is forwarded.

**What was foreseen may arrive early, and the present outranks the instant.** A want minted
at a foreseen instant says *hold at T*, and a plan for it is placed to land at T (#619). The
holder presented an hour before the lapse; a reading showed the pot below its floor before
the drift said it would. The cluster is unmet NOW and its want still said T, so a plan found
from `pursuing()` was placed at the deadline less the pour while the buyer waited — hosting's
own presentation path served now, and the two doors disagreed. The road re-mints such a want
with no instant, under the same name, so the trace, a remembered plan and the keeper meet the
want they kept; and a pass that stood on the old judgment is handed the new one. The instant
was only ever the road's reading of the predictions. A plan ALREADY placed at the instant is
the keeper's, and stands until its lapse or a surprise (#527) — the road does not reach into
the ledger.

**The road's contract is a table, and the table found a defect on its first run.**
`packages/orexis-agent-deliberation/tests/derive_wants/` holds one TriG file per case — the
world, the levers, the desire with its met-test, the present, the foreseen, what stands —
loaded into a bare store and judged, and `packages/orexis-agent-deliberation/tests/derive_wants/`
one per case of the judged state alone — the judgments, the desires, the levers, what stands — derived from
([judge-desires-then-derive-wants](/decisions/judge-desires-then-derive-wants.md)), each in
milliseconds, where the four world files that covered the road each stood an agent up to
show one case. What the road leaves is held to a SNAPSHOT
of the whole store beside the case (`<case>.snapshot.trig` in each function's directory,
the case's own text with the
road's changes in it — an unchanged graph verbatim, a changed one re-rendered in place, what
the road wrote after — so `diff` of case against snapshot is what the road did), never to a
reading of it:
the first cut compared five things per want and a want writes nineteen quads, so a label, a
link, a period or an owner could be wrong with every case green — under-reporting, the
sovereign's word for it — and a change in the road's behaviour is now a diff of the snapshot,
regenerated by a flag and reviewed by eyes. Two tanks low
about their level are two clusters, per instance as two debts are, and were ONE name,
`<desire>.pursued.level`; the second mint overwrote the first, and no shipped world could
show it, since sensing's desires and the greenhouse's name their one node and a debt's want
is about the debt itself. A want is named for its instance where the desire ranges over
several — its shape targets a class, or whatever bears a property — and what stands is
checked by name; a desire naming its one node (`sh:targetNode`) keeps every name it had.

**A want carries the desire's met-test instantiated at its witness — it pointed at the
universal for a while.** The sovereign, reading a case's expected want as a name, two abouts
and an instant, expected a want to be structurally a desire, only more specific: *all
properties in range* becomes *this tank's level from 10*. It was; the implementation had the
want point at the desire's whole shape, and the table showed what that meant — tank1's want
read UNMET with tank1 fixed, because tank2 was low, and a debt's want read unmet for any
debt unpaid. `mint` carves the desire's shape now and narrows it — `sh:targetNode` the
instance, only the property blocks and `sh:sparql` constraints about what the want is about
— and writes it into the want's own graph as `<want>.met`; the avoided state and the
estimate are still pointed at, one owner each. The container judges a derived want's STATE
by its own shape and keeps the root's MEASURE (met-and-urgent is a true situation, and the
choir's words, `stale` and `unmeasured`, are finer than a shape's two); the planner already
compiled the judgment's own met-test. A case's expected want is written as that shape.

- **Clustering runs within a desire**, not across. A want derived from two desires would name two
  parents, and nothing here needs it: one universal per premise is what puts soil and air under
  one desire in the first place.

# Seams left open

- **Scope is over predicates**, so two debts to two hosts are one scope and one want — correctly,
  since they may draw from one vessel — and two vans in one vocabulary are one scope though
  nothing they do touches the same van. A scope over variables is what would split them, and
  `scope.md` names it as unbuilt. This record makes the split's consequence concrete — a want per
  cluster — without building the finer cluster.
- **A cluster's instant is its earliest**, and a plan is placed from it. Where two instances in
  one cluster cross far apart, the later one is held to the earlier instant it was already
  meeting; whether that ever costs a plan something is unmeasured.
- **A ratified want stays a want.** hanoi's *every disk home* is authored under no desire and
  handed to the search as it is. It could be a desire — *all disks on peg C* — decomposed per
  disk; nothing needs it to be, and a root is a position rather than a level.
