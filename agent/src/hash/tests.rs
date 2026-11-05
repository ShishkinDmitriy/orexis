//! Hashing what a named graph holds, held to `agent/tests/hash_named_graph/`'s cases — the digests the Python
//! kernel wrote into each diff, so the two kernels agree on where a world stands — and to the partition each case
//! is about, as `agent/tests/test_hash_named_graph.py` declares it.

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;

use super::*;
use crate::snapshots;

fn cases() -> Vec<PathBuf> {
    snapshots::cases_in(&snapshots::tree().join("tests/hash_named_graph"))
}

/// Which graphs of a case are one place: every graph it names stands in exactly one group.
fn same(case: &str) -> Vec<BTreeSet<&'static str>> {
    let groups: &[&[&str]] = match case {
        "a_graph_is_its_content_and_not_its_name" => &[&["here", "there"], &["elsewhere"]],
        "a_term_is_its_kind_and_not_only_its_text" => &[&["iri"], &["text"], &["one"], &["number"], &["en"], &["de"]],
        "a_number_is_its_value_rounded" => &[&["integer", "decimal", "near"], &["apart"]],
        "a_blank_node_is_its_content" => &[&["minted", "again"], &["deeper"], &["cyclic"]],
        other => panic!("{other} declares no partition"),
    };
    groups.iter().map(|g| g.iter().copied().collect()).collect()
}

/// Every graph of a store hashed, bar the catalogue, by the local part of its name.
fn hashed(store: &Store) -> BTreeMap<String, String> {
    let catalogue = store.catalogue().unwrap();
    store
        .graph_names()
        .unwrap()
        .into_iter()
        .filter(|g| Some(g) != catalogue.as_ref())
        .map(|g| {
            let digest = hash_named_graph(store, &g, None).unwrap();
            (g.rsplit('#').next().unwrap().to_string(), digest)
        })
        .collect()
}

#[test]
fn hashing_leaves_the_catalogue_the_diff_says() {
    for case in cases() {
        let store = snapshots::stand_in(&case);
        hashed(&store);
        snapshots::held_to_diff(&case, &store, "hash_named_graph");
    }
}

#[test]
fn the_graphs_a_case_calls_one_place_hash_alike_and_the_rest_do_not() {
    for case in cases() {
        let stem = case.file_stem().unwrap().to_str().unwrap().to_string();
        let groups = same(&stem);
        let digests = hashed(&snapshots::stand_in(&case));
        let named: BTreeSet<&str> = groups.iter().flatten().copied().collect();
        let held: BTreeSet<&str> = digests.keys().map(String::as_str).collect();
        assert!(
            named.is_subset(&held),
            "{stem}: {:?} is in no graph",
            named.difference(&held)
        );
        let loose: Vec<_> = held.difference(&named).filter(|g| **g != "ontology").collect();
        assert!(loose.is_empty(), "{stem}: {loose:?} is in no group");
        let mut apart = BTreeSet::new();
        for group in &groups {
            let one: BTreeSet<&String> = group.iter().map(|g| &digests[*g]).collect();
            assert_eq!(one.len(), 1, "{stem}: {group:?} is one place, and hashed {one:?}");
            apart.insert(one.into_iter().next().unwrap().clone());
        }
        assert_eq!(apart.len(), groups.len(), "{stem}: two groups hash alike");
    }
}

#[test]
fn every_case_is_read_and_no_diff_is_orphaned() {
    let found = cases();
    assert!(found.len() >= 4, "{found:?}");
    let directory = snapshots::tree().join("tests/hash_named_graph");
    assert!(snapshots::orphans_in(&directory).is_empty());
}

// --- what a case cannot reach ----------------------------------------------------------------------------------

fn store() -> Store {
    let store = Store::new(snapshots::namespaces()).unwrap();
    store
        .update("INSERT DATA { GRAPH <urn:test:catalogue> { <urn:test:catalogue> a orexis:CatalogueGraph } }")
        .unwrap();
    store
}

fn row(store: &Store, graph: &str) -> Vec<String> {
    store
        .quads("urn:test:catalogue")
        .unwrap()
        .into_iter()
        .filter(|q| q.subject.to_string() == format!("<{graph}>") && q.predicate.as_str() == HASH)
        .map(|q| match q.object {
            Term::Literal(l) => l.value().to_string(),
            other => other.to_string(),
        })
        .collect()
}

