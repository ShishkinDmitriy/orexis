# One Containerfile, an image per agent. Which agent a container IS comes from the id its command is
# given — the single identifier a process has always been told. What is baked in is what that agent
# runs: the kernel, the packages it loads and those their code imports (`PACKAGES`), the libraries
# those bring (`EXTRAS`), and the simulator where the image is the simulator's (`SIMULATOR`).
# `orexis-compose` writes each service's build with them, so an observer's container holds no
# planning code and an agent on no bus no MQTT client
# (knowledge/decisions/a-package-brings-its-own-dependencies.md).
#
#   cd world/<name> && podman compose build
#
# THE COPY LIST IS THE BOUNDARY. There is one distribution, so nothing about pip keeps the
# operator's tools out of an agent: `onboarding/` is absent because it is not named below, and
# for no other reason. tests/test_layout.py asserts exactly that, and fails if a line is added
# here.

# ── the source, laid out as this image keeps it ─────────────────────────────────────────────────
# `python -m agent.tree`, the standard library alone, copies the kernel and the packages named, the
# domains and the simulator where asked, and beside them the distribution's metadata with every
# extra's dependency file, which setuptools reads to know the extras. Nothing of this stage but what
# it lays out reaches the image.
FROM docker.io/library/python:3.13-slim AS source

WORKDIR /src
COPY pyproject.toml pyproject.toml
COPY agent/ agent/
COPY domains/ domains/
COPY simulation/ simulation/
ARG PACKAGES=""
ARG SIMULATOR="no"
RUN python -m agent.tree /src /out "$PACKAGES" "$SIMULATOR"

# ── the image ───────────────────────────────────────────────────────────────────────────────────
FROM docker.io/library/python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so editing the agent does not reinstall the world. This layer holds the
# THIRD-PARTY set — the core's, pyoxigraph and rdflib, and the extras named — and changes only when
# the dependency files or the extras do.
ARG EXTRAS=""
COPY --from=source /out/deps/ ./
RUN pip install "setuptools>=68" && pip install -e ".${EXTRAS:+[$EXTRAS]}"

# Everything this agent runs, and nothing else: the runtime and its packages, the domains its worlds
# import — a world is mounted at /app/world/<name>, so its `owl:imports <../../domains/...>` resolve to
# /app/domains — and the simulator where the image is its. Not world/: a world is MOUNTED, one per
# container, so the image is world-agnostic.
COPY --from=source /out/trees/ ./
# The editable install again, now that the trees it maps are here; no network, no dependencies.
RUN pip install --no-build-isolation --no-deps -e .

# An agent runs as nobody in particular. Its belief base is a file in its own volume, which
# nothing outside this container can name — that is the isolation, and it needs no credential
# and no access registry, because there is no shared store to be let into.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin orexis \
 && chown -R orexis:orexis /app
USER orexis

# No default command: the compose file says whether this container is an agent or the simulator.
