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
cp infra/.env.example infra/.env             # where the series store is — URL and org, no secret
cp infra/admin.env.example infra/secrets/admin.env   # the admin token. Fill it in; never committed
cd infra && podman compose up -d influxdb grafana    # the broker needs its ACL first, below
agora-keygen <world>          # that world's host + clearing signing keys, once
```

`infra/.env` holds **only** the URL and the org, because the generated compose files hand that
file to every agent container. The admin token opens every bucket and lives apart from it, read
by the infra containers and the two provisioning tools and by nothing else.

Keys are **per world**, in `world/<name>/secrets/` and gitignored. Two worlds are two
societies: the host that runs a market and the clearing authority that co-signs its vouchers
belong to that society, and must not be able to sign for another.

The MQTT broker is part of `infra/compose.yaml`, built from `infra/mosquitto/Containerfile`
with a config that listens on `0.0.0.0` — mosquitto binds loopback only without one, and every
LAN board gets `Connection refused`.

It **no longer accepts anonymous clients**, and its password and ACL files are generated from
the worlds' wiring, so at least one world must be provisioned before it will start. If the files
are missing, podman creates directories in their place and mosquitto exits reading its config.

```bash
agora-mqtt <world>            # credentials + the ACL, derived. Do this first
cd infra && podman compose up -d
ss -lntp | grep 1883          # expect 0.0.0.0:1883
```

A **host** mosquitto left over from an earlier setup will hold that port and win. Retained
cadences live in whichever broker published them, so they do not follow you across the switch —
each agent re-publishes one after its next reading.

**Reloading it does not restart it, and `agora-mqtt` does the reload itself** — so the paragraph
below is background, not a step you have to perform.

Getting a signal to the broker took two goes, and the shape of the answer is worth keeping. PID 1
in that container is a root shell (`infra/mosquitto/entrypoint.sh`) which starts mosquitto as a
child; the broker still drops to `user mosquitto` and nothing listens on the network as root.
Both halves were necessary:

- rootless podman cannot signal a container whose PID 1 is unprivileged (`send signal to pidfd:
  Permission denied`), and the kernel shields a namespace's PID 1 from `kill` inside it. Simply
  dropping `USER` from the image is **not** enough — mosquitto drops privileges itself, so PID 1
  ends up unprivileged anyway.
- while the host had mosquitto installed, the root PID 1 still could not forward the signal:
  that package ships `/etc/apparmor.d/mosquitto`, a profile bound to `/usr/sbin/mosquitto` — so
  it confined the *container's* broker too, and under `abi <abi/4.0>` a profile with no `signal`
  rules denies every signal sent to it. **Removing the host package fixes this**, and the
  difference is measurable: `podman stop` goes from 10s-then-`SIGKILL` (exit 137) to 1s and a
  clean exit 0, which is what lets mosquitto flush its persistence file instead of losing
  retained cadences.

`agora-mqtt` sends the reload from the host to that container's broker child either way — that
path works whether or not the profile is loaded, which is why it was chosen. By hand it is:

```bash
pkill -HUP -P $(podman inspect -f '{{.State.Pid}}' agora_mosquitto_1)
```

Making PID 1 a root shell fixed something else that had been wasting time: `podman stop` could
not reach an unprivileged PID 1 either, so the container wedged in `Stopping` and needed `kill -9`
on its conmon before the name could be reused. It stops cleanly now.

**One caveat, seen once and not explained.** A broker instance that had been running for hours
under repeated manual signalling stopped honouring SIGHUP: `agora-mqtt` reported a reload, the
files on disk were right, and a newly added principal was refused until the container was
restarted — at which point three reload cycles in a row worked again. If a freshly provisioned
agent is refused and everything on disk looks correct, restart the broker before looking further.
`infra/tests/test_bus_acl_runtime.py` (run with `pytest infra -q`) is what would catch this turning into a pattern. Note
also that mosquitto's `log_dest stdout` goes quiet after its first reload, so `podman logs` stops
being evidence of anything — check by connecting, not by reading the log.

# Deploy a world

```bash
agora-onboard society         # validate, then all three below

