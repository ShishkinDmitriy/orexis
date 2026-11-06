//! `admit`, held to `agent/planning/tests/admit/`'s cases, as `test_admit.py` holds the Python act: the present
//! ground admitted for the agent, and the diff the candidates written.

use std::path::PathBuf;

use orexis::snapshots;
use orexis::store::iri;

use super::*;

const PRESENT_Q: &str = "
SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start } }
ORDER BY ?start LIMIT 1";

const CANDIDATES_Q: &str = "SELECT ?c WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?c a planning:Candidate } }";

fn directory() -> PathBuf {
    snapshots::tree().join("planning/tests/admit")
}

fn present(store: &Store) -> String {
    iri(&store.rows(PRESENT_Q, &[]).unwrap()[0], "g").unwrap()
}

#[test]
fn admit_writes_the_candidates_the_diff_says() {
    for case in snapshots::cases_in(&directory()) {
        let store = snapshots::stand_in(&case);
        admit(&store, &present(&store), &Scope::default(), &mut Memo::default()).unwrap();
        snapshots::held_to_diff(&case, &store, "admit");
    }
}

#[test]
fn every_case_is_read_and_no_diff_is_orphaned() {
    snapshots::all_read(&directory(), 3);
}

fn candidates(store: &Store) -> BTreeSet<String> {
    store
        .rows(CANDIDATES_Q, &[])
        .unwrap()
        .iter()
        .filter_map(|r| iri(r, "c"))
        .collect()
}

#[test]
fn a_filling_the_world_admits_under_another_name_is_not_admitted_twice() {
    let store = snapshots::stand_in(&directory().join("one_lever_two_tanks.trig"));
    let ground = present(&store);
    admit(&store, &ground, &Scope::default(), &mut Memo::default()).unwrap();
    let written = candidates(&store);
    assert_eq!(written.len(), 2, "one lever, two tanks: two fillings");
    let first = written.iter().next().unwrap().clone();
    store
        .update(&format!(
            "DELETE {{ GRAPH ?cat {{ <{first}> ?p ?o }} }} INSERT {{ GRAPH ?cat {{ <urn:test:handed> ?p ?o }} }}
             WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{first}> ?p ?o }} }}"
        ))
        .unwrap();
    admit(&store, &ground, &Scope::default(), &mut Memo::default()).unwrap();
    let mut expected = written.clone();
    expected.remove(&first);
    expected.insert("urn:test:handed".to_string());
    assert_eq!(candidates(&store), expected);
}

#[test]
fn a_local_part_is_after_the_last_hash_or_slash() {
    assert_eq!(local_of("http://example.org/hanoi#disk"), "disk");
    assert_eq!(local_of("http://example.org/a/b"), "b");
}

// --- the wait, which no case reaches: two grounds, and whether the second holds anything else ------------------

fn grounds(second: &str) -> Store {
    let store = Store::new(snapshots::namespaces()).unwrap();
    store
        .load_trig(&format!(
            r#"@prefix orexis: <http://example.org/orexis#> .
@prefix planning: <http://example.org/orexis/planning#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix : <http://example.org/test#> .
:catalogue {{
  :catalogue a orexis:CatalogueGraph .
  :actions a orexis:ActionGraph .
  :now a planning:GroundGraph , orexis:Graph ; orexis:hash "sha256:a" ;
      dcterms:temporal [ orexis:start "2026-01-01T12:00:00Z"^^xsd:dateTime ; orexis:end "2026-01-01T13:00:00Z"^^xsd:dateTime ] .
  :later a planning:GroundGraph , orexis:Graph ; orexis:hash "{second}" ;
      dcterms:temporal [ orexis:start "2026-01-01T13:00:00Z"^^xsd:dateTime ] .
}}
:actions {{ planning:Wait a orexis:Action . }}
"#
        ))
        .unwrap();
    store
}

fn waits_from_now(store: &Store) -> bool {
    admit(
        store,
        "http://example.org/test#now",
        &Scope::default(),
        &mut Memo::default(),
    )
    .unwrap();
    store
        .rows(
            "SELECT ?c WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?c planning:fills planning:Wait } }",
            &[],
        )
        .unwrap()
        .len()
        == 1
}

#[test]
fn a_wait_is_admitted_where_a_later_ground_holds_something_else_and_nowhere_else() {
    assert!(
        waits_from_now(&grounds("sha256:b")),
        "a later ground the search can tell apart"
    );
    assert!(
        !waits_from_now(&grounds("sha256:a")),
        "every ground the same place: nothing to wait for"
    );
}

#[test]
fn a_scope_that_does_not_name_the_wait_admits_none() {
    let store = grounds("sha256:b");
    let only: HashSet<String> = HashSet::from(["http://example.org/test#fill".to_string()]);
    let scope = Scope {
        only: Some(&only),
        elsewhere: None,
    };
    admit(&store, "http://example.org/test#now", &scope, &mut Memo::default()).unwrap();
    assert!(candidates(&store).is_empty());
}
