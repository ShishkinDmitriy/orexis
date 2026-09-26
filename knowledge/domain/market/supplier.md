---
type: Role
title: Supplier
description: >-
  The allotment's host - an agent acting for a water source, holding the valves that reach the
  growers' plots. It sells by the market and serves by its own devices, and it is the only agent
  that can open a valve, because it is the one that holds them.
---

# What it is

In `world/allotment` the supplier acts for the water source and hosts the venue the two growers bid
in. A grower that wins a claim still cannot water its fern: it holds no valve. What the supplier's
`market:Serving` does beside saying the claim discharged is an `execution:Command` to the valve that
reaches the holder's subject: the claim's litres as a dose, capped at what the valve may give
at once (`actuation:maxDoseMl`).

# What it shows

That the market is a domain and not a service: the supplier is an ordinary agent with two desires
([host](/domain/market/host.md)) and the market's six actions, and everything it does falls out of
planning for those desires over the documents its peers say.
