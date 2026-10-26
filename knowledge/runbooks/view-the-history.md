---
type: Runbook
title: View the history
description: >-
  How to draw a world's history from what its agents kept - orexis-history over their journals and observations,
  into one page with a scrubber, or live on the host's loopback, following the run as it goes - a pane per agent drawn
  by each domain's scene and each package's layer from the rows their SPARQL selects answer. What it shows is what
  each agent believed and did, never the world's truth.
---

# What this is

`orexis-history` reads every agent's journal and observations and writes one HTML page, the history view: the instants they hold on a
scrubber, a scene with every agent shown on it, or a pane per agent, and beside it what each agent did
([history view](/domain/onboarding/history-view.md)). It is what the agents kept, drawn, and never a belief
([the-journal-is-the-agents-flight-recorder](/decisions/the-journal-is-the-agents-flight-recorder.md)), so nothing runs
it inside an agent and nothing it shows reaches a plan.

# Against a running world

```bash
orexis-history lane --since 1h --out lane.history.html
```

Each agent's journal is asked at the endpoint the installation allocated it, `onboarding:journal` in
`infra/installation.derived.ttl`, on the host's loopback; its observations are read from its history bucket with the
admin token in `infra/secrets/`, as `orexis-explain` reads them ([reflect](/runbooks/reflect.md)). `--since` is a Flux
duration or an RFC 3339 instant; everything held where it is not given. An agent whose endpoint answers nothing is
said in the log and left out.

# Live

```bash
orexis-history lane --live --window 10m
```

serves the page at `http://127.0.0.1:8765/`, holding the last ten minutes, and asks the agents again every few seconds;
it follows the latest instant while *live* is ticked, and stays where it is put when the scrubber moves back.

# After an agent stopped

A stopped agent's journal is read off its volume, opened read-only — safe, since nothing writes it any more:

```bash
podman volume inspect orexis-lane-courier_a-journal --format '{{.Mountpoint}}'
orexis-history lane --journal courier_a=<that mountpoint> --out lane.history.html
```

What came before an incident is there whatever the window: the log records of the window before a step that did not
land, an intention failed, a want nothing reaches, or a warning, are kept beside it
([journal](/domain/kernel/journal.md)). Ask for them directly at the endpoint:

```bash
curl -s http://127.0.0.1:7885/sparql --data-urlencode 'query=
  PREFIX orexis: <http://example.org/orexis#> PREFIX prov: <http://www.w3.org/ns/prov#>
  SELECT ?t ?level ?m WHERE { ?r orexis:keptBy ?i ; prov:atTime ?t ; orexis:level ?level ; orexis:message ?m } ORDER BY ?t'
```

# Over a walk

A world's test installs a journal and a recorder for each agent before it boots them, and draws the two:

```python
from agent.journal import Journal, install as keep
from agent.series import HISTORY, install
from onboarding.history import data, drawings, queries, recorder, recording, run_of

for agent in ("courier_a", "courier_b"):
    keep(journals[agent], agent)                     # each agent's events, in a store in memory
    install(HISTORY, recorder(path, agent), agent)   # each agent's observations to one file, a JSON line each
...
drawn = data("lane", run_of(reading.world(LANE), {a: j.store for a, j in journals.items()}, recording(path)),
             queries(drawings(LANE)))
```

`world/lane/tests/test_history.py` walks the head-on meeting that way and holds the history view to it, rendering a pane with
the page's own components under Node (`onboarding.history.headless`): each courier sees the other where the other is
fixed, and both agree who won the draw.

# Drawing a domain or a package

A domain draws its world in a `ui/` folder beside its documents, a package what it decided in one beside its
`events.py`: `ui/index.tsx`, its components, and beside them the selects they read, `ui/<Query>.rq`. The page gathers the scene of every domain
the world imports, the world's own, and every package's layer. Each is a module of Preact components in TSX,
exporting what the contract in `onboarding/history/core/index.ts` says, imported as `@orexis/ui`:

```sparql
# agent/coordination/ui/Concluded.rq
SELECT ?e ?at ?c ?peer ?standing WHERE { GRAPH ?e {
  ?e a coordination:Concluded ; prov:atTime ?at .
  OPTIONAL { ?e coordination:conflict ?c . ?c coordination:with ?peer ; coordination:standing ?standing } } }
```

```tsx
import type { StatusProps } from "@orexis/ui";
import { latest, local } from "@orexis/ui";

function Conflicts({ agent, of }: StatusProps) {
  const last = latest(of("Concluded"), () => "all").get("all");
  const now = of("Concluded").filter(r => r.v.e === last?.v.e && r.v.standing === true);
  return <span>{agent}: {now.map(c => `conflict with ${local(c.v.peer)}`).join(", ") || "none"}</span>;
}
```

`of(query)` is an agent's rows of one query up to the instant shown, each binding what the select projects — an IRI
as its text, a number, a boolean. A select reads an event within its own graph, `GRAPH ?e`, since every event copies
the nodes it is about, and what the world states outside it. A value a thing holds under a predicate the drawing does
not name — a parameter of a step, the key of a constraint — is a `?key` and its `?value` per row, and `pivot` makes
them one record by local name, which is what `place` takes. A scene exports `scene: Scene` — a `frame` measuring every
row of the whole run once and answering `place`, and the `Scene` drawn under every layer.

The toolchain is `npm ci` at the repository's root, once: Preact, esbuild, which bundles the drawings into the page,
and TypeScript, which `npm run check` and the tests hold every drawing to. No agent loads any of it.

# Many agents

The page shows the first four agents at first; the chips pick others — filtered by name, all or none — and *side by
side* gives each a pane of its own, to compare what two believed. The log holds the last 300 lines of the agents
shown, filtered by text. A sensor's reading the same as the one before it on its series is left out before it is
loaded, and every query's variables are said once in the page, a row its values in that order. `--since` and
`--until` take a stretch of a longer run.

# Reading the page

The arrow keys step an instant; Play steps one every half second. Everything is drawn in the colour of the agent
whose journal or observations said it. On the courier's road, a filled circle is a van as its agent fixed it and an
outlined square a contact as seen; the path is the plan's steps not yet taken and an outlined cell the step in
flight; a solid cell is what the agent asked with, a dashed one what a peer said, a dotted one what the agent foresaw
of a silent peer — bright while the holding's period holds, faint before it. Each agent's conflicts are said under the
scene.
