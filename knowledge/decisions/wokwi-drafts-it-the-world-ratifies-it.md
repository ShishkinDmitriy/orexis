---
type: Decision
title: A drawing drafts a stand; the world ratifies it
description: Why the import is one-way and produces a draft rather than a source of truth — what Wokwi's model can give back, what it cannot express at all, and why bidirectional sync was refused rather than deferred.
tags: [wokwi, wireviz, hardware, genesis, drafting, seams]
timestamp: 2026-08-08T00:00:00Z
---

# Drawing is a better way in than typing Turtle

Writing a stand by hand means naming every leg and every wire in a text file, with nothing
checking that the thing described is the thing on the desk until `agora-validate` runs. Drawing
it is better at exactly that step: real part graphics, drag and drop, and a tool that already
knows a `wokwi-dht22` has an `SDA`.

**And the mapping we already have is invertible.** `wokwi:part` and `wokwi:pin`/`wokwi:name` are
a two-column table; reading it backwards turns `wokwi-dht22` into `dht11:Dht11` and `SIG` into
`mc:AnalogInPinRole`. The importer is mostly that lookup run the other way, which is why this is
cheap rather than a second implementation of anything.

# It drafts. It does not become the source

[genesis](/decisions/genesis.md) already has the shape this needs: *sovereign narrates → LLM
drafts → sovereign ratifies*. The draft is never authoritative, and the ratifying step is where
a person takes responsibility for it. Importing a diagram is the same move one layer down —
which is why the import writes a file you then complete and commit, and refuses to overwrite one
that already exists.

## What Wokwi can give back, and what it cannot say at all

The asymmetry is the whole argument, so it is worth being concrete. For one temperature sensor:

| recovered | not expressible in Wokwi |
|---|---|
| the part type, so the class | `ag:localId` — it has ids, but `sen1`, not `air_sensor_fern` |
| its legs, via the class's pin mapping | `mc:model` — "KY-015 (DHT11)" |
| every wire, and the colours | `mc:railVolts`, `mc:logicVolts` |
| where the parts sit | `probe:rawDry` / `rawWet` — the calibration |
| | **all of `world.ttl`** — sense mode, topics, what it monitors, what it observes |

So it recovers the **shape** of a wiring and none of its **meaning**. That is fine for a draft
and disqualifying for a source.

# Why bidirectional sync was refused rather than deferred

Two sources of truth is the failure this project rejects everywhere else, and here it would be
worse than usual. When the two disagree, the lossy side would have to win on the fields it knows
and lose on the ones it does not — which is not a merge rule anyone can hold in their head at
the moment it matters, which is always during a change.

It would also cost the checking. `agora-validate` refuses a 5 V rail feeding a 3.3 V input,
a driven leg on an input-only pin, a leg no wire reaches. Wokwi will draw all three quite
happily. A world synced from a drawing is a world whose shapes have nothing to refuse, because
whatever was drawn is by definition what the world now says.

**The draft is therefore deliberately incomplete rather than plausible.** What cannot be derived
is emitted as an explicit marker, so a half-finished import fails validation loudly instead of
looking finished. A draft that validates is worse than one that does not: it is the one nobody
re-reads.

# The same holds for WireViz, and it drafts better

`agora-wireviz --import` reads a harness back by the same rule, and the asymmetry falls out
differently. A harness is meant to be TYPED, so it carries the names you chose and the models you
wrote — a Wokwi diagram gave back `sen1` and nothing else. What it cannot say is what a part IS:
`type: KY-015 (DHT11)` is free text, and picking `dht11:Dht11` out of it would be guessing.

Which connector is the BOARD is not stated in a harness at all. The one every cable touches is
the usual answer, and the draft labels it `GUESSED` rather than asserting it quietly.

# One triple turns a draft into a compilable source

The gap between "drafts something you finish by hand" and "is enough to generate a world" turned
out to be a single statement. A part's package now says what the part is CALLED:

```turtle
dht11:Dht11 mc:modelName "KY-015 (DHT11)" .
```

so `type: KY-015 (DHT11)` in a harness resolves to a class instead of being free text nobody can
act on. It is the mirror of `wokwi:part`, which already says how a part is identified in the
other tool — a package states how the thing it describes is named outside this repository, and
both directions fall out of the same habit.

**Which connector is the board stops being a guess** as a side effect: a type that resolves to
something under `mc:Microcontroller` IS the board. The old heuristic — whichever connector every
cable touches — survives only for a harness where nothing resolves, and says so when it fires.

Round-tripping our own stand went from **eighteen markers to one**. The one left is
`mc:logicVolts`, which is a fact about the DevKitC and not about our DevKitC, so it belongs on
the class — which is [#55]. Once that lands, a harness plus the vocabulary IS a world.

**That is deliberately not the same as the harness becoming the source.** `hardware.ttl` stays
authoritative and `wiring.yaml` stays a view: author in YAML if you like, generate, read the
diff, commit both. The moment the YAML is the truth we are back to two sources with no merge
rule, and `agora-validate` is back to having nothing to refuse — which is the argument above,
and it does not weaken because the import got better.

## Identifiers come from the authoring file, which is a new way to be wrong

A connector's name becomes a device's `ag:localId`, and `world.ttl` names the same sensors. When
those disagree there is no error anywhere: instead of one device described twice you get two
devices described once — a sensor nothing is wired to, and a part nothing polls. Both halves
validate on their own.

`ag:CarriedPeripheralShape` catches the visible half: a peripheral with legs that no board
mounts. It also forced a real omission out of the importer, which was drafting stands with no
`mc:carries` at all — so every generator that walks a board from its parts found none of them.

Two of the three tools have now been through this, and the shape has not changed: a drawing
carries the wiring and never the meaning. What changed is how much of the meaning the VOCABULARY
can supply once asked.

# Seams left open

- **Part types are not uniquely invertible.** `wokwi-dht22` maps to `dht11:Dht11` today and would
  be ambiguous the day a real DHT22 is added. The importer detects a collision and refuses rather
  than choosing; nothing yet lets a package say "this is the one to prefer".
- **A board's silkscreen cannot be recovered.** Wokwi calls a leg `34`; what is printed beside it
  is a fact about the physical board that no diagram carries, so `skos:notation` is left for the
  person to fill in.
- **Genesis does not use this yet.** The intended next step is that drawing a stand is one of the
  ways a world gets narrated, alongside the prose — but genesis produces a whole world and this
  produces one file of it.
