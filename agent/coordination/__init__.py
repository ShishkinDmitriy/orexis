"""The coordination package of Agent 0.2.0: two agents that want one resource ask each other what their
constraint reads, and a draw decides which goes first
(two-agents-that-want-one-resource-ask-each-other-and-draw-lots-for-it, knowledge/domain/coordination/coordinator.md).

**A RESOURCE IS A VALUE OF A SHARED CONSTRAINT'S KEY, OVER A PERIOD.** `holdings` reads what the agent's
walking plans give the things it acts for on a constraint's key; `ask` says them to each peer it believes in
range; `answer` says back, under a constraint it holds too, only the holdings that meet; `conclude` makes of
an answer that is not empty a conflict of the agent's own; a draw a world imports decides it, in this
package's word; and `lay` lays what the agent yields to as forecasts. `mint` makes the secret the draw's
numbers come from. The package is above planning, execution and speech, imports none of their code, and
meets them at the store.
"""
