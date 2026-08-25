---
type: Decision
title: Sensing owns the reading pipeline — bytes to quantity to observation is the package's, and the kernel asks what is known
description: >-
  Six kernel files were sensing's: the codec and scaling contracts, the pointer between them,
  the sensed writer, the observations recorder and `readings.rq`. Their only callers were the
  sensing module and the pipeline's plug-ins, and the query named sensing's own words from
  the kernel. All six move to `packages/capability/sensing/`; the one thing the kernel needed
  from them — what is known, with its horizon — becomes the `readings` choir hook, with a
  sosa-only fallback for a build that senses nothing. The pipeline's plug-ins (codec, scaling,
  transport) import the contract they implement from sensing, which is the one place a
  package imports another's Python, and it is a family importing its family's contract.
status: accepted
timestamp: 2026-08-27T00:00:00Z
---

# What was true before

`bytes ─[codec]→ document ─[pointer]→ raw value ─[scaling]→ quantity ─[observations]→ the
sensed graph` — every stage of the reading pipeline lived in `agent/`, and every caller of it
was `packages/capability/sensing/module.py` or one of the pipeline's own plug-ins
(`packages/codec/json`, `packages/scaling/identity`, `packages/transport/mqtt`). The kernel
also read the result back: `agent/readings.rq`, run by `regions.py` to give the desire
modality each reading's value, instant and horizon — and to do that it named
`sensing:staleAfterS` and `sensing:monitors`, a kernel file reading a package's words that
[the-kernel-names-no-package-word](/decisions/the-kernel-names-no-package-word.md) could
only list as debt.

# What is decided

**The pipeline is sensing's.** `codec.py`, `scaling.py`, `pointer.py`, `sensed_writer.py`,
`observation.py` and `readings.rq` move to `packages/capability/sensing/`. Nothing about them
changes but their imports. Two empty kernel directories (`agent/codecs`, `agent/scalings`)
that had outlived the packages they once held are deleted.

**The kernel judges no staleness.** `readings.rq` gave the desire modality each reading's value,
instant and *horizon*, and the horizon's only kernel use was to mark a stake maximally urgent
once its reading was older than `sensing:staleAfterS`. That word is sensing's — the sovereign's
ruling — and so is the judgment: whether a reading is still evidence is the freshness want's
business, derived and measured by sensing, and sensing's `want_about` already answers that want
first. So a stake judges the number it has, `regions.py` reads the sensed graph in sosa alone
(`sosa:madeBySensor`, which the sensed writer stamps, keys the freshness wants to their
instrument), and `readings.rq` is deleted rather than moved. A choir hook was tried first and
refused by the sovereign for the reason rule 2 refuses a capability of one member: a hook one
module answers is a function call in disguise.

**A family's plug-ins import the family's contract.** `packages/codec/json` implements
`Codec`, `packages/scaling/identity` implements `Scaling`, `packages/transport/mqtt` decodes
with `codec_for` and resolves with `pointer` — and all of those are sensing's now, so those
packages import `packages.capability.sensing`. That is a package importing another's Python,
which rule 2 says never happens between *capabilities*; here the importer is not a
capability but a member of a family sensing defines, importing the contract it exists to
implement — the same relation a capability module has to `agent.module.Module`, one level
down. The independence contract in `pyproject.toml` still holds among the four capability
packages, and this record is where the exception is written.

# What it cost

One behaviour: a stake whose reading has gone cold no longer reads maximally urgent — it reads
by its last number, and the freshness want beside it is what is hot. Two tests that read the
freshness want through a property-keyed dict pinned the old arrangement and now name the want
they mean.

# Seams left open

- **A stake's urgency trusts a number that may be cold.** The freshness want outranks it while
  it is, and the search answers the look first; a reader of the stake's urgency alone sees the
  last number's verdict. That is the split the ruling asked for, stated so nobody rediscovers
  it as a bug.
