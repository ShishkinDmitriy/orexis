---
type: Decision
title: A shape belongs to whatever makes its rule mean something, and deleting that package must delete the rule
description: >-
  Two records disagreed about which end of a shape decides its home — the terms it selects on
  or the terms it constrains. Neither answer survives, because the deletion that matters is not
  a shape LEFT BEHIND but a shape that goes WITH its directory: a stand-in's invariant filed
  under the transport disappears the day the transport is replaced, silently, and nothing
  refuses a stand-in that reports nowhere. So the owner is whichever package's absence makes
  the rule MEANINGLESS, its constraints may name any vocabulary, and a capability still says
  nothing about how its subject is spoken to.
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
  one stand-in*, and the transport took reachability, because reachability "is a sentence in this
  transport's words". **The constraints decide.** (That shape is `sim:StandInReachableShape` now:
  it is the simulation's invariant, and it followed the report shape home.)

Both readings are defensible from the text, and the repo ran on the first while the second was the
one it had actually done. The visible cost was `actuation:ActuatorShape` requiring
`mqtt:commandTopic` of every actuator, and `actuation:SimulatedActuatorShape` requiring
`mqtt:statusTopic` — a **capability** deciding how its subject must be spoken to, which is the
error [a-stand-in-is-not-a-device](/decisions/a-stand-in-is-not-a-device.md) removed one level
down when sensing stopped deciding what its subject was made of. The mirror error was there too
and took a second pass to see: the transport was holding the simulation's invariants.

# What is decided

**A shape lives with whatever makes its rule mean something — and deleting that package must
delete the rule.** Its constraints may name any vocabulary, and so may its selector.

The test is deletion, which is what a package boundary is for — *a directory is how a package is
found and how one is deleted*. The first draft of this record ran that test on a shape LEFT
BEHIND, and got an answer that looked clean:

| | delete the package it SELECTS on | delete the package it CONSTRAINS |
|---|---|---|
| the shape stays behind | the target matches nothing — silent, harmless | every constraint fires against a vocabulary nobody declares |

**That is not the deletion that happens.** A shape goes WITH its directory, and the question is
what the world loses when it goes. Run it that way and the answer inverts for exactly the shapes
that had gone wrong:

> *A stand-in must say where it reports* is a rule the SIMULATION needs — a stood-in valve that
> reports nowhere opens into nothing, because physics has no wire between two containers and a
> simulated sensor waters only on what the valve says. Filed under the transport, that rule is
> deleted by replacing the transport. Nothing would refuse the world; the soil would simply stay
> dry, which is the silent loss this repo has been bitten by more than once.

Filed under the simulation, the same replacement breaks the shape **loudly** — its constraint is
spelled in a vocabulary that is gone — and whoever is doing the replacing is exactly the person who
should be rewriting it.

So the owner is the package whose **absence makes the rule meaningless**, not the one that owns the
words the rule happens to be spelled in. *An actuator on a bus must state a command topic* is
meaningless without the bus, so it is the transport's. *A stand-in must report* is meaningless
without stand-ins, so it is `domains/sim/`'s — and `sim:StandInReportsShape` and
`sim:StandInReachableShape` live there, naming `mqtt:` terms and, in the first case,
`actuation:actuates` too. A package about pretending to be an X reachable over a Y has both words
in its subject; that is its business rather than a leak.

**And a capability's shapes name no transport at all.**
`tests/test_shapes.py::test_no_capability_shape_names_a_transport` reads the machine-read part of
every `packages/orexis-capability-*/shapes.ttl` and refuses any transport-family term in it, discovering
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

# What is still coupled, and honestly

`mqtt:MqttActuatorShape` selects on `actuation:actuates` — it did before any of this, as a full
IRI inside its SPARQL target. The transport cannot say *of the things that take commands, each on
my bus must say where* without a word for taking commands, and `sosa:Actuator` would not remove the
dependency, only hide it behind a standard namespace: a world types its valve `actuation:Valve`,
and SOSA reaches it through the subclass axiom that actuation's own ontology declares. That trap is
named in [the-kernel-names-no-package-word](/decisions/the-kernel-names-no-package-word.md) and it
applies here unchanged.

So the count is: actuation names no transport, the transport names actuation once, in the one shape
that is the transport's own rule, and the simulation names both because both are what it is about.

# Seams left open

- **An actuator on no bus at all is now unconstrained about channels**, which is the point and is
  also untested, because no world has one. The day a second transport lands, `sim:StandInReportsShape`
  and `sim:StandInReachableShape` are the two that need the neutral word — findable because they are
  filed under the reason they exist rather than under the words they use.
- **The rule is enforced for capabilities and transports only.** Nothing stops a `part` package
  from constraining a `plant` term, or the reverse; the pair that had gone wrong is the pair that
  is guarded, and widening the guard should wait for a second case rather than a second worry.
- **Nothing enforces the new rule itself.** *Whose absence makes this meaningless* is a judgment, and
  a test cannot make it — what a test can do is what
  `test_no_capability_shape_names_a_transport` does, catch the one direction that has twice gone
  wrong. A shape filed under the wrong reason is found by a reader, or by the day someone deletes
  a package and looks at what broke.
