"""The manifest: what this capability contributes to a build.

One of the two ways of reporting. `reporting:Announcing` — putting the account on the bus rather
than in a series bucket — is declared in `ontology.ttl` and deliberately absent here, exactly as
`review:Consulting` and `perception:Polling` are: the vocabulary should be honest that the sink is
the replaceable part, but nothing implements this one yet. Adding it is a class and one line of
`PROVIDES`; no other package moves.

The two would fail independently, which is the reason it is the member worth building next — and
also its limit: a member reporting over the bus cannot report having lost the bus.
"""

from .module import StoringModule
from .terms import ANNOUNCING, INTERVAL_S, REPORTING, STORING

PROVIDES = (StoringModule,)

__all__ = ["PROVIDES", "StoringModule", "REPORTING", "STORING", "ANNOUNCING", "INTERVAL_S"]
