---
type: Role
title: Sovereign
description: >-
  Whoever writes a world's documents and stands behind them — its agents, subjects, wiring and
  desires. A role, not an agent: nothing in the society is sovereign, and what the sovereign
  authored arrives in each agent's store as `orexis:Asserted`, true by ratification rather than
  by argument.
---

# What it is

The person who authors `world/<name>/` and runs the operator's tools over it. What they write is
the only thing in an agent's store no one argues with: the loader classifies every document it
reads `orexis:Asserted`, beside `orexis:Derived` for what a rule concluded, `orexis:Received` for
what an instrument or a peer said and `orexis:Recorded` for the agent's own acts.

# What the role may and may not do

It picks: the ranges a subject needs, the value a litre is worth to a grower, the lot a supplier
puts up, a search's budget. It does not act: nothing a sovereign writes names a step, a dose or a
price paid — those are the agents' to find, which is the one move this architecture refuses
everywhere ([control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md)).

It is outside the society. No agent holds its credentials — the admin token that opens every
bucket lives in `infra/secrets/` and in code no image carries — and no agent is it.
