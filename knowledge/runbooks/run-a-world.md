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
cd infra && podman compose up -d   # influxdb, grafana
agora-keygen <world>          # that world's host + clearing signing keys, once
```

Keys are **per world**, in `world/<name>/secrets/` and gitignored. Two worlds are two
societies: the host that runs a market and the clearing authority that co-signs its vouchers
belong to that society, and must not be able to sign for another.

The MQTT broker runs on the **host**, not in compose, and binds to loopback until told
otherwise — every LAN board gets `Connection refused` until:

```bash
sudo cp infra/mosquitto/lan.conf /etc/mosquitto/conf.d/agora.conf
sudo systemctl restart mosquitto
ss -lntp | grep 1883          # expect 0.0.0.0:1883
```

# Deploy a world

```bash
agora-compose society         # writes world/society/compose.yaml FROM the world.ttl beside it
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
cd world/society
podman compose up -d            # each agent builds its own belief base
podman compose logs -f          # all of them, interleaved
podman compose logs -f agent-fern
podman compose ps
podman compose down             # stop and remove THIS world's containers
```

A world is self-contained: its topology, its agents' opening beliefs and the compose file that
runs it are one directory. There is no separate deploy tree to keep in step.

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
podman compose restart
```

Rebuild only when a **dependency** changes (`backend/pyproject.toml`) or you added a file the
image copies rather than mounts:

```bash
podman build -t agora:local -f backend/Containerfile .
podman compose up -d --force-recreate
```

# Switching worlds — nothing is lost

Each world has its own dataset, so switching destroys nothing and you can switch back:

```bash
podman compose -f world/society/compose.yaml down
podman compose -f world/sensing/compose.yaml up -d
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

# Unattended, across reboots

There are no agora services. Every agent already declares `restart: unless-stopped`, so the
only thing missing after a reboot is something to start them again — and podman ships that:

```bash
loginctl enable-linger $USER                 # user services run without a login session
systemctl --user enable podman-restart.service
```

`podman-restart` brings back every container that has a restart policy, which is exactly the
set you want and nothing else. Bring each world up once by hand and reboots take care of
themselves.

We shipped per-agent systemd units before and removed them. They ran agents as **host
processes**, which is no longer a deployment mode — and worse, a unit left enabled would put a
host agent on the same topics as its container, both ingesting every reading. That failure has
already cost time here twice; the fix was to stop having two ways to run an agent.

Mosquitto is the exception and is a **system** service, because it is not ours:
`sudo systemctl enable --now mosquitto`.

# Sensor-only until a pump is wired

`.env` has `AGORA_ACTUATE=false` — rounds run and log the allocation, but publish **no** valve
commands. Watch the supplier decide against real moisture first. When a pump is wired and
calibrated, set `AGORA_ACTUATE=true` and restart that world.

Valve *calibration* is not a deployment toggle: it lives on the valve in `world.ttl`, because
it is a fact about the hardware rather than about this installation.

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
| agent refuses to start, `BeliefsInvalid` | its opening beliefs do not satisfy the shapes for the capabilities the world derived for it. The report names the shape; fix `world/<name>/beliefs/<agent>.ttl` |
| agent logs `born` on every start | it is not keeping its volume — check the `agora-<world>-<agent>` volume is mounted at `/app/state` |
| `--userns and --pod cannot be set together` | the generated `x-podman: in_pod: false` was removed or the file is stale — regenerate |
| cannot read an agent's belief base from outside | by design: the store is exclusively locked by its owner, and nothing else can open it |
| readings arrive twice | two writers. A stray host process from an earlier run, or `agora-sim` covering a real board |
| agent cannot reach the broker | the world says `ag:brokerHost "localhost"`, so the containers use `network_mode: host`. On a bridge network that address is wrong for them |
