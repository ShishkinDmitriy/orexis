"""The manifest: what this capability contributes to a build.

One way of keeping commitments — by rule, with a patience clock. A member that weighed a
commitment against what has changed since it was made (the open-minded commitment of the BDI
literature, and the natural seat for a model's judgement) would be a second, and is deliberately
not declared yet: unlike `desire:Consulting`, nothing has even sketched what it would read, and
a reserved term nobody has an argument about is speculation rather than honesty. Adding it is a
class and one line of `PROVIDES`; no other package moves.
"""

from .graphs import intentions_graph
from .module import IntentionModule, KeepingBeliefs, Standing
from .terms import ACQUIRE, APPLY, INTENTION, KEEPING, OBSERVE

PROVIDES = (IntentionModule,)

__all__ = ["PROVIDES", "IntentionModule", "KeepingBeliefs", "Standing", "intentions_graph",
           "INTENTION", "KEEPING", "OBSERVE", "ACQUIRE", "APPLY"]
