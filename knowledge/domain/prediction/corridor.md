---
type: Domain Concept
title: Corridor
description: >-
  The lowest and highest trajectory a predicted value may follow, where a drift knows its rate
  only as a range. Rates add as ranges do; a stretch is the corridor's worst side, so a want is
  minted at the earliest instant a value may cross.
---

# What it is

A [drift](/domain/prediction/prediction.md) that knows its rate only as a range - rain of nought to
two millimetres an hour - answers `?low` and `?high` instead of `?rate`. Ranges add as rates do,
`[a,b] + [c,d] = [a+c, b+d]`, so `predict` carries two trajectories from the observation: the LOW
one, moved by every drift's lowest rate, and the HIGH one, moved by every drift's highest. Where
every drift answers one rate the two are one line and there is no corridor to speak of.

Each trajectory asks the drifts at its own value, so a drift whose rate depends on the value sees
the value that trajectory has reached.

# Which side a stretch is

The corridor's worst, range by range: **below** where the low trajectory is under the floor,
**above** where the high one is over the ceiling, **inside** where neither is. The number written
is the low trajectory's where any range reads below and the high one's where any reads above, so
a domain's transition judges of it exactly the side the corridor has. A stretch therefore begins at the
earliest instant the value MAY cross, which is the safe side for a desire that wants it inside:
nothing is left unwatered on the strength of rain that may not come.

The width at an instant is how much the agent does not know about the value then. It is never
written: what leaves prediction is a number on a side, and the search reads the state a transition makes of it.
