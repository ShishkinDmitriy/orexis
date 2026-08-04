---
type: Runbook
title: Run a world
description: Deploy, up, down, logs, and what to do after a code change. One container per agent, generated from the world — with ordinary compose verbs and no wrapper commands.
tags: [deploy, compose, podman, containers, operations]
timestamp: 2026-08-04T00:00:00Z
---

# The shape of it

```
agora-acl <world>       ─┐
agora-compose <world>   ─┤ produce things from the world      (agora-specific)
                         │
podman compose up -d    ─┤ run them                            (ordinary compose)
podman compose logs -f   │
podman compose down     ─┘
```

Everything after the generators is a plain compose project. There is deliberately no
`agora-up` or `agora-down` — see [runbooks](/runbooks/) on why not.

# Once, per machine

Infra first: Fuseki holds the belief base, Influx the series, Grafana the view. It is a
separate compose project from any world, and stays up across them.

```bash
cp .env.example .env
podman compose up -d          # repo root: influxdb, grafana, fuseki
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
agora-acl society             # per-agent credentials — BEFORE compose, or agents fall back to admin
agora-compose society         # writes deploy/compose.society.yml FROM genesis/society/world.ttl
```

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
podman compose -f compose.society.yml up -d      # seed runs to completion, then the agents
podman compose -f compose.society.yml logs -f    # all of them, interleaved
podman compose -f compose.society.yml logs -f agent-fern
podman compose -f compose.society.yml ps
podman compose -f compose.society.yml down       # stop and remove THIS world's containers
```

`up` is **start**, not birth: it authors nothing and may be run as often as you like. `down` is
stop. Beliefs, readings and the world survive both — see [agent](/domain/agent.md) §Lifecycle.

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

# Switching worlds

Two worlds must not run at once — both would drive the same devices on the same topics.

```bash
cd deploy
podman compose -f compose.society.yml down
agora-seed sensing && agora-acl sensing && agora-compose sensing
podman compose -f compose.sensing.yml up -d
```

Seeding a different world replaces `:world` and the beliefs graphs; the other world's beliefs
graphs are *not* cleared, they simply stop being referenced.

# No hardware?

```bash
agora-sim     # virtual subjects: dry over time, sense on their agent's interval, get watered
```

Set `AGORA_SIM_PLANTS` to **only the virtual ones** if any real board is connected. Empty means
*every subject in the world*, and the simulator will happily publish over a real board on the
same topic — it has done exactly that here, overwriting real readings with `0.0`.

# It went wrong

| symptom | cause |
|---|---|
| agent logs `no store credential — connecting as admin` | `agora-acl <world>` was not run before `agora-compose`; the mount became a directory |
| `--userns and --pod cannot be set together` | the generated `x-podman: in_pod: false` was removed or the file is stale — regenerate |
| an agent crashes once with `WorldError: knows no agent`, then recovers | store readiness, not ordering — the seeder had exited, but the replaced world graph was not yet queryable. `restart: unless-stopped` covers it. Only worrying if it does *not* recover |
| readings arrive twice | two writers. A stray host process from an earlier run, or `agora-sim` covering a real board |
| agent cannot reach the broker | the world says `ag:brokerHost "localhost"`, so the containers use `network_mode: host`. On a bridge network that address is wrong for them |
