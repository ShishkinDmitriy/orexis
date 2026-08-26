---
type: Decision
title: A shape belongs to the vocabulary it checks, not to the one it selects on
description: >-
  Two records disagreed about which end of a shape decides its home. One said a shape targeting
  `actuation:actuates` is actuation's whatever terms it checks; the other split a shape in two
  and gave the transport the half whose terms were the transport's. Settled by asking what
  breaks on deletion: a selector that matches nothing costs nothing, while a constraint on a
  term nobody declares refuses every world for a vocabulary that is not there. So the
  constraints decide, the selector may be foreign, and a capability stops saying how its
  subject must be spoken to.
status: accepted
timestamp: 2026-08-27T18:00:00Z
---

# What was true before

A shape has two ends — what it **selects** (`sh:targetClass`, `sh:targetSubjectsOf`, a SPARQL
target) and what it **constrains** (`sh:path`, `sh:class`, the terms inside `sh:select`). When the
two belong to different packages, two records had answered the ownership question differently.

- [the-kernel-names-no-package-word](/decisions/the-kernel-names-no-package-word.md) moved
  `ag:SimulatedActuatorShape` out of the kernel and into actuation, and the note left on the
  shape spelled the rule out: *a shape targeting `actuation:actuates` is this package's, whatever
  the term it checks belongs to.* **The selector decides.**
- [the-kernel-has-no-mailbox](/decisions/the-kernel-has-no-mailbox.md) split
  `SimulatedDeviceShape` down the middle. One selector, two homes: the kernel kept *one device,
  one stand-in*, and `mqtt:SimulatedDeviceReachableShape` took reachability, because reachability
  "is a sentence in this transport's words". **The constraints decide.**

Both readings are defensible from the text, and the repo ran on the first while the second was the
one it had actually done. The visible cost was `actuation:ActuatorShape` requiring
`mqtt:commandTopic` of every actuator, and `actuation:SimulatedActuatorShape` requiring
`mqtt:statusTopic` — a **capability** deciding how its subject must be spoken to, which is the
error [a-stand-in-is-not-a-device](/decisions/a-stand-in-is-not-a-device.md) removed one level
down when sensing stopped deciding what its subject was made of.

# What is decided

**The constraints decide.** A shape lives in the package that declares the terms it CONSTRAINS.
Its selector may name any package's term.

The test is deletion, which is what a package boundary is for — *a directory is how a package is
found and how one is deleted*:

| | delete the package it SELECTS on | delete the package it CONSTRAINS |
|---|---|---|
| the shape stays behind | the target matches nothing | every constraint fires against a vocabulary nobody declares |
| what that costs | nothing — a shape with no focus nodes is silent | a false refusal of every world, for a term that is not there |

Asymmetric, and the asymmetry is the whole argument. A selector is a *question* — "of the things
that actuate, which…" — and a question nobody answers is harmless. A constraint is a *demand*, and
a demand outliving the vocabulary that gave it meaning is a world refused for no reason anyone can
read.

**So `mqtt:` owns both statements about a valve's channels.** `mqtt:MqttActuatorShape` demands the
command topic — of an actuator on a bus, which is the honest scope, where actuation demanded it of
every actuator including one no transport reaches. `mqtt:SimulatedActuatorReportsShape` demands the
status topic of a stood-in actuator, selecting on `actuation:actuates` from inside the transport,
which this record now says is fine.

**And a capability's shapes name no transport at all.**
`tests/test_shapes.py::test_no_capability_shape_names_a_transport` reads the machine-read part of
every `packages/capability/*/shapes.ttl` and refuses any transport-family term in it, discovering
the transports by directory rather than by a list.

# What did not change

- **The kernel still may name NO package word, at either end.** That is
  [the-kernel-names-no-package-word](/decisions/the-kernel-names-no-package-word.md)'s actual
  ruling and it is untouched; what this amends is only the incidental note about where a shape
  leaving the kernel should land. A shape whose selector and constraints are both a package's has
  one obvious home and always did.
- **A capability's `rules.ru` may still join through a transport's terms.** Sensing's three
  derivation rules read `mqtt:readingTopic` and `mqtt:onBus` to find the device sharing a sensor's
  stream. That is a recorded wait rather than a debt —
  [channel](/domain/channel.md) says a transport-neutral class earns its place the day a second
  transport exists, and a capability's premise is its own to state whatever happens, so those
  rules could not move here even if the word existed.
- **Every requirement still fires.** A valve on a bus with no command topic is refused; a stood-in
  valve with no status topic is refused. Both are proved from the world rather than from the shape
  file, so the move could not have quietly emptied them.

# Seams left open

- **An actuator on no bus at all is now unconstrained about channels**, which is the point and is
  also untested, because no world has one. The day a second transport lands, the shape it needs is
  its own — and that is where the neutral word gets decided, with two instances to generalise from
  instead of one.
- **The rule is enforced for capabilities and transports only.** Nothing stops a `part` package
  from constraining a `plant` term, or the reverse; the pair that had gone wrong is the pair that
  is guarded, and widening the guard should wait for a second case rather than a second worry.
