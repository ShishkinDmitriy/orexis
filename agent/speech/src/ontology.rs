//! THE SPEECH PACKAGE'S OWN WORDS, as `agent/speech/ontology.py` names them, and the name it spells for eyes: what is
//! said and what is believed of it are two graphs, the statement and the belief derived from it.

pub const SPEECH: &str = "http://example.org/orexis/speech#";
pub const STATEMENT_GRAPH: &str = "http://example.org/orexis/speech#StatementGraph";
pub const EXTRACTION: &str = "http://example.org/orexis/speech#Extraction";

/// Where what the extractions conclude of `statement` is kept: a belief derived from it.
pub fn believed_graph(statement: &str) -> String {
    format!("{}/believed", statement.trim_end_matches('/'))
}
