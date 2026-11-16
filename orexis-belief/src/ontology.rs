//! BELIEF'S TERMS that code names, as `agent/belief/ontology.py` names them, and the names it spells for eyes.

pub const BELIEF: &str = "http://example.org/orexis/belief#";
pub const TRANSITION: &str = "http://example.org/orexis/belief#Transition";
pub const UPDATE: &str = "http://example.org/orexis/belief#update";
pub const RULES_GRAPH: &str = "http://www.w3.org/ns/shacl#RulesGraph";
pub const REVISION_GRAPH: &str = "http://example.org/orexis/belief#RevisionGraph";
/// Whether a revision graph's rules settled over it.
pub const SETTLED: &str = "http://example.org/orexis/belief#settled";
/// How many rule executions one pass may spend: a figure the deliberator's role states.
pub const BUDGET_TERM: &str = "http://example.org/orexis/belief#budget";
/// The role a deliberator plays.
pub const DELIBERATOR: &str = "http://example.org/orexis/belief#Deliberator";
/// A revision pass, as the event it is said as, and what it names: each source it revised, each state it changed.
pub const REVISED: &str = "http://example.org/orexis/belief#Revised";
pub const REVISED_SOURCE: &str = "http://example.org/orexis/belief#revised";
pub const CHANGED: &str = "http://example.org/orexis/belief#changed";
/// What belief does as an activity, and what starts it: each graph to revise, and the kind its revisions are to be.
pub const REVISING: &str = "http://example.org/orexis/belief#Revising";
pub const REVISING_TRIGGER: &str = "http://example.org/orexis/belief#RevisingTrigger";
pub const REVISES: &str = "http://example.org/orexis/belief#revises";
pub const INTO: &str = "http://example.org/orexis/belief#into";
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

/// `iri` as a node, refused where it is no IRI — so a name spliced into a text is one the grammar reads as one.
pub(crate) fn node(iri: &str) -> Result<oxigraph::model::NamedNode, orexis::Error> {
    oxigraph::model::NamedNode::new(iri).map_err(|e| orexis::Error::Evaluation(format!("no IRI: {iri}: {e}")))
}
