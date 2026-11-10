//! THE COORDINATION PACKAGE'S OWN WORDS, as `agent/coordination/ontology.py` names them, and the names it spells for
//! eyes — a question, an answer, a conflict, the graph of the agent's conflicts and each holding it lays, spelled from
//! the agents and the constraint they are about, so both agents of a pair name a conflict alike.

use sha2::{Digest, Sha256};

use orexis::ontology::local_of;

pub const COORDINATION: &str = "http://example.org/orexis/coordination#";
pub const QUESTION_GRAPH: &str = "http://example.org/orexis/coordination#QuestionGraph";
pub const ANSWER_GRAPH: &str = "http://example.org/orexis/coordination#AnswerGraph";
pub const QUESTION: &str = "http://example.org/orexis/coordination#Question";
pub const ANSWER: &str = "http://example.org/orexis/coordination#Answer";
pub const HOLDING: &str = "http://example.org/orexis/coordination#Holding";
pub const CONFLICT: &str = "http://example.org/orexis/coordination#Conflict";
pub const WON_BY: &str = "http://example.org/orexis/coordination#wonBy";
pub const SECRET: &str = "http://example.org/orexis/coordination#secret";
pub const PATIENCE_S: &str = "http://example.org/orexis/coordination#patienceS";
pub const ROUNDS: &str = "http://example.org/orexis/coordination#rounds";
pub const LOOKAHEAD: &str = "http://example.org/orexis/coordination#lookahead";

/// WHAT HOLDS WHERE THE SELF STATES NO STANCE: how many seconds a draw stands undecided, and a question holds, before
/// it is said again; how many rounds a draw restarts before the peer is taken as silent; and how many of a silent
/// peer's steps the agent looks ahead.
pub const PATIENCE: f64 = 60.0;
pub const BOUND: f64 = 3.0;
pub const LOOKING: f64 = 2.0;

/// THE WORDS OF THE PACKAGES BENEATH THAT THIS ONE READS AT THE STORE, spelled here since it imports no code of theirs.
pub const CONSTRAINT_GRAPH: &str = "http://example.org/orexis/planning#ConstraintGraph";
pub const COMMITTED_STEP_GRAPH: &str = "http://example.org/orexis/execution#CommittedStepGraph";

const ROOT: &str = "http://example.org/orexis/graph/coordination";

/// The graph one agent's question to a peer under one constraint is said in, again each time.
pub fn question_graph(asker: &str, peer: &str, constraint: &str) -> String {
    format!(
        "{ROOT}/{}/question/{}/{}",
        local_of(asker),
        local_of(peer),
        local_of(constraint)
    )
}

/// The graph one agent's answer to a peer's question under one constraint is said in.
pub fn answer_graph(answerer: &str, asker: &str, constraint: &str) -> String {
    format!(
        "{ROOT}/{}/answer/{}/{}",
        local_of(answerer),
        local_of(asker),
        local_of(constraint)
    )
}

/// The conflict between two agents over one constraint, named alike by both.
pub fn conflict_of(one: &str, other: &str, constraint: &str) -> String {
    let (low, high) = if one <= other { (one, other) } else { (other, one) };
    let hash = Sha256::digest(format!("{low}|{high}|{constraint}").as_bytes());
    let hex: String = hash.iter().map(|b| format!("{b:02x}")).collect();
    format!("{ROOT}/conflict/{}", &hex[..16])
}

/// The draw of one round of a conflict.
pub fn draw_of(conflict: &str, round: i64) -> String {
    format!("{conflict}.round.{round}")
}

/// Where the agent keeps what it concluded of its conflicts.
pub fn conflicts_graph(me: &str) -> String {
    format!("{ROOT}/{}/conflicts", local_of(me))
}

/// Where the agent keeps the secret it minted.
pub fn secret_graph(me: &str) -> String {
    format!("{ROOT}/{}/secret", local_of(me))
}

/// What every forecast the agent lays of a peer's holdings is named under.
pub fn laid_root(me: &str) -> String {
    format!("{ROOT}/{}/laid/", local_of(me))
}

/// The `n`th holding of `peer`'s the agent lays as a forecast under one constraint.
pub fn laid_graph(me: &str, peer: &str, constraint: &str, n: usize) -> String {
    format!("{}{}/{}/{n}", laid_root(me), local_of(peer), local_of(constraint))
}

/// A draw won, as the event it is said as, and planning's word for the wants it names.
pub const DRAW_WON: &str = "http://example.org/orexis/coordination#DrawWon";
pub const REOPENS: &str = "http://example.org/orexis/planning#reopens";
