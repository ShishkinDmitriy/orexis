---
type: Domain Concept
title: Replay
description: >-
  A world's run drawn from its agents' history, every agent at every instant - a core naming no package's word, a
  scene each domain draws of its world, and a layer each package draws of what it decided, each a replay.tsx beside
  the code or documents it draws, typed by the contract the core states. Never a belief.
---

# What it is

A **replay** is one page `orexis-replay` writes from every agent's [series](/domain/kernel/series.md) — its history
buckets, or a recording a world's test made of a walk ([replay-a-run](/runbooks/replay-a-run.md)). It shows what each
agent believed and did, so two agents disagreeing about where a van stands is something a replay shows and does not
settle; it reads no belief and opens no volume.

It is three parts, and only the first is the tool's:

- **The core** (`onboarding/replay/core/`) — the instants on a scrubber; the agents to show, picked from however many
  the world has, drawn together on one scene or side by side to compare; and the log of what the agents shown did. It
  names no package's word: a measurement nobody describes is said as its tags and fields. Its `index.ts` is the
  contract every drawing is held to.
- **A scene** — a domain's picture of its world, the ground everything else stands on: `domains/courier/replay.tsx`
  draws the road as a grid, each van where its fix puts it and each contact where its offsets put it from the van
  carrying it. It is handed what the world states of the things the history names, and answers `place`: where the
  values a point carries put it on the scene.
- **A layer** — a package's drawing of what it decided, on whatever scene there is, once per agent shown and in that
  agent's colour, put where `place` says: coordination's holdings, planning's path, execution's step in flight, each in
  `agent/<package>/replay.tsx` beside the events that write the points it draws. What is no place — a conflict
  standing — a layer says as a status, a line under the scene.

A scene and a layer are Preact components in TSX, exported as `scene` or `layer`, reading their points through `of`,
an agent's points of one measurement up to the instant shown; each may say how its measurements read in the log. The
package that decides a thing draws it
([a-replay-is-the-history-drawn-by-the-package-that-decides-it](/decisions/a-replay-is-the-history-drawn-by-the-package-that-decides-it.md)):
a world whose domains draw no scene is the core and its log alone.
