"""The knowledge linker (#210): no loaded package may reference a term nobody declares.

Dependencies between packages are soft by IRI, and soft has one sharp edge: a reference to a
term nobody declares matches NOTHING, and an empty result is not an error. The linker is the
link step of the found-by-looking build — a check, never a resolver. Its first run over the
shipped tree caught `ag:modelDryRate` in DeviceModelShape: a constraint that had survived TWO
renames of its term by matching nothing, exactly the vacuous green it exists to refuse.
"""

from agent import loader
from onboarding import linker


def test_the_shipped_tree_links_clean():
    assert linker.dangling() == {}


def test_the_scan_is_looking_at_something():
    """The guard on the guard, the a-test-that-asserted-nothing discipline: an empty declared
    set or a near-empty reference map would make the test above a vacuous green of its own.
    The tree declares hundreds of terms and references most of them; well below that, a glob
    has gone stale."""
    assert len(linker.declared_terms()) > 100
    assert len(linker.referenced_terms()) > 100


def test_a_typo_is_caught_and_named(tmp_path, monkeypatch):
    """The failure mode, synthesised: a package referencing `market:ofGoods` — one letter from
    a real term — must be refused with the term and the file named, not left to match nothing
    for the rest of its life."""
    toy = tmp_path / "actions.ttl"
    toy.write_text('@prefix ag: <http://example.org/orexis#> .\n'
                   'ag:Toy a ag:Action ; ag:available "SELECT ?m WHERE { ?v market:ofGoods ?g }" .')
    real = loader.action_files()
    monkeypatch.setattr(loader, "action_files", lambda: real + (toy,))
    broken = linker.dangling()
    assert "http://example.org/orexis/market#ofGoods" in broken
    assert any("actions.ttl" in f for f in broken["http://example.org/orexis/market#ofGoods"])


def test_a_tolerated_non_reference_stays_tolerated(tmp_path, monkeypatch):
    """The three tolerances, pinned so a refactor cannot quietly widen the check into noise:
    a bare namespace (a constant), a minted-IRI base (a function of an id, trailing dot the
    tell), and prose in a docstring that merely mentions a keyword."""
    toy = tmp_path / "actions.ttl"
    toy.write_text('@prefix ag: <http://example.org/orexis#> .\n'
                   'ag:Toy a ag:Action ; ag:available """SELECT ?m WHERE { ?v ?p '
                   '"http://example.org/orexis/market#" , "http://example.org/orexis#market." }""" .')
    real = loader.action_files()
    monkeypatch.setattr(loader, "action_files", lambda: real + (toy,))
    assert linker.dangling() == {}
