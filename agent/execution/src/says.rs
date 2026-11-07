//! WHAT TAKING A STEP SAYS, as `agent/execution/says.py` makes it: an action a step says something by has an
//! `execution:Saying` among its operations, an `sh:construct` over the beliefs holding as the step is taken, with the
//! step's parameters as `$tokens` and `$now`. What it constructs is read as documents — one per IRI said to be
//! `execution:to` somebody, holding every fact about it and the blank nodes those reach, its kinds of graph and its
//! period as the document's rows — and the container hands each to speech; execution names no speech.

use std::collections::{BTreeMap, BTreeSet, HashSet};

use oxigraph::model::{GraphName, NamedNode, NamedOrBlankNode, Quad, Term, Triple};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::ontology::{BELIEF, GRAPH, RECORD, local_of};
use orexis::store::{Store, Within};

use crate::Said;
use crate::command::tokens;
use crate::implementation::operations;
use crate::ontology::{EXECUTION, SAYING};

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const TEMPORAL: &str = "http://purl.org/dc/terms/temporal";

/// Every document the step `said` tells, with the agents it is to, made over the beliefs holding at `now`: every
/// saying of the action's implementation, or those of one `order`. Empty where it has none or its texts construct
/// nothing.
pub fn says(
    store: &Store,
    said: &Said,
    order: Option<f64>,
    now: DateTime,
) -> Result<Vec<(Vec<String>, Document)>, Error> {
    let Some(action) = said.get("fills") else {
        return Ok(Vec::new());
    };
    let texts: Vec<String> = operations(store, action)?
        .into_iter()
        .filter(|op| op.kind == SAYING && order.is_none_or(|o| op.order == o))
        .filter_map(|op| op.text)
        .collect();
    if texts.is_empty() {
        return Ok(Vec::new());
    }
    let tokens = tokens(store, said, action, now)?;
    let tokens: Vec<(&str, Value)> = tokens.iter().map(|(k, v)| (k.as_str(), v.clone())).collect();
    let known = store.graphs_of(
        &[BELIEF, RECORD],
        &Within {
            at: Some(now),
            now: Some(now),
            ..Within::default()
        },
    )?;
    let known: Vec<&str> = known.iter().map(String::as_str).collect();
    let mut triples = Vec::new();
    for text in texts {
        triples.extend(store.construct(&bind(&text, &tokens)?, &known)?);
    }
    documents(store, &triples, action)
}

fn blanks_of<'t>(triples: impl Iterator<Item = &'t Triple>) -> HashSet<NamedOrBlankNode> {
    triples
        .filter_map(|t| match &t.object {
            Term::BlankNode(b) => Some(NamedOrBlankNode::from(b.clone())),
            _ => None,
        })
        .collect()
}

