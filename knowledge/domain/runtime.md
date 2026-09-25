---
type: Service
title: Runtime
description: >-
  The process of Agent 0.2.0: one agent, one world, booted from the world's files into a store
  whose catalogue says what every graph is, then run pass by pass — the planner's pass, then the
  executor walked until nothing is due — and stopped when no desire is held, no want stands and
  no intention walks; an agent holding a desire runs for good. `agent/runtime.py`.
---

# Runtime

The runtime is what a container runs: `python -m agent.runtime world/<name> <agent-id>`, one
process told one identifier and given one world. It has two acts.

**`boot` reads documents, and each says what graph it is.** The kernel's T-Box
(`agent/ontology.ttl`), every package's ontology and rule set, and every `.ttl` and `.trig` file
in the world's directory, whatever it is called, are read the same way. A Turtle file is one graph
named by its own IRI, and `<> a orexis:DesireGraph` in it says what that graph is — the Linked
Data reading, where a document describes itself. A TriG file names its graphs and states their
kinds in its default graph, as a nanopublication's head does. The rows about a graph go to the
catalogue, where every reader asks, and not into the graph, where a rule would read them as a fact
about the world. A document says what its graphs are and nothing about how they arrived or whose
they are: the loader writes `orexis:Asserted`, and the owner where a graph is the agent's. A
graph stating no kind, one claiming to be the catalogue and one stating an arrival or an owner are
refused (`store.document`).

A document may import others, `owl:imports` with a relative IRI that resolves to the imported
file's `file:` IRI, which is the name its graph is loaded under; the boot reads every import too,
once each, so a world brings the [domains](/domain/domain.md) it speaks and a domain its own
actions and shapes. The vocabulary goes first, since whether a graph is public is the vocabulary's to say: every
document that says it is an ontology graph, each a graph of its own, then the closure over
`rdfs:subClassOf` across all of them, written into one graph the runtime derives, so that a kind
is every kind it is beneath. Then the world's public graphs, then the agent's identity, read off
`orexis:localId` in the world graph, then the world's other graphs — the desires with their
met-tests and estimates, the first state — owned by the agent. The catalogue is closed and
`scope_actions` writes the scopes. A store that already holds a catalogue is a volume the agent
has lived in: every graph a document put in and nobody owns is forgotten and read again, with the
closure, which is how an updated ontology or rule set reaches an agent that has lived; the graphs
the agent owns are left as they are, since they are its beliefs now.

**`run` is a loop of passes, and it stops.** A pass is the [planner](/domain/planner.md)'s — the
wants derived, each searched, the plans handed to the [executor](/domain/executor.md) — and then
the executor ticked and drained until nothing more happens at that instant, which for a fictive
action is the whole plan and for a real one is up to the first landing the world has not
answered. A [desire](/domain/desire.md) is universal, so an agent holding one is never done: a
pass with nothing to do waits for the world to move, and so does one whose wants nothing
reaches, since the world may yet open a way. A want is one-shot: a pass that weighs one met in
the present ground withdraws it, from the planner's imaginaria and from the beliefs, where a want
a world authored lives. So an agent holding wants and no desire —
[Hanoi](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md)'s mover, the courier —
exits once every want is reached and no intention walks. Wants standing with nothing walking is
one of two things, told apart by the plan's `planning:outcome`: a search the budget cut short,
`planning:Exhausted`, which the next pass continues, or nothing this agent holds reaching the
want, which such an agent exits as unreachable rather than looping on.

**A sensed world runs through its transport.** Where the world says a sensor is reached over a
[transport](/domain/transport.md), the runtime brings the member up from the environment and
hands it `deliver`: a message arrives on the member's thread and is queued, and each pass drains
the queue on the one executing thread — [sensing](/domain/sensing.md) writes the observation,
the [deliberator](/domain/deliberator.md) runs the rules that conclude its side, the
[prediction](/domain/prediction.md) package writes the stretches ahead and the rules conclude
theirs, and a reading fallen due is asked for again. A step whose action carries
`execution:command` is taken by sending what the command answers, sized from the present, through
the transport's `actuate`, signed with the agent's own key since a device opens only for its holder;
the [greenhouse](/domain/domain.md)'s pump and heater are taken so.

**A world's tests live with the world.** `world/hanoi/tests/` boots the world from the files
beside it and runs it to met; the target is no global tests at all.
