---
type: Domain Concept
title: Model
term: http://example.org/orexis/translation#Model
description: >-
  The language model a translator asks. Its role names one, onboarding says where that one answers, and the
  translation package reads it as it starts; which model it is and its key stay the agent's secret, and a
  translator naming none answers nobody.
---

# What it is

What a [translator](/domain/translation/translator.md) asks at its three edges: Anthropic's API today. It is
linked the way a [tracer](/domain/journal/tracer.md) is, by a link on the role and an address onboarding derives,
and this page says only what differs.

# The link

`translation:translatedBy`, on the translator's role in the agent's self graph:

```turtle
:terrace_agent orexis:plays [ a translation:Translator ; translation:translatedBy :model ] .
```

The address onboarding gives the named node is the installation's one `onboarding:Model`'s. A translator's role
with no such link is refused at onboarding by the package's own shape, since it would keep a person's words and
say nothing back.

# What stays secret

Which model it is and the key that opens it: `MODEL_NAME` and `MODEL_API_KEY` in `infra/secrets/model.env`,
mounted into each translating agent's container and no other. `orexis-translation/` makes its client from those and
the address, in a deployed agent alone; a check and a test are handed a model or have none, so neither calls one.
