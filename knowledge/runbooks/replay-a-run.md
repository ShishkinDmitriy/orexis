---
type: Runbook
title: Replay a run
description: >-
  How to draw a world's run from its agents' history - orexis-replay over the history buckets with the
  admin-side token, or over a recording a world's test made of a walk - into one page with a scrubber,
  a pane per agent drawn by each domain's scene and each package's layer. What it shows is what each agent believed
  and did, never the world's truth.
---

# What this is

`orexis-replay` reads every agent's history and writes one HTML page: the instants the history holds
on a scrubber, a pane per agent for each scene its domains draw, and beside them what each agent did
([replay](/domain/onboarding/replay.md)). It is the history drawn and never a belief
([a-replay-is-the-history-drawn-by-the-package-that-decides-it](/decisions/a-replay-is-the-history-drawn-by-the-package-that-decides-it.md)),
so nothing runs it inside an agent and nothing it shows reaches a plan.

# Against a live store

```bash
orexis-replay lane --since 1h --out lane.replay.html
```

It reads each agent the world states from its history bucket, with the admin token in `infra/secrets/`,
as `orexis-explain` does ([reflect](/runbooks/reflect.md)). `--since` is a Flux duration or an RFC 3339
instant; everything held where it is not given.

# Over a walk

A world's test records a walk by installing a recorder for each agent before it boots them, and replays
the file it wrote:

```python
from agent.series import HISTORY, install
from onboarding.replay import recorder

for agent in ("courier_a", "courier_b"):
    install(HISTORY, recorder(path, agent), agent)    # each agent's points to one file, a JSON line each
```

```bash
orexis-replay lane --recording head_on.jsonl --out head_on.html
```

`world/lane/tests/test_replay.py` walks the head-on meeting that way and holds the replay to it, rendering
a pane with the page's own components under Node (`onboarding.replay.headless`): each courier sees the other
where the other is fixed, and both agree who won the draw. Recorded for fifty ticks of ten seconds, the
meeting is 1,329 points, 25 instants once thinned.

# Drawing a domain or a package

A domain draws its world in a `replay.tsx` beside its documents, a package what it decided in one beside its
`events.py`; the page gathers the scene of every domain the world imports, the world's own, and every package's
layer. Each is a module of Preact components in TSX, exporting what the contract in `onboarding/replay/core/index.ts`
says, imported as `@orexis/replay`:

```tsx
import type { Layer, LayerProps } from "@orexis/replay";

function Holding({ box, tint }: { box: Place; tint: string }) { return <rect x={box.x} y={box.y} … stroke={tint} />; }

function Coordination({ of, place, tint }: LayerProps) {
  return <g>{of("Holding").map(h => { const box = place(h.fields); return box && <Holding box={box} tint={tint} />; })}</g>;
}

export const layer: Layer = { name: "coordination", order: 10, Layer: Coordination, Status: Conflicts, describe };
```

A scene exports `scene: Scene` — a `frame` measuring the whole run once and answering `place`, and the `Scene` drawn
under every layer. `of(measurement)` is an agent's points of one measurement up to the instant shown; `place` takes
the values a point carries in the domain's own words, so a layer draws on any scene without a word of its domain.

The toolchain is `npm ci` at the repository's root, once: Preact, esbuild, which bundles the drawings into the page,
and TypeScript, which `npm run check` and the tests hold every drawing to. No agent loads any of it.

# Many agents

The page shows the first four agents at first; the chips pick others — filtered by name, all or none — and *side by
side* gives each a pane of its own, to compare what two believed. The log holds the last 300 lines of the agents
shown, filtered by text. A run is thinned before it is written: a sensor's reading the same as the one before it on
its series is left out, and every point names its series by index, so its tags are said once. Measured on 30 couriers
over 200 instants, 160,000 points: a page of 5 MB, loaded in 0.7 s, a step of the scrubber 50 to 130 ms with all 30
shown. `--since` and `--until` take a stretch of a longer run.

# Reading the page

The arrow keys step an instant; Play steps one every half second. Everything is drawn in the colour of the agent
whose history said it. On the courier's road, a filled circle is a van as its agent fixed it and an outlined square
a contact as seen; the path is the plan's steps not yet walked and an outlined cell the step in flight; a solid cell
is what the agent asked with, a dashed one what a peer said, a dotted one what the agent foresaw of a silent peer —
bright while the holding's period holds, faint before it. Each agent's conflicts are said under the scene.
