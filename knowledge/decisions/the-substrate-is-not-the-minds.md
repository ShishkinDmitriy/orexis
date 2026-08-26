---
type: Decision
title: The substrate is not the mind's — a device, its stand-in and the physics between them leave the kernel
description: >-
  A BDI kernel declared what a thing is MADE OF — a physical edge node, the process that stands
  in for one, and the physics that stand-in computes between readings. The sovereign asked
  whether SOSA and SSN are not enough for all of it. They are enough for the ROLE and say
  nothing about the substrate, deliberately — SOSA's classes may be virtual — so the word
  survives; what does not survive is the kernel owning it. Decided that `packages/part/device/`
  holds the substrate, its stand-in and their shapes, and the kernel declares no hardware.
status: accepted
timestamp: 2026-08-26T23:00:00Z
---

# What was true before

`agent/ontology.ttl` declared `ag:Device` ("a physical edge node"), `ag:simulatedBy` ("no such
device exists; a process stands in for it"), `ag:DeviceModel` and eight `ag:model*` properties —
initial value, dose effect, loses-per-day, daily swing, tick seconds, floor and ceiling — plus
three world-level scenario knobs (`ag:timeScale`, `ag:strayDoseMeanDays`, `ag:rainTopic`); and
`agent/shapes.ttl` held the three shapes that check them. Everything else non-BDI had already
left the kernel; this was the last of it, and the ratchet's last non-migration entry lived in
one of those shapes.

# What is decided

**The substrate axis is real, and it is not SOSA's.** The sovereign's question — *we have sosa
and ssn, is that not enough?* — is answered no, for a reason the vocabulary itself gives: SOSA
is explicit that its major classes may be **virtual**, so `sosa:Sensor` says *this observes* and
never *this exists*. `ssn:System` asks what implements a procedure; `sosa:Platform` asks where
something is mounted. Neither says a thing is made of anything, and `device:simulatedBy` — whose
whole content is *there is no hardware here, something is pretending* — needs a word that does.
Two earlier audits reached the same conclusion, recorded in sensing's and actuation's own
ontologies.

**And the kernel does not own it.** That is the part those audits got wrong by leaving it where
it was: a mind is not made of anything, so what a thing is made of cannot be the kernel's word.
`packages/part/device/` — a knowledge-only package, no Python and nothing to grant — holds
`device:Device`, `device:simulatedBy`, `device:DeviceModel` and the model's physics, with
`device:DeviceShape`, `device:SimulatedDeviceReachableShape`'s kernel half and
`device:DeviceModelShape` beside them. It sits in the `part` family because that is where
hardware description already lives, and the parts that describe pins and volts already take
`device:Device` as their domain.

**The kernel keeps what is about the installation rather than the hardware**: `ag:ComputeHost`,
`ag:lanHost`, `ag:runsOn` — where a society executes — which is a fact about a deployment and
not about a thing with legs. `ag:ComputeHost` stops being a kind of device.

**And the ratchet reaches its floor.** The widener that read `sensing:monitors` from a kernel
shape went with `DeviceModelShape`; a package naming another package's word is ordinary, and
only the kernel doing it was debt. What remains on the allowlist is migration destinations —
spellings `vocabulary.MOVED` carries for volumes older than each move — and nothing else.

# What did not change

- **What a world says.** `a sosa:Sensor , device:Device` where it said `ag:Device`; every
  statement about topics, buses, sense modes and models is otherwise identical, and a deployed
  belief base is carried across by `vocabulary.MOVED`.
- **The simulation.** `onboarding/compose.py` still keys a stand-in off `simulatedBy` and reads
  the same physics; the generators read the term through `onboarding/namespaces.py`, as they
  read every other package's.

# Seams left open

- **`device:` is a `part` family package that no part requires.** Every part names it, and it
  names none of them; a world with no hardware at all would still load it, harmlessly, because
  a knowledge-only package costs a merge and nothing else.
- **The stand-in's physics is still a vocabulary without an owner-runtime.** The simulated
  devices are containers the compose generator writes, not a package that provides code; if a
  simulation package ever exists, the physics is what it takes with it.
