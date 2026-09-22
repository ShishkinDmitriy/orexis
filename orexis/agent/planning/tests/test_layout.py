"""What the tree's SHAPE promises, which no other test would notice going wrong.

One claim, and it is about a file that must NOT exist.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_the_namespace_portions_stay_unclaimed():
    """`orexis/` and `orexis/agent/` carry no `__init__.py`, so a subtree can be lifted out
    into a pip distribution of its own later and still import as `orexis.agent.planning`.

    PEP 420: a directory with no `__init__.py` is a NAMESPACE portion, and several
    distributions may contribute into one — measured before this was relied on, with two
    separate trees on the path answering `orexis.agent.store` from one and
    `orexis.agent.planning` from the other, `orexis.agent.__path__` spanning both. The moment
    either directory gains an `__init__.py` it belongs to ONE distribution, a second
    contributing into it collides, and the split stops being possible.

    It is the kind of file somebody adds reflexively — for a docstring, for an `__all__`, to
    make an editor stop complaining — and nothing else here would fail if they did. A
    subpackage's own `__init__.py` is fine and expected: `orexis/agent/planning/` and
    `orexis/agent/execution/` each have one, because each is one distribution's to claim.
    """
    for portion in (ROOT / "orexis", ROOT / "orexis" / "agent"):
        init = portion / "__init__.py"
        assert not init.exists(), (
            f"{init.relative_to(ROOT)} makes {portion.name}/ one distribution's, and a second "
            "one contributing into it would collide — see this test's docstring")
    for package in (ROOT / "orexis" / "agent" / "planning",
                    ROOT / "orexis" / "agent" / "execution"):
        assert (package / "__init__.py").exists(), f"{package.name}/ is a package and says so"
