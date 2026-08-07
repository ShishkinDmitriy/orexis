"""The manifest: what this capability contributes to a build.

Two sides of one venue, and they are separate capabilities because they are separate
decisions: a bidder answers with a private number, a host runs the round. An agent may hold
either, both, or neither.
"""

from .bidding import BiddingModule, value_bid
from .hosting import HostingModule
from .terms import BIDDING, HOSTING

PROVIDES = (BiddingModule, HostingModule)

__all__ = ["PROVIDES", "BiddingModule", "HostingModule", "value_bid", "BIDDING", "HOSTING"]
