---
type: Runbook
title: Run a world
description: Deploy, up, down, logs, and what to do after a code change. One container per agent, generated from the world — with ordinary compose verbs and no wrapper commands.
---

# The shape of it

```
orexis-compose <world>   ─┤ produce things from the world      (orexis-specific)
                         │
podman compose up -d    ─┤ run them                            (ordinary compose)
podman compose logs -f   │
podman compose down     ─┘
```

Everything after the generators is a plain compose project. There is deliberately no
`orexis-up` or `orexis-down` — see [runbooks](/runbooks/) on why not.

# Once, per machine

Infra first: Influx holds the series, Grafana the view. There is **no triplestore** — an
agent's belief base lives inside that agent. Infra is a separate compose project from any
world and stays up across them.

```bash
cp infra/admin.env.example infra/secrets/admin.env   # the admin token. Fill it in; never committed
cd infra && podman compose up -d influxdb grafana    # the broker needs its ACL first, below
```

Where the series store is — its URL and org — and where a broker's ports are allocated from are
stated in `infra/installation.ttl`, which says nothing secret; `infra/compose.yaml` is
generated from it (`orexis-infra-compose`), and each world's compose file hands every agent the
URL and org as environment. The admin token opens every bucket and lives apart from both, read by
the infra containers and the two provisioning tools and by nothing else.

An agent's credentials are **per world**, in `world/<name>/secrets/` and gitignored, and nothing
is signed in 0.2.0: the broker's ACL admits an agent only to its own topics.

**The MQTT broker is a world's, not the installation's**: one per world, in `world/<name>/compose.yaml`,
on the ports the world asserts in its `deployment.ttl` or the installation allocates it
(`infra/installation.derived.ttl`), built from `infra/mosquitto/Containerfile` with a config that
listens on `0.0.0.0` — mosquitto binds loopback only without one, and every LAN board gets
`Connection refused`.

It **accepts no anonymous clients**, and its password, ACL and config files are generated into
`world/<name>/mosquitto/` from that world's wiring, so the world must be onboarded before its broker
will start. If the files are missing, podman creates directories in their place and mosquitto exits
reading its config.

```bash
orexis-mqtt <world>                 # credentials + the ACL, derived. Do this first
cd world/<world> && podman compose up -d
ss -lntp | grep 18                  # expect 0.0.0.0:<the world's port>, 1890 for the allotment
```

A **host** mosquitto left over from an earlier setup will hold that port and win. Retained
cadences live in whichever broker published them, so they do not follow you across the switch —
each agent re-publishes one after its next reading.

**Reloading it does not restart it, and `orexis-mqtt` does the reload itself** — so the paragraph
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

`orexis-mqtt` sends the reload from the host to that container's broker child either way — that
path works whether or not the profile is loaded, which is why it was chosen. By hand it is:

```bash
pkill -HUP -P $(podman inspect -f '{{.State.Pid}}' orexis-<world>_mosquitto_1)
```

Making PID 1 a root shell fixed something else that had been wasting time: `podman stop` could
not reach an unprivileged PID 1 either, so the container wedged in `Stopping` and needed `kill -9`
on its conmon before the name could be reused. It stops cleanly now.

**One caveat, seen once and not explained.** A broker instance that had been running for hours
under repeated manual signalling stopped honouring SIGHUP: `orexis-mqtt` reported a reload, the
files on disk were right, and a newly added principal was refused until the container was
restarted — at which point three reload cycles in a row worked again. If a freshly provisioned
agent is refused and everything on disk looks correct, restart the broker before looking further.
`infra/tests/test_bus_acl_runtime.py` (run with `pytest infra -q`) is what would catch this turning into a pattern. Note
also that mosquitto's `log_dest stdout` goes quiet after its first reload, so `podman logs` stops
being evidence of anything — check by connecting, not by reading the log.

# Deploy a world

```bash
orexis-onboard greenhouse      # all four below, each where the world has what it serves

# or separately, when you want only one of them:
#   orexis-influx greenhouse     # a history bucket per agent, a metrics one where monitored, each with a token that opens only it
#   orexis-mqtt greenhouse       # a credential per principal, and the broker ACL, derived — where the world has a bus
#   orexis-compose greenhouse    # writes world/greenhouse/compose.yaml from the world beside it
#   orexis-dashboards greenhouse # a Grafana folder for the world
```

