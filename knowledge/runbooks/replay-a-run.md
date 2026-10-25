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
a pane with the page's own scripts under Node (`onboarding.replay.headless`): each courier sees the other
where the other is fixed, and both agree who won the draw. Recorded for fifty ticks of ten seconds, the
meeting is 1,329 points.

# Drawing a domain or a package

A domain draws its world in a `replay.js` beside its documents, a package what it decided in one beside
its `events.py`; the page gathers the scene of every domain the world imports, the world's own, and every
package's layer. Each is a plain script registering a Preact component written with `htm`:

```js
replay.scene("road", { label, frame(points, things) { return { width, height, place(values) }; }, Scene });
replay.layer("coordination", { order, Layer, describe: { Holding: group => [...lines] } });
```

`place` takes the values a point carries in the domain's own words and answers where they put it, so a
layer draws on any scene without a word of its domain. Nothing is built: the vendored Preact and `htm`
are inlined into the page beside the drawings.

# Reading the page

The arrow keys step an instant; Play steps one every half second. On the courier's road, a filled circle is a
van as fixed and an outlined square a contact as seen; the blue path is the plan's steps not yet walked and
an outlined cell the step in flight; blue cells are what the agent asked with, orange what a peer said,
red what the agent foresaw of a silent peer — bright while the holding's period holds, faint before
it. A standing conflict is said at the pane's foot.
