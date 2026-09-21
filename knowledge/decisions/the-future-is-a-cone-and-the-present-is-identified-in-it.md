---
type: Decision
title: The future is a cone of diffs, and the present is identified among its children
status: accepted
timestamp: 2026-09-06T12:00:00Z
description: >-
  The sovereign's model of world state in time, agreed 2026-09-06 and recorded before it is
  built. The PRESENT is observed; the FUTURE is a tree of possible worlds under it, each node
  its parent plus a diff, kept as diffs and materialised only while rules run; a DESIRED FUTURE
  is one path in that tree; the PAST is the chain of presents left behind, as diffs, bounded.
  Execution is IDENTIFICATION, not assertion — after an action, and whenever the present
  changes, progression asks which child the present is in, the match becomes the root and its
  siblings die — so an outcome the search already explored continues with no search. Each diff
  carries the facts its rule read, a chain's applicability is their regression, and a method is
  that pair lifted. Refused — asserting a predicted world as the present, keeping worlds as
  graphs in the belief volume, and the per-pass lifetime as the imaginarium's identity.
---

# The claim

**Amended 2026-09-10 by
[planning-branches-on-action-forecasting-on-belief](/decisions/planning-branches-on-action-forecasting-on-belief.md).**
Nothing below becomes false; the tree gains an axis and a twin. Every node carries a TIME, so
two nodes holding the same facts at different instants are different worlds — the world moves
whether or not the agent does — and beside this cone, which branches on what the agent may DO,
there is a second that branches on what it will come to BELIEVE. The second is not searched: it
is folded into each node, because nothing chooses the weather. A LOOK belongs to it, which is
why a look changes no fact here and survives only by a special case.

World state has three regions in time, and the agent walks from one to the next through a
tree it built itself.

- **Present.** The belief store's graphs, observed. Never predicted, never written by a search.
- **Future.** A tree of possible worlds under the present, in the
  [imaginarium](/domain/imaginarium.md). A node is its parent plus a **diff**, and the diff is
  the node: graphs are materialised while the rules run and along the path being executed,
  and dropped otherwise. The search weights and filters the tree; a want's
  urgency and estimate pick where to expand.
- **Desired future.** One path in the tree ending where the want is met — the
  [intention](/domain/intention.md), whose steps already carry their diffs as canonical facts.
- **Past.** The chain of presents left behind, each with the act taken and the diff that
  actually happened — [history](/domain/history.md), kept as diffs and bounded.

**Execution is identification.** After an action, and whenever the present changes for any
other reason, progression asks *which child of the root is the present in?* — by the child's
predicted [interval](/domain/interval.md) and by whether the next step's
[precondition](/domain/precondition.md) holds. The match becomes the root; its siblings and
their subtrees are dropped; the old root goes to the Past. If the world landed in a sibling the
search had already explored — an action's other outcome — the continuation is already there and
no search runs. If no child matches, the cone is dead and a fresh search starts from the present.
The name for this is [identification](/domain/identification.md), and the page says what
distinguishes it from asserting a prediction.

**A diff carries its precondition.** The instantiated facts its effect rule's WHERE read,
obtained from the rule's bindings once along the winning path at adoption — depth queries,
never per fork. A chain's precondition is the *regression* of its steps': step n's minus what
steps 1 to n−1 produce. A [method](/domain/method.md) is the pair of regressed precondition and
diff chain, lifted to variables at promotion, applicable wherever those facts hold whatever
else the present says. The check is an ASK over the present; a shape gives the same verdict
with a report saying which fact is missing.

**Numbers are intervals.** The companion record
[a-predicted-number-is-an-interval](/decisions/a-predicted-number-is-an-interval.md) carries that
half: a reading widened by staleness and by the actuator's learned tolerance, an effect
declaring two bounds, met meaning the interval lies inside the region. It is what makes
identification need no tolerance of its own — "am I in this child" is "is the reading inside
the interval this child predicted".

