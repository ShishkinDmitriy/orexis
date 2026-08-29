---
okf_version: "0.1"
---

# Orexis — Agent Society

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

# Runbooks

* [runbooks/](runbooks/) - How to operate a society: genesis a world, run it, and take it apart — and why stopping it is not one command.

# How to use this bundle

* Building a component? Read its [domain](domain/) concept, then any [decision](decisions/) it links.
* **Want to know what is true NOW, not how it got that way?** The domain concept is the current
  statement; a decision record is the argument that produced it, and several may amend one
  another. Where that has happened the records carry a banner pointing at the concept — see
  [domain/package](/domain/package.md) and [domain/model-and-unit](/domain/model-and-unit.md),
  which each stand in for four records.
* Trying to *operate* one? Start at [runbooks](runbooks/) — the domain says what things are, the runbooks say what to type.
* Tempted to change something? Check whether a decision pins it — several choices exist to keep v2/v3 open and must not be welded shut.
* Runtime testimony (attested sensor triples — the witness of record, not "shared knowledge") is NOT here — see [domain/belief-base](/domain/belief-base.md).
* Adding a document? Concept files carry frontmatter with a non-empty `type` — one of `Decision` (why the code is as it is), `Domain Concept` (a thing in the model), `Process` (something that happens, with phases and an end), `Capability` (a named ability with interchangeable implementations), `Role` (a kind of principal), `Service` (a part of the implementation that holds logic), `Repository` (a part that passively holds data) or `Runbook` (how to operate it) — plus `title` and `description` — and a domain page whose word the T-Box carries also binds it with `term:` (see [the-dictionary-names-its-terms](/decisions/the-dictionary-names-its-terms.md)). An `index.md` carries **none** — it is navigation, and its title is its heading. Only this root file may declare `okf_version`.

# Format

This is an [Open Knowledge Format](https://okf.md) v0.1 bundle — markdown with YAML
frontmatter, readable by any OKF consumer rather than only by this repo's conventions.
Conformance is three rules: every non-reserved `.md` has frontmatter, every frontmatter has a
non-empty `type`, and reserved files (`index.md`, `log.md`) follow their structures. Validate
with the OKF skill's `scripts/validate.sh`, or `okflint` if you have it.
