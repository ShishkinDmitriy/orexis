"""The manifest: what this capability contributes to a build.

Two of the three perception capabilities. `perception:Polling` is declared in the vocabulary and
deliberately absent here: it needs a device that is reachable at any moment, and nothing in
this world is. Adding it later is a class and one line of PROVIDES — no other package moves.
"""

from .module import ListeningModule, PerceptionModule, SubscribingModule
from .terms import LISTENING, PERCEPTION, POLLING, SUBSCRIBING

PROVIDES = (SubscribingModule, ListeningModule)

__all__ = ["PROVIDES", "PerceptionModule", "SubscribingModule", "ListeningModule",
           "PERCEPTION", "POLLING", "SUBSCRIBING", "LISTENING"]
