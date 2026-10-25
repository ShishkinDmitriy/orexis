---
type: Domain Concept
title: View
term: http://example.org/orexis/onboarding#ViewGraph
description: >-
  How a domain's history is drawn in a replay, stated by the domain as a document of onboarding's kind
  beside its ontology - a view of a kind orexis-replay renders, saying in the domain's own words which
  of the history's points place what on it. The grid is the one kind today; no agent loads a view.
---

# What it is

A **view** is a domain's word on how its history looks. `orexis-replay` draws a run from the agents'
[series](/domain/kernel/series.md) — never a belief — and the part of it every world shares is the
same for all: a scrubber over every instant, a pane per agent, and what the agent did at that instant
in the history's own tags. What a domain adds is a picture: the courier's road is a grid, and a run
on it is read best as vans moving on cells. A domain is documents and no code, so it says that in a
document of kind `onboarding:ViewGraph`, imported from its ontology as its requirements are
(`domains/courier/views.ttl`), and the tool brings the renderer for each kind of view. No agent loads
a view graph: its kind is onboarding's, read by the operator's tools alone.

# The grid

`onboarding:Grid` is a plane of whole numbers, an axis `onboarding:across` and an axis
`onboarding:down`. An axis says what places a thing on it in each kind of point the history holds,
each in the domain's own word:

| on an axis | the point | places |
|---|---|---|
| `onboarding:fixes` | an observation of the property | the observation's feature, where it reads |
| `onboarding:offsets` | an observation of the property | the observing sample, read from the thing hosting it as that thing is fixed — drawn as the thing it is a sample of, and not at all outside the range its sensor declares |
| `onboarding:moves` | a step's taking and a plan's step, by the parameter | where the step puts its thing |
| `onboarding:holds` | a holding coordination asked with or laid, by the key predicate | the holding's thing |

So at each instant a pane holds each thing as fixed and as seen, the plan's steps not yet walked, the
step in flight, what the agent asked with, what it laid of its peers as they said it and as it foresaw
them, and its conflicts. Two panes disagreeing about where a van stands is what a replay is for: each
shows what its agent believed.

A world whose domains state no view is drawn by the core alone; a kind of view the core lacks — a line
of a reading over time, say — is a renderer added to the tool once, after which any domain can state one.
