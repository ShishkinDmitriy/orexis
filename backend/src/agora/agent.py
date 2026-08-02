"""Plant agent — the only tier with a stake (a desire + a wallet).

v1 is deliberately LLM-free: the **bid is deterministic code** (this value model over
attested moisture, target, and prior allocation), and the LLM — when added later — produces
only the *stance/justification*, never the number. Stub the LLM out and the agent still
transacts on its deterministic bid.

See knowledge/domain/agent.md, knowledge/domain/plant-agent.md,
knowledge/decisions/deterministic-bid.md, knowledge/decisions/bids-as-unmet-demand.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config
from .market import EPS, Bid
from .ontology import band_for


@dataclass(frozen=True)
class Charter:
    """Static identity + chartered desire. The agent does not invent new desires."""

    agent: str
    plant_uri: str
    species: str
    target: float  # desired moisture fraction (the desire)
    endowment: float  # starting credits
    litres_per_fraction: float  # L to raise moisture by 1.0
    max_value_per_l: float  # €/L willingness at peak urgency
    low: float  # below this the agent judges itself LOW (its own band)
    high: float  # above this, HIGH


def value_bid(
    current_moisture: float,
    charter: Charter,
    balance: float,
    allocated_l: float = 0.0,
) -> Bid | None:
    """Deterministic willingness-to-pay. Returns None to cede (no bid).

    - deficit below target drives both the litres demand and the urgency (price);
    - the bid is a function of *unmet* demand (demand minus what was already allocated);
    - qty is capped by affordability so the bid stays solvent.
    """
    deficit = charter.target - current_moisture
    if deficit <= 0:  # at or above target — cede (a reflex)
        return None

    demand_l = deficit * charter.litres_per_fraction
    unmet_l = demand_l - allocated_l
    if unmet_l <= EPS:
        return None  # prior allocation already covers the need

    urgency = min(1.0, deficit / charter.target)  # 0..1, drier = higher
    price = charter.max_value_per_l * urgency
    if price <= EPS or balance <= EPS:
        return None  # broke or negligible value — cede

    affordable_l = balance / price
    qty = min(unmet_l, affordable_l)
    if qty <= EPS:
        return None

    return Bid(agent=charter.agent, max_qty_l=round(qty, 3), max_price_per_l=round(price, 3))


@dataclass
class Agent:
    """A staked participant: its charter, wallet balance, and deterministic bid."""

    charter: Charter
    balance: float

    @classmethod
    def from_charter(cls, charter: Charter) -> "Agent":
        return cls(charter=charter, balance=charter.endowment)

    def band(self, current_moisture: float) -> str:
        """The agent's own LOW/OK/HIGH judgment — desire-relative, from its charter.
        The gateway attests the number; the verdict is the agent's."""
        return band_for(current_moisture, self.charter.low, self.charter.high)

    def bid(self, current_moisture: float, allocated_l: float = 0.0) -> Bid | None:
        return value_bid(current_moisture, self.charter, self.balance, allocated_l)


def load_charters(cfg: dict | None = None) -> list[Charter]:
    """Build charters from plants.yaml (plant list + shared value_model)."""
    cfg = cfg or config.load_plants()
    vm = cfg["value_model"]
    return [
        Charter(
            agent=p["id"],
            plant_uri=p["uri"],
            species=p["species"],
            target=p["target"],
            endowment=p["endowment"],
            litres_per_fraction=vm["litres_per_fraction"],
            max_value_per_l=vm["max_value_per_l"],
            low=p["low"],
            high=p["high"],
        )
        for p in cfg["plants"]
    ]


def load_agents(cfg: dict | None = None) -> list[Agent]:
    return [Agent.from_charter(c) for c in load_charters(cfg)]
