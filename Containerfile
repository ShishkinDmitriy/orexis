# One image, every agent. Which agent a container IS comes from AGORA_AGENT_ID at run time —
# the same single identifier a process has always been given. Nothing is baked in per agent.
#
#   podman build -t agora:local .
#
# THE COPY LIST IS THE BOUNDARY. There is one distribution now, so nothing about pip keeps the
# operator's tools out of an agent: `onboarding/` is absent because it is not named below, and
# for no other reason. tests/test_layout.py asserts exactly that, and fails if a line is added
# here — which is the whole reason two directories were collapsed into one distribution. What
# used to be implied by packaging is stated in one place and checked.

FROM docker.io/library/python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so editing a capability does not reinstall the world.
COPY pyproject.toml pyproject.toml
COPY agent/__init__.py agent/__init__.py
RUN pip install -e .

# Everything an agent runs, and nothing else.
#
# Two trees: the KERNEL that loads packages, and the packages. `packages/` holds both what an
# agent imports and what it merely reads — a capability's Python and a part's ontology sit in one
# tree now — and it is copied whole because onboarding derives capabilities from the same terms
# and neither side owns it.
#
# WHAT KEEPS ONBOARDING OUT IS THIS FILE NOT NAMING IT, and that is the only thing that does.
# It used to be reinforced by a directory: capability Python lived under `agent/`, so the tree
# showed which of it a runtime loads. It does not show that any more, which makes this line and
# the import contracts in pyproject.toml the whole of the boundary rather than a reminder of it.
# tests/test_layout.py fails if a `COPY onboarding/` ever appears.
#
# Note what is NOT here: world/. A world is MOUNTED, one per container, so the image is
# world-agnostic — the same image is every agent of every world, and which one it is comes from
# AGORA_AGENT_ID and the world mounted beside it.
COPY agent/    agent/
COPY packages/ packages/

# An agent runs as nobody in particular. Its belief base is a file in its own volume, which
# nothing outside this container can name — that is the isolation, and it needs no credential
# and no access registry, because there is no shared store to be let into.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin agora \
 && chown -R agora:agora /app
USER agora

# No default command: the compose file says whether this container seeds or is an agent.