All four read the world as an agent boots it and grant exactly what its wiring implies, so adding an
agent to the world and re-running is the whole of deploying one — there is no list to keep in
step. They are idempotent: an agent that already holds a bucket and a credential keeps them.

A world with no bus — hanoi, the courier, the tower, the dispatcher, the driver — is onboarded the same way. It
has no broker, so `orexis-onboard` skips the MQTT step and says so in one line, and its compose file
is its agents alone, each with its history credential; `orexis-influx <world>` is the one thing to
run before `podman compose up`. **One that holds only wants finishes, and stays finished:** such a
world's agent holds wants and no desire and no transport reaches it, so it exits when they are reached — 0, or 1 when
nothing it holds reaches one — and its service says `restart: "no"`, so the container stays
exited. `orexis-compose` decides that per agent ([onboarding](/domain/onboarding/onboarding.md));
under `unless-stopped`, as before, it was started again on its lived-in volume, found nothing
left and exited after one pass (measured on hanoi, about a second), over and over. Bringing it
up again does the same once: the wants it reached are gone from its volume.

Still no store to prepare, and **no agent and no world is disturbed** — existing containers keep
running, keep their beliefs and keep their credentials, because every grant is per principal and
nothing is re-issued that already exists. Adding a bucket restarts nothing.

**The one running thing that must hear about it is the world's broker**, since `orexis-mqtt`
rewrites its `passwd` and `acl.conf`. Mosquitto reads both only at startup — but `orexis-mqtt`
**reloads it for you**, and a reload is not a restart: connected agents keep their sessions and
nothing is interrupted. You will see it say so:

```
wrote world/allotment/mosquitto/passwd and world/allotment/mosquitto/acl.conf (4 principals)
reloaded orexis-allotment_mosquitto_1 — connected agents kept their sessions
```

If no broker is running it says that instead, and the files are simply read when it next starts.
`--no-reload` suppresses it. Nothing else in the society is touched: **no restart, anywhere.**

A world with a **new device** in it does still mint a credential that has to be flashed into that
board before it can connect.

The compose file is **generated, never hand-edited**: one service per agent, named for its id,
plus a `simulation` service where the world marks systems `sim:simulatedBy`. Adding an agent is
adding it to the world and regenerating; a hand-edit is a second roster waiting to drift from the
documents. Each container mounts exactly one store credential per purpose — its own — and of the
world's documents the public ones and those that say they are its agent's; the simulator's, the
public ones alone.

# Monitor a world, or stop

Metrics — how each agent is doing, a point a minute — are written only by a world whose own
`deployment.ttl` says so ([deployment](/domain/onboarding/deployment.md)):

```turtle
<> onboarding:monitored true .
```

Then re-run the tools that read it, and restart the agents so they are told the metrics store:

```bash
orexis-influx greenhouse       # mints each agent a metrics bucket and a write-only token
orexis-compose greenhouse      # adds INFLUX_METRICS_* and METRICS_INTERVAL_S to each agent
orexis-dashboards greenhouse   # writes infra/grafana/dashboards/greenhouse/<package>.json, one per package that reports
cd world/greenhouse && podman compose up -d    # recreates the agents whose environment changed
```

Taking the statement out and running the same four stops it: `orexis-influx` revokes the metrics
tokens and removes their files, the compose file stops telling the agents, and the health
dashboards are removed; the bucket is left for its retention to empty. The window's length is the
installation's `onboarding:intervalSeconds`, sixty; an installation serving metrics from no store
refuses a world that asks.

# Up, down, and watch

```bash
cd world/greenhouse
podman compose up -d            # each agent builds its own belief base
podman compose logs -f          # all of them, interleaved
podman compose logs -f grower
podman compose ps
podman compose down             # stop and remove THIS world's containers
```

A world is self-contained: its topology, its agents' opening beliefs and the compose file that
runs it are one directory. There is no separate deploy tree to keep in step.

`up` is **start**, not birth. The first boot builds the agent's store from the documents; every
boot after that logs `booted from … (a volume lived in: its own graphs kept)`, reads the public
documents again and leaves the agent's own graphs alone, so a restart cannot reset what it
believes. The store lives in a named volume per agent and survives `up`, `down` and `restart`
alike — see [belief-base](/domain/belief/belief-base.md).

`down` removes only what *this* file declares. It is not a way to stop everything; for that see
[tear-down](/runbooks/tear-down.md).

