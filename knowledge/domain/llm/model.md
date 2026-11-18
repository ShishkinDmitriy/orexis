---
type: Domain Concept
title: Model
term: http://example.org/orexis/llm#Model
description: >-
  A language model the world is connected to, `llm:Model`: a role that asks one names it, onboarding says where
  it answers, and the package playing the role reads both as it starts; which model it is and its key stay the
  agent's secret, and a role naming none asks nobody.
---

# What it is

What a role asks at a run-time edge: Anthropic's API today, asked by a [translator](/domain/translation/translator.md)
alone. It is linked the way a [tracer](/domain/journal/tracer.md) is, by a link on the role and an address onboarding
derives, and this page says only what differs.

Its words are a family's, `orexis-llm/`, which registers no package, as the transport family's crate registers
none: the client a package asks a model through and `llm:`, which a package asking one brings beside its own as it
joins (`Handed::joins_with`). What the model is told and as which role are the asking package's words, a translator's
prompts and its chats' [style](/domain/translation/style.md) among them.

# The link

A role names the model it asks by a link of its package's, a translator's `translation:translatedBy`:

```turtle
:terrace_agent orexis:plays [ a translation:Translator ; translation:translatedBy :model ] .
```

The address onboarding gives the named node is the installation's one `onboarding:Model`'s, stated in the derived
deployment as an `llm:Model` with its `schema:url`. A translator's role with no such link is refused at onboarding by
the package's own shape, since it would keep a person's words and say nothing back.

# How it is asked

A call is awaited on the agent's runtime, over `reqwest`, as a task of the asking package's; how long one may take and
how often a failing one is asked again are the asking role's to say,
`llm:calledWithinS` and `llm:retries`, sixty seconds and three where it says none, the defaults `llm:`'s ontology
states for any role; each is held at onboarding to one value of its kind.

# What stays secret

Which model it is and the key that opens it: `MODEL_NAME` and `MODEL_API_KEY` in `infra/secrets/model.env`,
mounted into each translating agent's container and no other. The asking package makes its client from those and
the address, in a deployed agent alone; a check and a test are handed a model or have none, so neither calls one.
