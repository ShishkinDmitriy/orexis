---
type: Runbook
title: Run a world
description: Deploy, up, down, logs, and what to do after a code change. One container per agent, generated from the world — with ordinary compose verbs and no wrapper commands.
tags: [deploy, compose, podman, containers, operations]
timestamp: 2026-08-04T00:00:00Z
---

# The shape of it

```
agora-compose <world>   ─┤ produce things from the world      (agora-specific)
                         │
podman compose up -d    ─┤ run them                            (ordinary compose)
podman compose logs -f   │
podman compose down     ─┘
```

Everything after the generators is a plain compose project. There is deliberately no
`agora-up` or `agora-down` — see [runbooks](/runbooks/) on why not.

# Once, per machine

Infra first: Influx holds the series, Grafana the view. There is **no triplestore** — an
agent's belief base lives inside that agent. Infra is a separate compose project from any
world and stays up across them.

```bash
cp .env.example .env
podman compose up -d          # repo root: influxdb, grafana
agora-keygen                  # host + clearing signing keys, once
```

The MQTT broker runs on the **host**, not in compose, and binds to loopback until told
otherwise — every LAN board gets `Connection refused` until:

```bash
sudo cp infra/mosquitto/lan.conf /etc/mosquitto/conf.d/agora.conf
sudo systemctl restart mosquitto
ss -lntp | grep 1883          # expect 0.0.0.0:1883
```

# Deploy a world

```bash
agora-compose society         # writes deploy/compose.society.yml FROM genesis/society/world.ttl
```

That is the whole of it. No credentials to generate, no store to prepare, no service to restart
— adding a world or an agent disturbs nothing that is already running.

```
agent-fern       Bidding, Subscribing
agent-supplier   Actuation, Hosting  +signing keys
```

The file is **generated, never hand-edited**. Adding an agent is adding it to `world.ttl` and
regenerating; a hand-edit is a second roster waiting to drift from the model. Only the agent
that derived `ag:Actuation` is given signing keys, and each container mounts exactly one store
credential — its own. That is the boundary, not packaging taste
([world](/domain/world.md) §Deployment).

# Up, down, and watch

```bash
cd deploy
podman compose -f compose.society.yml up -d      # each agent builds its own belief base
podman compose -f compose.society.yml logs -f    # all of them, interleaved
podman compose -f compose.society.yml logs -f agent-fern
podman compose -f compose.society.yml ps
podman compose -f compose.society.yml down       # stop and remove THIS world's containers
```

`up` is **start**, not birth. An agent is born the first time it runs — it writes its opening
beliefs once, and logs `born`. Every start after that refreshes the public world from the files
and leaves beliefs alone, so a restart cannot reset who an agent became. Beliefs live in a
named volume per agent and survive `up`, `down` and `restart` alike — see
[agent](/domain/agent.md) §Lifecycle.

`down` removes only what *this* file declares. It is not a way to stop everything; for that see
[tear-down](/runbooks/tear-down.md).

# After a code change

The source trees are mounted read-only into the containers, so a restart is enough:

```bash
podman compose -f compose.society.yml restart
```

Rebuild only when a **dependency** changes (`backend/pyproject.toml`) or you added a file the
image copies rather than mounts:

```bash
podman build -t agora:local -f Containerfile .
podman compose -f compose.society.yml up -d --force-recreate
```

# Switching worlds — nothing is lost

Each world has its own dataset, so switching destroys nothing and you can switch back:

```bash
cd deploy
podman compose -f compose.society.yml down
podman compose -f compose.sensing.yml up -d
```

Nothing to seed, and nothing shared to overwrite: each agent's belief base is its own volume,
so worlds cannot touch each other at all.

```bash
agora-validate society && agora-validate sensing   # checked from the files, no store needed
```

**Two worlds may run at once only if their devices differ.** `society` and `sensing` share
device ids on purpose — that is what lets one flashed board run in either — so both up
together puts two agents on `sensors/fern/moisture` and both ingest every reading. Nothing
prevents this; it is your job to know.

# No hardware?

```bash
agora-sim <world>   # virtual subjects: dry over time, sense on the agent's interval, get watered
```

Set `AGORA_SIM_PLANTS` to **only the virtual ones** if any real board is connected. Empty means
*every subject in the world*, and the simulator will happily publish over a real board on the
same topic — it has done exactly that here, overwriting real readings with `0.0`.

# It went wrong

| symptom | cause |
|---|---|
| agent refuses to start, `BeliefsInvalid` | its opening beliefs do not satisfy the shapes for the capabilities the world derived for it. The report names the shape; fix `genesis/<world>/beliefs-<agent>.ttl` |
| agent logs `born` on every start | it is not keeping its volume — check the `agora-<world>-<agent>` volume is mounted at `/app/state` |
| `--userns and --pod cannot be set together` | the generated `x-podman: in_pod: false` was removed or the file is stale — regenerate |
| cannot read an agent's belief base from outside | by design: the store is exclusively locked by its owner, and nothing else can open it |
| readings arrive twice | two writers. A stray host process from an earlier run, or `agora-sim` covering a real board |
| agent cannot reach the broker | the world says `ag:brokerHost "localhost"`, so the containers use `network_mode: host`. On a bridge network that address is wrong for them |
