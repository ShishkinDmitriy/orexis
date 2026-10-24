"""The coordination package's own words, and the names it spells for eyes (`ontology.ttl` beside this file,
knowledge/domain/coordination/coordinator.md).

THE NAMES ARE FOR EYES. A question, an answer, a conflict, the graph of the agent's conflicts and each
holding it lays are spelled from the agents and the constraint they are about, so both agents of a pair
name a conflict alike; every reader asks the catalogue by class.
"""

from __future__ import annotations

import hashlib

from agent.ontology import local_of

COORDINATION = "http://example.org/orexis/coordination#"

COORDINATOR = COORDINATION + "Coordinator"
QUESTION_GRAPH = COORDINATION + "QuestionGraph"
ANSWER_GRAPH = COORDINATION + "AnswerGraph"
QUESTION = COORDINATION + "Question"
ANSWER = COORDINATION + "Answer"
HOLDING = COORDINATION + "Holding"
CONFLICT = COORDINATION + "Conflict"
OUTCOME = COORDINATION + "Outcome"
WON_BY = COORDINATION + "wonBy"
SECRET = COORDINATION + "secret"
PATIENCE_S = COORDINATION + "patienceS"
ROUNDS = COORDINATION + "rounds"
LOOKAHEAD = COORDINATION + "lookahead"
#  WHAT HOLDS WHERE THE SELF STATES NO STANCE: how many seconds a draw stands undecided, and a question holds,
#  before it is said again; and how many rounds a draw restarts before the peer is taken as silent.
PATIENCE = 60.0
BOUND = 3
#  AND HOW MANY OF A SILENT PEER'S STEPS THE AGENT LOOKS AHEAD, where the self states none.
LOOKING = 2

#  THE WORDS OF THE PACKAGES BENEATH THAT THIS ONE READS AT THE STORE, spelled here since it imports no code
#  of theirs: planning's constraints, execution's committed steps, speech's statements.
CONSTRAINT_GRAPH = "http://example.org/orexis/planning#ConstraintGraph"
COMMITTED_STEP_GRAPH = "http://example.org/orexis/execution#CommittedStepGraph"

#  WHERE THIS PACKAGE'S OWN NAMES LIVE: one root, for eyes.
_ROOT = "http://example.org/orexis/graph/coordination"


def question_graph(asker: str, peer: str, constraint: str) -> str:
    """The graph one agent's question to a peer under one constraint is said in, again each time."""
    return f"{_ROOT}/{local_of(asker)}/question/{local_of(peer)}/{local_of(constraint)}"


def answer_graph(answerer: str, asker: str, constraint: str) -> str:
    """The graph one agent's answer to a peer's question under one constraint is said in."""
    return f"{_ROOT}/{local_of(answerer)}/answer/{local_of(asker)}/{local_of(constraint)}"


def conflict_of(one: str, other: str, constraint: str) -> str:
    """The conflict between two agents over one constraint, named alike by both: the pair in the
    order of their names, and the constraint, hashed so no name is longer than it need be."""
    low, high = sorted((one, other))
    return f"{_ROOT}/conflict/{hashlib.sha256(f'{low}|{high}|{constraint}'.encode()).hexdigest()[:16]}"


def draw_of(conflict: str, round_: int) -> str:
    """The draw of one round of a conflict: so nothing of another round, conflict or pair can be said
    into it. Dotted, as a name within a name is spelled here, so a case abbreviates it under the conflict's
    prefix (`.claude/skills/snapshot-tests`)."""
    return f"{conflict}.round.{round_}"


def conflicts_graph(me: str) -> str:
    """Where the agent keeps what it concluded of its conflicts: a belief of its own."""
    return f"{_ROOT}/{local_of(me)}/conflicts"


def secret_graph(me: str) -> str:
    """Where the agent keeps the secret it minted: a belief of its own, never said."""
    return f"{_ROOT}/{local_of(me)}/secret"


def laid_root(me: str) -> str:
    """What every forecast the agent lays of a peer's holdings is named under."""
    return f"{_ROOT}/{local_of(me)}/laid/"


def laid_graph(me: str, peer: str, constraint: str, n: int) -> str:
    """The `n`th holding of `peer`'s the agent lays as a forecast under one constraint."""
    return f"{laid_root(me)}{local_of(peer)}/{local_of(constraint)}/{n}"