# After a code change

The source trees are mounted read-only into the containers, so a restart is enough:

```bash
podman compose restart
```

Rebuild only when a **dependency** changes (`pyproject.toml`) or you added a file the
image copies rather than mounts:

```bash
podman build -t orexis:local .
podman compose up -d --force-recreate
```

# Changing what an agent may reach

Three things you will actually want to do, on each of the two shared services. They behave
differently, and the differences are not guessable — each line below is pinned by a test in
`infra/tests/`, which is where to look if a
version upgrade changes any of it.

|  | the bus (mosquitto) | the series store (InfluxDB) |
|---|---|---|
| **grant** more | edit `society.ttl`, `orexis-mqtt <w>` — reaches a connected agent that subscribed *before* the grant existed; no reconnect | `orexis-influx <w>` mints the bucket and token; the agent must be recreated to be handed them |
| **revoke** | edit `society.ttl`, `orexis-mqtt <w>` — delivery stops at once, and the agent is **not** disconnected | delete the token; refused on its very next request |
| **rotate** credential | `orexis-mqtt <w> --rotate` — **evicts** the session it invalidates | `orexis-influx <w> --rotate` — old token refused at once |

**Revoking a grant is immediate on both, and neither needs a restart.** Mosquitto re-checks the
ACL on every *delivery*, not just at subscribe — which is also why an agent may subscribe `#` and
still receive only its own topics. Influx checks the token on every request. The bus needs its
SIGHUP, which `orexis-mqtt` sends for you; the store needs nothing at all.

# Removing an agent

Take it out of the world's documents and re-run `orexis-onboard <w>`. Nothing of it is taken back
by that: the run ends by **reporting** what the world still holds that its wiring no longer
implies — its broker credential, its certificate, its series token's file, and where the admin
token is on this host its tokens and buckets in the store — each with the command that would take
it. Then say so, per service:

```bash
orexis-mqtt <w> --revoke <id>       # credential gone, ACL rebuilt and reloaded, certificate on the CRL
cd world/<w> && podman compose restart mosquitto    # the CRL is TLS material: read at start, not on SIGHUP
orexis-influx <w> --revoke <id>     # its tokens deleted; its buckets KEPT
```

The bucket stays on purpose: it is the record of what that agent observed and did while it was
here, and a removed agent's readings are still what happened. Delete it by hand with the admin
token if you mean to. `--revoke` on an agent still in the documents is an eviction for one run —
the next `orexis-onboard` grants it again, with a new certificate, and the revoked one stays on the
CRL — which is the shape for *stop this agent now, decide later*.

**Rotation is a revocation, not a re-key.** Both credentials are handed to a container as an
`env_file` when it is *created*, and the agent holds them in memory. So rotating takes that agent
off the service and does not give it the new credential — it must be recreated to pick it up:

```bash
orexis-mqtt <w> --rotate && orexis-influx <w> --rotate
cd world/<w> && podman compose up -d          # recreates the agents, with the new credentials
```

Which is the right shape for the emergency it exists for: rotate to *stop* an agent, recreate to
let it back. `orexis-mqtt --rotate` never touches a **device** password, because that one is
flashed into a board that may not be in front of you.

# Switching worlds — nothing is lost

Each world has its own dataset, so switching destroys nothing and you can switch back:

```bash
podman compose -f world/greenhouse/compose.yaml down
podman compose -f world/sensing/compose.yaml up -d
```

Nothing to seed, and nothing shared to overwrite: each agent's belief base is its own volume,
so worlds cannot touch each other at all.

**Two worlds may run at once only if their topics differ.** Two worlds naming the same topic put
two agents on it and both ingest every reading. Nothing prevents this; it is your job to know.

# Unattended, across reboots

There are no orexis services. Everything that lasts declares `restart: unless-stopped` — every
agent that does, each world's broker and simulator, and the installation's series store and
Grafana; an agent that finishes says `"no"`, and a reboot has nothing to bring back for it. So the
only thing missing after a reboot is something to start them again, and podman ships most of it:

```bash
loginctl enable-linger $USER                 # user services run without a login session
mkdir -p ~/.config/systemd/user/podman-restart.service.d
cat > ~/.config/systemd/user/podman-restart.service.d/unless-stopped.conf <<'UNIT'
[Service]
ExecStart=
ExecStart=/usr/bin/podman $LOGGING start --all --filter restart-policy=always --filter restart-policy=unless-stopped
ExecStop=
ExecStop=/usr/bin/podman $LOGGING stop --all --filter restart-policy=always --filter restart-policy=unless-stopped
UNIT
systemctl --user daemon-reload
systemctl --user enable podman-restart.service
```

