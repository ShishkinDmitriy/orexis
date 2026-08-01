---
type: Decision
title: English for contested, formal for trusted
description: The line between what agents argue and what infrastructure guarantees.
status: accepted
stage: v1
tags: [architecture, ontology, principle]
timestamp: 2026-08-01T00:00:00Z
---

# Decision

- **English** where things are *contested*: persuasion, preference, negotiation, coalition.
  The LLM owns this.
- **Formal** (RDF/SOSA facts, SHACL/rule constraints) where things are *trusted*:
  provenance, hard constraints, the common record agents cite. No rhetoric moves these.

# Why each formal job can't be English

- **Attested facts** need provenance an agent can *cite but not author* — an English claim
  in a prompt is unverifiable. See [belief-base](/domain/belief-base.md).
- **The constitution** must be enforced by code that can't be argued with — an English rule
  is one clever justification from being talked around. See [constitution](/domain/constitution.md).
- **Shared state** needs a concurrent, queryable, consistent store — a pile of English
  assertions is not a database.

# On the wire

The ACL envelope is structured; the move is structured (numbers); the justification is
English. Binding part formal, persuasive part English, in one message.
