"""The events packages signal each other by, through the runtime (a-package-starts-itself).

AN EVENT IS A SIGNAL, NOT A FACT. It says something just happened — a graph was written, a plan
was published, an intention ended — so that whoever listens can act now; what happened is in the
store, and a listener reads it there. A restart replays no event and loses nothing, because the
state an event pointed at is where the listener would look anyway.

THE NAMES ARE THE KERNEL'S, because a package may not name a word of one above it: execution
listens for a plan planning publishes, and planning for an intention execution ends. The runtime
routes them and knows none of what they mean: `emit` calls every listener at once, on the one
thread, and what each wrote is `GRAPH_WRITTEN` in its turn.
"""

#  A GRAPH A JOB WROTE: `graph`, and the `kinds` its catalogue row carries. `runtime.on(kind, …)`
#  listens for one kind of it; belief revises, prediction predicts.
GRAPH_WRITTEN = "graph-written"

#  A PLAN PLANNING PUBLISHED: `plan`, a graph of `orexis:PlanGraph`, and the `want` it pursues.
#  Execution adopts it, or absorbs it by its patience.
PLAN_PUBLISHED = "plan-published"

#  A WANT AN INTENTION WALKS IS MET IN THE PRESENT: `want`. Execution ends the intention, reached.
WANT_REACHED = "want-reached"

#  THE STEP AN INTENTION IS ABOUT TO TAKE CAN NO LONGER BE TAKEN — its action's precondition does not
#  admit it in the present: `step`. Execution ends the intention, failed.
STEP_BLOCKED = "step-blocked"

#  AN INTENTION ENDED: `intention`, the `want` it pursued and its `outcome`. Planning plans at once.
INTENTION_RESOLVED = "intention-resolved"

#  A STEP'S COMMAND, sized from the present: `actuator` and `payload`. The transport reaching it sends it.
COMMANDED = "commanded"

#  WHAT A STEP SAID: `document`, and the agents it is `to`. Speech believes it as said, and tells each.
SAID = "said"

#  A DOCUMENT FOR A PEER: `to`, and the `document` as TriG bytes. The transport reaching the peer sends it.
TOLD = "told"

#  HOW A RUN ENDS, said by whoever lets go of the agent last (`runtime.release`) — planning, when
#  every want is reached and no desire holds it, or when a want stands that nothing reaches; and the
#  runtime's own when its passes run out.
MET, UNREACHABLE, UNFINISHED = "met", "unreachable", "unfinished"
