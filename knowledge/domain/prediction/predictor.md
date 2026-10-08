---
type: Role
title: Predictor
term: http://example.org/orexis/prediction#Predictor
description: >-
  An agent that foresees its readings by the drifts - the role whose part is prediction's. Declared
  in the agent's self graph; it needs a sensor of the agent's and a drift. A drift no predictor reads
  is not refused, since foresight is the author's to decline.
---

# Who is one

An agent stated `prediction:Predictor` beside its self. Declaring it loads the
[prediction](/domain/prediction/prediction.md) package, whose part answers every observation written
with the stretches ahead. Every shipped predictor is an [observer](/domain/sensing/observer.md) too,
since the observation it accumulates from is sensing's to write; the role is not beneath the
observer's, so nothing but the author's declaration says both.

# What it needs, and what it does not

A sensor of the agent's and a `prediction:Drift`, a shape prediction ships beside the role; an agent
declared a predictor in a world stating neither is refused at onboarding.

The other way round is NOT refused. A world may ship drifts — a domain's `drifts.ttl` imported for
its actions — whose agents foresee nothing; declining foresight is the author's choice, and refusing
it would make the declaration a premise restated
([a-package-is-loaded-only-for-a-role-the-agent-is-declared-in](/decisions/a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md)).
