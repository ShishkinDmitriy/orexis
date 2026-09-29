---
type: Decision
title: Planning and execution meet at the store, signal each other, and the mind starts itself
status: accepted
timestamp: 2026-09-29T15:00:00Z
description: >-
  The sovereign's choices of 2026-09-29, the mind's half of a-package-starts-itself. The Planner
  held the executor and the executor held the Planner's refine; now neither calls the other.
  Planning publishes a plan once, an orexis:PlanGraph it owns, and an intention adopts it by
  reference; a package owns its signals (the Planner's plan published, the executor's intention
  resolved) and its part connects them when all the parts are linked; belief, planning and
  execution start themselves; the intentions are a graph of the belief base,
  so a restart finds them (#842). An intention ends early where planning says its want is reached
  before it began, or its next step is blocked. Refused - copying the plan into the intentions,
  a kernel list of every package's events, events as stored facts, planning holding the executor, and ending a begun plan when its want is met.
---

# The claim

**A plan is published once, and adopted by reference.** Planning writes each plan a pass found into
the belief base as an `orexis:PlanGraph` — the kernel's, since planning writes it and execution
reads it — under a name minted for that plan, its steps moved under it, the root saying which want it
`execution:pursues`. Planning owns it and it stays. An intention `execution:adopts` it and holds only
its own rows: where it stands, its acts, its outcome. Every read of a step's facts looks in the plan
it adopts. A second plan for one want never shares a step's name with the first, so the executor's
renaming went with the copy.

**A package owns its signals, and they are connected when the parts are linked.** A
[signal](/domain/kernel/signal.md) says something just happened, and it is an attribute of the
object that says it: the Planner's `plan_published`, and the executor adopts the plan; the
executor's `intention_resolved`, and the Planner plans again at once; the Planner's
`want_reached` and `step_blocked`, and the executor ends an intention early; the deliberator's
`revised`, and the executor walks, since what it waits on is the present. The runtime makes every
[part](/domain/kernel/part.md) first, then links them, then starts them, so planning's part connects
its Planner to the executor however the two were ordered; a connection points down, as an import
does. The one signal the runtime owns is a graph written, heard by kind. A signal is not stored:
what it points at is, and a handler reads it there.

**The mind starts itself.** Belief revises every belief and prediction written; planning plans every
pass and holds or lets go of the agent (met, unreachable); execution walks what is due every pass and
takes a step by its commands and its sayings, which its part hands the transports and speech it
was linked to. The runtime keeps the parts and no longer runs a pass of its own.

**What is walked is read, not asked.** Planning reads the intentions by pattern: a want a standing
intention pursues, or a plan published and adopted by no intention yet pursues, is walked — neither
searched again nor withdrawn.

**A step kept below is marked, then answered.** Planning marks, when it publishes a plan, every step
taken fictively whose predicted fact a bridge's head binds (`bridge.keeps`) as `execution:keptBelow`;
the executor does not take it and waits. When it falls due, planning mints the want that keeps it and
writes `<step> execution:keptBy <want>`, which the executor records on the act and waits on.
`planning:refines`, the inverse, is retired.

**An intention ends early, and only in two cases.** Both judgments are planning's, since the met-test
and the precondition are its texts; both end with execution, which alone writes the intentions.

- *Its want is reached before it began.* Planning signals a walked want the present meets; execution
  ends the intention `reached` where none of its steps has been taken — rain before the dose.
- *Its next step is blocked.* Planning asks the present ground, for every step an intention stands
  at, fallen due, not taken and not kept below, whether its action's precondition still admits the
  step's own values; where it does not, execution ends the intention `failed`, and planning plans
  again at once.

Otherwise an intention stands until it is done or a taken step goes unanswered past its patience,
and planning never replaces it on its own, even with a cheaper plan found. That is single-minded
commitment in Rao and Georgeff's sense — kept until achieved or believed impossible — where the
executor before noticed neither until a step timed out.

**The intentions are a graph of the belief base.** `execution:IntentionGraph`, the agent's own and not
public, classified at the first adoption, so a lived-in volume keeps them and a restart finds each
intention where it stood (#842).

# What was refused

- **Copying the plan into the intentions**, which #855 first did: the plan existed three times, and
  after the last copy nothing said which plan an intention walked or who found it.
- **A kernel list of every package's events**, which #855 first had in a kernel module of events: the
  kernel named a plan published and a want reached, words that are planning's, so a package's
  vocabulary lived below it. The sovereign moved each onto the object that says it.
- **Events as stored facts**, recommended and not chosen: a graph written by kind would survive a
  restart as an event; the sovereign chose a channel of signals, and what survives is the state the
  signals point at.
- **Planning holding the executor.** It kept the one pair of packages that called each other.
- **Ending a begun plan when its want is met.** The supplier's round, once opened, answers a call
  and must still be cleared; ending it there left the fern unserved.

# Seams left open

- **A step whose own facts no bridge binds, and whose frame one does,** is taken fictively.
- **A step becoming due within one walk** is taken before planning can say it is blocked; the next
  pass sees only steps that stand.
- **A plan whose intention is resolved stays**, as the history of what was committed.
- **A planner with no executor** leaves its plans unadopted, and reads their wants as walked.
