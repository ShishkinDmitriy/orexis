---
type: Domain Concept
title: Askable
term: http://example.org/orexis#Askable
description: >-
  A question a person may ask an agent about itself, declared by the package or domain whose words it is
  asked in - a node shape whose fields the asker fills, the kinds of graph it reads and the select the agent
  runs. Answered from the agent's own store, writing nothing; FIPA's query-ref, beside the sayable.
---

# What it is

```turtle
:viewings_offered a orexis:Askable , sh:NodeShape ;
    sh:description "the viewings offered for a listing, when, and by whom" ;
    sh:property [ sh:path :listing ; sh:class :Listing ; sh:minCount 1 ; sh:description "which listing" ] ;
    orexis:reads orexis:BeliefGraph ;
    orexis:select """SELECT ?at ?by WHERE { ?o a :ViewingOffer ; :listing $listing ; :at ?at ; speech:saidBy ?by }""" .
```

An **askable** is a question an agent can be asked and answers from what it holds. Its fields are declared as a
[sayable](/domain/speech/sayable.md)'s are, so the model is offered both kinds as tools alike; `orexis:reads`
names the kinds of graph its select is handed as the default graph, and `orexis:select` is the text, each filled
field bound into it as the `$` token of its local name. The asker picks it and fills it; the text is the
declaring package's, and the asker never writes it nor sees it. Nothing is written by an answer — every other act
is a statement, kept ([a-question-is-answered-and-every-other-act-is-kept](/decisions/a-question-is-answered-and-every-other-act-is-kept.md)).

# Who declares one

Whoever owns the words it is asked in, in an `orexis:AskableGraph` of its own. Sensing ships `observes`, the
latest reading of each sensor, and execution `does`, each intention standing, each in `askables.ttl` beside its
ontology and held only where the package is loaded; a domain or a world ships its own, as the viewing world asks
after the viewings a person's statement made it believe. The class is the kernel's because sensing and execution
may not speak translation's words, nor speech's.

# Who asks one

The [translator](/domain/translation/translator.md): a question in a chat is offered to the model with every
sayable and every askable as tools, and the rows of the one it calls are phrased back. `/status` answers with the
rows of every askable that takes no field, and asks no model. An answer is telemetry, never a belief
([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)).
