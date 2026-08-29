---
type: Service
title: Gateway
description: Thin stake-free attestor on the RPi; turns the ESP32's raw readings into citable, provenance-stamped current-state.
---

# What it is

> **Status: decommissioned in v1** ([trusted-agent-mode](/decisions/trusted-agent-mode.md)).
> Under the trusted-agent assumption there is no separate witness: each plant asserts its own
> current-state (`:sensed` / `:classification`, provenance = the plant). The gateway's store-writing
> folds into the sensor edge (the virtual plant / device writes directly). This doc describes
> the *adversarial-mode* witness — the role returns as a **signing sensor** (device cert) if
> you open the society, never as a central process. The measurement-witness reasoning below
> is why the role exists at all; it just no longer runs as its own component in v1.

Trusted, stake-free infrastructure, and the **only** component that WOULD author the attested
graph. It is **not a monolith** — it is a thin RPi process (≈ one file) that turns raw
sensor numbers into citable qualitative state. Build it first: it owns the most settled
decisions and everything downstream trusts it.

**Everything below this line is the adversarial-mode design, in its own present tense.** It was
never built: the graph it describes — `:attested`, and `:attested/<plant>` beside it — is not one
of the agent's, and the readings it would have witnessed land in `:sensed`, authored by the agent
that took them.

The measurement root is split across the hardware, and the split is the point:

- **ESP32 = transducer.** Reads the moisture sensor (ADC/I2C) and emits **raw numbers**. It
  is the honest sensor edge precisely because it is stake-free — no wallet, no LLM, no
  desire, so it *cannot* be self-interested. It makes no judgements.
- **Gateway (RPi) = attestor.** Signs the **measurement**, stamps provenance, and files it
  into the attested current-state.

> **Correction (see [agent-centric-epistemics](/decisions/agent-centric-epistemics.md)):**
> the gateway attests the *measurement*, not the *judgment*. "Is 0.18 LOW?" is
> desire-relative — a succulent shrugs where a fern is parched — so the **band is the
> agent's private opinion**, computed from the attested value + its target, not the
> gateway's call. The gateway's enduring role is the **honest measurement witness** (the
> sealed meter-reader), and the reading is scoped **private / need-to-know**, not broadcast.
> The band logic in the sections below is what the v1 code still does; it moves to the agent.

# The reading is split, not the trust

Raw numbers and citable facts live in different stores (see
[two-store-beliefs](/decisions/two-store-beliefs.md) and [belief-base](/domain/belief-base.md)):

```
ESP32 ──raw reading──► InfluxDB            (the series / record — every reading)
                          │
              gateway reads latest
                          ▼
              threshold→band (0.18→:LOW) + prov stamp
                          ▼
                    :sensed, per agent       (current qualitative state — what agents cite)
```

Writing raw numbers to Influx is **not** attestation. Only the gateway's materialization
into the attested graph is citable; a bare Influx point is just a record.

# Responsibilities

1. Receive readings from the ESP32 (soil moisture) and the weather **forecast** from an API
   (a forecast is just an external reading, source = the API).
2. Ensure **every** reading lands in InfluxDB (the record) — see ingest options below.
3. **Materialize** only the current-state triple into the attested graph, overwriting rather than
   accumulating — a thin, current, qualitative projection of the series.
4. Apply the **threshold→band** decision as part of attestation. See below.
5. Stamp provenance (`prov:wasGeneratedBy :gateway`) so the belief is citable-but-unforgeable.

# The threshold lives here, never in ESP32 firmware

The `0.18 → :LOW` decision (and the per-species dry points — fern ≠ succulent) lives in
**one place**: this process, as config/T-Box. Keep the ESP32 dumb — it emits numbers, not
judgements. Two reasons:

- **One authority.** If each ESP32 hardcoded a threshold, agents would disagree about ground
  truth. The band is the gateway's call and nobody else's.
- **Recalibration is a config edit on the Pi, not a firmware reflash.**

# Ingest — two viable wirings

- **A — ESP32 → Influx direct.** Simplest; ESP32 has Influx client libs. The gateway polls
  Influx for the latest reading and attests. Trust assumption: only trusted ESP32s can write
  Influx (a write token on a trusted LAN). Acceptable v1 shortcut.
- **B — ESP32 → MQTT → gateway → both stores.** The gateway is sole writer of *both* stores
  (firsthand provenance), and the same MQTT reading fires "situation opens" when a plant
  crosses `:LOW` (see [round](/domain/round.md) step 1). MQTT is already the agents' bus.
  Preferred for provenance + round-trigger coherence.

# SOSA shape (attested current-state)

```turtle
:obs_2f a sosa:Observation ;
  sosa:hasFeatureOfInterest :plant1 ;
  sosa:observedProperty :SoilMoisture ;
  sosa:hasSimpleResult 0.18 ;
  :qualitativeBand :LOW ;                 # gateway's call — the one authority
  sosa:resultTime "..."^^xsd:dateTime ;
  sosa:madeBySensor :moisture_sensor_1 ; # device id from the ESP32
  prov:wasGeneratedBy :gateway .          # the leash hook
```

Forecast reuses this exactly: `madeBySensor :weather_api`, `phenomenonTime` in the future.
Same class; tense lives in the timestamp.

# Device identity (v1 vs v2)

v1: a trusted LAN + a device-id string is enough. v2: device certs (TLS client cert to the
broker/Influx) make the ESP32 a certified device principal — the same cert model as agents.
See [authn-authz-capabilities](/decisions/authn-authz-capabilities.md).

# Invariant

The gateway is the single **witness of record** — the sole author of attested *measurements*
(not "shared knowledge", and not judgments; agents form their own private beliefs and bands
from them). The ESP32 supplies numbers; the gateway signs them; agents never write the
attested store. See [trust-boundary](/decisions/trust-boundary.md),
[belief-base](/domain/belief-base.md), and
[agent-centric-epistemics](/decisions/agent-centric-epistemics.md).
