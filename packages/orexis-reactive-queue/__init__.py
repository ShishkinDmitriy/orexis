"""The manifest: the reactive layer — a queue of work and one loop that never stops draining it.

The bottom of the kernel's three layers (a-layer-is-a-package-and-need-loads-it, #452), and
the one that was INTRODUCED rather than moved: before it, every cadence and every deadline in
the society ran on a `threading.Timer` of its own — eight callers, eight threads, and nothing
that could be called "the executing thread". This package is that thread. It holds a
`Loop` — a FIFO of callables and a daemon that runs them one after another — and nothing
else: no store, no timer, no act, no BDI word. What a piece of work IS is the layer above's
business; what this layer promises is that whatever is enqueued runs, in order, on one
thread, and that the enqueuer gets a handle it can wait on from somewhere else.

The family is `reactive` because knowledge/decisions/layered-by-timescale-and-interruptibility.md
names the row — milliseconds, atomic, no search — and the member is `queue` because THIS way
of having it is a single queue drained by a single thread. A member that kept several
workers, or a priority, would be its sibling and would answer the same `submit`.

Not a capability: nothing grants it and there is no `provides()` here. It imports nothing
of this repository's — not even `assembly` — and `tests/test_layering.py` holds it to that.
"""
