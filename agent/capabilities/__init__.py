"""What an agent can DO — one directory per capability, discovered by looking.

Inside `agent/` because only an agent runtime loads this Python. Onboarding reads these
packages' `ontology.ttl`, `shapes.ttl` and `rules.ru`, which it finds through the loader
wherever they live; it never imports a module from here.
"""
