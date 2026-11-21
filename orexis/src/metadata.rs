//! WHERE A GRAPH'S METADATA IS WRITTEN (knowledge/domain/kernel/metadata.md).
//!
//! A graph holds the facts it states and nothing else. What it IS - its kinds, how it arrived, whose it is, what it
//! holds by hash, when it holds, and what a package says of it - is said in a graph of its own beside it, its
//! `orexis:MetadataGraph`, which says of itself only which graph it is of. A reader finds it by that link, never by
//! its name; a writer names a new one by the one convention below.

use std::collections::BTreeSet;

use oxigraph::model::{GraphName, NamedNode, NamedOrBlankNode, Quad, Term};

use crate::Error;
use crate::ontology::{METADATA_GRAPH, METADATA_OF};
use crate::rdf::RDF_TYPE;
use crate::store::Store;

/// The name a writer gives the metadata graph of a graph that has none: the graph's name with a word after it.
///
/// ```
/// assert_eq!(orexis::metadata::named("urn:a"), "urn:a.metadata");
/// ```
pub fn named(graph: &str) -> String {
    format!("{graph}.metadata")
}

/// The metadata graph a writer makes for the new graph `graph`, and what it says of itself: that it is one, and
/// which graph it is of. For a writer that says a graph's metadata as quads; a text takes `Store::entry`.
pub fn header(graph: &str) -> Result<(NamedNode, [Quad; 2]), Error> {
    let node = |iri: &str| NamedNode::new(iri).map_err(|e| Error::Evaluation(format!("{iri}: {e}")));
    let metadata = node(&named(graph))?;
    let says = [
        Quad::new(
            metadata.clone(),
            node(RDF_TYPE)?,
            node(METADATA_GRAPH)?,
            metadata.clone(),
        ),
        Quad::new(metadata.clone(), node(METADATA_OF)?, node(graph)?, metadata.clone()),
    ];
    Ok((metadata, says))
}

/// WHAT `block` SAYS OF `graph`, MOVED INTO THE GRAPH'S METADATA GRAPH, with every blank node those statements
/// lead to, its period among them: for a store whose graphs' metadata was said together in one graph, a volume
/// lived in while one graph said what every graph is, and a test's fixture that says it so for brevity.
pub fn moved(store: &Store, block: &str, graph: &str) -> Result<(), Error> {
    let node = |iri: &str| NamedNode::new(iri).map_err(|e| Error::Evaluation(format!("{iri}: {e}")));
    let said = store.quads(block)?;
    let metadata = node(&store.metadata_for(graph)?)?;
    let mut about: BTreeSet<String> = BTreeSet::from([format!("<{graph}>")]);
    let mut taken: Vec<Quad> = Vec::new();
    loop {
        let more: Vec<Quad> = said
            .iter()
            .filter(|q| about.contains(&q.subject.to_string()) && !taken.contains(q))
            .cloned()
            .collect();
        if more.is_empty() {
            break;
        }
        for quad in &more {
            if let Term::BlankNode(b) = &quad.object {
                about.insert(b.to_string());
            }
        }
        taken.extend(more);
    }
    if taken.is_empty() {
        return Ok(());
    }
    store.remove_all(&taken)?;
    let within = GraphName::NamedNode(metadata.clone());
    let mut says = vec![
        Quad::new(metadata.clone(), node(RDF_TYPE)?, node(METADATA_GRAPH)?, within.clone()),
        Quad::new(metadata.clone(), node(METADATA_OF)?, node(graph)?, within.clone()),
    ];
    says.extend(
        taken
            .into_iter()
            .map(|q| Quad::new(q.subject, q.predicate, q.object, within.clone())),
    );
    if store.quads(block)?.is_empty() {
        store.clear_graph(block)?;
    }
    store.add(says)
}

/// Every named thing `block` says something of that `is_graph` answers for, in name order.
pub fn subjects(store: &Store, block: &str, is_graph: impl Fn(&str, &[Quad]) -> bool) -> Result<Vec<String>, Error> {
    let said = store.quads(block)?;
    let named: BTreeSet<String> = said
        .iter()
        .filter_map(|q| match &q.subject {
            NamedOrBlankNode::NamedNode(s) if s.as_str() != block => Some(s.as_str().to_string()),
            _ => None,
        })
        .collect();
    Ok(named
        .into_iter()
        .filter(|s| {
            let of: Vec<Quad> = said
                .iter()
                .filter(|q| matches!(&q.subject, NamedOrBlankNode::NamedNode(n) if n.as_str() == s))
                .cloned()
                .collect();
            is_graph(s, &of)
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn what_one_graph_said_of_another_is_moved_into_that_graphs_metadata_graph_with_its_period() {
        let store = Store::new().unwrap();
        store
            .update(
                "PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX orexis: <http://example.org/orexis#>
                INSERT DATA { GRAPH <urn:all> {
                  <urn:a> a orexis:BeliefGraph ; orexis:ownedBy <urn:me> ;
                          dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start 1 ] .
                  <urn:thing> a <urn:Weighing> . }
                  GRAPH <urn:a> { <urn:x> <urn:p> 1 } }",
            )
            .unwrap();
        let graphs = subjects(&store, "urn:all", |_, of| {
            of.iter().any(|q| q.predicate.as_str().ends_with("ownedBy"))
        })
        .unwrap();
        assert_eq!(graphs, ["urn:a"]);
        moved(&store, "urn:all", "urn:a").unwrap();
        assert_eq!(store.metadata_of("urn:a").unwrap().as_deref(), Some("urn:a.metadata"));
        assert_eq!(store.quads("urn:a.metadata").unwrap().len(), 7);
        assert_eq!(store.quads("urn:all").unwrap().len(), 1);
        assert_eq!(store.quads("urn:a").unwrap().len(), 1);
    }
}