# or separately, when you want only one of them:
#   agora-influx society        # a bucket per agent, and a token that opens only it
#   agora-mqtt society          # a credential per principal, and the broker ACL, derived
#   agora-compose society       # writes world/society/compose.yaml FROM the world.ttl beside it
```

All three read the same `world.ttl` and grant exactly what its wiring implies, so adding an
agent to the world and re-running is the whole of deploying one — there is no list to keep in
step. They are idempotent: an agent that already holds a bucket and a credential keeps them.

Still no store to prepare, and **no agent and no world is disturbed** — existing containers keep
running, keep their beliefs and keep their credentials, because every grant is per principal and
nothing is re-issued that already exists. Adding a bucket restarts nothing.

**The one shared thing that must hear about it is the broker**, since one broker serves every
world and `agora-mqtt` rewrites `passwd` and `acl.conf` across all of them. Mosquitto reads both
only at startup — but `agora-mqtt` **reloads it for you**, and a reload is not a restart:
connected agents keep their sessions and nothing is interrupted. You will see it say so:

```
wrote infra/mosquitto/passwd and infra/mosquitto/acl.conf (15 principals)
reloaded agora_mosquitto_1 — connected agents kept their sessions
```

If no broker is running it says that instead, and the files are simply read when it next starts.
`--no-reload` suppresses it. Nothing else in the society is touched: **no restart, anywhere.**

A world with a **new device** in it does still mint a credential that has to be flashed into that
board before it can connect.

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

# Changing what an agent may reach

Three things you will actually want to do, on each of the two shared services. They behave
differently, and the differences are not guessable — each line below is pinned by a test in
`infra/tests/`, which is where to look if a
version upgrade changes any of it.

|  | the bus (mosquitto) | the series store (InfluxDB) |
|---|---|---|
| **grant** more | edit `world.ttl`, `agora-mqtt <w>` — reaches a connected agent that subscribed *before* the grant existed; no reconnect | `agora-influx <w>` mints the bucket and token; the agent must be recreated to be handed them |
| **revoke** | edit `world.ttl`, `agora-mqtt <w>` — delivery stops at once, and the agent is **not** disconnected | delete the token; refused on its very next request |
| **rotate** credential | `agora-mqtt <w> --rotate` — **evicts** the session it invalidates | `agora-influx <w> --rotate` — old token refused at once |

**Revoking is immediate on both, and neither needs a restart.** Mosquitto re-checks the ACL on
every *delivery*, not just at subscribe — which is also why an agent may subscribe `#` and still
receive only its own topics. Influx checks the token on every request. The bus needs its SIGHUP,
which `agora-mqtt` sends for you; the store needs nothing at all.

**Rotation is a revocation, not a re-key.** Both credentials are handed to a container as an
`env_file` when it is *created*, and the agent holds them in memory. So rotating takes that agent
off the service and does not give it the new credential — it must be recreated to pick it up:

```bash
agora-mqtt <w> --rotate && agora-influx <w> --rotate
cd world/<w> && podman compose up -d          # recreates the agents, with the new credentials
```

Which is the right shape for the emergency it exists for: rotate to *stop* an agent, recreate to
let it back. `agora-mqtt --rotate` never touches a **device** password, because that one is
flashed into a board that may not be in front of you.

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

Mosquitto used to be the exception, running as a **system** service. It is now in
`infra/compose.yaml` like everything else, so there is again only one way to run each thing —
`sudo systemctl disable --now mosquitto` if a host one survives from before.

# Sensor-only until a pump is wired

commands. Watch the supplier decide against real moisture first. When a pump is wired and

Valve *calibration* is not a deployment toggle: it lives on the valve in `world.ttl`, because
it is a fact about the hardware rather than about this installation.

# No hardware?

Not by running a simulator beside the agents — there isn't one any more, and there was no good
place to put it. A program pretending to be hardware had to be told which subjects to pretend
to be, and getting that wrong put two publishers on one topic with both readings ingested.

**A simulation is a world.** The model already says what every device is and how it is driven;
a device that is simulated is a *kind of device*, so an agent derives a simulated capability
from it exactly as it derives any other. Nothing is toggled, nothing is passed a flag, and a
world cannot disagree with how it is actually running.

**That world does not exist yet** — the capability and its binding are unbuilt, so today the
society needs real boards. See [world](/domain/world.md) §Simulation.

# It went wrong

| symptom | cause |
|---|---|
| agent refuses to start, `BeliefsInvalid` | its opening beliefs do not satisfy the shapes for the capabilities the world derived for it. The report names the shape; fix `world/<name>/beliefs/<agent>.ttl` |
| agent logs `born` on every start | it is not keeping its volume — check the `agora-<world>-<agent>` volume is mounted at `/app/state` |
| `--userns and --pod cannot be set together` | the generated `x-podman: in_pod: false` was removed or the file is stale — regenerate |
| cannot read an agent's belief base from outside | by design: the store is exclusively locked by its owner, and nothing else can open it |
| agent cannot reach the broker | the world says `ag:brokerHost "localhost"`, so the containers use `network_mode: host`. On a bridge network that address is wrong for them |
