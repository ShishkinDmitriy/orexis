---
type: Decision
title: A class is timeless and a graph is not — validity belongs to the named graph
status: accepted
timestamp: 2026-09-10T18:00:00Z
description: >-
  The sovereign's proposal, weighed and adopted in one place first. What a class IS does not
  change; what changes is how long anything an agent SAYS is worth believing, so validity is a
  property of the named graph a thing is said in and never of the triple. Four horizons are
  ad-hoc today — a reading's staleness, a round's close, a venue's cooldown, and a possible
  world's instant — and a graph with an interval is one mechanism for all of them, plus the one
  that has no mechanism at all: a forecast is facts valid over a FUTURE interval. Refused —
  timestamping triples, a validity filter inside rules, and a big-bang retrofit ahead of the
  measurement.
---

# The claim

**A class is not temporal. Knowledge about instances is.** `sosa:Observation` does not become
less true at four o'clock; the reading an agent holds does stop being worth acting on. So the
place to say *how long this is worth believing* is the named graph the saying lives in — one
interval per graph, said of the graph and never of a triple.

Half of it is already built, which is what makes the proposal cheap to reason about. The
vocabulary graphs are timeless and every other graph is bounded in some ad-hoc way, and a graph
already carries metadata about itself: its class, `orexis:arrivedBy`, and — for a per-agent class
— its prefix. `orexis:validFrom` and `orexis:validUntil` are the same kind of statement and need
no new plumbing.

# What it unifies

Four horizons, solved four ways, none of them wrong and none of them the same:

| what ends | how it ends today |
|---|---|
| a reading is no longer evidence | `sensing:staleSince`, written by a deadline landing on the loop (#598) |
| a round is over | the host declares it, with `closesAt` as the backstop horizon (#599) |
| a venue has cooled | `market:coolingUntil`, retracted by a deadline (#601) |
| a possible world is at an instant | the path's summed `orexis:landsAfter`, which is not identity ([#587](https://github.com/ShishkinDmitriy/orexis/issues/587)) |

And the fifth, which has no mechanism at all and is why this is worth building: **a forecast is
facts valid over a future interval.** *Rain between six and nine* is not a fact about now and
must not be read as one, and the graph it is said in is the natural place to say so.

There is a fold here that is worth noticing rather than assuming: the GROUND a possible world
stands on
([planning-branches-on-action-forecasting-on-belief](/decisions/planning-branches-on-action-forecasting-on-belief.md))
is which of the world's own branches the agent is assuming, and under this model a branch is a
graph valid over an interval the agent has not reached yet. Whether the ground IS that set of
graphs, or stays a name beside them, is a seam below rather than a claim here.

# Where the clock goes, and it must not go back

The reason to be careful is that three changes just took the clock out of every rule
deliberation evaluates ([#598](https://github.com/ShishkinDmitriy/orexis/issues/598)), and
"valid until" is a clock read wearing a new coat unless it is placed exactly.

**The door filters, never the rule.** `Store.public_graphs()` already ASKS the store which
graphs to merge and remembers the answer until a write. Validity makes that answer depend on
when it is asked — one clock read, in Python, at the one place that already decides what a query
reads. A rule still reads triples and asks nothing.

**Inside a pass it is the pass's clock.** A search that filtered graphs by the wall clock would
watch a graph expire between one fork and the next, and two worlds would differ by how long the
agent had been thinking. That is the same lesson `$lands` learned
([#588](https://github.com/ShishkinDmitriy/orexis/issues/588)): a pass reads one clock, at its
root, and everything downstream is told.

**And the memo needs a deadline.** What `public_graphs` remembers is dropped on every write; a
validity that lapses is not a write, so the sense of time arms a timer for the next lapse and
drops it then — the machinery that already exists, applied to the door.

# What is refused

- **Timestamping triples.** The obvious alternative, by reification or by an RDF-star
  annotation, and it fails on the same argument that took `NOW()` out of the rules: every reader
  becomes responsible for filtering, so every rule carries a comparison, and a rule that forgets
  one reads facts nobody believes any more. A graph is a scope a reader is HANDED; a triple is
  something a reader matches, and the difference is exactly who has to remember.
- **A validity filter inside rules.** The same thing arriving as a convention rather than a
  mechanism: `?g orexis:validUntil ?t . FILTER(?t > NOW())` in a premise is the round's
  `?closes > NOW()` again, in a costume, and `tests/test_clockless.py` would refuse it.
- **A big-bang retrofit.** One graph per reading is the proposal's sharpest form and it collides
  with an invariant that carries weight: the sensed graph holds ONE node per (subject, property),
  which every effect's `orexis:retracts` leans on and which the signature is built from. Ending
  a graph's validity is not something an effect rule can say — rules write triples into `$state`;
  they do not mint or end graphs. There is a version where the invariant survives untouched, and
  it is the one to take if readings ever move: validity *until the next observation*, which is
  non-overlapping by construction, so exactly one reading is ever valid. Refused for now is doing
  it before the mechanism has been shown to work somewhere cheaper.
- **Eager deletion of what has lapsed.** *All stale graphs can be removed* is true of the search
  and false of the agent: the trend is two readings and the interval between them, and the
  history ring is what an agent has to show for itself. Lapsing and forgetting are two decisions,
  and only the first belongs to validity.

# Order of work

**The forecast first, because it is the only case with nothing to replace.**
[#589](https://github.com/ShishkinDmitriy/orexis/issues/589) is reshaped around this: a forecast
arrives as its own graph, `orexis:Received`, valid over the interval it speaks for, and a rule
reading the world at a step's landing sees it exactly when the door says it is valid. No upsert
invariant is at risk, nothing existing is retrofitted, and the mechanism either carries a real
case or it does not.

**Then the measurement, before anything else moves.** A reading a minute is 1,440 graphs a day
per pair, and the cost of a query tracks the number of VALID graphs plus whatever the engine
charges per graph in a merge. `world/simulation`, the runbook's own bench, and the number that
matters is what `_begin` and one fork cost with tens of valid graphs against nine.

**Then, and only with those numbers, whether readings and rounds move.** If they do, three
ad-hoc horizons collapse into one mechanism and this record gets its second half. If the numbers
refuse it, the forecast keeps its own graph and the horizons stay where they are, which is a
perfectly good outcome and the reason to measure rather than to argue.

# Seams left open

- **Identity under intervals.** A node is its facts and its ground (#587). If a world becomes a
  set of graphs over an interval, identity has to say when two intervals are the same world —
  and the answer is not obvious, because a world that lasts longer is not thereby a different
  one. Nothing here decides it, and the forecast does not force it: a forecast graph is read,
  never written by a step, so it stays out of the diff exactly as the outside temperature does.
- **Whose validity.** A graph's interval is the belief of whoever holds it, so two agents with
  different clocks can disagree about whether a round's graph is valid. That is already true and
  already the honest answer — a belief about another agent is revisable, an arithmetic is not —
  but under this model the disagreement becomes visible, which is a change in what an agent can
  be asked about itself.
- **Retention.** How long a lapsed graph is kept before it is forgotten is a policy nobody has
  had to state, because nothing lapses today. It belongs beside the history ring's bound.
- **A graph valid in the past.** History is exactly that, and it is currently a ring of diffs
  rather than graphs. Whether the two are one thing is a question this record deliberately does
  not open.
