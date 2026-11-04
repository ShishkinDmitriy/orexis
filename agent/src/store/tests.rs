//! The store's reads, held to what `agent/store.py` answers over the same catalogue.

use std::path::Path;
use std::sync::Arc;

use super::*;
use crate::clock::instant as at;
use crate::namespaces::Namespaces;
use crate::ontology::{BELIEF, DERIVED, RECORD};

const T: &str = "http://example.org/test#";

/// A catalogue of five graphs: the world's, the agent's own state, a peer's, one holding for an hour, and a record
/// whose hour is over — with the vocabulary saying a state graph is a belief.
const CATALOGUED: &str = r#"
@prefix orexis: <http://example.org/orexis#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix : <http://example.org/test#> .

:catalogue {
  :catalogue a orexis:CatalogueGraph .
  :vocabulary a orexis:OntologyGraph .
  :world a orexis:BeliefGraph .
  :mine a orexis:BeliefGraph ; orexis:ownedBy :me .
  :theirs a orexis:BeliefGraph ; orexis:ownedBy :them .
  :hour a orexis:BeliefGraph ; dcterms:temporal [ orexis:start "2026-01-01T12:00:00Z"^^xsd:dateTime ;
                                                    orexis:end "2026-01-01T13:00:00Z"^^xsd:dateTime ] .
  :record a orexis:RecordGraph ; dcterms:temporal [ orexis:start "2026-01-01T10:00:00Z"^^xsd:dateTime ;
                                                     orexis:end "2026-01-01T11:00:00Z"^^xsd:dateTime ] .
}
:vocabulary { :StateGraph rdfs:subClassOf orexis:BeliefGraph . }
:world { :bed :moisture 0.3 . }
:mine { :bed :believed :dry . }
"#;

fn store() -> Store {
    let tree = Path::new(env!("CARGO_MANIFEST_DIR"));
    let store = Store::new(Arc::new(Namespaces::of_tree(tree).unwrap())).unwrap();
    store.load_trig(CATALOGUED).unwrap();
    store
}

fn t(local: &str) -> String {
    format!("{T}{local}")
}

#[test]
fn the_catalogue_is_found_by_its_own_row_and_two_are_refused() {
    let store = store();
    assert_eq!(store.catalogue().unwrap(), Some(t("catalogue")));
    store
        .load_trig(&format!(
            "<{T}other> {{ <{T}other> a <http://example.org/orexis#CatalogueGraph> . }}"
        ))
        .unwrap();
    assert!(
        store
            .catalogue()
            .unwrap_err()
            .to_string()
            .contains("two graphs describe themselves as the catalogue")
    );
}

#[test]
fn graphs_of_a_kind_are_every_graph_typed_so_in_name_order() {
    let found = store().graphs_of(&[BELIEF], &Within::default()).unwrap();
    assert_eq!(found, [t("hour"), t("mine"), t("theirs"), t("world")]);
}

#[test]
fn a_holder_is_handed_its_own_and_the_common_and_common_is_what_no_agent_owns() {
    let store = store();
    let mine = Within {
        holder: Some(t("me")),
        ..Within::default()
    };
    assert_eq!(
        store.graphs_of(&[BELIEF], &mine).unwrap(),
        [t("hour"), t("mine"), t("world")]
    );
    assert_eq!(
        store.graphs_of(&[BELIEF], &Within::common()).unwrap(),
        [t("hour"), t("world")]
    );
}

#[test]
fn at_an_instant_a_graph_is_handed_while_its_period_holds_and_a_record_at_the_present() {
    let store = store();
    let inside = store
        .graphs_of(&[BELIEF], &Within::at(at("2026-01-01T12:30:00Z").unwrap()))
        .unwrap();
    assert!(inside.contains(&t("hour")));
    let after = store
        .graphs_of(&[BELIEF], &Within::at(at("2026-01-01T13:00:00Z").unwrap()))
        .unwrap();
    assert!(!after.contains(&t("hour")), "an end is exclusive");
    let over = Within {
        at: Some(at("2026-01-01T12:30:00Z").unwrap()),
        until: Some(at("2026-01-01T13:30:00Z").unwrap()),
        ..Within::default()
    };
    assert!(
        !store.graphs_of(&[BELIEF], &over).unwrap().contains(&t("hour")),
        "held throughout a period, or not"
    );
    let asked = Within {
        at: Some(at("2026-01-01T10:30:00Z").unwrap()),
        now: Some(at("2026-01-01T12:00:00Z").unwrap()),
        ..Within::default()
    };
    assert_eq!(
        store.graphs_of(&[RECORD], &asked).unwrap(),
        Vec::<String>::new(),
        "a record is read at the present"
    );
}

#[test]
fn a_reader_reads_the_union_of_the_graphs_it_is_handed() {
    let store = store();
    let text = "SELECT ?p ?o WHERE { <http://example.org/test#bed> ?p ?o } ORDER BY ?p";
    let both = store.rows(text, &[&t("world"), &t("mine")]).unwrap();
    assert_eq!(
        both.iter().filter_map(|r| value(r, "p")).collect::<Vec<_>>(),
        [t("believed"), t("moisture")]
    );
    assert!(
        store.rows(text, &[]).unwrap().is_empty(),
        "handed nothing, a text naming no graph reads nothing"
    );
}

#[test]
fn a_class_is_closed_by_one_step_of_the_vocabulary() {
    let store = store();
    assert_eq!(
        store.closed(&t("StateGraph")).unwrap(),
        [BELIEF.to_string(), t("StateGraph")]
    );
    assert_eq!(
        store.closed(BELIEF).unwrap(),
        [BELIEF],
        "a class the vocabulary puts beneath nothing is itself"
    );
}

#[test]
fn an_entry_says_every_kind_whose_and_when_and_lands_in_the_catalogue_with_its_graph() {
    let store = store();
    let start = at("2026-01-01T12:00:00Z").unwrap();
    let entry = store
        .entry(
            &t("state"),
            &[&t("StateGraph")],
            DERIVED,
            Some(&t("me")),
            Some(start),
            None,
        )
        .unwrap();
    store
        .update(&format!(
            "INSERT DATA {{ GRAPH <{T}state> {{ <{T}bed> <{T}believed> <{T}wet> }} {entry} }}"
        ))
        .unwrap();
    let mine = Within {
        holder: Some(t("me")),
        at: Some(at("2026-01-01T12:30:00Z").unwrap()),
        ..Within::default()
    };
    assert!(
        store.graphs_of(&[BELIEF], &mine).unwrap().contains(&t("state")),
        "typed beneath, owned, holding"
    );
    let early = Within {
        at: Some(at("2026-01-01T11:00:00Z").unwrap()),
        ..Within::default()
    };
    assert!(
        !store.graphs_of(&[BELIEF], &early).unwrap().contains(&t("state")),
        "not before it starts"
    );
}

#[test]
fn a_text_run_again_is_not_parsed_again() {
    let store = store();
    for _ in 0..10 {
        store.graphs_of(&[BELIEF], &Within::default()).unwrap();
    }
    let (parsed, run) = store.statements();
    assert_eq!((parsed, run), (1, 10));
}

#[test]
fn a_prefix_the_tree_declares_is_spoken_without_a_header() {
    let store = store();
    let rows = store
        .rows("SELECT ?g WHERE { GRAPH ?g { ?g a orexis:CatalogueGraph } }", &[])
        .unwrap();
    assert_eq!(rows.len(), 1);
    assert!(
        store
            .rows("SELECT * WHERE { ?s nobody:knows ?o }", &[])
            .unwrap_err()
            .to_string()
            .contains("nobody")
    );
}
