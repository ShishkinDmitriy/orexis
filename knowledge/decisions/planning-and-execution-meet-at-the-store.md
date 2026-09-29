---
type: Decision
title: Planning and execution meet at the store, and the intentions are the belief base's
status: accepted
timestamp: 2026-09-29T15:00:00Z
description: >-
  The sovereign's choice of 2026-09-29, the first half of the mind starting itself. The
  Planner held the executor and the executor held the Planner's refine; now neither calls the
  other. A plan goes down as an execution:PlanGraph in the belief base, which the executor takes
  up and commits; planning reads what is walked and where each intention stands off the
  intentions by pattern; a step a bridge keeps below is marked so when it is handed down, and
  planning answers it with the want that keeps it, execution:keptBy, which the executor waits
  on. The intentions become a graph of the belief base, the agent's own and not public, so a
  restart finds them (#842). Refused - planning holding the executor, one start for the mind,
  and refinement asked by a call.
---

# The claim

**A plan is handed down through the store.** `publish_plan` copies each plan a pass found for a
want nothing walks into the belief base as an `execution:PlanGraph` — the steps in execution's
words as the search wrote them, the root saying which want it `execution:pursues`, and beside it
what the want was derived from. `Executor.commit_plans` takes each up, commits it as it always
did, and forgets the graph. Planning is above execution, so it writes execution's words; execution
reads nothing of planning's.

**What is walked is read, not asked.** The intentions are rows, and planning reads them by
pattern: a want a standing intention pursues, or a plan handed down and not yet taken up
pursues, is walked — neither searched again nor withdrawn; the step each standing intention
stands at is what a want kept below is for.

**A step kept below is marked, then answered.** Refinement asks, before a step would be taken
fictively, whether a rule the store holds keeps it one level down. That was a call from the
executor into the Planner. Now the Planner marks, when it hands a plan down, every step taken
fictively whose predicted fact a bridge's head binds (`bridge.keeps`) as `execution:keptBelow`;
the executor does not take such a step fictively, and waits. When it has fallen due, the
Planner's next pass mints the want that keeps it (`refine`) and writes `<step> execution:keptBy
<want>`, and the executor, finding it, records it on the act and waits on the want, as before.
`planning:refines`, the inverse, is retired: one relation, in the words of the layer that must
read it. A pass marks and answers before the walk, so a step waits at most one pass.

**The intentions are a graph of the belief base.** `execution:IntentionGraph`, beneath
`orexis:Graph` and not public — so it never crosses into an imaginarium — classified as the
agent's own when the first plan is committed. A lived-in volume keeps the agent's own graphs,
so a restart finds every intention where it stood, and the executor takes the head of each
from there (#842). Whether a step walking when the process stopped should survive is left to
the world: the executor holds a taken step to its landing and its patience as it would anyway.

# What was refused

- **Planning holding the executor.** Execution lies beneath planning, and the Planner's pass
  could have built and fed the executor it hands plans to. It kept the one pair of packages that
  called each other, and the runtime could not start either without the other.
- **One start for the mind.** Belief, planning and execution started together by one module
  would be a start that is no package's own.
- **Refinement asked by a call at take time.** A question from below to above is the call this
  refuses; marking at hand-off and answering by a row keeps the arrow pointing down.

# Seams left open

- **A step whose own facts no bridge binds, and whose frame one does,** is taken fictively: the
  mark asks of the facts a step adds, which is what makes a want certain, and the frame alone
  once kept such a step below.
- **A planner with no executor** leaves its plans handed down and untaken, and reads their wants
  as walked; a test that plans without walking drops them.
- **The mind still runs its pass in the runtime**, planning then taking up then walking; it starts
  itself next ([a-package-starts-itself](/decisions/a-package-starts-itself.md)).
