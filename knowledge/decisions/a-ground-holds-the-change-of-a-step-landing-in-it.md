---
type: Decision
title: A ground holds the change of a step landing in it, and the plan that replaced a step's intention waits for the world to show it
status: accepted
timestamp: 2026-10-21T18:30:00Z
description: >-
  Found porting the dispatcher's pins onto the lane (#1004), where a drive is told to the van and the
  world shows it a fix or two after its earliest landing. A want reopened round an answered step in
  flight was searched from a ground where that step had not happened, and planned it again; and the
  plan that replaced the step's intention took its first step when the step was due to land, before the
  world showed it had. Decided - the ground laid where a step in flight lands holds the step's own
  change, whoever answers it; and a plan adopted in place of an intention ending after its step in
  flight waits for that intention, `execution:waitsFor`. Refused - the executor forecasting the change,
  writing it into the present when taken, letting the replacement fail, the take-time check as the only
  guard, and holding every head of the agent.
---

# The question

The dispatcher's drives were fictive. A fictive step writes its own prediction into the beliefs when
it is taken, so the present already holds where the van will be, and the step lands at its earliest
landing, exactly, because nothing but the executor answers it. Every pin #905 and #921 put on the
dispatcher stood on that: a want reopened round van A's step in flight was searched from the ground in
which that step had landed, and the joint plan's first step was taken in the pass that resolved van A's
intention.

On the lane a drive is a command to the van (#1002). The simulator has the van there forty-five seconds
on, its fix reports every ten, and the courier's transition concludes the position, so a drive whose
earliest landing is thirty seconds is shown at fifty, inside its band of thirty to sixty. Ported onto
the lane, with one agent playing both drivers, the dispatcher's arrivals failed in two ways, each
measured:

- **The reopened want planned the step in flight again.** `lay_ground` lays a boundary where each step
  in flight lands, and its docstring said what that ground holds: what the agent already sees holding
  then — a fictive step's change, written into the present when taken, or a flow's, integrated from the
  committed step. An answered step no flow reads, a drive, is neither. Its ground held van A where it
  stood, and the joint plan began with van A's drive to the position the drive in flight was already
  taking it to; when the fix showed the van there, that step's precondition no longer held, and the
  joint plan's intention ended `failed`.
- **The replacement walked before the step in flight landed.** The joint plan's first step, van B's
  drive, was due at van A's step's earliest landing and was taken then, twenty seconds before the world
  showed van A's drive. Where the replacement's first step was van A's own — a want reopened by a peer
  seen ahead (#921) — its precondition read van A still short of the position, the step was "not taken —
  the present admits it no more", and the replacement ended `failed`.

# Decided

**The ground laid where a step in flight lands holds that step's change, whoever answers it.** The
planner reads each step in flight's own claim off the plan it published — the triples
`execution:retracts` and `execution:adds` name, the diff the search planned on and the executor holds
the world to — and `lay_ground` applies it in the ground at the step's landing, the retractions taken
out and the additions superseding by key as a prediction's do (#988). A fictive step's change is in the
present already, so laid again it changes nothing; a dose's is the state its transition concludes, which
is what the search planned on; a drive's is the position the van will hold. What a re-search starts from
is then the world in which the step has landed, as #905 said it was.

**A plan adopted in place of an intention ending after its step in flight waits for that intention.**
Planning says a reconsideration before it publishes the plan that made it (`Reconsidered` names the
want the replacement is for); the executor marks the intention to end after its step in flight as
before, and when it adopts the replacement writes `execution:waitsFor` from the new intention to the
one ending. No head of an intention is taken while the one it waits for stands, and the heads already
taken are answered first in a tick, so the replacement's first step goes in the tick the world answers
the step in flight. The plan was found in the ground in which that step has landed, and only the world
says when it has.

Ported so, the dispatcher's pins hold on the lane with the dispatcher's figures where the search is the
same: a parcel arriving reopens van A's want at 157 candidates and 125 worlds in the yard, 127 and 102
with seven impossible on the corridor. Where the step in flight changes what the search starts from,
the figure is the lane's: a peer seen ahead of van A is planned round in 15 candidates, since van A is
a drive further on than a fictive pass would have read it.

# Refused

**The executor forecasting an answered step's change**, a belief of its own holding from the step's
landing until the world answers it. It would be a second record of what the published step already
says, written by execution in planning's words for planning to read back, and a third thing to close
when the step is answered, beside the committed step's window. The committed step is the executor's
forecast already (#992), and it holds from the step's opening, which is right for a flow reading a rate
over the window and wrong for a change that holds only once the step has landed.

**Writing the change into the present when the step is taken**, as a fictive step does. A fictive step
is its own world; an answered one is not, and a present holding a position no fix reported is a belief
nobody had testimony for. The world moves an intention, and the executor only says what happened.

**Letting the replacement fail and planning again.** It recovers — the next pass plans from where the
van is — but each reopening round an answered step cost a plan found, a plan adopted and a plan failed,
and the failure is the executor reporting a fault in planning's arithmetic as a fact about the world.

**The take-time check as the only guard.** A head is checked when it is taken (#916), and that is what
refused van A's early drive; but van B's drive passed its check, since van B stood where the plan said,
while the plan's premise — van A where its step in flight takes it — was twenty seconds from holding.
A precondition says whether a step can be taken, not whether the plan it belongs to has begun.

**Holding every head while any intention ends after a step in flight.** It would couple intentions no
reconsideration related: one scope's reopening would stall another scope's walk for a band and a
patience. The wait is between the intention ending and the plan that replaced it, which planning named.

# Seams left open

**A step answered late lands at no boundary ahead.** Past its earliest landing and not yet answered, a
step in flight lands, as the planner reads it, now; so no ground ahead holds its change, and a want
reopened then is searched from the present, where the step has not happened. The replacement waits for
the step and its first step's precondition is asked when it is taken, so it fails rather than acts on a
false premise; and the second trigger replays the walking plan from its step in flight, which keeps
that check right. Laying the change at the instant after now is the obvious mend, and would put a
change nobody has seen into the ground every search of the pass starts beside.

**A pass between a reopening and its landing drops the replacement's cone.** The lane passes every ten
seconds, so in the pass after a reopening the present still matches the ground the reopening's pass
stood in, and the re-root keeps that ground's cone and drops the replacement's, which hangs under the
landing ground. The plan is walked regardless; what is lost is the cone #925 keeps for a re-search. The
dispatcher passed only at landings and never met it; it is #1015.
