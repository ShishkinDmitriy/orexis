"""How bytes become a DOCUMENT — one directory per wire format, discovered by looking.

The first of the three stages a reading passes through: codec, then pointer, then scaling.
Borne by a binding rather than by an agent, so a member is chosen at runtime from what the
sensor declares and nothing is derived into the graph — see `packages/capability/sensing/codec.py` for why the bearer
is what decides that, and knowledge/decisions/bytes-become-a-quantity-in-stages.md for the rest.

Inside `agent/` for the same reason capabilities and transports are: only an agent runtime loads
this Python. Onboarding reads the `ontology.ttl` through the loader and imports nothing.
"""
