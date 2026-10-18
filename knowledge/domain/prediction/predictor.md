---
type: Role
title: Predictor
term: http://example.org/orexis/prediction#Predictor
description: >-
  An agent that foresees its readings by the flows - the role whose part is prediction's. Declared
  in the agent's self graph; it needs a sensor of the agent's and a flow. A flow no predictor reads
  is not refused, since foresight is the author's to decline.
---

# Who is one

An agent stated `prediction:Predictor` beside its self. Declaring it loads the
[prediction](/domain/prediction/prediction.md) package, whose part offers the planner the integration
of the flows, advanced ground by ground as the grounds are laid (#1000). Every shipped predictor is an
[observer](/domain/sensing/observer.md) too, since the observation it integrates from is sensing's to
write; the role is not beneath the observer's, so nothing but the author's declaration says both. A
predictor that is no [planner](/domain/planning/planner.md) foresees for nobody: the part is made and
nothing takes what it offers.

# What it needs, and what it does not

A sensor of the agent's and a `prediction:Flow`, a shape prediction ships beside the role; an agent
declared a predictor in a world stating neither is refused at onboarding. Nothing else: flows that
read each other - the soil moving by the air and the air by the soil - are coupled flows, every key
advancing together from one ground, and were refused as a cycle only while the keys were predicted
one at a time (#996, undone by #1000).

The other way round is NOT refused. A world may ship flows — a domain's `flows.ttl` imported for
its actions — whose agents foresee nothing; declining foresight is the author's choice, and refusing
it would make the declaration a premise restated
([a-package-is-loaded-only-for-a-role-the-agent-is-declared-in](/decisions/a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md)).
