"""The sensing layer of Agent 0.2.0: the belief revision function.

**THREE ACTS OVER THE STORE, AND NO WANT.** A reading arrives as a number, and this layer is
what turns it into belief: `revise` writes the observation it is — keyed by subject and
property, typed with the sides the domain declares, standing as the present until the
horizon, the number beside it as the instrument's own word — `predict` runs every drift the
domain packages declare over the reading in hand and writes what comes out as predictions,
graphs of side sets holding during their windows, each starting where the classification
probably changes, and `surprise` says whether a reading contradicts what was predicted for
its instant. It declares no desire, weighs nothing and mints nothing: what the mind does with
a side and a crossing is the derivation's, and what to do about not knowing is the desire's
own sentence (#783).

**IT IS THE LAYER THAT WORKS WITH THE NUMBERS**, and the one that decides what is state. The
mind's world is sides: the graph a reading is read from holds its key and its sides, and its
number, its instant and its instrument are a graph of another kind beside it, holding for the
same stretch, so the world a plan is placed in hashes the same for two readings the domain
calls the same. Every drift and every envelope reads the number where it is.

**WHAT ENDS BY THE CLOCK IS A GRAPH WITH A PERIOD.** A reading's standing as the present ends
at the horizon this layer gives it, and what stands in for it then is what the drift
predicted for that window; unmeasured is silence past the last prediction, and that is the
desire's to notice. Nothing here keeps a timer.

The predecessor was a module (`packages/orexis-capability-sensing/module.py`) that kept the
pipeline, the predictions, a freshness desire of its own, a timer per reading and the
keeper's verdicts; the pipeline and the drift runner are what came across, as functions.
"""
