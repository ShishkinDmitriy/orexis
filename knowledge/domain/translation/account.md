---
type: Domain Concept
title: Account
description: >-
  What an agent says of itself for a person - each loaded package's account.rq, a SELECT shipped
  beside its ontology, asked over the graphs it says it reads when a person asks, a line per row
  under its title. Stored nowhere; telemetry, never a belief.
---

# What it is

An **account** is what an agent says of itself for a person, read off its store when asked. Every
package with something to say ships an `account.rq` beside its ontology:

```sparql
# observes
# reads: sensing:ObservationGraph
SELECT ?observed ?of ?reading ?sensor ?at WHERE { … }
```

The first comment line is the section's title; the `# reads:` line names the kinds of graph the
select is handed as its default graph, as every reader states the kinds it reads
([a-reader-states-the-kinds-it-reads](/decisions/a-reader-states-the-kinds-it-reads.md)). Sensing's
says the latest percept of each sensor, the one no later percept names as `sensing:previous`;
execution's says each intention standing, the want it pursues and the step it is at. A package that
ships none says nothing, and planning ships none yet.

`agent/translation/account.py` asks each loaded package's select over the beliefs and the intentions,
and writes a line per row: `name: value`, an IRI by its local name, an instant to the minute.
Nothing is written to the store and nothing is published: the account is **telemetry**, since no plan
branches on what the agent said of itself
([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)).

# Who reads it

The [translator](/domain/translation/translator.md): `/account` in a chat is answered with it as it
stands, and a question in words is handed to the model beside it, to be answered from it alone and
to say where it does not say.
