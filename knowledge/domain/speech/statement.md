---
type: Domain Concept
title: Statement
term: http://example.org/orexis/speech#StatementGraph
description: >-
  What was said, kept as it was said - one graph of a document a peer told the agent or the agent told
  a peer, heard arrived Received and said arrived Recorded, holding over the period it states. Handed
  to no reader of the mind; what the agent believes of it is what an extraction concludes. Whatever kind
  the document gives its graph, it is a statement, and only a kind beneath that is kept.
---

# What it is

```turtle
# a round, as its host said it — a statement, read by nothing the mind reads
<round-0042> a speech:StatementGraph , market:RoundGraph ; orexis:arrivedBy orexis:Received ;
    dcterms:temporal [ orexis:start "…12:00" ; orexis:end "…12:05" ] .
<round-0042> { <round-0042> a market:Round ; market:onVenue :water ; market:lotL 40 . }
```

An **statement** is a graph of a document, as a peer or the agent said it. A document names its
graphs and says in its default graph what each one is, as a world's files do; but a world's file is
asserted and a statement is testimony, so `heard` and `said` keep every graph of a document as an
statement (`agent/speech/statements.py`). It is the speech package's kind, beneath `orexis:Graph` alone,
as sensing keeps an [observation](/domain/sensing/observation.md): no reader of the mind is handed one.

# What it may say it is

Anything; what is kept is what was said. A kind the document gives its graph is kept only where it is
a kind of statement, as the market's round, call, bid, claim and presentation are; a peer typing its
graph an action graph, a desire, a belief or the world is kept as a statement and read by no planner,
executor or rule as any of those. Its other rows, its period first, stay as said.

# What is believed of it

What an [extraction](/domain/speech/extraction.md) concludes of it, alone, and nothing else. The
language a statement is in is the language the society speaks: the market speaks the triples its
agents believe, which is a coincidence of the market and no assumption of the layer
([a-peers-word-is-testimony-and-a-rule-makes-it-a-belief](/decisions/a-peers-word-is-testimony-and-a-rule-makes-it-a-belief.md)).
