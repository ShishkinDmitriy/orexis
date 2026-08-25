---
type: Decision
title: A dead session is resigned, not endured
description: >-
  The kernel watchdog for issue #53 — an agent cut off from its bus past ag:resignAfterS sends
  itself the same SIGTERM podman stop would, and the container's restart policy is the
  recovery. In the kernel like upkeep, on a clock of its own because paho's network thread is
  one of the things watched, with the bound in the ontology as what the society tolerates.
status: accepted
timestamp: 2026-08-14T19:36:12Z
---

# A dead session is resigned, not endured

# Context

The incident is [#53](https://github.com/ShishkinDmitriy/orexis/issues/53)'s measurements: an
agent's MQTT session ended and never came back, and for 48 hours every surface a person would
look at said the system was healthy — the container `Up 2 days`, the broker never restarted,
the board publishing on schedule, the agent's log quiet. Nothing was ingested. The disconnect
was *counted*, and later *logged*, and neither helped, because a metric is watched only after
something has visibly gone wrong and nothing had. A permanently dead session looks exactly like
a quiet one from every side but the agent's own.

The container was the tell: restarting it cured everything, because a restart is a fresh
socket, a fresh TLS session, a fresh subscribe. What was missing was not a remedy but a
*decision to apply it* — and the only party positioned to decide is the agent itself.

# Decision

**The agent notices, and resigns.** `agent/watchdog.py` runs in the kernel on a `Timer` of its
own — not a capability, by [upkeep's](self-review-is-a-capability.md) argument: every agent has
one connection whatever else it can do, and noticing you are dead is not an ability whose *how*
could differ. Not on paho's thread, because that thread is one of the things being watched.

Three checks, ordered by how wrong things are:

- **the network thread died.** The callbacks are wrapped so no exception can kill it, and
  "should be impossible" is precisely what a watchdog is for — a dead loop thread fires no
  callbacks, so the connected flag would stay stale-true forever; the corpse is checked before
  the flag is believed.
- **cut off past the bound.** `Metrics` keeps a *continuous* disconnection clock — started at
  construction (an agent whose CONNACK is refused in a loop is exactly as cut off as one whose
  session died), reset by one successful reconnect (a flapping link never accumulates its way
  to a resignation; `mqtt_reconnects` is flapping's counter). Past `ag:resignAfterS`, resign.
- **something expected has gone silent.** Each module's `quiet()` — sensing answers with
  every sensor that delivered once and then went silent past the same `stale_after_s` its
  freshness rule uses, so the log and the refusal cannot disagree. Said once on entry and once
  on recovery, never per tick. This check only speaks; the first two act.

**Resigning is SIGTERM to self, through the front door.** The signal is blocked and pending,
`run()`'s `sigwait` receives it exactly as `podman stop`'s would be, modules stop cleanly, the
writer flushes — and `restart: unless-stopped` brings the process back to the fresh session
that actually cured the incident. One CRITICAL line carries the story; in the series, the
restart shows as `uptime_s` resetting.

**The bound is the ontology's** — `ag:Agent ag:resignAfterS 600`, beside the compaction ratio
and for the same reason: what a society tolerates is not how the code happens to be written.
Ten minutes is far past any reconnect paho would achieve and far under the hours a quiet
failure used to cost.

# Consequences

- **A broker outage becomes a restart loop, deliberately.** Every agent resigns every ten
  minutes until the broker returns — cheap, bounded, honest, and visible as a sawtooth in
  `uptime_s` where the old behaviour was a flat healthy-looking line over nothing. Beliefs are
  untouched: a restart has never been a re-birth.
- **The two-day failure is now bounded at ten minutes** plus one watchdog tick.
- `_on_connect` is wrapped like `_on_message` always was, so the thread-death check guards a
  door that is also locked.

# Seams left open

- **Nothing reproduces the original paho failure against a live broker.** The issue's first
  to-do — drop a session at the broker, confirm whether the client returns — belongs in
  `infra/tests/` as a contract with paho the way the existing ones are contracts with mosquitto
  and InfluxDB. The watchdog makes the answer matter less: whichever way paho behaves, the
  bound holds.
- **`_thread` is paho's private attribute** — read by `MqttLink.alive()` now, the kernel asking the [link](/domain/link.md) for a pulse. The deliberate price of watching a thing that
  offers no public pulse; if a future paho renames it, the check degrades to never-true and the
  disconnection bound still stands guard behind it.
- **The quiet() sweep informs and does not act.** A sensor gone silent is the *board's* fault
  or the wire's, and restarting the agent would cure neither — the sibling
  [freshness-follows-the-cadence](freshness-follows-the-cadence.md) records from the other
  side: nothing nudges a returning sensor either.
