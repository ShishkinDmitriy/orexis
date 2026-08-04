# One image, every agent. Which agent a container IS comes from AGORA_AGENT_ID at run time —
# the same single identifier a process has always been given. Nothing is baked in per agent.
#
# The whole repo layout is present because `agora.loader` discovers capabilities, transports
# and the domain by looking at directories; a build that copied only backend/ would come up
# with no capabilities and an agent that can do nothing.

FROM docker.io/library/python:3.13-slim

# Fuseki and the broker are reached over the network; nothing here needs a compiler.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so editing a capability does not reinstall the world.
COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/src/agora/__init__.py backend/src/agora/__init__.py
RUN pip install -e ./backend

# The trees the loader discovers. Each is a mount point in dev (see the generated compose),
# so a code change needs a restart rather than a rebuild.
COPY kernel/       kernel/
COPY capabilities/ capabilities/
COPY transports/   transports/
COPY domain/       domain/
COPY genesis/      genesis/
COPY backend/      backend/

# An agent runs as nobody in particular. Its belief base is a file in its own volume, which
# nothing outside this container can name — that is the isolation, and it needs no credential
# and no access registry, because there is no shared store to be let into.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin agora \
 && chown -R agora:agora /app
USER agora

# No default command: the compose file says whether this container seeds or is an agent.
