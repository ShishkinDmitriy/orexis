---
type: Component
title: Choir
description: >-
  How capabilities contribute judgments to one another without knowing each other exists — the
  kernel puts a question to every loaded module, whoever holds an opinion answers, and the
  asker never learns who sang. Eight hooks on Module, each with its own way of resolving many
  answers into one; silence is a first-class answer, distinct from judging fine.
---

# What it is

The **choir** is the kernel's second way for capabilities to reach each other, beside
`agent.provider(family)`. The provider hands back ONE module — whoever implements an ability.
The choir collects from ALL of them — whoever holds an opinion. The asker addresses nobody: it
puts a question to every loaded module through a hook on `agent/module.py`'s `Module`, modules
with a stake answer, and the answers are resolved into one result without the asker ever
learning who contributed.

Why it exists is a fact about stakes. Sensing knows how to look; it does not know what counts
as trouble, because trouble is a fact about a stake, and the stake belongs to whoever holds the
band — so sensing asks, and whoever can, answers. The same shape repeats wherever one
capability holds a judgment another merely needs, and it is half of what makes
[capability](/domain/capability.md)'s no-imports rule livable: the other half is the provider.

# The hooks

The kernel owns the MECHANISM — `Agent.ask(hook, …)` collects every module's answer to a
question and `Agent.tell(hook, …)` delivers an event, an error in one voice logged and never
silencing the rest — and defines by name only the BDI-shaped hooks. The hooks about a READING
are sensing's contract (`packages/capability/sensing/choir.py`): a module joins by defining the
method, and sensing says what it is asked with and how the answers merge
([the-stake-is-sensings-want](/decisions/the-stake-is-sensings-want.md)).

| hook | the question | resolved by |
|---|---|---|
| `annotate` | what do you add to my public announcement about this reading? | merged dict (sensing's) |
| `urgency` | how close does this reading put you to your own trouble? | max of the answers (sensing's) |
| `bounds` | where do you want this property held? | intersection — highest floor, lowest ceiling (sensing's) |
| `on_reading_recorded` | something new is known — told, not asked | every listener (sensing's) |
| `desires` | what do you contribute to what the agent pursues? | ranked together by `agent.pursuing()`, one want per node |
| `desire_urgency` | how urgent is this want, in this world? | first opinion |
| `size` | how big would the act this row commits to be? | the taker's answer |
| `take` | carry this committed row out | any True |
| `subscriptions` / `handle` / `send` | which channels do you need; take this message; carry this out to the society | the [transport](/domain/transport.md)'s — asked by the module that holds the connection |
| `notices` | which pairs are unknown or too stale to act on? | concatenated for the deliberator |
| `quiet` | what did you expect to hear and have stopped hearing? | a set of log lines |
| `series` | which tagged rows go to the agent's own bucket? | concatenated, one writer |
| `reports` | which fields go on the agent's health point? | merged dict |

Prose around the project often names the choir by an older five — `annotate`, `urgency`,
`notices`, `series`, `quiet` — a shorthand from before the rest joined. This table is the
roster.

# Silence is an answer, and it is not zero

Every hook tells *no stake* apart from *judging fine*: `urgency` answers `None` for no opinion
and `0.0` for fine, `bounds` answers `None` rather than the only scale its module owns. That is
why the judgment hooks are asked about a (subject, property) pair rather than a subject — a
module handed a property it holds nothing in must be able to stay silent instead of
misjudging it.

Absence composes the same way. A module that is not loaded contributes nothing to any hook, so
the missing lines are themselves a reading: this agent was never granted that ability, which is
a different fact from having had nothing to say.

# Adding a singer is nothing; adding a hook is a kernel edit

A package whose module implements a hook joins the choir by being loaded — no registration, no
list to append to. A new hook is different: it needs an asker — the kernel's, for a BDI-shaped
question, or a package's through `Agent.ask` for one in its own words — and it must obey the discipline the first collision taught — two hooks may not share a
name with different contracts. `notices()` is named for the act rather than the object because
desire already had a `gaps()` with a different contract, and the collision broke the keeper's
tick before a test caught it.

# Who asks what

[sensing](/domain/sensing.md) asks `urgency` so attention follows need, and the watchdog asks
`quiet` on its own clock; announcements carry whatever `annotate` gathered, which is what makes
them the agent's rather than sensing's; the deliberator turns `notices` into moves and
[gap](/domain/gap.md) explains why noticing is collective while deciding stays singular; a
crossing-watching board is told the `bounds` intersection; and the reporting tick flushes
`series` and `reports` in one write.