/// The result read as documents: one per IRI said to be `execution:to` somebody.
fn documents(store: &Store, triples: &[Triple], action: &str) -> Result<Vec<(Vec<String>, Document)>, Error> {
    let to_p = format!("{EXECUTION}to");
    let mut to: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for t in triples {
        if t.predicate.as_str() == to_p
            && let NamedOrBlankNode::NamedNode(graph) = &t.subject
        {
            let agent = match &t.object {
                Term::NamedNode(n) => n.as_str().to_string(),
                Term::Literal(l) => l.value().to_string(),
                other => other.to_string(),
            };
            to.entry(graph.as_str().to_string()).or_default().insert(agent);
        }
    }
    let mut out = Vec::new();
    let mut used: HashSet<&Triple> = HashSet::new();
    for (graph, agents) in &to {
        let node: NamedOrBlankNode = NamedNode::new_unchecked(graph).into();
        let mut mine: HashSet<&Triple> = HashSet::new();
        let mut frontier: HashSet<NamedOrBlankNode> = HashSet::from([node.clone()]);
        while !frontier.is_empty() {
            let here: Vec<&Triple> = triples
                .iter()
                .filter(|t| frontier.contains(&t.subject) && !mine.contains(t))
                .collect();
            mine.extend(here.iter().copied());
            frontier = blanks_of(here.into_iter());
        }
        let mut about: HashSet<&Triple> = HashSet::new();
        for t in mine.iter().copied().filter(|t| t.subject == node) {
            let p = t.predicate.as_str();
            let a_graph = p == RDF_TYPE
                && match &t.object {
                    Term::NamedNode(kind) => store.closed(kind.as_str())?.iter().any(|k| k == GRAPH),
                    _ => false,
                };
            if p == to_p || p == TEMPORAL || a_graph {
                about.insert(t);
            }
        }
        let mut rows = about.clone();
        let mut frontier = blanks_of(about.into_iter());
        while !frontier.is_empty() {
            let here: Vec<&Triple> = mine.iter().copied().filter(|t| frontier.contains(&t.subject)).collect();
            rows.extend(here.iter().copied());
            frontier = blanks_of(here.into_iter());
        }
        let named = GraphName::NamedNode(NamedNode::new_unchecked(graph));
        let mut quads: Vec<Quad> = mine
            .iter()
            .filter(|t| t.predicate.as_str() != to_p)
            .map(|t| {
                let into = if rows.contains(*t) {
                    GraphName::DefaultGraph
                } else {
                    named.clone()
                };
                Quad::new(t.subject.clone(), t.predicate.clone(), t.object.clone(), into)
            })
            .collect();
        quads.sort_by_key(|q| q.to_string());
        used.extend(mine);
        out.push((agents.iter().cloned().collect(), Document::of_quads(quads)));
    }
    let stray: BTreeSet<String> = triples
        .iter()
        .filter(|t| !used.contains(t))
        .filter_map(|t| match &t.subject {
            NamedOrBlankNode::NamedNode(n) => Some(local_of(n.as_str())),
            _ => None,
        })
        .collect();
    if triples.iter().any(|t| !used.contains(t)) {
        log::warn!(
            "{} says {} fact(s) about no graph it is to anyone: {}",
            local_of(action),
            triples.iter().filter(|t| !used.contains(t)).count(),
            stray.into_iter().collect::<Vec<_>>().join(", ")
        );
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    //! `says`, held as `agent/execution/tests/test_says.py` holds it: a graph is an IRI the result says is
    //! `execution:to` an agent; its kind and whom it is to are rows about it, and everything else said of it is its
    //! content.

    use orexis::clock::instant;
    use orexis::snapshots::namespaces;

    use super::*;

    const T: &str = "http://example.org/test#";

    fn store() -> Store {
        let st = Store::new(namespaces()).unwrap();
        st.update(&format!(
            r#"INSERT DATA {{
  GRAPH <{T}vocabulary> {{ <{T}NoteGraph> rdfs:subClassOf orexis:BeliefGraph , orexis:Graph . }}
  GRAPH <{T}actions> {{
    <{T}Noting> a orexis:Action ; orexis:takes <{T}topic> ;
      execution:implementation [ execution:operation [ a execution:Saying ; sh:construct """CONSTRUCT {{ ?note a <{T}Note> , <{T}NoteGraph> ; <{T}about> $topic ; <{T}at> $now ;
                                              execution:to ?peer }}
          WHERE {{ ?peer <{T}reads> $topic . BIND(IRI(CONCAT(STR($topic), "-note")) AS ?note) }}""" ] ] .
    <{T}Looking> a orexis:Action ; orexis:takes <{T}topic> . }}
  GRAPH <{T}world> {{ <{T}ann> <{T}reads> <{T}rain> . <{T}bob> <{T}reads> <{T}rain> . }}
  GRAPH <{T}catalogue> {{
    <{T}catalogue> a orexis:CatalogueGraph .
    <{T}vocabulary> a orexis:OntologyGraph , orexis:BeliefGraph .
    <{T}actions> a orexis:ActionGraph .
    <{T}world> a orexis:BeliefGraph . }} }}"#
        ))
        .unwrap();
        st
    }

    fn step(action: &str) -> Said {
        [
            ("step", format!("{T}s")),
            ("fills", format!("{T}{action}")),
            ("topic", format!("{T}rain")),
        ]
        .into_iter()
        .map(|(k, v)| (k.to_string(), v))
        .collect()
    }

    #[test]
    fn a_step_tells_one_document_to_every_agent_it_is_to() {
        let store = store();
        let now = instant("2026-01-01T12:00:00+00:00").unwrap();
        let told = says(&store, &step("Noting"), None, now).unwrap();
        assert_eq!(told.len(), 1);
        let (agents, doc) = &told[0];
        assert_eq!(*agents, [format!("{T}ann"), format!("{T}bob")]);
        let note = format!("{T}rain-note");
        assert_eq!(
            doc.kinds(),
            BTreeMap::from([(note.clone(), BTreeSet::from([format!("{T}NoteGraph")]))]),
            "the kind is a row, the note its own graph"
        );
        let content: BTreeSet<String> = doc
            .quads()
            .iter()
            .filter(|q| q.graph_name.to_string() == format!("<{note}>"))
            .map(|q| q.predicate.as_str().rsplit('#').next().unwrap().to_string())
            .collect();
        assert_eq!(content, BTreeSet::from(["type".into(), "about".into(), "at".into()]));
        assert!(
            !doc.quads()
                .iter()
                .any(|q| q.predicate.as_str() == format!("{EXECUTION}to")),
            "whom it is to addresses the document and is no part of it"
        );
    }

    #[test]
    fn a_step_whose_action_says_nothing_tells_nothing() {
        let now = instant("2026-01-01T12:00:00+00:00").unwrap();
        assert!(says(&store(), &step("Looking"), None, now).unwrap().is_empty());
    }
}
