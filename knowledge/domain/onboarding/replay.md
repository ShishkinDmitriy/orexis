---
type: Domain Concept
title: Replay
description: >-
  A world's run drawn from its agents' history, every agent side by side at every instant - a core naming no
  package's word, a scene each domain draws of its world, and a layer each package draws of what it decided, each a
  replay.js beside the code or documents it draws. Never a belief.
---

# What it is

A **replay** is one page `orexis-replay` writes from every agent's [series](/domain/kernel/series.md) — its history
buckets, or a recording a world's test made of a walk ([replay-a-run](/runbooks/replay-a-run.md)). It shows what each
agent believed and did, so two panes disagreeing about where a van stands is something a replay shows and does not
settle; it reads no belief and opens no volume.

It is three parts, and only the first is the tool's:

- **The core** (`onboarding/replay/core.js`) — the instants on a scrubber, a pane per agent for each scene, and each
  agent's log, a line per thing it did. It names no package's word; a measurement nobody describes is said as its
  tags and fields.
- **A scene** — a domain's picture of its world, the ground everything else stands on: `domains/courier/replay.js`
  draws the road as a grid, each van where its fix puts it and each contact where its offsets put it from the van
  carrying it. It is handed what the world states of the things the history names, and answers `place`: where the
  values a point carries put it on the scene.
- **A layer** — a package's drawing of what it decided, on whatever scene there is, put where `place` says:
  coordination's holdings and conflicts, planning's path, execution's step in flight, each in `agent/<package>/replay.js`
  beside the events that write the points it draws.

A scene and a layer each register with the core (`replay.scene`, `replay.layer`) as Preact components written with
`htm`, and each may say how its measurements read in the log (`replay.describe`). The package that decides a thing
draws it ([a-replay-is-the-history-drawn-by-the-package-that-decides-it](/decisions/a-replay-is-the-history-drawn-by-the-package-that-decides-it.md)):
a world whose domains draw no scene is the core and its log alone.
