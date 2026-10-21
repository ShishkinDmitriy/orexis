---
type: Decision
title: Two agents that want one resource ask each other what their constraint reads, and draw lots for it
status: accepted
timestamp: 2026-10-21T21:00:00Z
description: >-
  The sovereign, 2026-10-21, for #923 - the goal of 0.2.0 is the core of two agents that want one
  resource and must decide which goes first; a world is a test and an example, never the goal. It
  settles the three questions #923 left open. Decided - a resource is a value of the key of a
  constraint both agents hold, over a period; a package of its own, coordination, asks a peer believed
  in range what its constraint reads, answers a peer only under a constraint it holds too, and says
  each in the agent's holdings; each agent concludes a conflict of its own from the answer it said or
  heard, and nothing tells it there is one, and it stands while the peer is in range; the draw is a
  domain of documents, a commitment, a reveal and an outcome coordination asks, its numbers derived
  from a secret each agent mints at first boot; while a draw stands each agent lays everything the
  peer may hold at each instant, and once it is decided the loser lays every holding the winner says
  and the winner only the loser's step in flight; and a head is taken only into a world the agent
  believes possible at the taking. Refused - a number drawn at take time, a secret in a deployment
  file, a conflict planning writes, the draw as code, a draw-free precedence, laying nothing until the
  draw ends, a transition concluding the winner, a conflict ended when the answers stop meeting, and
  taking heads only after the pass has planned.
---

# The question

#568 asks how two minds that cannot see each other's plans keep two vans off one position, and
[two-minds-meet-by-saying-their-routes-and-drawing-lots-on-a-conflict](/decisions/two-minds-meet-by-saying-their-routes-and-drawing-lots-on-a-conflict.md)
answered with a protocol: sense, ask what the constraint reads, answer under a shared constraint, draw
lots by commit and reveal, and let the loser yield. #923 was to build it, and left three questions to
settle before code: where an agent keeps the number it draws between commitment and reveal, what fact
says there is a conflict, and where the question, the answer and the draw live.

The sovereign put the goal first, 2026-10-21: *I want to add core functionality; worlds are for
testing and as an example. Focus on a problem when two agents want one resource and should decide who
will be first. It is the goal for 0.2.0; we could have a world on a grid or on a lane. The world
itself is not a goal.* And of the conflict: *agents are independent, they should decide themselves
that there is a conflict.* So nothing below speaks a courier's word, and the lane is where it is
held, not what it is for.

# Decided

**A resource is a value of a shared constraint's key, over a period.** A constraint's
[footprint](/domain/planning/footprint.md) reads predicates joined on a key; the courier's *no two vans
at one position* reads `courier:x` and `courier:y` on two vans joined on the pair. Two agents want one
resource where each believes it will hold one thing of its own at the same values of that key over
periods that overlap. That is the whole of what is contested, and it is said in the constraint's own
words, so any constraint a world states over a key two agents' things can share is a resource of this
kind without a line of code.

**A HOLDING is what an agent says of its own future, and only there.** For each thing it acts for
(`orexis:actsFor`) and each constraint it holds, the agent reads its walking intentions' untaken steps:
the value each step's change gives the key, held from the step's earliest landing to the latest
landing of the next step that changes it, the last open-ended. A holding is that value and that
period; nothing else of the plan crosses. An agent with no walking plan has no holdings, and a peer
standing still is what sensing sees, as #922 left it.

**A new package, coordination, asks and answers.** Deriving a question from a footprint and an answer
from the intentions is code, and it can live neither in speech, which may not speak planning's or
execution's words, nor in planning, which knows no peer. It is a package above all three, loaded for a
role, `coordination:Coordinator`, beneath `speech:Speaker`, and it meets the others at the store and
says through speech's part, as a step's saying does.

