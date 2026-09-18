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
instances in trouble. Run it now, through the door, and at the start of each prediction the
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
instant the door can be asked at. The road does the rest, for both, the same way.

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

- **`crossing_row_of` returns a boolean per root.** It uses `unmet_select` and asks *any rows?*
  It becomes `report_select` and returns the rows — instance, constraint, first instant. That is
  stage one and most of the mechanism.
- **`Want.about` is single-valued** and a cluster is about several things. It becomes a tuple,
  which is the lossiness `Wants` was built with and noted then.
- **`mint` names the want `<desire>.pursued`**, once per desire ever. It names one per cluster.
- **The ledger's met-test and prediction**, then `owe` stops minting and the `is_obligation`
  sites collapse. #675 carries this and is superseded in part by the framing here.
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
