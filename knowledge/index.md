---
okf_version: "0.1"
---

# Agora — Agent Society

A multi-agent resource-allocation system: self-interested agents bid in an iterative
auction for a scarce resource from a limited supply, under a hard trust/constitution
boundary, grounded in real sensor data on a Raspberry Pi. Conversation sets valuations;
the auction settles allocation. The domain is a plug-in — the **v1 example is plant
watering** (agents bid for water), so plant/water language throughout is the concrete
instance, not the architecture. This bundle records the architecture *decisions* and the
*domain model* — the durable "what and why", not the live sensed state (that lives in the
runtime belief base).

# Decisions

* [decisions/](decisions/) - Architecture decisions with rationale and the seams left open for later stages.

# Domain

* [domain/](domain/) - The shared contract: what each component is, its responsibilities, and its invariants.

# How to use this bundle

* Building a component? Read its [domain](domain/) concept, then any [decision](decisions/) it links.
* Tempted to change something? Check whether a decision pins it — several choices exist to keep v2/v3 open and must not be welded shut.
* Runtime testimony (attested sensor triples — the witness of record, not "shared knowledge") is NOT here — see [domain/belief-base](/domain/belief-base.md).
* Adding a document? Concept files carry frontmatter with a non-empty `type` (`Decision`, `Domain Concept`, `Component`), plus `title` and `description`. An `index.md` carries **none** — it is navigation, and its title is its heading. Only this root file may declare `okf_version`.

# Format

This is an [Open Knowledge Format](https://okf.md) v0.1 bundle — markdown with YAML
frontmatter, readable by any OKF consumer rather than only by this repo's conventions.
Conformance is three rules: every non-reserved `.md` has frontmatter, every frontmatter has a
non-empty `type`, and reserved files (`index.md`, `log.md`) follow their structures. Validate
with the OKF skill's `scripts/validate.sh`, or `okflint` if you have it.
