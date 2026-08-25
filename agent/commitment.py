"""A commitment — REA's promised economic flow, and the shape a valve fulfils.

`settlement-speaks-rea` aligned the market to ValueFlows and found the correction: what you
win in an auction is not a claim but a **commitment** — "a planned economic flow", fulfilled
by the economic event of a valve opening. The market's `Claim` is its embodiment (it adds the
credit leg and, on the wire, the signatures); a self-dose (#190) is one with nobody to pay.

KERNEL, and the reason is the independence contract: actuation fulfils commitments and may not
import the market's Python, the market issues them and may not import actuation's, so the
shape both hold is the kernel's — BDI's structure holds an intention (the agent's own
commitment, `ag:Intention`) and REA's holds this one. Two words for two things, as
a-mandate-is-not-a-commitment ruled. See knowledge/domain/commitment.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Commitment:
    """A promised flow: who it is for, what it permits, how much, from which round, once."""

    sub: str          # whose subject the flow reaches — the buyer, or the self-dosing agent
    scope: str        # what the token permits — a valve, or "actuate:self"
    amount_l: float   # the flow, in the good's unit (litres here; the domain is a plug-in)
    auction_id: str   # the round it was won in, or a self-minted id — never a bidding pass
    jti: str          # anti-replay id
    #  When the venue stops holding it, in epoch seconds — JWT's word, as `jti` is. None
    #  means a market that named no window.
    exp: float | None = None
