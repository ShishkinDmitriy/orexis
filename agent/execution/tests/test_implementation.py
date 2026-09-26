"""`operations`: an action's implementation, read off its row — every operation with its kind,
its order (0 where none is said) and its text, in order."""

from __future__ import annotations

import pyoxigraph as ox

from agent.execution.implementation import COMMAND, FICTIVE, SAYING, Operation, operations
from agent.store import update

T = "http://example.org/test#"


def _store(implementation: str) -> ox.Store:
    st = ox.Store()
    update(st, f"""INSERT DATA {{
  GRAPH <{T}actions> {{ <{T}Serve> a orexis:Action {implementation} . }}
  GRAPH <{T}catalogue> {{ <{T}catalogue> a orexis:CatalogueGraph . <{T}actions> a orexis:ActionGraph . }} }}""")
    return st


def test_every_operation_is_read_in_order_with_its_kind_and_text():
    st = _store("""; execution:implementation [ execution:operation
        [ a execution:Saying ; sh:order 1 ; sh:construct "CONSTRUCT {} WHERE {}" ] ,
        [ a execution:Command ; sh:select "SELECT ?actuator ?payload WHERE {}" ] ]""")
    assert operations(st, T + "Serve") == [
        Operation(COMMAND, 0.0, "SELECT ?actuator ?payload WHERE {}"),
        Operation(SAYING, 1.0, "CONSTRUCT {} WHERE {}")]


def test_a_fictive_operation_has_no_text_and_an_action_with_no_implementation_has_none():
    assert operations(_store("; execution:implementation [ execution:operation [ a execution:Fictive ] ]"), T + "Serve") \
        == [Operation(FICTIVE, 0.0, None)]
    assert operations(_store(""), T + "Serve") == []
