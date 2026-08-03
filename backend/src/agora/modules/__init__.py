"""Capability modules — one per ontology module.

A module is the code half of a capability. Its ontology module (`ontology/<name>.ttl`) defines
the vocabulary, its shapes module (`shapes/<name>.ttl`) defines the rules, and the class here
reads *only* those terms. Composing the capability onto an agent in the world is what makes
this code run for that agent.

To add one — say, forecasting — you write `ontology/forecast.ttl` defining `ag:Forecasting`
and its terms, `shapes/forecast.ttl` requiring the beliefs it needs, `rules/forecast.ru`
deriving it from wiring, a `Module` subclass here, and one line of registry. No existing
module changes, and no agent gains the capability until genesis derives it.

Adding a *transport* is a smaller thing and deliberately so: a `Driver` in drivers.py plus
its terms and completeness rules. No capability, no module, no belief changes — because how
a device is reached is not something an agent decides.
"""

from __future__ import annotations

from .actuation import ActuationModule
from .base import Module
from .bidding import BiddingModule
from .hosting import HostingModule
from .perception import ListeningModule, PerceptionModule, PollingModule

REGISTRY: dict[str, type[Module]] = {
    m.CAPABILITY: m
    for m in (PollingModule, ListeningModule, BiddingModule, HostingModule, ActuationModule)
}

__all__ = ["REGISTRY", "Module", "PerceptionModule", "PollingModule", "ListeningModule",
           "BiddingModule", "HostingModule", "ActuationModule"]
