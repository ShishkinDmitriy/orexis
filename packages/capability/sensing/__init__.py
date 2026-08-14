"""The manifest: what this capability contributes to a build.

Two of the three sensing capabilities. `sensing:Polling` is declared in the vocabulary and
deliberately absent here: it needs a device that is reachable at any moment, and nothing in
this world is. Adding it later is a class and one line of PROVIDES — no other package moves.
"""

from .module import ListeningModule, SensingModule, SubscribingModule
from .terms import LISTENING, SENSING, POLLING, SUBSCRIBING

PROVIDES = (SubscribingModule, ListeningModule)

__all__ = ["PROVIDES", "SensingModule", "SubscribingModule", "ListeningModule",
           "SENSING", "POLLING", "SUBSCRIBING", "LISTENING"]
