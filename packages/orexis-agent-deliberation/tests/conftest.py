"""The deliberation package's own test options.

`--update-snapshots` rewrites every road case's snapshot (`road/<case>.nq`) from what the road
actually left in the store, instead of holding the store to it. Registered here, beside the
tests that read it, so it is recognised when these tests are named on the command line:

    pytest packages/orexis-agent-deliberation/tests --update-snapshots

A regenerated snapshot is reviewed by eyes before it is committed — the diff IS the claim
that the road's behaviour changed on purpose.
"""


def pytest_addoption(parser):
    parser.addoption("--update-snapshots", action="store_true", default=False,
                     help="rewrite the road cases' snapshots from what the road left, then review the diff")
