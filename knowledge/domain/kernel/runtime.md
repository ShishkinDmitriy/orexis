---
type: Service
title: Runtime
description: >-
  The process of Agent 0.2.0: one agent, one world, booted from the world's files into a store
  whose catalogue says what every graph is, then run pass by pass — the planner's pass, then the
  executor walked until nothing is due — and stopped when no desire is held, no want stands and
  no intention walks, or, for a planner that is no executor, when every want standing has a plan
  published; an agent holding a desire runs for good. `agent/runtime.py`.
---

# Runtime

The runtime is what a container runs: `python -m agent.runtime world/<name> <agent-id>`, one
process told one identifier and given one world. It has two acts.

**`boot` reads documents, and each says what graph it is.** The kernel's T-Box
(`agent/ontology.ttl`), the ontologies and rule sets of the packages the agent loads, and every `.ttl` and `.trig` file
in the world's directory, whatever it is called, are read the same way. A Turtle file is one graph
named by its own IRI, and `<> a planning:DesireGraph` in it says what that graph is — the Linked
Data reading, where a document describes itself. A TriG file names its graphs and states their
kinds in its default graph, as a nanopublication's head does. The rows about a graph go to the
catalogue, where every reader asks, and not into the graph, where a rule would read them as a fact
about the world. A document says what its graphs are and nothing about how they arrived or whose
they are: the loader writes `orexis:Asserted`, and the owner where a graph is the agent's. A
graph stating no kind, one claiming to be the catalogue and one stating an arrival are refused
(`store.document`), and so is one stating the [self](/domain/kernel/self.md) anywhere but once in a
self graph. Whose a graph of an agent's own is, its document says — `<> orexis:beliefsOf` beside its
kind, or the self a self graph states — and never its file's name.

A document may import others, `owl:imports` with a relative IRI that resolves to the imported
file's `file:` IRI, which is the name its graph is loaded under; the boot reads every import too,
once each, so a world brings the [domains](/domain/kernel/domain.md) it speaks and a domain its own
actions and shapes. The vocabulary goes first, since whether a graph is public is the vocabulary's to say: every
document that says it is an ontology graph, each a graph of its own, then the closure over
`rdfs:subClassOf` across all of them, written into one graph the runtime derives, so that a kind
is every kind it is beneath. A graph whose kind that closure does not put beneath `orexis:Graph`
is passed over, neither its quads nor its row read in: a kind says who reads a document, and one
the agent's vocabulary does not declare is another reader's, such as the hardware
[onboarding](/domain/onboarding/onboarding.md) reads. Then the world's public graphs, then the agent's identity, read off
`orexis:localId` in the society graph, or in the world graph of a world with no society, and the
self graph the world authored for that agent put in and checked — or held to the self a lived-in
volume already has. That is
the first half, read with the kernel's and the world's documents alone; the agent's
[roles](/domain/kernel/role.md) are read off the self graph it put in, and the documents of each
[package](/domain/kernel/package.md) a role calls for go in after, the closure taken again and any
world graph passed over for a kind only such a package declares looked at a second time. Hanoi's
mover, a planner alone, loads planning and nothing else. Then the world's other
graphs that say they are this agent's — the desires with their met-tests and estimates, the first
state — owned by it; another agent's are passed over, and one naming nobody, or no agent of the
world, is refused. The catalogue is closed and, for a planner, `scope_actions` writes the scopes. A
store that already holds a catalogue is a volume the agent
has lived in: every graph a document put in and nobody owns is forgotten and read again, with the
closure, which is how an updated ontology or rule set reaches an agent that has lived; the graphs
the agent owns are left as they are, since they are its beliefs now — the self graph among them, so
a role declared after birth reaches only a fresh volume.

**A package's part is created, linked and started.** Every package the agent loads — each a
declared role calls for, and each transport a loaded role needs — that has a `create` module makes a
[part](/domain/kernel/part.md) of the runtime; when all exist, each links to the others, connecting
its [signals](/domain/kernel/signal.md) to what lies beneath it; then each starts and says what it
does: belief revises what is written, planning plans every pass, execution walks what is due and
whenever the deliberator revises, a transport listens or polls, sensing asks every minute what has
fallen due, prediction answers every observation written. The runtime offers `submit` a job from any
thread, `every` so many seconds of the one timeline, `on` a kind of graph written — a signal it
owns, beside a pass — `hold` and `release` the agent, `again`, and `lap`, a part of the pass; it runs
every job and handler on its one thread, knows no package's words, keeps the parts in `parts` and
stops them last-first. Where the environment names a series store it creates the part that writes
it too, metrics or history, last, so it hears every other part
([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md))
([a-package-starts-itself](/decisions/a-package-starts-itself.md),
[planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)).
A transport package is created only where the process is told to connect; a test hands a member it
brought up.

**`run` is a loop of passes, and it stops when nobody holds the agent.** A pass drains the packages'
jobs — what was queued and what their writes set off — then what is due: the
[planner](/domain/planning/planner.md)'s pass, which publishes its plans for the
[executor](/domain/execution/executor.md) to adopt, then the executor's walk, which for a fictive action
is the whole plan and for a real one is up to the first landing the world has not answered. A
transport holds the agent, since what it senses goes on arriving: the terrace, which wants nothing,
watches for good. Planning holds it while a desire is held or a want stands. A [desire](/domain/planning/desire.md) is universal, so an agent holding one is never done: a
pass with nothing to do waits for the world to move, and so does one whose wants nothing
reaches, since the world may yet open a way. A want is one-shot: a pass that weighs one met in
the present ground withdraws it, from the planner's imaginaria and from the beliefs, where a want
a world authored lives. So an agent holding wants and no desire — the courier, the tower's mover —
exits `met` once every want is reached and no intention walks. An agent that is a planner and no
executor walks nothing, so a plan it publishes is as far as a want goes:
[Hanoi](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md)'s mover exits `planned` once
every want standing has a plan published, which `walking` would otherwise count as walked for ever
— planning knows nothing will walk it because its part found no executor's to link to (#928).
`planned` exits nought, as `met` does: the agent did all it was declared for. Wants standing with
nothing walking or planned is
one of two things, told apart by the plan's `planning:outcome`: a search the budget cut short,
`planning:Exhausted`, which the next pass continues, or nothing this agent holds reaching the
want, which such an agent exits as unreachable rather than looping on.

**A sensed world runs through its transport.** Where a loaded role needs the member — a speaker
listens to a topic, or a sensor of an observer's publishes on one — the
[transport](/domain/transport/transport.md) is imported and the runtime brings the member up from the environment and
starts it: a message arrives on the member's thread and is submitted, and each pass drains it on
the one executing thread — [sensing](/domain/sensing/sensing.md) writes the observation, the
[deliberator](/domain/belief/deliberator.md) runs the rules that conclude its side, the
[prediction](/domain/prediction/prediction.md) package writes the stretches ahead and the rules conclude
theirs — each hearing the graph written, where its package was loaded. A step whose action's
implementation holds an `execution:Command` is taken by handing what the command answers, sized from
the present, to the transport reaching the device; the [greenhouse](/domain/kernel/domain.md)'s pump
and heater are taken so.

**A world's tests live with the world.** `world/hanoi/tests/` boots the world from the files
beside it and runs it to `planned`, held to the plan; `world/courier/tests/` runs its world to met.