- **It ASKS** a peer that acts for a thing it believes NOW to hold a key's predicate — a peer in range,
  since what is out of range is believed nowhere (contact) — when its own holdings touch the key of a
  constraint it holds, and again whenever its holdings change. The QUESTION names the constraint and
  carries the asker's holdings; it is never a query text, and the answerer runs nothing a peer wrote.
- **It ANSWERS** only where it holds the named constraint too, and only with its own holdings at the
  same values of the key over periods that overlap the asked ones; a question over a constraint it
  does not hold gets no answer, which the asker takes as silence. An answer never carries a fact
  outside the asked constraint's key, values and periods.

**Each agent concludes the conflict itself.** An answer that is not empty is a conflict to the agent
that said it and to the agent that heard it, each from its own documents and by its own rule: the same
values, overlapping, under the same constraint. Nothing tells an agent there is a conflict, no
judgment crosses, and there is no third party to rule. Two answers between the same pair are one
conflict, the one of the lower name, so two agents that asked at once draw once.

**The draw is a domain of documents, the draw domain.** A commitment and a reveal are steps whose
sayings make documents, as the market's are; what a heard one means is extracted; whether a reveal
matches its commitment, and who won, is an OUTCOME, a rule the draw ships and coordination asks every
pass over everything the agent believes, `coordination:Outcome`, as speech asks an extraction; and the
desires that drive both are a world's to hold. So the fair coin is a domain a world imports and could
swap for another, and coordination reads only the outcome, concluded in its own word,
`coordination:wonBy` ([draw](/domain/draw/draw.md)).

**The number drawn is derived from a secret the agent mints at first boot.** Coordination mints one
random secret into the agent's own store the first time it starts and never says it; the number for a
draw is a hash of the secret and the draw's name, its commitment a hash of the draw and the number,
and the winner the first digit of a hash of both numbers in the agents' order, as #923's comment
specified. Nothing is kept per draw, both agents compute the same winner from the same documents, a
test fixes the secret, and a draw's name binds the pair, the conflict and the round, so nothing from
another draw can be replayed into it.

