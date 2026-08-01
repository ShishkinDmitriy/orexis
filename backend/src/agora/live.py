"""A live round, end to end against the running gateway.

  sensor -> gateway -> Fuseki :attested  ->  agents read + bid  ->  host proposes  ->
  clearing validates + issues grants.

Reads each plant's attested moisture, has the agents bid deterministically, and runs one
round through the host + clearing. No LLM; the number is code.
"""

from __future__ import annotations

import logging

from . import config
from .agent import load_agents
from .auction import run_round
from .beliefs import Beliefs
from .market import Limits, MarketState, Offer

log = logging.getLogger("live")


def run_live_round() -> None:
    cfg = config.load_plants()
    agents = load_agents(cfg)
    sup = cfg["supplier"]
    beliefs = Beliefs(config.env("FUSEKI_URL", "http://localhost:3030/ds"))

    bids = []
    for a in agents:
        moisture = beliefs.current_moisture(a.charter.plant_uri)
        if moisture is None:
            log.warning("%-9s no attested moisture yet — skipping", a.charter.agent)
            continue
        bid = a.bid(moisture)
        log.info(
            "%-9s moisture=%.3f target=%.2f -> %s",
            a.charter.agent, moisture, a.charter.target,
            f"bid {bid.max_qty_l} L @ €{bid.max_price_per_l}" if bid else "cede",
        )
        if bid is not None:
            bids.append(bid)

    if not bids:
        log.info("no bids above reserve — no auction (dispense or wait)")
        return

    state = MarketState(
        bids={b.agent: b for b in bids},
        wallets={a.charter.agent: a.balance for a in agents},
        certified=frozenset({sup["id"], *(a.charter.agent for a in agents)}),
        limits=Limits(tank_capacity_l=sup["tank_capacity_l"], rot_headroom_l={}),
    )
    offer = Offer(
        supplier=sup["id"],
        quantity_l=sup["quantity_l"],
        reserve_price_per_l=sup["reserve_price_per_l"],
    )

    result = run_round(offer, bids, state, round_id="live")
    if not result.validation.ok:
        log.warning("clearing RED — rejected: %s", result.validation.violations)
        return
    log.info("clearing GREEN — %d grant(s), %.3f L allocated:",
             len(result.grants), result.trade.total_qty_l)
    for g in result.grants:
        log.info("  grant: %-9s %.3f L  debit €%.2f", g.sub, g.amount_l, g.debit)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_live_round()


if __name__ == "__main__":
    main()
