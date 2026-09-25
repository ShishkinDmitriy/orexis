---
type: Runbook
title: Move a deployed world to Agent 0.2.0
description: >-
  What to type on the bench to take a running 0.1.0 world onto the 0.2.0 image, the terrace first:
  rebuild, clear what 0.1.0 generated, regenerate the broker and the dashboards, replace the belief
  volume, and bring the agent up again. The board is not touched.
---

# Before you start

The world's files are already the 0.2.0 world's, from `main`: its documents, each saying which
graph it is, and its tracked `compose.yaml`. Nothing below touches a board. The terrace's board
keeps its topic, its payload and its credential, so it goes on publishing through the switch, and
what it publishes while the agent is down is simply not read.

The history is safe where it is. The readings live in the agent's Influx bucket, which the 0.2.0
agent keeps writing to in the same shape, so the Grafana panels draw across the switch. The belief
volume is the one thing replaced: it holds a 0.1.0 belief base, which the 0.2.0 runtime would take
for one it had lived in.

# The steps

The terrace is the example; put another world's name and its agent's id in their place.

```bash
cd ~/projects/orexis && git pull
source .venv/bin/activate && pip install -e . $(ls -d packages/*/)

# 1. The image: `orexis-agent` is the 0.2.0 runtime now, and the image carries agent/ and domains/.
podman build -t orexis:local .

# 2. What 0.1.0 generated and 0.2.0 refuses or no longer draws.
rm world/terrace/keys.ttl                               # a 0.2.0 boot refuses a document stating no kind
rm -f infra/grafana/dashboards/terrace/health.json      # 0.2.0 reports no health of its own

# 3. The broker's ACL and passwords, from the world's MQTT4SSN words; reloads the running broker.
orexis-mqtt terrace
orexis-influx terrace                                   # a no-op where the bucket is already granted
orexis-dashboards terrace
orexis-compose terrace && git diff --exit-code world/terrace/compose.yaml   # the tracked one, unchanged

# 4. Stop the 0.1.0 agent, keep its belief base as a file, and give the 0.2.0 agent a fresh volume.
cd world/terrace
podman compose stop agent-terrace && podman compose rm -f agent-terrace
podman volume export orexis-terrace-terrace > ~/orexis-terrace-0.1.0-beliefs.tar
podman volume rm orexis-terrace-terrace

# 5. Up, and watch it.
podman compose up -d
podman compose logs -f agent-terrace
```

# What you should see

The agent's log says it booted from `/app/world/terrace` and is listening on
`sensors/moisture_sensor_terrace/reading`. At the next heartbeat or crossing, it logs the four readings, and a point per reading lands in the bucket:
the terrace panels go on drawing. The agent sends nothing — it holds no desire, it watches — and
it does not exit: a transport keeps it running.

# If it goes wrong

`podman compose logs agent-terrace` names the document a boot refused and why; a stray generated
file beside the world is the usual cause. To go back, stop the agent, `podman volume import` the
exported belief base into a fresh `orexis-terrace-terrace`, check out the 0.1.0 world's files and
the last 0.1.0 image, and bring it up as before.