**While a draw stands, each lays the peer's holdings; once decided, the loser does, and the winner the
step in flight.** Both lay the peer's holdings, as forecasts of the peer's thing, so each plans as if
yielding and neither enters the contested values: safety never waits on the draw. What is laid at each
instant a holding changes is every value any holding then gives: a step lands somewhere in its band, so
between its earliest landing and its latest the thing may stand at either, and laid one after another
the later took the earlier's key out where it began, so the band was the peer's earliest landing alone
and a van planned into a cell its peer had not yet left - measured on the lane. Decided, the LOSER lays
the winner's holdings, and every holding the winner says after, and its walking plan reopens where they
make a world of it impossible (#921), so it waits (#920) or goes round. The WINNER lays only the loser's
next holding: a drive the loser took before the draw reached it is a step in flight, which nothing the
draw decides cancels ([commitment](/domain/execution/commitment.md)), and the winner that laid none drove
into it. Only the loser ever adapts its plan, and two minds cannot yield to each other in turn for ever.

**A conflict stands while the peer is in range.** Not while the answers meet: two plans that no longer
meet are what yielding made of them, and the conflict ended there stopped the laying that kept them
apart, so the next pass's plans met again in a later round, undecided - measured as two vans in one cell
on the lane. A peer believed nowhere ends it ([conflict](/domain/coordination/conflict.md)).

**A head is taken only into a world the agent believes possible as it stands at the taking.** The
take-time check (#916) asked the precondition alone, and the one-mind record kept "weighing constraints
as a head is taken" refused, stating no reason. Two heads it let through decided otherwise. A van's
radar sees a hedge first when the hedge is beside the van, and the walk that reading wakes takes the
next drive before any pass has foreseen the hedge - the winner drove into one. And a peer's word heard
between two passes - the cell its van will drive into - is in no ground until the next pass lays one,
while the walk at the start of that pass takes the head - both vans drove into one cell in one tick. So
`Planner.check` asks the held constraints of the world the head lands in: the present beside every
forecast holding at some instant of the head's band, the head's own change applied by key, a violation
the world before already held refusing nothing; and it refuses a head after which the last pass
foresaw a world of its plan impossible, though the search that reopened the want has not yet found
another ([commitment](/domain/execution/commitment.md)).

**Silence is the absence of an answer, and sensing is the net.** A question unanswered, or refused,
leaves no conflict and nothing of the peer's future to lay: the agent takes the whole of the avoiding,
and what it sees of the peer is what keeps it off it. A draw restarted past the bound the agent states
of itself leaves the peer SILENT: this agent lays the peer's holdings as a loser does. A withheld
reveal restarts the draw in the next round and is a breach anyone holding both documents can compute.

# Refused

**A number drawn at take time**, `RAND()` in the commitment's saying with a private copy kept beside
it. A saying makes the documents it says, so the copy needs a document addressed to nobody, and a test
of a draw would not be reproducible.

**A secret in the agent's deployment secrets**, beside its broker credential. It would never be in a
volume, but no text reads the environment, so code would have to bind it into the saying, and the draw
would stop being documents.

**A conflict planning writes.** Planning already finds a heard holding making a walking plan's world
impossible (#921), and it could write a row the draw reads. But that is a judgment over the agent's
own plan, made after the holding was laid, and the sovereign's word was that each agent decides there
is a conflict itself: the answer is the agent's own evidence, read the same way by both.

**The draw as code**, inside coordination. It would be one package to read, but the fair coin would
stop being something a world can inspect, test as documents, or replace.

**Precedence without a draw**, a rank the world states or the lower name winning. The two-minds record
refused a rank; a fixed order is a rank by another name, and the agent named first would win every
conflict it ever meets.

**Laying nothing until the draw ends.** A van first heard four cells off on the lane is two drives
from the cell between, and the question, the answer, both commitments and both reveals take passes;
with nothing laid, both drives into it could be taken while the documents are still on the bus. Four
is the receiver's range for that reason: at two, the first sight was one drive from the contested cell,
and the two vans met there before either had heard the other.

**A transition concluding the winner on the reveal's arrival** - built first. A peer's word is a
statement no reader of the mind is handed, and what is extracted of it is a belief of the agent's own,
arrived `orexis:Derived`, which triggers no transition ([transition](/domain/belief/transition.md)): the
rule waited for an arrival that never came, and no draw was ever decided. Making an extracted word
testimony would give every peer's document a second, mind-facing arrival beside its statement. An
outcome asked each pass reads what the transition would have, and needs no arrival.

**Taking heads only after the pass has planned**, the walk a reading wakes taking none. It closes the
same window, but moves when every step of every agent is taken, a holder of no constraint included,
where the check at the taking costs a holder of none one query.

# Seams left open

**Two heads taken in one tick, each before its taker heard the other.** The check reads what the agent
has heard, and two agents whose first sight of each other falls in one tick plan before either is
asked. Range is what keeps that sight away from the contested cell; a world whose instruments cannot
outreach one exchange has no answer here.

**What the check refuses, it refuses for the whole band.** A forecast holding at any instant of the
head's band is laid beside the present, so a cell a peer leaves early in the band refuses a head that
would arrive late in it. Conservative, and a pass later the plan finds the wait.

**The winner yields until it is decided.** Both agents plan as if yielding while the draw stands, so
the winner's plan carries a wait or a detour the draw then makes needless, and nothing reopens a walking
plan for a holding that went: a forecast leaving a world possible reopens nothing (#921). The cost is
the winner's wait, bounded by the draw. The trigger is a world where that wait is dear.

**Backoff between two agents that cannot hear each other** is sensing's, and asked of the lane by #923
as it stands; what each does there is not coordination's to say.

**A resource with no key.** A constraint whose footprint joins no key two things share, a sum or a
count, is no resource here; a capacity of three is not a value two things hold.
