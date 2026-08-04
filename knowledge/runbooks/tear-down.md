---
type: Runbook
title: Tear down — and why `down` is not "kill all"
description: A society lives in four places with four different lifetimes, and compose down addresses exactly one of them. What survives it, why each thing survives on purpose, and how to remove each in turn.
tags: [operations, teardown, compose, mqtt, cleanup]
timestamp: 2026-08-04T00:00:00Z
---

# Why this needs a page at all

`podman compose down` is not "stop agora". It removes the containers **that one compose file
declares**, and nothing else — which is correct behaviour, and still surprising, because a
society is not only its processes.

Measured on a running system, immediately after `down` on a world:

| | after `down` | why it survives |
|---|---|---|
| that world's agent containers | **gone** | what `down` is for |
| infra (Influx, Grafana) | **still up** | a separate compose project, shared across worlds |
| each agent's belief base | **intact** | a named volume per agent; beliefs outlive any process, which is the point |
| retained MQTT commands | **all four still standing** | they live in the broker, which is not in compose at all |

Every one of those is deliberate. `down` is not incomplete — the society simply spans more than
a compose project, and each layer has a lifetime the others do not.

# The one that actually bites

```
sensors/bench/cmd {"sleep_s": 10}
```

`bench` was removed from every world. The broker is still holding a standing instruction for
it, because a retained MQTT message belongs to the **broker**, not to any agent, world, or
container. Flash a board as `bench` and it will obey a cadence set by an agent that no longer
exists, from a world that no longer exists.

That is the honest reason `down` cannot be "kill all": a retained message is the one piece of a
society deliberately designed to outlive the agent that published it — it is what lets a
sleeping board receive an interval it was not awake for. The same property makes it survive the
agent's removal.

# Stop one world

```bash
cd deploy
podman compose -f world/society/compose.yaml down
```

Agents stop. Beliefs, readings, the world and any retained commands are untouched — this is
"pause", and starting again continues exactly where it left off.

# Stop everything that is running

In this order, because each layer is independent:

```bash
# 1. every world (each is its own compose project)
cd deploy
for w in ../world/*/; do (cd "$w" && podman compose down); done

# 2. host processes — compose never knew about these
pkill -f "agora.runtime|agora-agent"

# 3. infra, if you want the belief base and dashboards down too
cd .. && podman compose down
```

**Step 2 is the one people skip, and it has cost real time here twice** — once a leaked
killed supervisor doubling every write. A container is removed deterministically; a host
process is not. That is half the argument for deploying agents as containers at all.

Check nothing is left:

```bash
podman ps
pgrep -af agora | grep -v conmon
```

# Clear standing instructions on the broker

Only when you want devices to stop acting on a world that is gone. Publishing an empty retained
message deletes the retention:

```bash
mosquitto_pub -h localhost -r -n -t sensors/bench/cmd     # one topic
```

```bash
# everything the broker is holding under sensors/
mosquitto_sub -h localhost -t 'sensors/+/cmd' -v -W 2 --retained-only 2>/dev/null \
  | cut -d' ' -f1 | sort -u \
  | xargs -r -I{} mosquitto_pub -h localhost -r -n -t {}
```

Do **not** do this while a world is running: you would delete the cadence its agents just set,
and every board would fall back to its firmware default until the next reading round-trips.

# Remove a belief base

Rarely what you want. Beliefs are the agent's, and discarding them is a re-birth: the agent
comes back as whatever the sovereign last authored, having forgotten anything it revised.

```bash
cd deploy
podman compose -f compose.yaml down -v   # destroys THAT world's agents' belief bases
cd .. && podman compose down -v                 # repo root: destroys the Influx history
```

`-v` is not reversible. Per world it discards who those agents became — a re-birth by another
name — and at the root it takes every reading with it.

There is no shared graph store to remove: the world is files, and an agent's belief base is a
volume belonging to that agent alone.

# What to reach for

| you want | do |
|---|---|
| pause a society | `compose -f compose.yaml down` |
| swap worlds | `down`, re-seed, `agora-compose`, `up` — see [run-a-world](/runbooks/run-a-world.md) |
| stop everything | all worlds down, then `pkill`, then infra down |
| a device is obeying a world that is gone | clear its retained `cmd` topic |
| start completely fresh | the above, then `podman compose down -v`, then genesis from scratch |
