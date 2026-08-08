"""The agent image carries no operator code, asserted rather than implied.

This used to be a property of the packaging: two distributions, and an agent installed only
one of them. It never was, quite. Nothing here installs from an index — the image copies
directories and runs `pip install -e .` — so what actually kept `onboarding/` out of an agent
was the Containerfile not naming it, and a reader had to infer that from two pyproject files
that said nothing about images.

One distribution now, and the boundary is here. If someone adds `COPY onboarding/` for
convenience, this fails; before, nothing did.

Deliberately reads the Containerfile rather than building: a test that needed a container
runtime would be skipped on every machine that lacks one, which is exactly the machine where
someone is most likely to be editing quickly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTAINERFILE = REPO_ROOT / "Containerfile"

# What an agent legitimately runs. `agent/` carries capabilities and transports as subpackages;
# `vocabulary/` is the shared T-Box, which onboarding reads too and neither side owns.
ALLOWED_TREES = {"agent", "vocabulary"}

# Never in an agent image. `agora-influx` reads the admin token, which opens every bucket in the
# store and which no agent may ever hold; the surest guarantee is that the code using it is
# absent. See knowledge/domain/onboarding.md.
FORBIDDEN_TREES = {"onboarding"}


def copied_paths() -> list[str]:
    """Every source path the image copies, as written."""
    out: list[str] = []
    for line in CONTAINERFILE.read_text().splitlines():
        line = line.strip()
        if not line.upper().startswith("COPY "):
            continue
        parts = re.split(r"\s+", line)[1:]
        out.extend(p for p in parts[:-1] if not p.startswith("--"))
    return out


def test_the_image_copies_something():
    """A guard on the guard: if COPY were renamed or the file moved, every assertion below
    would pass vacuously and the boundary would be unwatched."""
    assert copied_paths(), f"no COPY lines found in {CONTAINERFILE} — this test is not looking"


@pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_TREES))
def test_the_agent_image_carries_no_operator_code(forbidden):
    offenders = [p for p in copied_paths() if p.split("/")[0].strip("./") == forbidden]
    assert not offenders, (
        f"the Containerfile copies {offenders} into the agent image. {forbidden}/ mints "
        "credentials and reads the admin token; an agent must not hold that code at all. "
        "If this is deliberate, the isolation design in "
        "knowledge/decisions/series-and-bus-isolation.md is what needs changing first."
    )


def test_the_image_copies_only_what_an_agent_runs():
    """The positive half. Forbidding one name only catches the tree we thought of; this
    catches the next one, which is the one that will actually be added."""
    trees = {p.split("/")[0].strip("./") for p in copied_paths() if "/" in p or "." not in p}
    unexpected = trees - ALLOWED_TREES - {"pyproject.toml"}
    assert not unexpected, (
        f"the agent image copies {sorted(unexpected)}, which is not part of what an agent runs. "
        f"Expected only {sorted(ALLOWED_TREES)} — add it here deliberately, or do not copy it."
    )


def test_onboarding_is_not_hidden_from_the_build_context():
    """The boundary must be visible where the decision is made.

    Ignoring `onboarding/` in .containerignore would also keep it out of the image, and would
    move the reasoning into a file nobody reads while making this test pass for the wrong
    reason. The Containerfile is where it is decided.
    """
    ignored = [
        line.strip() for line in (REPO_ROOT / ".containerignore").read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "onboarding" not in ignored, (
        ".containerignore excludes onboarding/. That works, but it hides the boundary: the "
        "Containerfile should be the one place that says what an agent image contains."
    )


# --- what an AGENT is given, which is less than the world -------------------------------------

def test_an_agent_is_given_the_society_and_not_the_hardware():
    """It never asks which pin a probe is on.

    The runtime queries what it acts for, what it may poll, which topics reach that sensor and
    how it is driven. Pins, wires, rails, silkscreen markings and part models are the
    sovereign's: they decide what CAN be built and what a board must be flashed with, and once
    it is built the agent talks to topics.

    Asserted on the CONTENT of what an agent would load rather than on the filename, so it also
    catches a pin assignment put into world.ttl — where nothing about the file name would warn
    anyone. Enforcement is that the container does not have the file at all, which is the same
    shape as the Containerfile keeping onboarding out of the image.
    """
    import rdflib

    from agent import genesis

    HARDWARE_NAMESPACES = (
        "http://example.org/agora/microcontroller#",
        "http://example.org/agora/esp32#",
        "http://example.org/agora/wokwi#",
        "http://example.org/agora/dht11#",
        "http://example.org/agora/rgb-led#",
        "http://example.org/agora/moisture-probe#",
        "http://example.org/agora/onewire#",
        "http://example.org/agora/i2c#",
    )

    for world in genesis.worlds():
        g = rdflib.Graph()
        for path in genesis.society_files(genesis.world_dir(world)):
            g.parse(path, format="turtle")
        leaked = {str(t) for triple in g for t in triple
                  if str(t).startswith(HARDWARE_NAMESPACES)}
        assert not leaked, (
            f"{world}: an agent would be handed hardware vocabulary it never queries: "
            f"{sorted(leaked)[:5]}")


def test_the_compose_file_does_not_mount_hardware_at_an_agent():
    """The other half, and the one that actually enforces it: a rule the agent is trusted to
    follow is not a boundary. What keeps the wiring out of an agent is that the file is not in
    its filesystem."""
    from agent.config import REPO_ROOT
    from agent import genesis

    for world in genesis.worlds():
        compose = REPO_ROOT / "world" / world / "compose.yaml"
        if not compose.exists():
            continue
        for name in genesis.HARDWARE_FILES:
            assert f"/{name}:" not in compose.read_text(), (
                f"{world}/compose.yaml mounts {name} into an agent — regenerate with "
                f"`agora-compose {world}`")
