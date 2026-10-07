---
type: Repository
title: Imaginarium
term: http://example.org/orexis/planning#PossibleGraph
description: >-
  The store a search thinks in - a second pyoxigraph store, in memory, one per scope, filled from
  the beliefs with every public graph, the agent's desires and wants, and the readings and
  predictions that are the scope's, and holding one graph per possible world. What is in it never happened, and nothing in it reaches
  the beliefs; it outlives the pass so the next can continue.
---

# Why a second store

A step's effect is SPARQL, and a query reads one store: "what would be true here" is answerable
only in a store where *here* is what is true. So the search forks worlds into a store of its own,
where a rule asked about a world reads that world's graphs beside the public ones, and the beliefs
are never touched. The word is the sovereign's, and says the thing that matters.

# How it is filled

The [planner](/domain/planning/planner.md) keeps one per [scope](/domain/planning/scope.md), and each pass
refreshes it:

- `prepare_ground` takes back every graph the last filling brought across and copies again every
  public graph — every one, since a pattern reaching a graph nobody copied returns an empty result
  rather than an error — the catalogue, the agent's desires, wants and records, and of its readings
  and predictions those that are the scope's: one whose named members' scopes meet elsewhere, with
  its revisions, stays behind, so the grounds laid here are the scope's readings and a world their size
  ([a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md)). What the
  store made for itself stays.
- `lay_ground` lays a `planning:GroundGraph` per period: the present, and the present with each
  [prediction](/domain/prediction/prediction.md) applied at its instant.

What it makes for itself: a `planning:PossibleGraph` per world a candidate reached, each forked from
its parent — or from the ground its step lands in, the path replayed there — and never mutated,
since the search holds siblings open at once; for a world forked from a ground, the two graphs
derived from it that say what its step's effect changed there, which go when it goes; the
weighings and candidates on the catalogue; and a `planning:PlanGraph` per want.

A candidate and the world it makes are named by one mint number — `possible/17.by` makes
`possible/17` — drawn from the store's own counter, the highest `planning:minted` anything in it
carries, so a cone kept from the last pass is never named over and a name is as short at depth
eight as at depth one. The path to a world is `planning:by` and `planning:from`, read off the rows;
nothing reads a name back ([#486](https://github.com/ShishkinDmitriy/orexis/issues/486)).

# What outlives the pass

The whole store, which is what lets a search the budget cut short be finished by the passes after,
and a [cone](/domain/planning/cone.md) be re-rooted where the present landed. Measured, a world's own
facts are a handful of quads against thousands shared, so a store in memory of every world kept is
cheaper than re-making them.
