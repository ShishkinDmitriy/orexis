---
type: Decision
title: Packages meet by events, policies and activities - an event is an instant, a policy decides, an activity takes time
status: accepted
timestamp: 2026-11-10T12:00:00Z
description: >-
  The sovereign's ruling of 2026-11-10, event-storming the agent. An event is an instant and never triggers another;
  each package's policy hears the events beneath its trigger class and decides whether to start an activity, whose
  start and end are events in turn and which says what happens inside it. The binary's links between parts go, and
  planning, execution and coordination stop running every pass for no cause. Refused - signals connected at link,
  events as telemetry alone, triggering on graph kinds alone, handlers as Tokio tasks, and a shared or static
  Planner. Not built yet; issue #1119 holds the steps.
---

# What was true (on main at d4dfd6f0)

Parts meet two ways. They read and write the store, and they are LINKED: `binary/src/lib.rs` hands planning a callback
that reads the Planner's fields after each pass and calls the executor's `end_for`, `supersede_after` and `adopt`, hands
the executor a `taking` that borrows the Planner, and hands belief a `revised` that raises execution's `soon`. Fourteen
`Rc<RefCell<…>>` hold the parts' objects so the links can reach them. Planning, execution and coordination ask for
`every(0.0)` and run whole on every pass, whatever caused it - a poll, a message, or another part asking `again` - so an
idle terrace agent plans every second. Events were what the watch hears and nothing else: the history, the metrics and,
since #1118, nothing that decides.

# The claim

**An event is an instant, and it never triggers another event.** What happened is said once, at the instant it
happened, and that is all an event is. A more specific event may be said at the same instant, naming the one it
specifies (`orexis:specifies`): a message arrived, and at that instant a reading of a sensor arrived.

**A policy decides, and what it starts is an activity.** Each package declares a trigger class and hears the events
beneath it ([policy](/domain/kernel/policy.md)); it judges, reading the store, whether they call for anything, and starts
an [activity](/domain/kernel/activity.md) if they do. An activity takes time. Its start and its end are events, triggered
by and naming what started it, and those events may trigger other packages. What happens inside it is said as events
within it.

**Who hears what is the vocabulary's, and the higher ontology says it.** An event is beneath a package's trigger by an
`rdfs:subClassOf` axiom in whichever of the two packages is higher, so planning's ontology puts belief's change beneath
planning's trigger and its own reached want beneath execution's, and no lower package names a word above it. A timer's
alarm and a request to plan are addressed to one part, and are no class's.

**An event names what happened and carries no facts to act on.** What a policy decides it reads from the beliefs, which
are still where packages meet ([a-package-starts-itself](/decisions/a-package-starts-itself.md)).

# The storm

What each package hears, and what its policy starts. Words not declared yet are this record's proposals and get their
classes as they are built.

| Package | Hears | Starts | Says |
|---|---|---|---|
| transports | its own timer (a poll, a nudge) | a fetch or a poll, as a task | `orexis:MessageArrived` |
| sensing | `orexis:MessageArrived` for a sensor it reads; its own timer | `sensing:Receiving`; asking after silence | `sensing:Observed`, `sensing:Silence` |
| belief | `orexis:GraphWritten` of a belief | `belief:Revising` | `belief:BeliefChanged`, where revision concluded something |
| planning | `belief:BeliefChanged` crossing into a scope; `execution:IntentionResolved`; its own timer, a ground starting; `planning:PlanningAttempt`, addressed | `planning:Planning`, holding a `planning:Searching` per scope | `planning:PlanPublished`, `planning:WantReached`, `planning:PlanSuperseded`, `planning:SearchEnded` |
| execution | `orexis:GraphWritten` of an `orexis:PlanGraph`; `planning:WantReached`; `planning:PlanSuperseded`; `belief:BeliefChanged` of the present; its own timer, a step due, landing or out of patience | `execution:Walking` | `execution:StepTaken`, `execution:Taking`, `execution:StepAnswered`, `execution:IntentionResolved` |
| coordination | a question or an answer heard; `planning:Planning` ended; `belief:BeliefChanged` of a peer in range; its own timer, a peer's patience | asking, answering, concluding | `coordination:Held`, `coordination:Concluded`, a `planning:PlanningAttempt` where a draw won reopens a walk |
| speech | `orexis:GraphWritten` of a statement | extracting | `speech:Heard`, `speech:Said` |
| translation | a person's prose; the model's answer | conversing, as a task | `translation:Conversed`, `translation:Translated` |

