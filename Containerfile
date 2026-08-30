# One image, every agent. Which agent a container IS comes from OREXIS_AGENT_ID at run time —
# the same single identifier a process has always been given. Nothing is baked in per agent.
#
#   podman build -t orexis:local .
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

# Dependencies first, so editing a capability does not reinstall the world. This layer holds
# the THIRD-PARTY set — pyoxigraph, pyshacl, rdflib, cryptography and the rest — and it changes
# only when the root's dependency list does.
COPY pyproject.toml pyproject.toml
COPY agent/__init__.py agent/__init__.py
COPY assembly/__init__.py assembly/__init__.py
# The kernel's three LAYERS are packages the root depends on — the container's own declared
# dependencies are what load them until #455 (a-layer-is-a-package-and-need-loads-it) — and
# each depends back on the root for `assembly`, a knowing cycle through the shared
# distribution. So the four editables are installed in ONE pip call, which resolves each
# against the others instead of asking an index for any. Stubs suffice here as they do for
# agent/: an editable install maps the directory, and the code arrives with the full COPY below.
COPY packages/orexis-agent-reactive/pyproject.toml         packages/orexis-agent-reactive/pyproject.toml
COPY packages/orexis-agent-reactive/__init__.py            packages/orexis-agent-reactive/__init__.py
COPY packages/orexis-agent-progression/pyproject.toml   packages/orexis-agent-progression/pyproject.toml
COPY packages/orexis-agent-progression/__init__.py      packages/orexis-agent-progression/__init__.py
COPY packages/orexis-agent-deliberation/pyproject.toml    packages/orexis-agent-deliberation/pyproject.toml
COPY packages/orexis-agent-deliberation/__init__.py       packages/orexis-agent-deliberation/__init__.py
RUN pip install "setuptools>=68" && pip install -e . \
    -e packages/orexis-agent-reactive/ -e packages/orexis-agent-progression/ -e packages/orexis-agent-deliberation/

# Everything an agent runs, and nothing else.
#
# Three trees: what ASSEMBLES a build, the KERNEL it assembles onto, and the packages. `packages/` holds both what an
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
# OREXIS_AGENT_ID and the world mounted beside it.
COPY assembly/ assembly/
COPY agent/    agent/
COPY packages/ packages/

# EVERY PACKAGE IS A PROJECT, so every package is installed as one. Twenty-two package
# distributions, each claiming its own top-level module and none claiming `packages/`, which is
# what leaves room for a twenty-third installed from somewhere else.
#
# `--no-build-isolation` because the build backend is already here from the layer above, and
# without it pip would fetch setuptools twenty-two times over. `--no-deps` because this layer
# must not reach the network at all: everything these projects depend on is either the root
# (installed above) or a sibling in this same directory, and a dependency that ISN'T is a
# mistake `pytest` catches at the gate rather than a container discovering it at build time.
RUN pip install --no-build-isolation --no-deps -e . $(ls -d packages/*/)

# The third T-Box source (#175): a firmware's ontology describes what a board running it IS,
# and an agent whose world types its board by firmware class derives its sensing capability
# from exactly this file — absent, the agent boots and subscribes to nothing, silently.
# `.containerignore` narrows this COPY to the ontologies alone: firmware code is flashed, not
# shipped, and a generated include/config.h carries credentials that must never reach a layer.
COPY firmware/ firmware/

# An agent runs as nobody in particular. Its belief base is a file in its own volume, which
# nothing outside this container can name — that is the isolation, and it needs no credential
# and no access registry, because there is no shared store to be let into.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin orexis \
 && chown -R orexis:orexis /app
USER orexis

# No default command: the compose file says whether this container seeds or is an agent.
