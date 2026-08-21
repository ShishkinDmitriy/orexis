"""These eight tests cannot share a broker with a second worker, and now they refuse to try.

`addopts = "-n auto"` is on for the whole repo, and `pytest infra` picks it up like everything
else. That is wrong here, and wrong in the worst way: `test_bus_acl_runtime.py` reads the world's
`passwd` and `acl.conf`, appends a grant block, exercises it against the RUNNING broker, and
restores both byte-for-byte in a `finally`. Two workers interleave read-read-write-write, the
second write discards the first block, and the first test then measures a grant somebody else
wrote. **It passes.** A test that proves an ACL nobody installed is worse than a failing one, and
it is the same family as the vacuity bug the root `conftest.py` exists for (#106).

So this is a refusal rather than a note in a doc. The note is also there — `pyproject.toml` says
it beside the flag, and AGENTS.md's command list spells `-n0` — but a comment is not a gate, and
the person who hits this will be running a command they copied.

WHY NOT `xdist_group`, which is the obvious answer: the marker is only read when the scheduler is
`--dist loadgroup`, and the default under `-n auto` is `--dist load`, which ignores it silently
(`xdist/remote.py` guards the whole thing on `config.getvalue("loadgroup")`). Marking these would
have looked like protection and been a no-op — which is the thing this file exists to prevent, so
it would have been a poor way to prevent it.

The check is on `workerinput`, which xdist sets on a worker's config and nothing else does, so it
is exact rather than a guess at the command line.
"""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    if hasattr(config, "workerinput"):
        raise pytest.UsageError(
            "infra/tests must run serially: use `pytest infra -q -n0`.\n"
            "These tests rewrite the world's passwd and acl.conf in place and restore them, so a "
            "second worker silently discards the block this one installed — and the test then "
            "passes against an ACL it did not write. See infra/tests/conftest.py."
        )
