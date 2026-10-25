---
type: Runbook
title: Replay a run
description: >-
  How to draw a world's run from its agents' history - orexis-replay over the history buckets with the
  admin-side token, or over a recording a world's test made of a walk - into one page with a scrubber,
  a pane per agent and the views the world's domains state. What it shows is what each agent believed
  and did, never the world's truth.
---

# What this is

`orexis-replay` reads every agent's history and writes one HTML page: the instants the history holds
on a scrubber, a pane per agent for each [view](/domain/onboarding/view.md) its domains state, and
beside them what each agent did, in the history's own tags. It is the history drawn and never a belief
([a-replay-is-the-history-drawn-by-the-views-a-domain-states](/decisions/a-replay-is-the-history-drawn-by-the-views-a-domain-states.md)),
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

`world/lane/tests/test_replay.py` walks the head-on meeting that way and holds the replay to it: each
courier sees the other where the other is fixed, and both agree who won the draw. Recorded for fifty
ticks of ten seconds, the meeting is 1,329 points and a page of 177 kB.

# Reading the page

The arrow keys step an instant; Play steps one every half second. In a grid pane, a filled circle is a
thing as fixed and an outlined square one as seen; the blue path is the plan's steps not yet walked and
an outlined cell the step in flight; blue cells are what the agent asked with, orange what a peer said,
red what the agent foresaw of a silent peer — bright while the holding's period holds, faint before
it. A standing conflict is said at the pane's head.
