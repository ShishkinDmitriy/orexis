---
type: Service
title: Choir
description: >-
  How capabilities contribute judgments to one another without knowing each other exists — the
  kernel puts a question to every loaded module, whoever holds an opinion answers, and the
  asker never learns who sang. Each extension point has its own way of resolving many answers
  into one, and silence is a first-class answer, distinct from judging fine. Eighteen run-time
  points, thirteen the kernel's and five a package's, with the roster below generated from what
  the code declares rather than from memory.
---

# What it is

The **choir** is the kernel's second way for capabilities to reach each other, beside
`agent.provider(family)`. The provider hands back ONE module — whoever implements an ability.
The choir collects from ALL of them — whoever holds an opinion. The asker addresses nobody: it
puts a question to every loaded module through an extension point, modules with a stake answer, and the answers are resolved into one result without the asker ever
learning who contributed.

Why it exists is a fact about stakes. Sensing knows how to look; it does not know what counts
as trouble, because trouble is a fact about a stake, and the stake belongs to whoever holds the
band — so sensing asks, and whoever can, answers. The same shape repeats wherever one
capability holds a judgment another merely needs, and it is half of what makes
[capability](/domain/capability.md)'s no-imports rule livable: the other half is the provider.

# The points

`Agent.ask(point, …)` collects every module's answer to a question and `Agent.tell(point, …)`
delivers an event, an error in one voice logged and never silencing the rest. Every point is a
TERM — an `assembly:Extension`, declared by whoever owns the question and refused if nobody does
([a-hook-is-a-term](/decisions/a-hook-is-a-term.md)) — and the MECHANISM is
[assembly](/decisions/the-assembly-is-not-the-mind.md)'s rather than the kernel's, because how
anything reaches anything is not belief, desire or intention. A module fills a point with
`@contributes(term)` on a method; an override by name inherits the term. Each RUN-TIME point also
declares **which row** answering it belongs to — `ag:row`, one of `ag:Reactive`,
`ag:Progression`, `ag:Deliberative` — because a row partitions the methods of one module, and no
directory can ([layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md)). The points about a READING
are sensing's contract (`packages/orexis-capability-sensing/choir.py`): a module joins by defining the
method, and sensing says what it is asked with and how the answers merge
([the-stake-is-sensings-want](/decisions/the-stake-is-sensings-want.md)).

## Declared by the kernel — 13

| point | row | signature | asked by | filled by |
|---|---|---|---|---|
| `beliefRevised` | Progression | `on_belief_revised(belief_term, value) -> None` | review | sensing |
| `desireUrgency` | Deliberative | `desire_urgency(desire, query, state, value=…) -> float \| None` | kernel | market, sensing |
| `desires` | Deliberative | `desires(now=…) -> list['Desire']` | kernel | market, sensing |
| `handle` | Reactive | `handle(topic, payload) -> bool` | mqtt | actuation, market, reporting, sensing |
| `notices` | Deliberative | `notices() -> list[tuple[str, str]]` | **nobody** | sensing |
| `quiet` | Reactive | `quiet() -> list[str]` | mqtt | sensing |
| `reports` | Reactive | `reports() -> dict` | reporting | actuation, mqtt, reporting, review, sensing |
| `send` | Reactive | `send(channel, payload, retain=…, not_after=…) -> bool` | kernel, reporting, sensing | mqtt |
| `series` | Reactive | `series() -> list[tuple[str, dict, dict]]` | reporting | sensing |
| `size` | Deliberative | `size(query, graph, row) -> float \| None` | kernel *(direct)* | actuation, market |
| `subscriptions` | Reactive | `subscriptions() -> list[str]` | mqtt | actuation, market, reporting, sensing |
| `sweep` | Progression | `sweep() -> int` | kernel | market |
| `take` | Progression | `take(act, desire, intention) -> bool` | kernel *(direct)* | actuation, market, sensing |

## Declared by `packages/orexis-capability-sensing/` — 4

