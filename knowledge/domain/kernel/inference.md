---
type: Service
title: Inference
description: >-
  The boot's closure of the vocabulary: every `rdfs:subClassOf` across every ontology graph,
  materialised into one graph the runtime derives, so that a reader asks what a thing IS and walks
  no subclass path. Rebuilt at every boot, since an ontology may have changed.
---

# What it does

After the ontology graphs are read and before anything else, the [runtime](/domain/kernel/runtime.md)
forgets the closure graph and writes it again: one `rdfs:subClassOf` triple for every pair the
vocabulary relates, however many steps apart, classified `orexis:OntologyGraph` and
`orexis:Derived`. The catalogue then closes its rows, so every graph carries every kind its class is
beneath (`store.closed`, `store.close_catalogue`).

# Why it is materialised

A query that walked `rdfs:subClassOf*` by hand was a query that had to remember to; one that asks
`?g a orexis:StateGraph` reads a sensing observation graph as a state graph because the closure
already said so. Subclass closure is the one entailment built — nothing else of RDFS or OWL is
computed, and a domain that needs a conclusion states a rule, which the
[deliberator](/domain/belief/deliberator.md) runs as a [revision](/domain/belief/revision.md).