#[test]
fn one_graph_hashes_to_one_row_however_often_it_is_asked() {
    let store = store();
    store
        .update("INSERT DATA { GRAPH <urn:test:a> { <urn:s> <urn:p> 1 } }")
        .unwrap();
    let first = hash_named_graph(&store, "urn:test:a", None).unwrap();
    assert_eq!(row(&store, "urn:test:a"), std::slice::from_ref(&first));
    assert_eq!(hash_named_graph(&store, "urn:test:a", None).unwrap(), first);
    assert_eq!(row(&store, "urn:test:a"), [first], "one row, not two");
}

#[test]
fn a_graph_the_store_never_heard_of_hashes_like_an_empty_one() {
    let store = store();
    assert_eq!(
        hash_named_graph(&store, "urn:test:nothing", None).unwrap(),
        hash_named_graph(&store, "urn:test:else", None).unwrap()
    );
}

#[test]
fn hashed_within_a_scope_a_fact_outside_it_is_not_where_the_world_stands() {
    let store = store();
    store
        .update(
            "INSERT DATA { GRAPH <urn:test:then> { <urn:disk> <urn:on> <urn:peg> . \
             <urn:disk> <urn:seenAt> \"2026-10-03T08:52:46Z\" } \
             GRAPH <urn:test:now> { <urn:disk> <urn:on> <urn:peg> . <urn:disk> <urn:seenAt> \"2026-10-03T09:12:45Z\" } }",
        )
        .unwrap();
    let within: BTreeSet<String> = ["urn:on".to_string()].into();
    assert_eq!(
        hash_named_graph(&store, "urn:test:then", Some(&within)).unwrap(),
        hash_named_graph(&store, "urn:test:now", Some(&within)).unwrap()
    );
    assert_ne!(
        hash_named_graph(&store, "urn:test:then", None).unwrap(),
        hash_named_graph(&store, "urn:test:now", None).unwrap()
    );
}

#[test]
fn within_a_scope_a_type_fact_counts_by_its_class() {
    let store = store();
    store
        .update(
            "INSERT DATA { GRAPH <urn:test:bare> { <urn:r> <urn:on> <urn:v> } \
             GRAPH <urn:test:round> { <urn:r> <urn:on> <urn:v> ; a <urn:Round> } \
             GRAPH <urn:test:other> { <urn:r> <urn:on> <urn:v> ; a <urn:Unread> } }",
        )
        .unwrap();
    let within: BTreeSet<String> = ["urn:on".to_string(), "urn:Round".to_string()].into();
    let [bare, typed, other] =
        ["bare", "round", "other"].map(|g| hash_named_graph(&store, &format!("urn:test:{g}"), Some(&within)).unwrap());
    assert_ne!(typed, bare, "a type the scope names is a fact the world stands by");
    assert_eq!(other, bare, "and one it does not name is not");
}

// --- Python's spelling, where a case does not reach it ---------------------------------------------------------

#[test]
fn a_float_is_spelled_as_python_spells_it() {
    for (x, spelled) in [
        (0.0, "0.0"),
        (-0.0, "-0.0"),
        (1.0, "1.0"),
        (0.3, "0.3"),
        (21.0, "21.0"),
        (0.0001, "0.0001"),
        (1e-5, "1e-05"),
        (1.5e-6, "1.5e-06"),
        (1e15, "1000000000000000.0"),
        (1e16, "1e+16"),
        (1.2345e20, "1.2345e+20"),
        (123.456, "123.456"),
        (f64::INFINITY, "inf"),
    ] {
        assert_eq!(py_float_repr(x), spelled, "{x}");
    }
    assert_eq!(py_round(1.0000001), 1.0);
    assert_eq!(
        py_round(0.1234565),
        0.123456,
        "rounded by the binary value, as Python rounds it"
    );
}

#[test]
fn a_string_is_quoted_as_python_quotes_it() {
    assert_eq!(py_str("plain"), "'plain'");
    assert_eq!(py_str("it's"), "\"it's\"");
    assert_eq!(py_str("both ' and \""), "'both \\' and \"'");
    assert_eq!(py_str("a\\b\n\tc\u{1}"), "'a\\\\b\\n\\tc\\x01'");
    assert_eq!(py_str("été"), "'été'");
    assert_eq!(py_str("\u{a0}"), "'\\xa0'");
    assert_eq!(py_tuple(&["x".into()]), "(x,)");
}
