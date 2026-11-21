//! WHAT TAKING A STEP SAYS, as `agent/execution/says.py` makes it: an action a step says something by has an
//! `execution:Saying` among its operations, an `sh:construct` over the beliefs holding as the step is taken, with the
//! step's parameters as `$tokens` and `$now`. What it constructs is read as documents — one per IRI said to be
//! `execution:to` somebody, its kinds of graph and its period the document's rows, and holding every fact about each
//! thing it `execution:states` and the blank nodes those reach — and the container hands each to speech; execution
//! names no speech. THE DOCUMENT IS NOT WHAT IT STATES: a text names the two apart, and one that types its document
//! as anything but a graph is refused, since a call and the graph a call is said in under one IRI is one name for two
//! things.

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

use orexis::rdf::RDF_TYPE;
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

/// The result read as documents: one per IRI said to be `execution:to` somebody, holding what it `execution:states`.
fn documents(store: &Store, triples: &[Triple], action: &str) -> Result<Vec<(Vec<String>, Document)>, Error> {
    let to_p = format!("{EXECUTION}to");
    let states_p = format!("{EXECUTION}states");
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
    let mut out: Vec<(String, Vec<String>, Document)> = Vec::new();
    let mut used: HashSet<&Triple> = HashSet::new();
    for (graph, agents) in &to {
        let node: NamedOrBlankNode = NamedNode::new_unchecked(graph).into();
        let mut mine: HashSet<&Triple> = HashSet::new();
        //  THE DOCUMENT, AND EACH THING IT STATES: what is said of either, and of the blank nodes those reach.
        let mut frontier: HashSet<NamedOrBlankNode> = HashSet::from([node.clone()]);
        frontier.extend(
            triples
                .iter()
                .filter(|t| t.subject == node && t.predicate.as_str() == states_p)
                .filter_map(|t| NamedOrBlankNode::try_from(t.object.clone()).ok()),
        );
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
            if p == RDF_TYPE && !a_graph {
                return Err(Error::Evaluation(format!(
                    "{} says a document, {graph}, that is a {}, which is no kind of graph: the thing a document \
                     states is named apart from it (execution:states)",
                    local_of(action),
                    t.object
                )));
            }
            if p == to_p || p == states_p || p == TEMPORAL || a_graph {
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
            .filter(|t| !(t.subject == node && (t.predicate.as_str() == to_p || t.predicate.as_str() == states_p)))
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
        //  TOLD IN THE ORDER OF WHAT IS STATED, never of the graphs' names, which are for eyes: a round is told
        //  before the claim named off it, whatever either is said in.
        let stated = triples
            .iter()
            .filter(|t| t.subject == node && t.predicate.as_str() == states_p)
            .map(|t| match &t.object {
                Term::NamedNode(n) => n.as_str().to_string(),
                other => other.to_string(),
            })
            .min()
            .unwrap_or_else(|| graph.clone());
        out.push((stated, agents.iter().cloned().collect(), Document::of_quads(quads)));
    }
    out.sort_by(|a, b| a.0.cmp(&b.0));
    let out: Vec<(Vec<String>, Document)> = out.into_iter().map(|(_, agents, doc)| (agents, doc)).collect();
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

    use super::*;

    const T: &str = "http://example.org/test#";

    fn store() -> Store {
        let st = Store::new().unwrap();
        st.update(&format!(
            r#"PREFIX : <http://example.org/test#>
  PREFIX execution: <http://example.org/orexis/execution#>
  PREFIX orexis: <http://example.org/orexis#>
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  PREFIX sh: <http://www.w3.org/ns/shacl#>
  INSERT DATA {{
  GRAPH :vocabulary {{ :NoteGraph rdfs:subClassOf orexis:BeliefGraph , orexis:Graph . }}
  GRAPH :actions {{
    :Noting a orexis:Action ; orexis:takes :topic ;
      execution:implementation [ execution:operation [ a execution:Saying ; sh:construct """PREFIX execution: <http://example.org/orexis/execution#> CONSTRUCT {{ ?note a <{T}Note> ; <{T}about> $topic ; <{T}at> $now .
                                              ?said a <{T}NoteGraph> ; execution:states ?note ; execution:to ?peer }}
          WHERE {{ ?peer <{T}reads> $topic . BIND(IRI(CONCAT(STR($topic), "-note")) AS ?note)
                   BIND(IRI(CONCAT(STR(?note), ".said")) AS ?said) }}""" ] ] .
    :Looking a orexis:Action ; orexis:takes :topic . }}
  GRAPH :world {{ :ann :reads :rain . :bob :reads :rain . }}
  GRAPH :catalogue {{
    :catalogue a orexis:CatalogueGraph .
    :vocabulary a orexis:OntologyGraph , orexis:BeliefGraph .
    :actions a orexis:ActionGraph .
    :world a orexis:BeliefGraph . }} }}"#
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
        let note = format!("{T}rain-note.said");
        assert_eq!(
            doc.kinds(),
            BTreeMap::from([(note.clone(), BTreeSet::from([format!("{T}NoteGraph")]))]),
            "the kind is a row, the note said in a graph of its own, named apart from it"
        );
        assert!(
            doc.quads()
                .iter()
                .filter(|q| q.graph_name.to_string() == format!("<{note}>"))
                .all(|q| q.subject.to_string() == format!("<{T}rain-note>")),
            "what the graph holds is about the note it states, never about itself"
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
    fn a_document_typed_as_the_thing_it_states_is_refused() {
        let store = store();
        store
            .update(&format!(
                r#"PREFIX : <http://example.org/test#>
  PREFIX execution: <http://example.org/orexis/execution#>
  PREFIX orexis: <http://example.org/orexis#>
  PREFIX sh: <http://www.w3.org/ns/shacl#>
  INSERT DATA {{ GRAPH :actions {{
    :Punning a orexis:Action ; orexis:takes :topic ;
      execution:implementation [ execution:operation [ a execution:Saying ; sh:construct """PREFIX execution: <http://example.org/orexis/execution#> CONSTRUCT {{ ?note a <{T}Note> , <{T}NoteGraph> ; execution:to ?peer }}
          WHERE {{ ?peer <{T}reads> $topic . BIND(IRI(CONCAT(STR($topic), "-note")) AS ?note) }}""" ] ] . }} }}"#
            ))
            .unwrap();
        let now = instant("2026-01-01T12:00:00+00:00").unwrap();
        let refused = says(&store, &step("Punning"), None, now).unwrap_err().to_string();
        assert!(refused.contains("no kind of graph"), "{refused}");
    }

    #[test]
    fn a_step_whose_action_says_nothing_tells_nothing() {
        let now = instant("2026-01-01T12:00:00+00:00").unwrap();
        assert!(says(&store(), &step("Looking"), None, now).unwrap().is_empty());
    }
}
