//! THE SPEECH PACKAGE'S OWN WORDS, as `agent/speech/ontology.py` names them, and the name it spells for eyes: what is
//! said and what is believed of it are two graphs, the statement and the belief derived from it.

pub const SPEECH: &str = "http://example.org/orexis/speech#";
pub const STATEMENT_GRAPH: &str = "http://example.org/orexis/speech#StatementGraph";
/// What speech does as an activity, what starts it, and what that names: each statement, each agent it is to.
pub const SPEAKING: &str = "http://example.org/orexis/speech#Speaking";
pub const SPEAKING_TRIGGER: &str = "http://example.org/orexis/speech#SpeakingTrigger";
/// What carrying the agent's own words is, and what starts it.
pub const CARRYING: &str = "http://example.org/orexis/speech#Carrying";
/// What speech does of a channel for as long as it runs, what it does of one arrival on it, and what it is done with.
pub const LISTENING: &str = "http://example.org/orexis/speech#Listening";
pub const HEARING: &str = "http://example.org/orexis/speech#Hearing";
pub const EXTRACTING: &str = "http://example.org/orexis/speech#Extracting";
pub const USED: &str = "http://www.w3.org/ns/prov#used";
pub const CARRYING_TRIGGER: &str = "http://example.org/orexis/speech#CarryingTrigger";
pub const STATEMENT: &str = "http://example.org/orexis/speech#statement";
pub const TO: &str = "http://example.org/orexis/speech#to";
/// A document the agent said, as the event it is said as.
pub const SAID: &str = "http://example.org/orexis/speech#Said";
pub const EXTRACTION: &str = "http://example.org/orexis/speech#Extraction";

/// Where what the extractions conclude of `statement` is kept: a belief derived from it.
pub fn believed_graph(statement: &str) -> String {
    format!("{}/believed", statement.trim_end_matches('/'))
}
