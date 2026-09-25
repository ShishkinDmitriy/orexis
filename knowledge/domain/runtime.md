---
type: Service
title: Runtime
description: >-
  The process of Agent 0.2.0: one agent, one world, booted from the world's files into a store
  whose catalogue says what every graph is, then run pass by pass — the planner's pass, then the
  executor walked until nothing is due — and stopped when every desire is met, which is when no
  want stands and no intention walks. `agent/runtime.py`.
---

# Runtime

The runtime is what a container runs: `python -m agent.runtime world/<name> <agent-id>`, one
process told one identifier and given one world. It has two acts.

**`boot` reads the world's files into the agent's store.** A 0.2.0 world is a directory of five
files, each becoming the graph it is: `ontology.ttl`, the world's own words, loaded into one
vocabulary graph after the kernel's T-Box (`agent/ontology.ttl`) and every package's, and closed
over `rdfs:subClassOf` so that a kind is every kind it is beneath; `world.ttl`, the world graph,
where the agent's identity is read off `orexis:localId`; `actions.ttl`, the actions; `desires.ttl`,
the graph of desires with their met-tests and estimates, the agent's; and `state.ttl`, the first
state graph, the agent's. Every graph is classified as it is created, the catalogue is closed and
`scope_actions` writes the scopes. A store that already holds a catalogue is a volume the agent
has lived in: the public graphs are reloaded, since they are asserted from files and replaced at
every boot, and the desires and the state are left as they are, since they are the agent's now.

**`run` is a loop of passes, and it stops.** A pass is the [planner](/domain/planner.md)'s — the
wants derived, each searched, the plans handed to the [executor](/domain/executor.md) — and then
the executor ticked and drained until nothing more happens at that instant, which for a fictive
action is the whole plan and for a real one is up to the first landing the world has not
answered. The loop ends when every desire is met: no want stands in any of the planner's
imaginaria, which is where the derivation mints them, and no intention walks. A world whose one
want is one-shot, [Hanoi](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md), solves
its tower in seven moves and exits. Wants standing with nothing walking is one of two things,
told apart by the plan's `planning:outcome`: a search the budget cut short, `planning:Exhausted`,
which the next pass continues, or nothing this agent holds reaching the want, which is exited
as unreachable rather than looped on.

**What is not wired yet.** Sensing, prediction, the deliberator and the transport. Hanoi has
none of them, and they join with the first sensed world, where the runtime will also own the
queue between a transport's network thread and the one executing thread.

**A world's tests live with the world.** `world/hanoi/tests/` boots the world from the files
beside it and runs it to met; the target is no global tests at all.
