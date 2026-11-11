---
type: Domain Concept
title: Policy
description: >-
  How a package decides to act - whenever an event of an activity's trigger class happens, judge
  whether it calls for that activity and start it if so. Each activity has a trigger class of its own,
  and the events beneath it are put there by whichever ontology is higher, so a lower package never
  names a higher one's word. The judgment is code reading the store; who listens to what is the vocabulary's.
  Execution's is built; the others are #1119's.
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

**A broadcast event, by an activity's trigger class.** Each package declares an abstract trigger
beneath `orexis:Event` and, beneath it, one trigger per activity it declares, named for the activity:
`planning:PlanningTrigger` starts `planning:Planning`. A package with several activities hears several
triggers, and an event beneath one starts that activity and no other. An event is beneath it by an
`rdfs:subClassOf` axiom, and the boot's closure makes it so, as for every kind. The axiom lives in
whichever of the two ontologies is the higher package's: belief is beneath planning, so planning's
ontology puts belief's event of a belief changed beneath planning's trigger; planning is above
execution, so planning's ontology puts its own event of a want reached beneath execution's trigger.
Either way the lower package names nothing above it, and which package wakes to what is read off the
vocabulary rather than wired in the binary. Execution's are built: planning's `planning:PlanPublished` is
beneath `execution:AdoptingTrigger`, `planning:PlanSuperseded` beneath `execution:SupersedingTrigger`
and `planning:WantReached` beneath `execution:ResolvingTrigger`, each naming what it is about under
execution's own predicates - the plan an intention would adopt (`execution:adopts`), the want pursued
(`execution:pursues`), the step in flight an intention ends after (`execution:endsAfter`) - and the
entity it names is what started the activity. And belief's `belief:Revised` is beneath
`execution:WalkingTrigger`, by execution's ontology, said in belief's own words (`belief:revised`,
`belief:changed`), which execution, above belief, reads. Sensing, above belief too, does both: its
`sensing:Perceived` is beneath `belief:RevisingTrigger`, naming the percepts to revise and the kind
their revisions are (`belief:revises`, `belief:into`), and `belief:Revised` is beneath its own
`sensing:ObservingTrigger`, so a percept is said as an observation once it is revised. Coordination's
`coordination:DrawWon` is beneath `planning:PlanningTrigger`, naming the walking wants to plan again
(`planning:reopens`), and its `coordination:Told` beneath `speech:SpeakingTrigger`, naming statements
it already believes it said (`speech:statement`) and the peer (`speech:to`): the event names them, and
speech reads each back from the store as it was said. And speech's `speech:ProseKept`, said by a
transport that kept a person's words as a `speech:ProseGraph`, is beneath `translation:TranslatingTrigger`;
translation keeps its own answer the same way and says the same event, which each transport's ontology puts
beneath its own carrying trigger (`telegram:CarryingTrigger`, with `speech:WritingAnnounced` for the agent shown writing),
and each judges by the graph's provenance whose words they are: a person's are translation's, the agent's the
carrier's. And speech's `speech:Said`, a document the agent said, naming its statements and each it is to, is
beneath `mqtt:TellingTrigger`, which tells it to each agent on the bus, and `translation:PhrasingTrigger`, which
phrases it for each person in a chat; each reads the statements back from the store as speech said them.
The others are declared as their policies are built (#1119).

**An addressed event, by who asked for it.** A timer alarms for the part that set it, and a request
to plan is planning's alone. Put beneath a trigger class, every package's timer would wake every
package listening for one, so these go to their addressee and are no class's members.

# What it is not

**A filter on the class.** Being beneath a trigger says only that the package hears the event; whether
it acts is the judgment, which a class cannot carry
([packages-meet-by-events-policies-and-activities](/decisions/packages-meet-by-events-policies-and-activities.md)).
