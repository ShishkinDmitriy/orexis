---
type: Decision
title: A landing is a band, and a possible world holds over a period
description: >-
  An action declares how long after the act the world can show its change as a BAND, the least and
  the most, and a possible world holds over the period its path's bands sum to. A step carries both
  ends, the executor looks for the answer from the earliest and gives up a patience past the latest,
  and the dose declares the band it always was. A point, an expected value and a second term were
  refused. The first half of #596; the second, a world forked from the ground holding at its
  landing with the path replayed there, followed a day later, and the landing that straddles a
  boundary is what stays open.
status: accepted
timestamp: 2026-10-03T22:00:00Z
---

> **Amended 2026-10-04**, the second half: a possible world is forked from the ground holding at
> its earliest landing where that is not the ground its parent stands in, every step on the path
> replayed onto that ground in order with its own filling, and this step's effect applied last;
> and what a world reads beside its facts is what holds THROUGHOUT its period. The seam below that
> said the world was still judged at its earliest, in its parent's ground, is closed to that
> extent; what it leaves is stated in its place.

# The claim

`planning:landsAfter` was a SELECT yielding one `?seconds`, and a possible world stood at one
instant, `planning:atInstant`, its parent's plus that figure. The figure carried a lie the search
believed: a dose declared the cadence of the sensor that would show it, which is the MOST the
reading could be away, and the executor did not look for the answer before then, so a reading that
came sooner was not read; declared as nothing, the step had failed a patience later while the
reading was still nine minutes off (#870, the first symptom). One number was standing for two,
the earliest and the latest the world could show the change, and the sovereign's ruling on #596
named the shape: an action has a DURATION stated as a range, and a possible world holds over a
TIME RANGE.

So, since 2026-10-03:

- **`planning:landsAfter` yields `?least` and `?most`**, in seconds after the act. A rule that knows
  exactly binds both to one figure; a rule that declares nothing lands at once, nought twice. An
  interval is how this project says it does not know, and membership in one is crisp
  ([a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md)).
- **A possible world's row carries `dcterms:temporal`**, as a ground's does: `orexis:start` is the
  parent's start plus the least, `orexis:end` the parent's end plus the most, a ground being a point
  — the instant the search stands at, not the stretch the ground holds for. `planning:atInstant` is
  retired. The re-root moves both ends by the stretch from the match's start to the new ground's.
- **A step carries both ends**: `execution:landsAt`, the earliest, from which the executor asks the
  present whether what the step predicted holds, and `execution:notAfter`, the latest, a patience
  past which it gives up. The committed step a drift reads is believed to `notAfter` plus the
  patience, so its `answeredWithinS` is the latest landing and `landsWithinS` the earliest, which is
  what the drift's two trajectories were already dividing by.
- **The dose and the heating declare the band they are**: the next reading is due within a cadence
  of the act, nothing at the least and the cadence at the most, read off the world in SSN-System's
  words. A market act lands when its round's window closes, exactly, both ends agreeing.

# What was refused

- **A point, kept.** The status quo. It could carry only the latest honestly or the earliest, and
  the executor had been bitten by each: declared as the earliest, a step failed before the world
  could answer; declared as the latest, an answer that came sooner waited. A band costs one more
  column in a SELECT and one more triple on a row.
- **An expected value.** The middle of the band, or the cadence halved, would have let the executor
  wait one figure and the search sum one number. But an expected value is a claim about a
  distribution nobody stated, and a world standing at the expected instant is judged in a ground
  that may hold at neither end — the exact failure the bands are for. A set of possibilities is
  kept where one would be invented.
- **A second term beside `landsAfter`** — `planning:occupies`, or two SELECTs, one for the least and
  one for the most. Two texts asked over one world can disagree, and nothing would hold them to
  each other; one text binding two columns cannot. The issue's own question, whether the two
  quantities it saw — how long the act occupies its actor, and when its effect lands — are two
  terms, is answered no for now: nothing shipped occupies an actor for longer than the search's
  grain, and a term nobody reads is annotation. Occupancy returns with a plan that is a partial
  order, the seam below, where two steps overlap exactly when neither occupies what the other needs.
- **Adding a duration to an instant in the re-root.** The engine binds nothing for
  `dateTime + dayTimeDuration` at about a third of the seconds of a minute (measured on 0.5.11,
  deterministic per instant), so the re-stamp takes the stretch from each end instead, which binds
  at every one; the predecessor added, and the test that pinned it ran at an instant the engine
  happened to bind.

# Measured

- `0.5 / xsd:double(0)` binds `INF` on pyoxigraph 0.5.11 — not nothing, as the other arithmetic
  traps do. A dose landing at the least at once hands the drift `landsWithinS 0`, and a rise over no
  time is `INF`, which multiplied by an elapsed nought is not a number; the actuation drift divides
  by one second where the earliest landing is nought, standing for *at once*.
- Every regenerated snapshot differs from its predecessor by the world's row alone — the instant
  become a period — and, in the cases whose fill declares a band of one to three minutes, by the
  period's two ends drawing apart along the path and the plan's steps gaining `notAfter`.

# Seams left open

- **~~Where within its period a world is judged~~** — closed in part, 2026-10-04. A possible
  world is forked from the ground holding at its earliest landing, the path replayed there
  (`take._replayed`): the two-tank case `a_fill_lands_in_a_later_ground` reads nine where a fork
  from the present read eleven, and chains the second fill the world would have demanded. The
  predictions keep a reading's node and replace its value, which is what lets a filling naming the
  reading be replayed in a later ground. Measured against the bench, alternated in one session: two
  queries more per pass (the grounds, and the ground at an instant, each remembered), and the
  times within the session's own drift. What stays: **a landing that straddles a boundary is
  judged in the ground at its earliest alone** — one child per ground overlapped, siblings under one
  step, with the re-root picking the one the present matches, is the strong-controllability half of
  the STNU reading (Morris, Muscettola and Vidal, 2001) and the next slice of #596; and **a step's
  `execution:predicts` is still the diff against the world it leaves**, so a step landing in a
  later ground is held to the prediction's changes beside its own, which is right while the
  prediction is and the executor's verdict otherwise.
- **Ranking by lateness.** Achievers rank by cost; a want with an instant is weighed at it (#858),
  and nothing yet prefers the achiever landing by the instant, nor refuses a world past the want's
  lifting. Both are #596's, stated there.
- **A plan is a chain, not a partial order.** `execution:then` orders every step after the one
  before it, and nothing shipped has two levers that must run at once, so no step occupies its actor
  for a stretch and no two steps overlap. The day a world has two, a step's occupancy is a term and
  two steps overlap exactly when neither occupies what the other needs. That was #591, whose first
  half — a step spans an interval — this record built, and whose second has no definition of done
  until such a world exists; it closed into this seam (2026-10-04).
- **The patience is still a figure beside the band.** With a latest landing stated, the grace the
  patience added was redundant at one end and honest at the other; it stays, since an action's
  band is the world's promise and the patience the agent's tolerance beyond it, and nothing here
  measured how often the two differ.

# What it amends

[a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md), whose table of
horizons said a possible world is AT an instant: it holds OVER a period now, laid on its row as a
ground's is, and the catalogue is the one place both are read.
[a-prediction-accumulates-rates-between-happenings](/decisions/a-prediction-accumulates-rates-between-happenings.md),
whose seam *a possible world holds at an instant, not over its landing* is half closed: the world
holds over its landing; where it is judged is still that seam.
