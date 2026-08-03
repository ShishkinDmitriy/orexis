"""The manifest: what this capability contributes to a build.

Two modules, one capability each. The loader reads this and nothing else — which is why
adding a capability never edits a registry.
"""

from .module import ListeningModule, PerceptionModule, PollingModule
from .terms import LISTENING, PERCEPTION, POLLING

PROVIDES = (PollingModule, ListeningModule)

__all__ = ["PROVIDES", "PerceptionModule", "PollingModule", "ListeningModule",
           "PERCEPTION", "POLLING", "LISTENING"]
