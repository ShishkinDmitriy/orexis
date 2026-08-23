---
type: Decision
title: The vigil costs standing, not looking
description: >-
  The ULP's energy is dominated by holding the RTC peripheral domain powered, not by taking
  samples — a look costs about 2e-7 mAh, so one radio wake buys roughly 1.1 million of them.
  The patrol period is therefore free within any range worth choosing, and the heartbeat is
  where the battery actually goes. Closes the "pricing the watching" seam #151 left open, and
  sets the patrol to 15s because there was never a reason to be sparing with looks.
status: accepted
timestamp: 2026-08-24T00:15:00Z
---

# The vigil costs standing, not looking

[#151](https://github.com/ShishkinDmitriy/orexis/issues/151) left a seam it called the energy
budget: *pricing that microamp vigil against the radio wakes it saves.* The sentinel's README
priced the radio and left the vigil as a single number — "~150 µA ≈ 3.6 mAh/day" — measured for
the one-look-per-second design. Asked whether doubling the patrol rate could be afforded, the
answer turned out not to depend on the rate at all.

# The model

The vigil's current is not one number, it is two terms:

```
I(f) = B + q·f          B = standing cost      q = charge per look      f = looks per second
```

**`q` is tiny.** A look is: start the 8 MHz oscillator, run about 25 instructions, take one SAR
conversion, halt. On the order of 200 µs at ~4 mA, so **q ≈ 0.8 µA·s ≈ 2.2 × 10⁻⁷ mAh**.

**`B` is nearly all of it.** At one look per second the `q·f` term is **0.8 µA** of the 150 µA
measured. The other 149 µA is standing: the RTC peripheral domain held powered — which
`armUlpWatch` forces, because the SAR lives in it — plus the coprocessor enabled.

So the patrol period barely enters the answer:

| patrol | looks/day | what the looking costs | total at a 20-minute heartbeat |
|---|---|---|---|
| 60 s | 1,440 | 0.00032 mAh/day | 21.6 mAh/day |
| 30 s | 2,880 | 0.00064 mAh/day | 21.6 mAh/day |
| 15 s | 5,760 | 0.0013 mAh/day | 21.6 mAh/day |

Going from a 60-second patrol to a 15-second one costs about **a thousandth of a mAh per day** —
roughly an hour of life over a three-month cell, which is far inside the error on every figure
here.

The clearest way to hold it: **one radio wake buys about 1.1 million looks.** At a 15-second
patrol that is nearly two hundred days of continuous watching for the energy of a single publish.

# What this decides

**The patrol period is set for latency, not for battery.** It is 15 s. There was never a reason
to be sparing, and the cost of being generous is a shorter time-to-notice: 15–25 s from a change
to a published alarm, against 10–70 s at the old sixty. The one-second period the governed node
derives from the worst credible slew is affordable too; what argues against it here is not energy.

**The heartbeat is the whole battery story.** Of 21.6 mAh/day at a 20-minute heartbeat, **18 is
the radio** and 3.6 is standing vigil. Halving the heartbeat rate roughly doubles the life:

| heartbeat | wakes/day | mAh/day | 2000 mAh cell |
|---|---|---|---|
| 20 min | 72 | 21.6 | ~93 days |
| 30 min | 48 | 15.6 | ~128 days |
| 40 min | 36 | 12.6 | ~159 days |
| 1 h | 24 | 9.6 | ~209 days |

Which restates the README's own conclusion with numbers behind it: **the battery is spent by the
agent's epistemology, not by the firmware.** `render_sentinel` fits the heartbeat under the
polling agent's `sensing:maxReadingAgeS`, so the belief that decides the battery is a freshness
rule held by someone else entirely.

**An alarm is the expensive event, not a look.** Each is a full wake — 0.25 mAh, about 1.7 hours
of standing vigil. A faster patrol notices more transients, so it can cost *indirectly* by
alarming more often; two extra alarms a day is +0.5 mAh/day, which is more than the entire
looking budget at any rate. If a faster patrol ever hurts, that is the mechanism, and the fix is
`WAKE_DELTA` rather than the period.

# What is measured and what is not

Honesty about provenance, because these numbers will be quoted:

- **0.25 mAh per radio wake** and **~150 µA vigil** are the README's bench figures.
- **q ≈ 0.8 µA·s** is an ESTIMATE from instruction count and conversion time. It is the one number
  here nobody has put a meter on. It would have to be about two hundred times larger before the
  patrol rate mattered at all, which is why the conclusion is robust even though the figure is not.
- The split of the 150 µA into standing and per-look is inferred from that estimate, not measured
  directly. Measuring deep-sleep current with the ULP disabled would settle it in an hour.

# Seams left open

- **Nobody has metered this board.** Every figure above is bench arithmetic over two measured
  constants. The cheap experiment — deep sleep current with `ULP_MINIMAL_TEST 1` at two very
  different patrol periods — would confirm or destroy the model in an afternoon.
- **The patrol period is firmware, not world.** It is a `#define` with an `#ifndef` fallback, like
  `LED_BRIGHTNESS`, and `render_sentinel` does not generate it. Detection latency is arguably a
  property of the promise a board makes and therefore the world's to state — but there is no
  vocabulary term for it, and inventing one to carry a number nothing yet varies would be the
  registry-of-one mistake [#25](https://github.com/ShishkinDmitriy/orexis/issues/25) already names.
- **Standing cost is treated as fixed and it is a choice.** `ESP_PD_DOMAIN_RTC_PERIPH` is forced ON
  for the SAR's sake. Whether the domain could be cycled per look — powered for the conversion and
  dropped between — is unexplored, and it is where the remaining 149 µA lives.
