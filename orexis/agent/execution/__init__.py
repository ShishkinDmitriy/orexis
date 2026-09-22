"""The execution layer: what an agent does with a plan once it has one.

The ledger of what this agent is committed to (`keeper.py`), and the one function that copies
a found plan into it (`plans.py`). That is the whole of it — 280 lines — and the smallness is
the point rather than an embarrassment: keeping a commitment honest is a small job, and the
predecessor's 1,736-line keeper was large because it also carried an expectation watch, held
conditions, methods, bridges and refusals, each of which returns attached to whatever needs it.

**WHAT IS NOT HERE IS WHAT BOTH LAYERS STAND ON.** The store engine, the kernel `orexis:`
vocabulary, the shape compiler and the clock sit in `orexis/agent/` beside this, not inside
it, and that is the correction this directory exists to make. They lived in the execution
package because its predecessor was "the lowest layer that persists" — and measured, the
planning layer imported 1,936 lines of them and NOT ONE LINE of the keeper or of `plans`. A
package should be named for most of what is in it; that one was named for a tenth.

`act.py` is beside them rather than in here for the same reason, though it is a near thing: a
`Step` is the ledger's shape, and the search fills one at every node. What decides it is who
READS it — both layers do — and a thing both layers read is not one layer's.

Nothing grants this and nothing contributes it. It is imported.
"""
