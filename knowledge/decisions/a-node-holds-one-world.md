---
type: Decision
title: A node holds one world, and the second copy is gone
description: >-
  A search node used to hold its world twice — once as an imaginarium graph and once
  flattened into rdflib — and the second copy was fifty-five percent of a solve: 198,144
  Graph.add calls to express steps that changed four triples each. It existed because the
  judge read rdflib, and nothing does since the judge moved to Rust. What a node keeps now is
  its own readings as N-Triples; the invariant half of every world in a pass is written once.
  The alternative the sovereign proposed — a base graph with per-node deltas, queried as a
  union of named graphs — is refused because SPARQL has no precedence and there is nothing
  left to save, NOT by retraction: every retract in this tree is an upsert. Measured on the bench:
  three disks from 5.52 s to 1.9 s.
status: accepted
timestamp: 2026-09-01T21:40:00Z
---

# A node holds one world, and the second copy is gone

`_Node` carried both an imaginarium graph — the world a rule reads, forked from its parent by
diff inside pyoxigraph — and `world`, that same world flattened over public knowledge into an
rdflib graph. The pair was deliberate and is recorded as such in
[a-rule-is-asked-about-a-world-not-about-a-store](/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md),
whose seam said plainly that materialising the second from the first was the piece of work the
design did not remove: two engines wanted different shapes of the same fact, and pySHACL only
speaks rdflib.

That premise expired when the judge moved to Rust
([the-judge-speaks-rust](/decisions/the-judge-speaks-rust.md)). Nothing on the planning path
reads rdflib any more, so the second copy was pure tax — measured at **55% of a hanoi solve,
198,144 `rdflib.Graph.add` calls**, a full copy of a 2,300-triple world per candidate to
express a step that changes four triples.

**What a node keeps now is its own readings, as N-Triples.** The rest of a judged world —
public knowledge, this agent's beliefs, whatever it records, and the wants — cannot be changed
by a step, so it is written ONCE per pass by the store's own engine and concatenated in front
of whichever node is being judged. N-Triples because its lines stand alone: two graphs join
with `+`, and nothing is re-parsed to merge them.

## The alternative, and the argument that does NOT carry it

The sovereign asked the right question: *we have a named graph per possible world — why not
keep the first one big and the others on top of it, and query the list of named graphs?*

The first answer given was that **a union can add but cannot un-say**, since a move's
`orexis:retracts` deletes. The sovereign refused the evidence, correctly: *you were lucky,
because this world effectively has no delete list — a disk is always on top of something.*
Checked across the tree, that is worse than a lucky example. **Every `retracts` clause here is
an UPSERT.** Hanoi's removes `$via hanoi:on ?old` while its construct adds `$via hanoi:on
?dest`; the other four remove `?obs ?p ?o` — the observation node their own construct
immediately re-creates, because the sensed graph keeps one node per (subject, property). Five
of five replace a value; none removes one. A domain with a genuine deletion would break an
overlay, and this repo has never had one, so that cannot be the load-bearing argument and was
not entitled to be stated as one.

What actually carries it is two things, neither about retraction:

- **SPARQL has no precedence.** An overlay needs *the newest value wins*, and a union of named
  graphs does not mean that — the rule would have to say so itself, in its own text. That puts
  planner bookkeeping into **every package's `rules.ru`**, and a domain author would have to
  know how hypotheses are stored in order to ask whether a disk is on a peg. It holds whether
  the change is an upsert or a deletion.
- **There is nothing left to save AT THIS SIZE, and size is the whole of it.** A node holds the
  FULL mutable slice, not a diff — `reached` copies its parent's readings and applies the
  change — so the per-node cost is O(state), not O(step). It is free here because the state is
  three triples: measured on a 3-disk solve, the dump costs 0.01 s across 78 nodes and the fork
  0.02 s, against 0.38 s for the rules. An overlay would optimise three hundredths of a second.

  **That is a limit, not a property**, and it was measured rather than assumed. Forking one
  node, as the mutable slice grows, the diff staying one triple throughout:

  | mutable slice | per node | × 78 nodes |
  |---|---|---|
  | 3 triples | 0.05 ms | 0.004 s |
  | 100 | 1.0 ms | 0.08 s |
  | 1,000 | 5.9 ms | 0.46 s |
  | 10,000 | 68 ms | **5.3 s** |
  | 50,000 | 404 ms | **32 s** |

  Linear in the slice, paid once per node. A society whose agents observe hundreds of subjects,
  or a domain whose state is thousands of facts, crosses into the regime where the sovereign's
  overlay is the right design and this one is not — and the cost of going there is stated
  above: precedence has to enter the rule text. The number to watch is the size of the mutable
  slice, and the place to watch it is
  [measure-the-search](/runbooks/measure-the-search.md).

So the world stays materialised per node — but in ONE store, the Rust one, forked by diff,
which is what the imaginarium was always for. The copy that was deleted is not the world; it is
the translation of the world into another library.

**Worth noticing, and worth not over-reading: today every state change in this system replaces
a value rather than removing one.** It is a fact about five effects, not a property of the
design, and it follows from what the mutable slice happens to be — observations keyed by
(subject, property), and hanoi's `on` — both FUNCTIONAL, one value per subject, so the natural
change is replacement. State modelled as a set-valued predicate would delete for real: a
`clear(peg)` formulation of this same puzzle removes a fact with no replacement, and so would a
lot leaving a venue's offers, or a sensor leaving a rig.

**The machinery takes one already**, and was checked rather than assumed: a retraction with an
empty add list forks a child whose readings are empty and whose `signature.advance` diff is a
removal, which is what cycle detection reads. So this is a note about what the shipped domains
happen to do, not a constraint on what one may do — and the moment a domain deletes for real,
the overlay argument above gains the leg it does not have today.

## What did not change

The imaginarium still forks a graph per node rather than replaying, still writes each world
once and mutates none, and `$state` still names exactly what it did. A membership test the flat
copy answered with `in` is now a scoped SPARQL ask — scoped deliberately, because an unscoped
`GRAPH ?g` would read every SIBLING world in the same store, which is the hazard the naming
collision found the hard way in
[the-domain-is-a-plug-in-and-hanoi-is-the-proof](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md).

# Seams left open

- **One world per pass is still flattened into rdflib**, in `_offer`: the legality check carves
  the shapes an agent holds out of its own data with `cbd`, which is an rdflib walk over blank
  nodes. Once per pass rather than once per node, so it costs what one node used to.
- **The invariant is written whole, not shared.** Every judged world hands the engine the same
  ~2,300 lines again, and rudof re-parses them; its reader has a fixed floor of its own
  ([measure-the-search](/runbooks/measure-the-search.md)). A judge that could hold a graph
  across verdicts would remove both, and neither rudof's API nor pySHACL's ever offered that.
