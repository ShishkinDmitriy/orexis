---
type: Domain Concept
title: Cone
description: >-
  The possible worlds a search leaves under the present, with its weighings - kept in the
  imaginarium from pass to pass. The next pass finds the present among them by hash, re-roots the
  cone there and drops the rest; where the present matches nothing, the whole cone goes.
---

# What it is

A search forks a possible world per candidate it takes, and a world's weighing for a want says
whether it met it, whether it is still open and what it cost. Together they are a tree under the
ground the search stood in — worlds widen away from the present, hence the name
([the-future-is-a-cone-and-the-present-is-identified-in-it](/decisions/the-future-is-a-cone-and-the-present-is-identified-in-it.md)).

# Why it is kept

The [imaginarium](/domain/planning/imaginarium.md) outlives the pass, so the cone does. At the start
of the next pass `reroot` looks for the world of the last pass whose `orexis:hash` the new ground
repeats: the old present, when nothing happened; a child, when a step landed as predicted. That
world's candidates are handed to the ground, the cone's periods are re-stamped and what it spent
is rebased, and everything else is dropped. Three disks re-planned after the first move in 34 ms
against 132 fresh.

A surprise — a reading no world predicted, another agent moving — matches nothing, and the cone
goes whole. The present is identified among the imagined worlds, never asserted from one: a child
is a prediction, and only the hash of what was observed says the world landed there.
