---
type: Domain Concept
title: History view
description: >-
  What the agents kept, drawn, every agent at every instant - a core naming no package's word, a scene each domain
  draws of its world, and a layer each package draws of what it decided, each a ui folder beside the code or documents
  it draws, its Preact components and the SPARQL selects they read, typed by the contract the core states. Written
  after a run or followed live. Never a belief.
---

# What it is

The **history view** is the page `orexis-history` writes, or serves live, from every agent's
[journal](/domain/kernel/journal.md) and the observations its [series](/domain/kernel/series.md) holds — or the
journals and a recording a world's test made of a walk ([view-the-history](/runbooks/view-the-history.md)). Watching a
run as it goes and drawing it after are one thing: the history, drawn. It shows what each agent believed and did, so
two agents disagreeing about where a van stands is something it shows and does not settle; it reads no belief and opens
no belief volume.

**What it draws is rows.** The journals, the observations — each point made a `sosa:Observation` again — and the
world's documents are loaded into one store in memory, and every drawing's selects are run once per agent: the
agent's observations and the world as the default graph, its journal's entries named, so a select reads an event
within its own graph and what the world states around it in one pattern. A select is `ui/<Query>.rq` beside the
drawing that reads it, in the words of whoever's things it reads, and binds `?at` where its rows happen at an instant.

It is three parts, and only the first is the tool's:

- **The core** (`onboarding/history/core/`) — the instants on a scrubber; the agents to show, picked from however many
  the world has, drawn together on one scene or side by side to compare; and the log of what the agents shown did. It
  names no package's word: a query nobody describes is said as what its rows bind. Its `index.ts` is the contract
  every drawing is held to, imported as `@orexis/ui`.
- **A scene** — a domain's picture of its world, the ground everything else stands on: `domains/courier/ui/` draws
  the road as a grid, each van where its fix puts it and each contact where its offsets put it from the van carrying
  it, inside the range its sensor declares. It answers `place`: where values in the world's words, by local name, put a
  thing on the scene.
- **A layer** — a package's drawing of what it decided, once per agent shown and in that agent's colour: on the scene
  where `place` says — coordination's holdings, planning's path, execution's step in flight — and, what is no place, as
  a status under the scene — a conflict standing, the latest statement said and heard — each in `agent/<package>/ui/`
  beside the events it reads. A layer that is no place, as speech's, draws nothing on the scene.

A scene and a layer are Preact components in TSX, exported as `scene` or `layer` from `ui/index.tsx`, reading their
rows through `of`, an agent's rows of one query up to the instant shown; each may say how its rows read in the log.
The package that decides a thing draws it
([a-replay-is-the-history-drawn-by-the-package-that-decides-it](/decisions/a-replay-is-the-history-drawn-by-the-package-that-decides-it.md)):
a world whose domains draw no scene is the core and its log alone.
