---
type: Decision
title: The sovereign may ask, and the agent answers about itself
description: Observe-via-sovereign made mechanism — one SPARQL question per message, over the
  world's own bus, gated to a single principal by the broker ACL, answered by the agent from
  its live store across everything it holds. Disclosure, not access; read-only by
  construction, because the engine's query API structurally cannot execute an update.
status: accepted
timestamp: 2026-08-17T11:03:04Z
---

# The sovereign may ask, and the agent answers about itself

[agent-centric-epistemics](/decisions/agent-centric-epistemics.md) has said "observe via
sovereign" since the founding records. This is the via: `orexis-ask <world> <agent> '<SPARQL>'`
publishes the question on `agents/<id>/sovereign/query`, the agent answers on its result
topic, and the broker's ACL is the whole of the admission control — a `sovereign` principal
per world, minted by `orexis-mqtt` like every other credential, held in the world's secrets
directory and **never mounted into any container**.

Three properties carry the design:

- **Disclosure, not access.** No shared store returns; no volume is opened around a lock; no
  isolation boundary grows a hole. The belief base stays the agent's, in its own volume,
  reachable by nothing — what exists is a question one principal may put and a voluntary
  answer the agent composes from its own store. The distinction is the same one the ladder
  record drew for pumps: possession of a channel is not authority over the store behind it.
- **Read-only by construction, not by filter.** The responder (in reporting — saying how you
  are and answering what you believe are one capability's two voices) runs the store's query
  API, and pyoxigraph's `query` structurally cannot execute an update: an INSERT arrives,
  raises in the engine, and the error is the answer. There is no allowlist to rot.
- **The answer spans one MODALITY of the agent, named in the ask.** First drawn wider — the
  union of everything the one store held — and narrowed when the mind became several stores:
  [a-store-is-a-modality](/decisions/a-store-is-a-modality.md)'s third ruling makes the
  modality a required argument, no default, exactly as there is no default world. Within the
  named modality the answer is still its whole self — `query_union` over that store, private
  graphs included — because making the sovereign spell graph IRIs would be rule 1's own trap:
  a graph IRI is an instance. A payload naming no modality, or one this mind lacks, is
  refused with the path spelled out.

The topic pair is the one channel an agent listens on that the world does not state
(`packages/orexis-capability-reporting/sovereign.py` — `agent/sovereign.py` until [metrics-are-an-aspect](/decisions/metrics-are-an-aspect.md) — is its single source, imported by both the ACL generator and the
responder): it is not the society's business — no agent may hear another's questions or speak
on another's answers, which the generated grants say explicitly, in the ACL's own idiom of
silence-is-not-permission.

Alongside, the passive half strengthened the same way (#61's argument extended from the
revisable picks to the wants): the deduced region and the aim per property now reach the
agent's own series bucket as an `agent_desire` measurement with the PROPERTY AS A TAG — the
sovereign's own correction to a first draft that baked it into field names: `desired_low`
grouped by `property` is one generic panel for any number of wants, where
`desired_low_SoilMoisture` is a string a dashboard can only match. Carried by a small generic
hook (`Module.series` — tagged rows on the same tick, same writer, same bucket), so the next
per-dimension figure rides the same rail.

**Found while testing**: the store's engine errors on decimal division when the dividend is
zero, so `gap.rq` had always lost its `?gap` for an agent sitting exactly at its region's
centre — perfectly content, and unable to say so. Short-circuited in the query with the
measurement recorded in its comment.

# Seams left open

- **No signature on the question.** The ACL is the admission control; a signed question
  (verifiable by the agent like an actuator verifies a claim) would defend against a
  compromised broker, and belongs with the same hardening pass as revocation
  ([#28](https://github.com/ShishkinDmitriy/orexis/issues/28),
  [#29](https://github.com/ShishkinDmitriy/orexis/issues/29)).
- **Answers are capped, not paged.** A truncated answer says how many rows matched; a
  sovereign who wants a million rows has the volume, offline.
- **One agent per question.** A fan-out ("ask every agent") is a loop in the CLI the day it
  is wanted, not a broadcast topic — a broadcast would be a channel every agent shares, and
  the per-agent pair is what keeps the grants exact.