**The drop-in is not optional.** The unit podman ships starts only `restart-policy=always`, and
nothing here says `always`: measured on podman 5.4.2, the shipped filter selected none of seven
containers, so the unit enabled as it stands brings back nothing. podman documents
`unless-stopped` as identical to `always`, and two filters on one key are either-or, which is what
the drop-in leans on. This page said the shipped unit brought back "every container whose policy
restarts it" until a power cut on 2026-10-03 left an installation down for two days.

What a boot will start is one read, and what a boot does can be run by hand:

```bash
podman ps -a --filter restart-policy=always --filter restart-policy=unless-stopped
systemctl --user start podman-restart.service
```

Three things follow from it being the policy that decides:

- **A world is kept down by removing it**, `podman compose down`. A container stopped with
  `podman stop` still exists and still says it lasts, so the next boot starts it.
- **A container keeps the policy it was created with.** One made before its compose file said
  `unless-stopped` is brought into line with `podman update --restart unless-stopped <name>`, or
  by `podman compose up -d`, which makes it again.
- **Bring each world up once by hand**, and the installation before it; reboots take care of
  themselves after that.

We shipped per-agent systemd units before and removed them. They ran agents as **host
processes**, which is no longer a deployment mode — and worse, a unit left enabled would put a
host agent on the same topics as its container, both ingesting every reading. That failure has
already cost time here twice; the fix was to stop having two ways to run an agent.

Mosquitto used to be the exception, running as a **system** service. It is in each world's
compose file like everything else, so there is again only one way to run each thing —
`sudo systemctl disable --now mosquitto` if a host one survives from before.

# No hardware?

**A simulation is part of a world.** The simulator (`simulation/`) is a process of its own that
reads the world as an agent boots it and plays every system marked `sim:simulatedBy` from the
world's own words — the topics, the cadence, the drying, a dose, a heating — so nothing is told
by hand which subjects to pretend to be. What it publishes is the instrument's number and not the
model's: each strays from the model's reading within the model's `sim:jitter` (one count of the
four places it publishes to, where the model states none) and is never the number published
before, since sensing says a sensor stuck whose number has not moved for `sensing:stuckAfter`
cadences, and a model nothing touches never moves (#879). The draw is seeded, so a run is
reproducible, and `tools/run-world-end-to-end.sh` fails where any agent's log says a sensor
stuck. `greenhouse` and `allotment` run whole without a board; `sensing` and `terrace` have a
real one.

# It went wrong

| symptom | cause |
|---|---|
| agent refuses to start, `DocumentRefused` | a document states no kind, claims to be the catalogue or states an arrival; states a self anywhere but once in a self graph; or a graph of an agent's own names nobody, or no agent of the world. The message names the file |
| agent refuses to start, `self graph` | its own documents hold no self graph, or two — the world authors exactly one per agent, under `beliefs/` — or its volume's self is another agent |
| agent starts, logs `declared in no role`, and exits at once | its self graph states no role beside its self, so it loads no package — or its volume was born before the world declared one, and keeps the self graph it had: a role reaches only a fresh volume. `orexis-onboard` refuses the first; the second needs the volume removed (`tear-down`) |
| `orexis-onboard` refuses, `declares its agents' roles in a way it does not bear out` | a role whose need the world lacks, a sensor reporting to an agent that is no observer, a topic listened to by no speaker, or a graph of a kind none of the agent's packages declares — each line names the agent and the reason |
| agent never logs `a volume lived in` | it is not keeping its volume — check the `orexis-<world>-<agent>` volume is mounted at `/app/state` |
| `--userns and --pod cannot be set together` | the generated `x-podman: in_pod: false` was removed or the file is stale — regenerate |
| cannot read an agent's belief base from outside | by design: the store is exclusively locked by its owner, and nothing else can open it |
| agent cannot reach the broker | the world's `mqtt4ssn:Broker` is on `localhost`, asserted in its `deployment.ttl` or allocated in `infra/installation.derived.ttl`, so the containers use `network_mode: host`. On a bridge network that address is wrong for them |
