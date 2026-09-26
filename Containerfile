# One image, every agent. Which agent a container IS comes from the id its command is given —
# the single identifier a process has always been told. Nothing is baked in per agent.
#
#   podman build -t orexis:local .
#
# THE COPY LIST IS THE BOUNDARY. There is one distribution, so nothing about pip keeps the
# operator's tools out of an agent: `onboarding/` is absent because it is not named below, and
# for no other reason. tests/test_layout.py asserts exactly that, and fails if a line is added
# here.

FROM docker.io/library/python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so editing the agent does not reinstall the world. This layer holds the
# THIRD-PARTY set — pyoxigraph, rdflib, paho and the rest — and changes only when the root's
# dependency list does.
COPY pyproject.toml pyproject.toml
RUN pip install "setuptools>=68" && pip install -e .

# Everything an agent runs, and nothing else: the runtime, the domains its worlds import — a world
# is mounted at /app/world/<name>, so its `owl:imports <../../domains/...>` resolve to
# /app/domains — and the simulator, a process of a world that plays the systems it says no one
# built. Not world/: a world is MOUNTED, one per container, so the image is world-agnostic.
COPY agent/ agent/
COPY domains/ domains/
COPY simulation/ simulation/
# The editable install again, now that the trees it maps are here; no network, no dependencies.
RUN pip install --no-build-isolation --no-deps -e .

# An agent runs as nobody in particular. Its belief base is a file in its own volume, which
# nothing outside this container can name — that is the isolation, and it needs no credential
# and no access registry, because there is no shared store to be let into.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin orexis \
 && chown -R orexis:orexis /app
USER orexis

# No default command: the compose file says whether this container is an agent or the simulator.
