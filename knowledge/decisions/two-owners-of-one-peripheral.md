---
type: Decision
title: Two owners of one peripheral, and the silent success that hid it
description: >-
  The sentinel's ULP never sampled in deep sleep, and the cause was ownership rather than
  power. Arduino's analogRead holds ADC1 through the oneshot driver and never releases it,
  while ESP-IDF 4.4's adc1_ulp_enable reported success anyway — so the coprocessor rode a
  configuration that existed only while the CPU was awake. The handover is now explicit in
  both directions, the same shape appears again on a shared GPIO, and the general lesson is
  that a peripheral with two owners needs a sequence, not a setting.
status: accepted
timestamp: 2026-08-23T22:00:00Z
---

# Two owners of one peripheral, and the silent success that hid it

The sentinel firmware (#151) promises to watch the probe for microamps while the radio and the
main core deep-sleep. It never did. Awake it sampled correctly; the moment the board slept the
ULP read a constant 4095 — full scale, what a SAR returns when it is not converting — and then
stopped running altogether.

The diagnosis took an evening and four wrong answers, all of them the same shape: *something
must be powered down*. CK8M, the analog clock generator's config bus, the analog bias pair, the
SAR's own power-management field. Each was measured, each made no difference, and one of them
(forcing CK8M) was itself a defect that left the coprocessor permanently hung.

**Nothing was powered down. The ADC had two owners and no protocol.**

# What was actually true

Arduino's `analogRead()` takes ADC1 through the oneshot driver and holds it. `adc1_ulp_enable()`
on ESP-IDF 4.4 then returned `ESP_OK` **with Arduino still holding the unit** — so the ULP was
never handed the converter at all. It rode a configuration that existed only while the CPU was
awake, and lost it the instant the board slept.

Every observation fits that and only that, which is the test a diagnosis has to pass:

- correct samples awake, full-scale asleep — the CPU-side driver was live in one case and gone
  in the other;
- every register we forced reading back exactly as set, and none of them helping;
- the coprocessor running perfectly in deep sleep with an ADC-free program, and only ever
  stalling on `I_ADC`;
- a hang on every *second* wake, because the ULP was still patrolling when the next boot's
  `analogRead()` took the unit out from under it mid-look.

ESP-IDF 5 refuses out loud — `adc1 is already in use`, `ESP_ERR_NOT_FOUND` — which is how it was
finally found, after the whole platform was moved for a driver we then discovered had never once
been allowed to run.

# The decision — sequence the handover, in both directions

```
ulpStop()             stop the coprocessor BEFORE the CPU's first analogRead
perimanClearPinBus()  release ADC1 from Arduino, deleting the oneshot unit
ulp_adc_init()        hand the converter to the ULP
ulp_run()             start patrolling again
```

`ulp_adc_init()` is IDF 5's own routine and exists precisely because this setup is easy to get
wrong by hand; preferring it to the three legacy calls is the cheap half of the fix. The
expensive half is the two lines around it, which no driver can supply because only the
application knows when each owner is finished.

**The same shape appears a second time in the same file**, and seeing it as one idea is the
point of this record. GPIO27 is both the status lamp's blue leg and the ULP's vigil lamp; the
lamp owns the pad in the RTC domain between wakes, and `analogWrite` needs it on the digital
matrix. So `vigilLampRelease()` hands it back and the next arm reclaims it. Get it wrong and
every magenta comes out red — a fault colour that lies about which fault it is.

# Why this is worth a record rather than a comment

Because the failure mode is **a success return that is not true**, and no amount of reading the
calling code reveals it. The API said yes. The registers read back exactly as written. The only
thing that could have found it was asking the coprocessor what it actually saw — which is why
the diagnostics that did (a look counter, and the ULP storing its own ADC sample where the CPU
could read it) are kept behind `ULP_VERBOSE` rather than deleted.

The generalisation is worth more than the instance: **a peripheral with two owners needs a
sequence, not a setting.** Whenever this project puts the ULP and the CPU on the same hardware
again — a second ADC channel, a touch pad, an RTC GPIO — the question to ask first is who holds
it now, not what is configured.

# Seams left open

- **The governed node is still on the old platform and the old calls.** `firmware/moisture-sensor`
  keeps its own `platformio.ini` (Arduino 2.0.17 / IDF 4.4) and its `ulp_watch.cpp` still does
  `adc1_config_*` + `adc1_ulp_enable()` with no release. Its ULP watch has the identical defect,
  latent, and it will surface as "the alarm never fires from sleep" exactly as it did here. That
  is a debt with a definition of done, not a choice.
- **Two platforms in one repository.** Pinning the pioarduino fork for one firmware and not the
  other means two toolchains on disk and two Arduino cores to reason about. Deliberate for now —
  moving the governed node is a separate change with its own bench time — but it is not a
  resting place.
- **Four measured-irrelevant register writes remain in `armUlpWatch`.** They are wrong
  explanations sitting where someone will read them, and they should come out.
- **Nothing tests any of this.** Firmware here is compile-untested by design and the bench has the
  last word, so the guarantee that the handover still works is a person watching a lamp.
