---
type: Decision
title: The substrate is not the mind's — what a thing is made of, and what stands in for one, leave the kernel
description: >-
  A BDI kernel declared what a thing is MADE OF — a physical edge node, the process that stands
  in for one, and the physics that stand-in computes between readings. The sovereign asked
  whether SOSA and SSN are not enough for all of it. They are enough for the ROLE and say
  nothing about substrate, deliberately — SOSA's classes may be virtual — so a word for it
  survives; what does not survive is the kernel owning it. Decided that the kernel declares no
  hardware and no stand-in, and that the two go to different packages because they are
  different claims.
status: accepted
timestamp: 2026-08-26T23:00:00Z
---

# What was true before

`agent/ontology.ttl` declared `orexis:Device` ("a physical edge node"), `orexis:simulatedBy` ("no such
device exists; a process stands in for it"), `orexis:DeviceModel` and eight `ag:model*` properties —
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
something is mounted. Neither says a thing is made of anything, and `mc:hasPin` needs a domain
that does. Two earlier audits reached the same conclusion, recorded in sensing's and actuation's
own ontologies.

**And the kernel does not own it.** That is the part those audits got wrong by leaving it where
it was: a mind is not made of anything, so what a thing is made of cannot be the kernel's word.
`packages/orexis-part-device/` — knowledge-only, no Python and nothing to grant — holds `device:Device`
and the shape that makes one reachable, and it sits in the `part` family because that is where
hardware description already lives.

**The stand-in went somewhere else, and that is the whole of the second record.** What the kernel
held was not one vocabulary but two: a word for substrate, and a word for its ABSENCE. They read
alike and they are opposites, which is why the first draft of this change put them in one package
and had to be corrected — see
[a-stand-in-is-not-a-device](/decisions/a-stand-in-is-not-a-device.md), which owns why
`packages/orexis-sim-standin/` exists and why nothing that observes or acts asks either package for
anything.

**The kernel keeps what is about the installation rather than the hardware**: `orexis:ComputeHost`,
`orexis:lanHost`, `orexis:runsOn` — where a society executes — which is a fact about a deployment and
not about a thing with legs. `orexis:ComputeHost` stops being a kind of device.

**And the ratchet reaches its floor.** The widener that read `sensing:monitors` from a kernel
shape went with the model's shape; a package naming another package's word is ordinary, and only
the kernel doing it was debt. What remains on the allowlist is migration destinations —
spellings `vocabulary.MOVED` carries for volumes older than each move — and nothing else.

# What did not change

- **The simulation.** `onboarding/compose.py` still keys a stand-in off `simulatedBy` and reads
  the same physics; the generators reach the term through `onboarding/namespaces.py`, as they
  reach every other package's.
- **A deployed belief base.** `vocabulary.MOVED` carries every old spelling to its new home, one
  entry for the substrate word and twelve for the stand-in's.

# Seams left open

- **The length of the world's day.** `ag:timeScale` left with the scenario knobs, rightly; the
  meaning of a rate stated per day did not, and
  [the-world-states-the-length-of-its-day](/decisions/the-world-states-the-length-of-its-day.md)
  makes it a fact of the world the mind reads, from which the stand-ins derive their scale.

- **`device:` is a `part` family package that no part requires.** Every part names it, and it
  names none of them; a world with no hardware at all would still load it, harmlessly, because
  a knowledge-only package costs a merge and nothing else.
- **The stand-in's physics is a vocabulary without an owner-runtime.** The simulated devices are
  containers the compose generator writes, not a package that provides code; if `sim/` ever ships
  Python, the physics is what it takes with it.
