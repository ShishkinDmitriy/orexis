---
type: Domain Concept
title: Extraction
term: http://example.org/orexis/speech#Extraction
description: >-
  What the agent comes to believe of a statement - a domain's construct, run by speech over the one
  statement and the world's documents, never over what was believed before, written into one belief
  graph derived from the statement, the agent's own, over its period. As sensing revises a percept,
  speech extracts from what was said; heard and said alike.
---

# What it is

```turtle
market:believed a speech:Extraction ;
    sh:construct """CONSTRUCT { ?s ?p ?o } WHERE {
        ?s a ?class ; ?p ?o .
        VALUES ?class { market:Call market:Round market:Bid market:Claim market:Presentation } }""" .
```

An **extraction** is a rule a domain ships in its rules graph, saying what an
[statement](/domain/speech/statement.md) makes the agent believe: an `sh:construct`, typed
`speech:Extraction`, beneath `sh:Rule` and not `sh:SPARQLRule`, so [revision](/domain/belief/revision.md)
and planning's bridge reader pass over it as they pass over a [transition](/domain/belief/transition.md).

# How it is run

Speech runs every extraction over one statement and the world's documents beside it
(`agent/speech/extract.py`), when the statement is written, heard or said: the agent believes the round
it opened as its bidders believe the round they heard, by one path. What they construct goes into one
belief graph derived from the statement (`prov:wasDerivedFrom`), the agent's own, arrived
`orexis:Derived`, holding over the statement's period, and gone when it is said again or forgotten. The
runtime then hands that belief to revision as it hands any belief, so a domain's inferences conclude of
it: the market's venue open, call answered, claim held.

# Why not a transition

A transition reads its arrival beside the agent's own state, so a rule restating what a document says
would restate what earlier documents said as well, and carry a round's lot into the belief made of a
claim. An extraction reads what was said alone. An inference cannot either: what it infers is what the
graph it reads does not already hold, and a statement it reads holds what it says.

# What it concludes, and what it leaves

A belief, today. A prediction — a peer's announced route, where the peer expects to be — is what a
drift would make of a belief extracted from it, built with the first world that says one (#568).
Nothing is believed of a statement no extraction concludes of: a peer saying the agent's bed is dry
changes no met-test unless a rule the agent holds extracts it.
