---
type: Decision
title: The self is a class held to one instance, written by the boot, and a text asks for it
status: accepted
timestamp: 2026-10-08
description: >-
  Every text about the agent was handed `$me`, because nothing in the store said who the agent
  was. The boot now writes `<agent> a orexis:Self` once, in a belief graph of the agent's own, and
  a text asks `?me a orexis:Self`. Refused - a singleton IRI, a public self graph, an existing
  per-agent kind, a guard in each text, and binding each agent in turn in a world's store. The
  first half of #876.
---

# What was true (measured 2026-10-08, on main at e99731d0)

**The one identifier a process is told was threaded by hand into every text that mentioned the
agent.** 37 `$me` tokens in 14 files under `agent/`, `domains/` and `world/` — 27 of them in 21
query texts, the rest in the prose describing them: the five premises, the three readings of the
agent's sensors (the premises', the MQTT driver's, the HTTP driver's), sensing's limits, the
planner's subject, and every precondition, effect, command and saying of the actuation, climate
and market domains. 15 Python sites bound it (`me=` and a `"me"` token), and `take`, `admit`,
`command`, `says`, `limit_of`, `packages_of` and couplings' helpers took the agent as an argument
for that alone.

**Nothing in the store could have answered for it.** One agent, one volume (rule 4) makes every
agent's store hold exactly one agent that is THIS one, but no fact said which: the boot found the
agent by its `orexis:localId` and kept the IRI in Python.

# The decision

**The boot writes `<agent> a orexis:Self`, once, in an `orexis:SelfGraph` the agent owns and
recorded**, for the agent the process was told to be, before it asks any premise. A text asks
`?me a orexis:Self` and is bound nothing; `store.bind` still refuses a token nobody binds when a
text runs, and `tests/test_store.py` now refuses a `$me` written anywhere in the trees a text lives
in ([self](/domain/kernel/self.md)).

**The self is held to one at every door**, because a class does not hold itself there. A document
stating that anything is the self, or that a graph is a self graph, is refused whole by the
loader — a world's file, a peer's message through `heard`, the agent's own saying through `said`.
The boot counts every self in every graph and stops on any count but one, and on a lived-in
volume whose self is another agent.

**A graph kind of its own, beneath `orexis:BeliefGraph`.** A belief, so every text answered over
what is known reads it — a precondition in a possible world, a command over the present — and it
crosses into an imaginarium with the beliefs; not public, so the five readers of the public graphs
alone that ask the self (the premises, the two drivers' sensors, sensing's limits, the planner's
subject) state its kind beside `orexis:PublicGraph`.

# What was refused

**A singleton IRI, `orexis:self`.** It was the first thought: one well-known node every text names.
It is an instance named in code, which rule 1 refuses; it is a second name for an agent the world
already names, the synonym the dictionary refuses; and it makes two instances impossible only by
making two agents indistinguishable — a test store holding three agents' documents would merge
whatever each said of itself into one node, without a word. The class is the project's own idiom:
ask what a thing IS.

**The self graph beneath `orexis:PublicGraph`**, which would have cost no reader anything, since
every reader of a text about the agent already reads the public graphs. Public means what every
agent of a world may read; the self is true of one store and of no other, and a graph typed public
is one whose content a reader may take for the world's.

**An existing per-agent kind.** A state graph is spoken for by the grounds — copied into every
world a search forks and into its hash; a record graph says how long what it states is worth
believing; a working graph is read by its own package alone and never crosses into a possible
world. The self is none of those.

**A guard in each text** — a `LIMIT 1`, a count beside the pattern. A text asking `?me a
orexis:Self` over two selves answers rows for both, the empty-result trap's twin; guarding every
text is the same rule written twenty times. The gate stands once, at the boot, where the instance
is made.

**Binding each agent in turn where a store holds a whole world.** The operator's dashboards asked
every package's premise once per agent, `$me` bound to each; a world's store holds no self, so a
premise there is asked of every `orexis:Agent` at once (`packages_of(store, orexis:Agent)`), which is
the union the dashboards took.

**A footprint reading the self's pattern.** Kept in, `?me a orexis:Self` binds nothing over the
public graphs a filling is asked over, stands first in rdflib's order as the pattern with fewest
variables, and reorders the OPTIONAL chain: the greenhouse's dose came to be filled with the heater
and its scopes moved, measured. A footprint reads a text without it, since no public graph holds
the self and no action writes it.

# Seams left open

- **A volume lived in before the self existed** holds none, and the boot writes it for the id it
  was told; the wrong-volume refusal cannot fire on that one boot.
- **A store of several holders and no self** — a test's world — answers nothing to a text naming
  the agent, so couplings read over such a store admit nothing for those texts and couple less.
  The derivation's own `holder=` is untouched: it names whose desires and constraints a pass reads.
- **The agent's IRI still travels where a graph is WRITTEN** — the owner a write classifies with,
  the planner's and the executor's identity read by `orexis:localId`. A writer must say whose a
  graph is; that is a write target, not a text being handed the agent.
- **What the agent's own stances are, and the roles it holds**, are #876's second half, recorded
  apart.
