---
type: Domain Concept
title: Activity
description: >-
  Something a package does over a stretch of time, started by a policy for the events that
  triggered it - planning a pass, searching a scope, walking the intentions, receiving a reading.
  Its start and its end are events of their own, so another package may be triggered by them, and
  what happens inside it is said as events within it. A span, to whoever traces the agent. Not
  built yet (#1119).
---

# What it is

An [event](/domain/kernel/event.md) has no duration; an activity has nothing else. It begins when a
[policy](/domain/kernel/policy.md) decides that the events it heard call for it, runs for as long as
the work takes, and ends. PROV's word is the one meant: an activity is a `prov:Activity`, of a class
its package declares beneath it - `planning:Planning`, `planning:Searching`, `execution:Walking`.

Its start and its end are instants, so each is an event, said as the activity starts and ends:
`orexis:Started`, beneath `prov:Start`, naming the activity and `orexis:triggeredBy` every event the
policy started it for, and `orexis:Ended`, beneath `prov:End`. Because they are events, the start or
the end of one activity may be what triggers another. An event said while it runs - a want derived,
a search ended, a step taken - names it as the activity it happened `orexis:within`. Several events
may start one activity: two readings revised in one pass start one planning.

An activity may hold others. Planning a pass holds one search per scope, each started and ended
inside it, and once the scopes run apart the searches overlap in time while the planning that started
them has ended.

# Where it runs is a separate question

What an activity is says nothing of the thread it runs on. One that writes the store runs on the
mind, as a job; one that waits on the outside - a fetch, the model's call, a timer - is a task; one
that computes for seconds without the store, a scope's search, runs off both. Its start and its end
are said the same way wherever it ran.

# Who reads it

The journal keeps the starts and ends with every other event, so the history view can draw an
activity as the stretch between them. A tracing sink on the watch turns the same events into spans -
an activity a span, an activity inside another a child span, the events that triggered it the span's
links - so the dependencies between packages can be seen. No package imports the tracing; it hears the
events as history and metrics do
([packages-meet-by-events-policies-and-activities](/decisions/packages-meet-by-events-policies-and-activities.md)).
