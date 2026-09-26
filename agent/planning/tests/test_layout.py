"""What the tree's SHAPE promises, which no other test would notice going wrong.

Four claims: a file that must NOT exist, what a module named for an act may export, that every
module with a public function has a test named for it, and that the rest of the tree uses the
`Planner` and nothing else.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_the_namespace_portions_stay_unclaimed():
    """`orexis/` and `agent/` carry no `__init__.py`, so a subtree can be lifted out
    into a pip distribution of its own later and still import as `agent.planning`.

    PEP 420: a directory with no `__init__.py` is a NAMESPACE portion, and several
    distributions may contribute into one — measured before this was relied on, with two
    separate trees on the path answering `agent.store` from one and
    `agent.planning` from the other, `agent.__path__` spanning both. The moment
    either directory gains an `__init__.py` it belongs to ONE distribution, a second
    contributing into it collides, and the split stops being possible.

    It is the kind of file somebody adds reflexively — for a docstring, for an `__all__`, to
    make an editor stop complaining — and nothing else here would fail if they did. A
    subpackage's own `__init__.py` is fine and expected: `agent/planning/` and
    `agent/execution/` each have one, because each is one distribution's to claim.
    """
    for portion in (ROOT / "agent",):
        init = portion / "__init__.py"
        assert not init.exists(), (
            f"{init.relative_to(ROOT)} makes {portion.name}/ one distribution's, and a second "
            "one contributing into it would collide — see this test's docstring")
    for package in (ROOT / "agent" / "planning",
                    ROOT / "agent" / "execution"):
        assert (package / "__init__.py").exists(), f"{package.name}/ is a package and says so"


#  A MODULE NAMED FOR A THING, which may export several reads of it. Every other module in
#  the package is named for an ACT and exports that act alone.
NOUNS = {"footprint", "ontology", "planner", "violation"}


def test_a_module_named_for_an_act_exports_that_act_and_nothing_else():
    """ONE FILE, ONE PUBLIC FUNCTION, NAMED FOR IT — and the name is the file's. A reader who
    wants `expand` opens `expand.py` and finds it first; what else the file holds is private,
    and a second public function is a second act wanting a file of its own. The allowance
    is a module named for a THING — `footprint` — which answers several
    questions about it, and `planner`, which holds the class that composes the acts.

    Constants and classes are not held: a module may export the term it writes by and the
    value it hands across (`expand.BUDGET`).
    """
    import ast
    package = ROOT / "agent" / "planning"
    for path in sorted(package.glob("*.py")):
        if path.stem in NOUNS or path.stem == "__init__":
            continue
        tree = ast.parse(path.read_text())
        public = sorted(n.name for n in tree.body
                        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"))
        assert public == [path.stem], (
            f"{path.name} exports {public}: a module named for an act exports that act alone")


def test_every_module_with_a_public_function_has_a_test_named_for_it():
    """PUBLIC MEANS TESTED. A function is public to the package so that its siblings may call
    it and a test may hold it — by name, in `tests/test_<module>.py`, and where the function is
    an act over the store, by a case directory `tests/<module>/` beside it. A public function
    with no test named for it is one whose claim is nowhere, and it was six of them here."""
    import ast
    package = ROOT / "agent" / "planning"
    for path in sorted(package.glob("*.py")):
        if path.stem in ("__init__", "ontology"):
            continue
        tree = ast.parse(path.read_text())
        if not any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_")
                   for n in tree.body):
            continue
        assert (package / "tests" / f"test_{path.stem}.py").exists(), (
            f"{path.name} has public functions and no tests/test_{path.stem}.py")


def test_outside_the_package_only_the_planner_is_imported():
    """PUBLIC MEANS PUBLIC TO THE PACKAGE. Outside `agent/planning/`, the one name the
    tree may import is `Planner`: a container builds one and calls `plan`, and what a pass is
    made of stays the package's to rearrange. Held over every Python file in the tree that
    is not the package's own."""
    import ast
    package = ROOT / "agent" / "planning"
    for path in sorted((ROOT / "agent").rglob("*.py")):
        if package in path.parents:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("agent.planning"):
                names = {a.name for a in node.names}
                assert node.module in ("agent.planning", "agent.planning.planner") \
                    and names == {"Planner"}, f"{path.relative_to(ROOT)} imports {names} from {node.module}"
            if isinstance(node, ast.Import):
                for a in node.names:
                    assert not a.name.startswith("agent.planning"), \
                        f"{path.relative_to(ROOT)} imports {a.name}"


#  THE READS: modules that write nothing, which any act may ask.
READS = {"ontology", "world_at", "find_wants", "find_scopes", "unweighed", "footprint", "violation"}


def test_an_act_calls_no_other_act_and_the_planner_sequences_them():
    """A STAR, NOT A CHAIN. The Planner sequences the acts; an act reads the store and writes
    it and calls no other act — what it needs of another's work it reads off the rows the
    other wrote. Held as imports: a module other than the planner imports a sibling only
    where the sibling is a READ, or imports a constant (a text, a term) and never a function.
    It was a chain: the pass called the search, the search the expansion and the extraction,
    the expansion the admission and the taking, the derivation the weighing."""
    import ast
    package = ROOT / "agent" / "planning"
    for path in sorted(package.glob("*.py")):
        if path.stem in ("planner", "__init__"):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                sibling = node.module or ""
                if sibling == "" or sibling in READS:
                    continue
                for a in node.names:
                    assert a.name.isupper() or a.name.startswith("_") is False and a.name == a.name.upper(), (
                        f"{path.name} imports {a.name} from {sibling}: an act calls no other act")
