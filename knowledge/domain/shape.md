---
type: Domain Concept
title: Shape
description: >-
  SHACL, and the one language this project says both "you may not" and "I want" in — the
  difference is SEVERITY, not structure. A violation refuses; `ag:ShouldBecome` is a desire, and a
  reader that treated them alike would stop a world onboarding because a plant is thirsty. The
  severity split is ours: the spec defines conformance as no results AT ALL, so a warning would
  block exactly as hard as a violation and be pointless to write. Validated in two places by who
  owns the data — an agent checks its own beliefs at boot and refuses to run, the sovereign
  checks the ratified world at the gates — and always against a graph whose entailments are
  already materialised, because the engines must not disagree.
---

# What it is

A **shape** is a SHACL `sh:NodeShape`: a pattern some node must satisfy. This project uses SHACL
for two things that look like opposites and are structurally identical — **what may not be**, and
**what an agent wants** — and that is deliberate rather than a shortcut.

A [desire](/domain/desire.md) compiles to shapes. A constitutional constraint is a shape. An
agent's own capability requirements are shapes. One language, one engine, one report.

# Severity is what tells a bound from a desire

The structure does not differ; the severity does.

| severity | means | consequence |
|---|---|---|
| `sh:Violation` | this may not be | refuses — a world does not onboard, an agent does not start |
| `sh:Warning` | legal, worth a look | printed and passed over |
| `ag:ShouldBecome` | this is wanted | not a finding about the world; it is the state of one |

**The severity split is ours, not SHACL's**, and it had to be. The spec defines conformance as
*no results at all*, so pySHACL reports `conforms: False` for a warning exactly as it does for a
violation — which makes writing a warning pointless, since it stops the world onboarding and the
only thing it changes is a word in the report. A rig that is legal but worth a second look has to
be sayable, so **violations decide the verdict here and everything else is printed and passed
over**.

The same choice is what keeps wants out of the verdict. Once desires compiled to SHACL, every
report grew one block per property nobody had read yet — which at genesis is all of them — and
`agora-validate` printed forty lines about a world it was accepting. A [gap](/domain/gap.md) is
not a finding about the world; asking for one is a query, not a validation.

# Two places, decided by who owns the data

- **An agent's own beliefs** are checked by that agent, at boot, and it refuses to run if they do
  not hold. The check sits where the data is, it happens before the agent acts rather than when an
  operator remembers, and refusing to start is not self-report — the consequence is not running.
- **The ratified world** is checked centrally, against the files, because there is one world and
  it is public. That is the sovereign's check on their own authorship.

An agent validates itself **focused** on its own node, because a capability shape targets every
agent the world declares while an agent holds only its own beliefs — unfocused, fern would report
tomato as missing a band it was never entitled to see.

**But a shape the agent HOLDS is checked unfocused**, and that exception is a measurement rather
than a preference: pySHACL answers `sh:qualifiedValueShape` wrong under `focus_nodes`, measured
both ways round, and every held shape reaches its readings through one. A focused answer would be
the wrong answer with nothing to show it had been. Ownership does the scoping instead — a shape an
agent `ag:holds` is a shape about that agent by construction.

# It is validated against a graph that already holds what the vocabulary implies

Once, this ran with RDFS inference switched on while the runtime ran none — so a world could
satisfy a shape about a relationship the code would never observe. The closure is materialised at
genesis now, and [model-and-unit](/domain/model-and-unit.md) has the mechanism and the guard.

What it costs a caller here is one obligation: **pass the ontology in the data.** Adding the
files on top of the materialised graph is harmless, because that graph is a superset of them, and
a validator handed less goes quiet rather than failing.

# A shape can be data

This is the part that surprises people. Because a desire compiles to SHACL and a derivation writes
it into the agent's graph, **shapes arrive in the DATA as well as in the shapes graph** — so
anything in the data typed `sh:NodeShape` joins the shapes being validated with, and the severity
decides which kind it is.

A validator reading only the files would see a desire as inert triples. That is why "what am I
pursuing" is an ordinary query over ordinary triples rather than a second format.

# Related

- [desire](/domain/desire.md) — what an agent wants, expressed as shapes it holds.
- [capability](/domain/capability.md) — brings the shapes an agent is held to, and only if it
  derived the capability.
- [constitution](/domain/constitution.md) — the constraints nobody may negotiate.
- [a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md) and
  [one-graph-both-engines-read](/decisions/one-graph-both-engines-read.md).