# What the code already is, and where it differs

Most of the model exists in diff form. Every [step](/domain/step.md) carries its diff as
canonical facts on the ledger, so the diff chain half of a method exists. A node's diff is
already relative to the root and the algebra to re-base it exists. The keeper already holds one
committed step to a band computed from the actuator's pick, so the primitive that identification
generalises to every child exists. The cone-dead path — an unmet verdict, the tail dropped, a
fresh search — exists. Two things differ, and one sentence of the sovereign's first picture was
refused on the way.

1. **The worlds do not survive the pass.** The imaginarium is built in `_begin` and dropped in a
   `finally`; the frontier, the seen set and the achievers are locals of one search. That is
   [#487](https://github.com/ShishkinDmitriy/orexis/issues/487) and
   [#527](https://github.com/ShishkinDmitriy/orexis/issues/527) together, and it is the
   supersession below.
2. **Nothing keeps what a rule read.** The effect rule's bindings are discarded; a remembered
   plan is keyed by a hash of the whole world, too strict and silent about why.
3. **"The child becomes the present"** was refused, and the refusal sharpened the model. The
   present's *content* is always what was observed; the present's *position* in the tree is the
   matched child. Both are true at once, and the distance between them is exactly the interval
   the identification uses.

# What was refused

- **Asserting a predicted world as the present.** A child is a conclusion drawn from beliefs
  plus an effect; writing it as an observation is the move
  [control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md)
  refuses everywhere, and it is what "computed, never asserted" means. Two standing exceptions
  are ruled on here rather than left: a kept promise's predicted facts are today INSERTed into
  the readings graph by the keeper on withdrawal, and that stops — the bridge's verdict is
  identified like any other; and a step an actor satisfies by its own say-so (a look at the
  reading, an offer at the command) is a match by construction, said so in the action's
  declaration rather than by the absence of a watch.
- **Keeping the worlds as graphs in the belief volume.** The seed copy costs about ten
  milliseconds a search; a fork is a write, and the volume is disk; and a store that was never
  on disk is what makes a crashed pass leave nothing behind and a search unable to write a
  belief. The Future stays in memory, beside the belief base, which
  [a-store-is-a-modality](/decisions/a-store-is-a-modality.md) already argued from lifecycle.
- **Keeping the worlds as graphs at all.** In hanoi nothing changes unless the agent acts; in a
  plant world a reading arrives every minute. A cone of graphs dies at the first exogenous
  reading; a cone of diffs is re-rooted on the fresh present by re-applying them, and the keeper
  verifies each step when it is taken, exactly as it does for a remembered plan today. The
  overlay [a-node-holds-one-world](/decisions/a-node-holds-one-world.md) refused was a UNION read
  over a base and a delta, which cannot express retraction; materialising a kept diff on demand
  from its nearest kept ancestor is a fork, not a union, and that record's refusal stands.
- **Keeping old nodes for cycles.** A diff is relative to the root, so after re-rooting a return
  to the old present is a new node under the new root with the inverse diff, and the search
  finds it as it finds anything. Signatures are recomputed relative to the new root; nothing
  outside the cone survives.
- **A tolerance of identification's own.** Tolerance is the interval's width, owned by the
  effect through the learned conversion tolerance and by freshness through staleness. No
  separate term, no separate owner.

# What it supersedes, and what stands

- [a-rule-is-asked-about-a-world-not-about-a-store](/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md)
  is superseded **in part**: the clause "in memory for the life of one plan" and "the only thing
  in the design that is required to be lost". What stands is everything the record was actually
  about — a rule is asked about a world, one named graph per node, the fork rather than the
  replay, the isolation from the ledger. The Future is still a store of its own and still never
  written back; what changes is how long it lives and that it is re-rooted rather than rebuilt.
- [there-is-no-bdi-ontology](/decisions/there-is-no-bdi-ontology.md) is superseded **in part**:
  its premise that "our plan is required to be lost" narrows to *a plan the world has moved away
  from is lost*. Its conclusion — no import, because a mind crosses no trust boundary — stands
  untouched, and nothing here makes a plan an entity anything cites.
- [a-remembered-plan-is-a-method-on-the-want](/decisions/a-remembered-plan-is-a-method-on-the-want.md)
  keeps its refusals and loses its keying: the whole-world signature gives way to the regressed
  precondition, which its own seams named. Amended with
  [#551](https://github.com/ShishkinDmitriy/orexis/issues/551).
- [progression-steps-through-a-plan-on-confirmed-feedback](/decisions/progression-steps-through-a-plan-on-confirmed-feedback.md)
  keeps its refusals — no re-simulation before taking a step, no unconditional tail — and its
  seam "what matches means" closes with
  [#554](https://github.com/ShishkinDmitriy/orexis/issues/554): matching is identification.
- [a-pass-is-budgeted-in-worlds](/decisions/a-pass-is-budgeted-in-worlds.md) is amended with
  [#553](https://github.com/ShishkinDmitriy/orexis/issues/553): the budget counts new forks,
  and a pass that re-rooted spent none.

# The order of work

Each row is one pull request with the suite green, and each closes when its issue says.

| # | item | issue | closes |
|---|---|---|---|
| 0 | the shapes the search judges by compile to SPARQL | [#548](https://github.com/ShishkinDmitriy/orexis/issues/548) | |
| 1 | a step carries its precondition | [#550](https://github.com/ShishkinDmitriy/orexis/issues/550) | |
| 2 | a remembered plan keyed by the regressed precondition | [#551](https://github.com/ShishkinDmitriy/orexis/issues/551) | |
| 3 | the frontier scored by one query | [#552](https://github.com/ShishkinDmitriy/orexis/issues/552) | |
| 4 | the cone outlives the pass | [#553](https://github.com/ShishkinDmitriy/orexis/issues/553) | #487, #527 |
| 5 | identification among the children | [#554](https://github.com/ShishkinDmitriy/orexis/issues/554) | #522, #523 |
| 6 | the Past as a bounded chain | [#555](https://github.com/ShishkinDmitriy/orexis/issues/555) | #311 |
| 7 | an effect declares two bounds | [#556](https://github.com/ShishkinDmitriy/orexis/issues/556) | |
| 8 | met, law, estimate and cost read the ends; a dose is an interval | [#557](https://github.com/ShishkinDmitriy/orexis/issues/557) | |
| 9 | staleness widens a reading | [#558](https://github.com/ShishkinDmitriy/orexis/issues/558) | |

Items 7 to 9 are superseded (2026-09-07): deliberation is on triples and a number is not
special, so the numeric half went to
[deliberation-is-on-triples-and-a-number-is-not-special](/decisions/deliberation-is-on-triples-and-a-number-is-not-special.md)
and its issues #576 and #579, and #556 to #558 are closed. Item 6 stands, deprioritised.

The order is dependency first and value second. The precondition is the seam the rest hangs on
and is small. The compiled law comes before a re-scored cone because a per-candidate judge
verdict has a fixed floor that re-scoring would multiply. The cone comes before intervals because
it works with today's execution-time band, and intervals are the widest change.

# Seams left open

- **Where the cone is held** — per want on the deliberator, which already keys decided plans by
  want, with one root readings graph shared. If two wants' cones want one tree, that is a
  measurement, not a decision.
- **What "present changed" fires identification** — the keeper's events and a readings write.
  Whether every belief write must, or a handler's budget is needed, is measured in #554.
- **A step predicting both a keyed reading and a plain fact** has no answering shape today, and
  identification inherits the gap.
- **Two fillings binding one lifted method at once** — each is a candidate on the menu, walked
  and settled like a primitive, or the cheapest adopted outright; decided when a world has two.
