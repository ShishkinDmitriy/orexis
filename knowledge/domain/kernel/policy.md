---
type: Domain Concept
title: Policy
description: >-
  How a package decides to act - whenever an event of its trigger class happens, judge whether it
  calls for an activity and start one if so. The trigger is a class each package declares, and the
  events beneath it are put there by whichever ontology is higher, so a lower package never names a
  higher one's word. The judgment is code reading the store; who listens to what is the vocabulary's.
  Not built yet (#1119).
---

# What it is

Event storming's "whenever this happens, then that": the step between an
[event](/domain/kernel/event.md) and an [activity](/domain/kernel/activity.md). An event never starts
another event. A policy hears it and decides, and what it decides is to start an activity or to do
nothing. Planning's policy hears that a belief changed and asks whether the graph crosses into any
imaginarium; where it crosses into none, nothing is planned and nothing is said.

A policy is the package's own and reads the store as any of its acts does. Hearing an event does not
carry the facts it acts on: the event says that something happened and names it, and the policy reads
what holds now from the beliefs.

# What it hears

**A broadcast event, by its package's trigger class.** Each package declares one class of events,
`planning:Trigger`, `execution:Trigger`, beneath `orexis:Event`, and listens for it alone. An event
is beneath it by an `rdfs:subClassOf` axiom, and the boot's closure makes it so, as for every kind.
The axiom lives in whichever of the two ontologies is the higher package's: belief is beneath
planning, so planning's ontology says `belief:BeliefChanged rdfs:subClassOf planning:Trigger`; planning
is above execution, so planning's ontology says `planning:WantReached rdfs:subClassOf
execution:Trigger`. Either way the lower package names nothing above it, and which package wakes to
what is read off the vocabulary rather than wired in the binary.

**An addressed event, by who asked for it.** A timer alarms for the part that set it, and a request
to plan is planning's alone. Put beneath a trigger class, every package's timer would wake every
package listening for one, so these go to their addressee and are no class's members.

# What it is not

**A filter on the class.** Being beneath a trigger says only that the package hears the event; whether
it acts is the judgment, which a class cannot carry
([packages-meet-by-events-policies-and-activities](/decisions/packages-meet-by-events-policies-and-activities.md)).