| point | row | signature | asked by | filled by |
|---|---|---|---|---|
| `annotate` | Reactive | `annotate(subject_uri, observed_property, value) -> dict` | sensing | sensing |
| `bounds` | Reactive | `bounds(subject_uri, observed_property) -> tuple[float, float] \| None` | sensing | sensing |
| `readingRecorded` | Reactive | `on_reading_recorded(subject_uri, observed_property, value) -> None` | sensing | actuation, market, review, sensing |
| `urgency` | Reactive | `urgency(subject_uri, observed_property, value) -> float \| None` | sensing | market, sensing |

## Declared by `packages/orexis-capability-reporting/` — 1

| point | row | signature | asked by | filled by |
|---|---|---|---|---|
| `record` | Reactive | `record(value, at=…) -> None` | sensing | reporting |

**Read the table this way.** *Asked by* is the package that puts the question — it decides how
the answers merge, and it is the contract's real owner. *Answered by* is every package that
currently has an opinion, which changes as packages are added and removed and is exactly what no
asker is allowed to know. Two rows say `kernel *(direct)*`: `size` and `take` are declared points
but are NOT broadcast — the caller has already resolved WHICH module by `ag:takenBy` and
`agent.providers(family)`, and calls the method on that one.

**Two ways to answer one.** Override the base method on `Module` — `reports()`, `desires()`,
`take()` — and `Module.answer` finds it through the MRO without a decorator, which is how five
packages answer `reports`. Or decorate any method with `@contributes(TERM)`, which is what a PACKAGE's
point needs, since there is no base method to override: sensing's `readingRecorded` is answered by
four packages, each on a method called `on_reading_recorded`.

**The signature is the point's, not the mechanism's.** `Agent.ask(point, *args)` calls
`fn(*args)` straight through, so an answerer whose parameters do not match raises `TypeError`,
which `ask` logs as *could not answer* and steps over. A mismatched signature is therefore a
module quietly not participating — the contract lives in the base method's docstring for a
kernel point, and in the asking package's `choir.py` for a package's.

**`notices` is declared and asked by nobody.** The term, the base method and sensing's override
all exist; nothing calls `ask(NOTICES, …)`. The deliberator stopped asking when freshness became
a WANT rather than a noticed gap — see
[a-desire-is-a-forest-of-derived-roots](/decisions/a-desire-is-a-forest-of-derived-roots.md) —
and the point was left behind. Whether it is rewired or retired is
[#413](https://github.com/ShishkinDmitriy/orexis/issues/413).

Prose around the project often names the choir by an older five — `annotate`, `urgency`,
`notices`, `series`, `quiet` — a shorthand from before the rest joined. This table is the
roster.

# Silence is an answer, and it is not zero

Every point tells *no stake* apart from *judging fine*: `urgency` answers `None` for no opinion
and `0.0` for fine, `bounds` answers `None` rather than the only scale its module owns. That is
why the judgment points are asked about a (subject, property) pair rather than a subject — a
module handed a property it holds nothing in must be able to stay silent instead of
misjudging it.

Absence composes the same way. A module that is not loaded contributes nothing to any point, so
the missing lines are themselves a reading: this agent was never granted that ability, which is
a different fact from having had nothing to say.

# Adding a singer is nothing; adding a point is an ontology edit

A package whose module implements a point joins the choir by being loaded — no registration, no
list to append to. A new point is different: it needs a TERM in the ontology of whoever owns the
question — the kernel's for a BDI-shaped one, a package's for one in its own words — and an
asker, and it must obey the discipline the first collision taught — two points may not share a
name with different contracts. `notices()` is named for the act rather than the object because
desire already had a `gaps()` with a different contract, and the collision broke the keeper's
tick before a test caught it.

# Who asks what

[sensing](/domain/sensing.md) asks `urgency` so attention follows need, and the watchdog asks
`quiet` on its own clock; announcements carry whatever `annotate` gathered, which is what makes
them the agent's rather than sensing's; [gap](/domain/gap.md) explains why noticing is
collective while deciding stays singular — though nothing asks `notices` today; a
crossing-watching board is told the `bounds` intersection; and the reporting tick flushes
`series` and `reports` in one write.
