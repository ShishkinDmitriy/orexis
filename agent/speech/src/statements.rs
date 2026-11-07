//! A DOCUMENT AS WHAT WAS SAID, as `agent/speech/statements.py` makes it: every graph it holds a statement
//! (`speech:StatementGraph`), and a kind it said of one kept only where the vocabulary puts that kind beneath the
//! statement — so whatever a peer types its graph as, it is read by no planner, no executor and no rule as anything
//! but what was said (a-peers-word-is-testimony-and-a-rule-makes-it-a-belief). Every other row stays as it was said.

use oxigraph::model::{GraphName, NamedNode, Quad, Term};

use orexis::Error;
use orexis::document::Document;
use orexis::store::Store;

use crate::ontology::STATEMENT_GRAPH;

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

/// `doc` with every graph it holds a statement.
pub fn statements(store: &Store, doc: &Document) -> Result<Document, Error> {
    let graphs: Vec<String> = doc.kinds().into_keys().collect();
    let mut out = Vec::new();
    for q in doc.quads() {
        let about_a_graph = matches!(q.graph_name, GraphName::DefaultGraph)
            && graphs.iter().any(|g| q.subject.to_string() == format!("<{g}>"))
            && q.predicate.as_str() == RDF_TYPE;
        if about_a_graph
            && let Term::NamedNode(kind) = &q.object
            && !store.closed(kind.as_str())?.iter().any(|k| k == STATEMENT_GRAPH)
        {
            continue;
        }
        out.push(q.clone());
    }
    for graph in &graphs {
        out.push(Quad::new(
            NamedNode::new_unchecked(graph),
            NamedNode::new_unchecked(RDF_TYPE),
            NamedNode::new_unchecked(STATEMENT_GRAPH),
            GraphName::DefaultGraph,
        ));
    }
    Ok(Document::of_quads(out))
}
