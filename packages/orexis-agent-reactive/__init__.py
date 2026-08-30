"""The manifest: the reactive layer — a queue of work and one loop that never stops draining it.

The bottom of the kernel's three layers (a-layer-is-a-package-and-need-loads-it, #452), and
the one that was INTRODUCED rather than moved: before it, every cadence and every deadline in
the society ran on a `threading.Timer` of its own — eight callers, eight threads, and nothing
that could be called "the executing thread". This package is that thread. It holds a
`Loop` — a FIFO of callables and a daemon that runs them one after another — and nothing
else: no store, no timer, no act, no BDI word. What a piece of work IS is the layer above's
business; what this layer promises is that whatever is enqueued runs, in order, on one
thread, and that the enqueuer gets a handle it can wait on from somewhere else.

The name is `reactive` because knowledge/decisions/layered-by-timescale-and-interruptibility.md
names the row — milliseconds, atomic, no search — and the family is `agent` because, in the
author's words, the three layers are "hard to locate in the list without it": the family
groups them, and a layer is still ONE package, not a family with members: there is one reactive layer in an agent, and a queue
with workers or a priority, if one ever arrives, is a decision for then rather than a sibling
waiting for a slot.

Not a capability: nothing grants it and there is no `provides()` here. It imports nothing
of this repository's — not even `assembly` — and `tests/test_layering.py` holds it to that.
"""
