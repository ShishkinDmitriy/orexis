---
type: Domain Concept
title: Pick
description: >-
  A point the agent chose inside room it did not choose — its aim, its cadences, its
  patience, its willingness to pay. Unfalsifiable by the world (only ill-chosen, never
  wrong), which is the test that sorts a pick from a belief; a want by modality, which is
  why the desire modality serves them; and the agent's own, which is what review exists to
  move. The code's shape for one capability's picks is `Picks`, declared beside the module
  that runs on them — the class this page names was called `Block` after the layout of the
  beliefs file it came from, a word that said how the file looked rather than what the
  thing is.
---

# What it is

A **pick** is a point chosen inside a range: the [aim](/domain/aim.md) inside the region, a
cadence inside the constitutional bounds, a patience, a grace, a willingness to pay.
[a-belief-is-a-pick-within-a-range](/decisions/a-belief-is-a-pick-within-a-range.md) owns the
claim — genesis writes the first pick, never a bound — and
[the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md)
owns whose it is. This page exists because the word carried two record titles and a whole
review capability before the dictionary said what it meant.

Three neighbours it is not:

- **Not a belief proper.** The world can refute a conversion — the next reading says the pot
  drains oddly — and can never refute 600 seconds of patience. Unfalsifiable is the sorting
  test [a-store-is-a-modality](/decisions/a-store-is-a-modality.md) ratified: falsifiable
  stays with belief, and every pick is a want.
- **Not the aim alone.** The aim is the one pick about the world; the rest are picks about
  the agent's own conduct. One kind, many instances.
- **Not a bound.** The room is the mandate's; the point is the agent's; and
  [review](/domain/review.md) moving the point inside the room is what "the author's job is
  to constrain well, not to guess well" means in practice.

# The code's shape

`Picks` (`packages/orexis-modality-graph/beliefs.py`): one capability's picks — the capability term, a dataclass, and
the term IRIs that fill it — declared beside the module that runs on them. Modules read them
from the desire modality, where a want belongs; the belief base keeps the RECORD of picking
(birth's first entries, review's revisions), and the desire store is recomputed from it. A
capability whose picks are missing refuses to start, naming the terms: there are no defaults,
because a fallback would be a policy decision made in code.