**A reading to a dose.** The MQTT session's task says `orexis:MessageArrived`, and sensing's
`sensing:ReadingArrived` specifies it at the same instant. Sensing's policy starts `sensing:Receiving`, which writes
the percept and says `sensing:Observed` within it; belief's `Revising` concludes the bed is dry and says
`belief:BeliefChanged`. Planning's policy finds the graph crossing into the soil's scope and starts `planning:Planning`
triggered by it; inside, `planning:Searching` in the soil's scope ends with `planning:SearchEnded`, and the pass says
`planning:PlanPublished`. Execution hears the plan's graph written and starts `execution:Walking`: the step is asked
(`execution:Taking`), planning's policy answers in execution's words in the same drain, and the walk says
`execution:StepTaken`, sends the pump its command and sets a timer for the landing.

**A timer.** At the landing the timer's task says `orexis:TimerAlarmed`, addressed to execution, whose policy starts
`execution:Walking` triggered by it; the present holds what the step predicted, and the walk says
`execution:StepAnswered`. Nothing else woke between the step and its landing.

**A peer's question.** The bus brings a peer's document; speech extracts it into a belief, and coordination hears the
question, answers within its activity and concludes the conflict it finds (`coordination:Concluded`). Where the draw is
won, it says `planning:PlanningAttempt` to planning, which plans the walking want again.

**A person's words.** A chat's carrier says `orexis:MessageArrived`; translation's policy starts conversing as a task,
the model's call waiting off the mind, and the answer comes back as an event of its own, which starts the activity that
writes what the person stated and says `translation:Conversed`.

# What was refused

- **Signals connected when the parts are linked.** A [signal](/domain/kernel/signal.md) is a handler on a package's
  object, and connecting it means the binary holds both packages and an `Rc` to each: the callback after planning's
  pass does execution's work inside planning's. An event heard by class leaves nothing to link.
- **Events as the watch's alone.** They already say everything a link carries - a plan published, an intention
  resolved - and keeping a second channel for control beside them is two words for one happening.
- **Triggering on graph kinds alone.** Today's `on(kind)` hears a graph written and nothing else, so it cannot say a
  timer alarmed, a part asked, or why an activity started. A graph written stays, as one event among the others.
- **An event triggering an event.** A chain of events with no decision in it is a decision nobody owns; the policy is
  where it is owned, and where a package can decline.
- **Each handler a Tokio task.** The parts hold the store borrowed and their objects shared, so they are not `Send`; a
  search does not yield and would stall the sessions on its worker; and jobs run in the order they came is what lets a
  snapshot case and a digest hold the binary to one result. A task is where an activity waits, never where the store is
  written.
- **A static or shared Planner.** One agent per binary makes a global possible, but execution and coordination reach it
  only because they are linked to it; with the links gone nothing needs it, and a global would want the lock that
  [the-agent-moves-to-rust-one-package-at-a-time](/decisions/the-agent-moves-to-rust-one-package-at-a-time.md) refuses.

# What it amends

- [a-package-starts-itself](/decisions/a-package-starts-itself.md), in part: a package is offered a policy over its
  trigger beside its timers, and its signals go.
- [planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md), in part: they
  still meet at the store; what one tells the other is an event, not a signal, and execution's check of a head is an
  exchange of events rather than a call into the Planner.
- [metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md), in part: an event
  is no longer only what the watch hears; it is still everything the watch hears, and the tracing sink hears it too.

# Seams left open

- **A trigger is an entity, and a span's link is the entity's generation.** PROV makes a start's trigger the thing an
  event was about (`prov:entity`), so a tracer links a span to the event that generated that thing, which needs the
  event named where it is said rather than where the journal keeps it (#1121 does).
- **Exactly where time changes what planning concludes** is assumed to be the start of a ground; a forecast's end is to
  be checked before planning stops running each pass, and the poll stays as a ceiling until it is.
- **A plan is heard published, not its graph written**: execution adopts on `planning:PlanPublished`, which names the
  plan and the want, rather than on the graph's kind, which would make execution read planning's words to find the
  want (#1119 step 4).
- **The check of a head stays a call until a hearer can hold the store**: the watch's hearers live as long as the
  process, and the Planner borrows the store, so planning cannot answer `execution:Taking` from one; it is asked so
  once the store is shared (#1119 step 7), the one link left between the two.
- **A head asked and never answered**: an executor with no planner in a test must not wait for an answer nobody gives,
  so saying `execution:Taking` answers whether anybody hears it.
