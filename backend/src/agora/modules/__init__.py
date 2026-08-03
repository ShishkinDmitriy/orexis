"""Capability modules — one per ontology module.

A module is the code half of a capability. Its ontology module (`ontology/<name>.ttl`) defines
the vocabulary, its shapes module (`shapes/<name>.ttl`) defines the rules, and the class here
reads *only* those terms. Composing the capability onto an agent in the world is what makes
this code run for that agent.

To add one — say, forecasting — you write `ontology/forecast.ttl` defining `ag:Forecasting`
and its terms, `shapes/forecast.ttl` requiring the beliefs it needs, a `Module` subclass here,
and one line of registry. No existing module changes, and no agent gains the capability until
genesis composes it.
"""

from __future__ import annotations

from .actuation import ActuationModule
from .base import Module
from .bidding import BiddingModule
from .hosting import HostingModule
from .polling import ListeningModule, PollingModule

REGISTRY: dict[str, type[Module]] = {
    m.CAPABILITY: m
    for m in (PollingModule, ListeningModule, BiddingModule, HostingModule, ActuationModule)
}

__all__ = ["REGISTRY", "Module", "PollingModule", "ListeningModule", "BiddingModule",
           "HostingModule", "ActuationModule"]
