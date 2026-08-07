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
# `agent/` now carries capabilities and transports with it — they are its subpackages, loaded
# only by a runtime — so the list that used to name five trees names two.
#
# `vocabulary/` stays out of it because it is genuinely shared: onboarding validates worlds and
# derives capabilities from the same terms, so it belongs to neither side.
#
# Note what is NOT here: world/. A world is MOUNTED, one per container, so the image is
# world-agnostic — the same image is every agent of every world, and which one it is comes from
# AGORA_AGENT_ID and the world mounted beside it.
COPY agent/      agent/
COPY vocabulary/ vocabulary/

# An agent runs as nobody in particular. Its belief base is a file in its own volume, which
# nothing outside this container can name — that is the isolation, and it needs no credential
# and no access registry, because there is no shared store to be let into.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin agora \
 && chown -R agora:agora /app
USER agora

# No default command: the compose file says whether this container seeds or is an agent.
