---
type: Role
title: Coordinator
term: http://example.org/orexis/coordination#Coordinator
description: >-
  An agent that asks the peers it believes in range what its constraints read, answers them under the
  constraints it holds too, and lays what it yields to - the role whose part is coordination's. Beneath
  the speaker, the planner and the executor, so declaring it loads speech, planning and execution as well;
  the draw it takes part in is a domain its world imports.
---

# Who is one

An agent whose self graph says it plays `coordination:Coordinator` - each courier on the lane. The class is
beneath [speaker](/domain/speech/speaker.md), since asking and answering is saying and hearing, and beneath
the [planner](/domain/planning/planner.md) and the [executor](/domain/execution/executor.md), since a draw is
taken part in only by committing and revealing, actions planning plans and execution takes. So the boot loads
speech, planning and execution with the package, every need of those roles holds of a coordinator too, and a
world declares the one role where the lane's couriers once declared three ([role](/domain/kernel/role.md)).

# What its part does

Linked, the part holds speech's, and says through it as a step's saying does (`agent/coordination/create.py`).
Started, it mints the agent's secret where its self graph states none (`agent/coordination/mint.py`); it
answers every [question](/domain/coordination/question.md) as it is heard; as each question or
[answer](/domain/coordination/answer.md) arrives it concludes its [conflicts](/domain/coordination/conflict.md)
and lays what it yields to, so the next pass plans against the peer's latest word; and each pass, after
planning and execution, it asks again where its [holdings](/domain/coordination/holding.md) changed.

# What it needs of its world

A [draw](/domain/draw/draw.md), which a world of coordinators imports with the desires that drive it; a world
whose rules ship no outcome is refused by `orexis-onboard`, since no conflict would ever be decided
(`agent/coordination/requirements.ttl`). And a constraint it holds whose key a peer's thing can share: without
one there is nothing to ask about, and the part asks nothing.

Two stances, each read through `agent/stance.py` where the self graph states it: `coordination:patienceS`,
how long a draw may stand undecided, sixty seconds where none is stated; and `coordination:rounds`, how many
times it restarts before the peer is taken as silent, three.
