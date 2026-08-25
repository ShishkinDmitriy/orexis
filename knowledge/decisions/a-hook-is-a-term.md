---
type: Decision
title: A hook is a term — the choir's questions are declared in the ontology of whoever owns them
description: >-
  `Agent.ask("annotate", …)` found an answer by a Python string and an attribute name, so a
  question nobody owned was answered by silence and a typo by nothing. Decided: every hook is
  an `ag:Hook` some ontology declares — the kernel's for wants, acts and the account, a
  package's for anything in its own words — a module answers one by decorating a method with
  the term, an override by name inherits it, and the runtime refuses a term no ontology
  declares. The sovereign asked for this on seeing the raw strings.
status: accepted
timestamp: 2026-08-26T12:00:00Z
---

# What was true before

The choir grew hook by hook, each a method name on `Module` or, since
[the-stake-is-sensings-want](/decisions/the-stake-is-sensings-want.md), a string handed to
`Agent.ask` and resolved with `getattr`. It worked, and it had the failure every string
registry has: `ask("anotate", …)` returns an empty list, a module that spelled its method
`on_reading_recorded` where the asker said `reading_recorded` is never told, and nothing in
the T-Box says what questions exist — the [choir](/domain/choir.md) page had to keep a roster
by hand.

# What is decided

**A hook is an `ag:Hook`, declared by whoever owns the question.** The kernel's ontology
declares the BDI-shaped ones — `ag:desires`, `ag:desireUrgency`, `ag:size`, `ag:take`,
`ag:reports`, `ag:series`, `ag:notices`, `ag:quiet`, `ag:beliefRevised` — and the three the
mailbox needs a word for, `ag:subscriptions`, `ag:handle`, `ag:send`: the QUESTION is the
kernel's (something can be sent, something can be handled), what carries it is the
transport's. Sensing declares its verdicts on a reading — `sensing:annotate`, `sensing:bounds`,
`sensing:urgency`, `sensing:readingRecorded` — and reporting declares `reporting:record`. A
package answering another package's hook spells the term as every cross-package reference is
spelled: bidding answers `sensing:urgency` for a held claim.

**A module answers by decoration, and inherits by name.** `@hook(term)` on a method; the
kernel's defaults on `Module` carry the kernel's terms, so a package overriding `reports` by
name answers `ag:reports` without saying so. `Module.answer(term)` resolves through the MRO.

**The runtime refuses what nobody declared.** `Agent.ask` and `Agent.tell` hold the term to
`loader.hooks()`, every `ag:Hook` in every ontology; an undeclared term raises rather than
returning nothing. `tests/test_hooks.py` holds every decorated term to the same set.

# What did not change

The askers, the answerers and the merging rules. What was `ask("reports")` is
`ask(REPORTS)`; the module list is still the registry; reporting still merges.

# Seams left open

- **A hook's signature is not in the ontology.** The term says the question exists and whose
  it is; what it is asked with is still the docstring's. SHACL could describe it; nothing reads
  that yet.
- **`take` and `size` are declared and asked by method**, of a family's providers rather than
  of the choir — an actor's contract. Declared so the roster is complete; the dispatch stays
  `ag:takenBy`'s.
