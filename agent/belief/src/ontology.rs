//! BELIEF'S TERMS that code names, as `agent/belief/ontology.py` names them, and the names it spells for eyes.

pub const BELIEF: &str = "http://example.org/orexis/belief#";
pub const TRANSITION: &str = "http://example.org/orexis/belief#Transition";
pub const UPDATE: &str = "http://example.org/orexis/belief#update";
pub const RULES_GRAPH: &str = "http://www.w3.org/ns/shacl#RulesGraph";
pub const REVISION_GRAPH: &str = "http://example.org/orexis/belief#RevisionGraph";
/// Whether a revision graph's rules settled over it.
pub const SETTLED: &str = "http://example.org/orexis/belief#settled";
/// How many rule executions one pass may spend: a stance the agent states of itself.
pub const BUDGET_TERM: &str = "http://example.org/orexis/belief#budget";
/// The role a deliberator plays.
pub const DELIBERATOR: &str = "http://example.org/orexis/belief#Deliberator";
/// A revision pass, as the event it is said as, and what it names: each source it revised, each state it changed.
pub const REVISED: &str = "http://example.org/orexis/belief#Revised";
pub const REVISED_SOURCE: &str = "http://example.org/orexis/belief#revised";
pub const CHANGED: &str = "http://example.org/orexis/belief#changed";
pub const DERIVED_FROM: &str = "http://www.w3.org/ns/prov#wasDerivedFrom";

/// Where the revisions of `source` — what the rules conclude of it — are kept.
pub fn revision_graph(source: &str) -> String {
    format!("{source}/revisions")
}

/// Where what the transitions `arrival` triggered inserted is kept: the state graph the runner prepares for them,
/// one per arrival of testimony.
pub fn state_graph(arrival: &str) -> String {
    format!("{arrival}/believed")
}
