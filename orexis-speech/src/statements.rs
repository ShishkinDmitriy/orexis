//! A DOCUMENT AS WHAT WAS SAID, as `agent/speech/statements.py` makes it: every graph it holds a statement
//! (`speech:StatementGraph`), and a kind it said of one kept only where the vocabulary puts that kind beneath the
//! statement — so whatever a peer types its graph as, it is read by no planner, no executor and no rule as anything
//! but what was said (a-peers-word-is-testimony-and-a-rule-makes-it-a-belief). Every other row stays as it was said.

use oxigraph::model::{BlankNode, GraphName, NamedNode, Quad, Term, Triple};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::metadata::stated_quads;
use orexis::store::{Store, iri};

use crate::ontology::STATEMENT_GRAPH;

use orexis::rdf::RDF_TYPE;

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

const TEMPORAL: &str = "http://purl.org/dc/terms/temporal";
const START: &str = "http://example.org/orexis#start";
const END: &str = "http://example.org/orexis#end";
/// The kinds the catalogue `cat` says `graph` is, but a statement's own and the bare graph, in name order.
fn kinds_of(beliefs: &Store, graph: &str) -> Result<Vec<String>, Error> {
    const KINDS_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
    PREFIX speech: <http://example.org/orexis/speech#>
    SELECT ?k WHERE { GRAPH $graph { $graph a ?k FILTER(?k NOT IN (speech:StatementGraph, orexis:Graph)) } } ORDER BY ?k";
    Ok(beliefs
        .rows(&bind(KINDS_Q, &[("graph", Value::iri(graph))])?, &[])?
        .iter()
        .filter_map(|r| iri(r, "k"))
        .collect())
}

/// The kinds `graph` says it is, and what it says.
pub(crate) fn described(beliefs: &Store, graph: &str) -> Result<(Vec<String>, Vec<Triple>), Error> {
    let kinds = kinds_of(beliefs, graph)?;
    let said = match NamedNode::new(graph) {
        Ok(g) => stated_quads(
            beliefs
                .engine()
                .quads_for_pattern(None, None, None, Some(g.as_ref().into()))
                .flatten()
                .collect(),
        )
        .into_iter()
        .map(|q| Triple::new(q.subject, q.predicate, q.object))
        .collect(),
        Err(_) => Vec::new(),
    };
    Ok((kinds, said))
}

/// THE STATEMENTS `graphs` AS THEY WERE SAID, read back from the store: each graph's contents, the kinds it says it
/// is - the most specific, since the store wrote every kind each is beneath and the statement kind beside them - and
/// its period, where it says one.
pub fn document_of(beliefs: &Store, graphs: &[String]) -> Result<Document, Error> {
    /// A STATEMENT'S PERIOD, as it was said.
    const PERIOD_Q: &str = "PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX orexis: <http://example.org/orexis#>
    SELECT ?start ?end WHERE { GRAPH $graph { $graph dcterms:temporal ?p OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } LIMIT 1";
    let mut quads = Vec::new();
    let rdf_type = NamedNode::new_unchecked(RDF_TYPE);
    for graph in graphs {
        let g = NamedNode::new(graph.as_str()).map_err(|e| Error::Evaluation(e.to_string()))?;
        //  WHAT THE GRAPH STATES: what it says of itself in the store is said in the document's own way, below.
        quads.extend(stated_quads(
            beliefs
                .engine()
                .quads_for_pattern(None, None, None, Some(g.as_ref().into()))
                .flatten()
                .collect(),
        ));
        let kinds = kinds_of(beliefs, graph)?;
        let mut beneath = Vec::new();
        for kind in &kinds {
            beneath.push(beliefs.closed(kind)?);
        }
        for (i, kind) in kinds.iter().enumerate() {
            let above_another = kinds
                .iter()
                .enumerate()
                .any(|(j, other)| j != i && other != kind && beneath[j].contains(kind));
            if !above_another {
                quads.push(Quad::new(
                    g.clone(),
                    rdf_type.clone(),
                    NamedNode::new_unchecked(kind.as_str()),
                    GraphName::DefaultGraph,
                ));
            }
        }
        let periods = beliefs.rows(&bind(PERIOD_Q, &[("graph", Value::iri(graph))])?, &[])?;
        if let Some(row) = periods.first() {
            let p = BlankNode::default();
            quads.push(Quad::new(
                g.clone(),
                NamedNode::new_unchecked(TEMPORAL),
                p.clone(),
                GraphName::DefaultGraph,
            ));
            for (key, predicate) in [("start", START), ("end", END)] {
                if let Some(value) = row.get(key) {
                    quads.push(Quad::new(
                        p.clone(),
                        NamedNode::new_unchecked(predicate),
                        value.clone(),
                        GraphName::DefaultGraph,
                    ));
                }
            }
        }
    }
    Ok(Document::of_quads(quads))
}
