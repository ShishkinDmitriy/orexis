//! A document says what its graphs are, held to what `agent/tests/test_document.py` holds the Python loader to.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

use super::*;
use crate::ontology::CATALOGUE;
use crate::snapshots;
use crate::store::{Within, iri, value};

const PREFIXES: &str = "@prefix orexis: <http://example.org/orexis#> .\n\
@prefix planning: <http://example.org/orexis/planning#> .\n@prefix dcterms: <http://purl.org/dc/terms/> .\n";
const PLANNING: &str = "http://example.org/orexis/planning#";

/// A directory of the test's own, removed when it is done.
struct Dir(PathBuf);

impl Dir {
    fn new() -> Self {
        static N: AtomicUsize = AtomicUsize::new(0);
        let path = std::env::temp_dir().join(format!(
            "orexis-doc-{}-{}",
            std::process::id(),
            N.fetch_add(1, Ordering::SeqCst)
        ));
        fs::create_dir_all(&path).unwrap();
        Dir(path)
    }

    fn write(&self, name: &str, text: &str) -> PathBuf {
        let path = self.0.join(name);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(&path, format!("{PREFIXES}{text}")).unwrap();
        path
    }
}

impl Drop for Dir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn store() -> Store {
    let store = Store::new(snapshots::namespaces()).unwrap();
    store
        .update(&format!(
            "INSERT DATA {{ GRAPH <{CATALOGUE}> {{ <{CATALOGUE}> a orexis:CatalogueGraph }} }}"
        ))
        .unwrap();
    store
}

fn uri(path: &Path) -> String {
    file_uri(path).unwrap()
}

/// What the catalogue says of `graph`, each predicate and object by its local part.
fn said(store: &Store, graph: &str) -> BTreeSet<(String, String)> {
    let text = format!("SELECT ?p ?o WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{graph}> ?p ?o }} }}");
    let local = |s: String| s.rsplit('#').next().unwrap().to_string();
    store
        .rows(&text, &[])
        .unwrap()
        .iter()
        .map(|r| (local(value(r, "p").unwrap()), local(value(r, "o").unwrap())))
        .collect()
}

fn refusal(result: Result<Document, Error>) -> String {
    match result {
        Ok(_) => panic!("a document that should have been refused was read"),
        Err(e) => e.to_string(),
    }
}

#[test]
fn a_turtle_file_is_one_graph_named_by_the_file_and_its_rows_go_to_the_catalogue() {
    let dir = Dir::new();
    let path = dir.write(
        "anything.ttl",
        "<> a orexis:BeliefGraph .\n<urn:disk> <urn:on> <urn:peg> .\n",
    );
    let (store, name) = (store(), uri(&path));
    let put = store
        .put_document(&Document::read(&path).unwrap(), None, None, None, false)
        .unwrap();
    assert_eq!(put, std::slice::from_ref(&name));
    assert_eq!(
        store.graphs_of(&[BELIEF], &Within::default()).unwrap(),
        std::slice::from_ref(&name)
    );
    assert_eq!(
        said(&store, &name),
        [
            ("type".into(), "BeliefGraph".into()),
            ("arrivedBy".into(), "Asserted".into())
        ]
        .into()
    );
    let held = store.rows("SELECT ?s ?p ?o WHERE { ?s ?p ?o }", &[&name]).unwrap();
    assert_eq!(held.len(), 1, "the graph holds its facts and not its kind");
    assert_eq!(iri(&held[0], "o").as_deref(), Some("urn:peg"));
}

#[test]
fn a_period_stated_of_the_document_goes_with_its_row() {
    let dir = Dir::new();
    let path = dir.write(
        "prediction.ttl",
        "<> a orexis:ForecastGraph ;\n    dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start \
         \"2026-01-01T00:00:00Z\" ] .\n<urn:a> <urn:b> <urn:c> .\n",
    );
    let store = store();
    let name = store
        .put_document(&Document::read(&path).unwrap(), None, None, None, false)
        .unwrap()[0]
        .clone();
    let starts = store
        .rows(
            &format!(
                "SELECT ?start WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{name}> dcterms:temporal ?p . \
                 ?p orexis:start ?start }} }}"
            ),
            &[],
        )
        .unwrap();
    assert_eq!(value(&starts[0], "start").as_deref(), Some("2026-01-01T00:00:00Z"));
    assert_eq!(store.rows("SELECT ?s WHERE { ?s ?p ?o }", &[&name]).unwrap().len(), 1);
}

#[test]
fn a_trig_file_names_its_graphs_and_states_their_kinds_in_its_default_graph() {
    let dir = Dir::new();
    let path = dir.write(
        "two.trig",
        "<#desires> a planning:DesireGraph .\n<#state> a orexis:BeliefGraph .\n\
         <#desires> { <urn:me> planning:holds <urn:home> . }\n<#state> { <urn:disk> <urn:on> <urn:peg> . }\n",
    );
    let doc = Document::read(&path).unwrap();
    let base = uri(&path);
    let kinds = doc.kinds();
    assert_eq!(
        kinds[&format!("{base}#desires")],
        [format!("{PLANNING}DesireGraph")].into()
    );
    assert_eq!(kinds[&format!("{base}#state")], [BELIEF.to_string()].into());
    let store = store();
    let put = store.put_document(&doc, Some("urn:me"), None, None, false).unwrap();
    assert_eq!(put, [format!("{base}#desires"), format!("{base}#state")]);
    assert!(said(&store, &format!("{base}#state")).contains(&("ownedBy".into(), "urn:me".into())));
}

#[test]
fn put_again_replaces_the_graph_and_its_row() {
    let dir = Dir::new();
    let path = dir.write(
        "state.ttl",
        "<> a orexis:BeliefGraph .\n<urn:disk> <urn:on> <urn:peg_a> .\n",
    );
    let store = store();
    store
        .put_document(&Document::read(&path).unwrap(), None, None, None, false)
        .unwrap();
    let path = dir.write(
        "state.ttl",
        "<> a orexis:WorldGraph .\n<urn:disk> <urn:on> <urn:peg_c> .\n",
    );
    let name = store
        .put_document(&Document::read(&path).unwrap(), None, None, None, false)
        .unwrap()[0]
        .clone();
    assert_eq!(
        said(&store, &name),
        [
            ("type".into(), "WorldGraph".into()),
            ("arrivedBy".into(), "Asserted".into())
        ]
        .into()
    );
    let held = store.rows("SELECT ?o WHERE { ?s ?p ?o }", &[&name]).unwrap();
    assert_eq!(
        held.iter().filter_map(|r| iri(r, "o")).collect::<Vec<_>>(),
        ["urn:peg_c"]
    );
}

#[test]
fn a_file_is_refused_where_it_says_too_little_or_what_only_the_loader_says_or_the_self_twice() {
    for (text, expected) in [
        ("<urn:a> <urn:b> <urn:c> .\n", "no kind"),
        ("<> a orexis:CatalogueGraph .\n", "catalogue"),
        (
            "<> a orexis:BeliefGraph ; orexis:arrivedBy orexis:Derived .\n",
            "only the loader",
        ),
        (
            "<> a orexis:BeliefGraph ; orexis:ownedBy <urn:ann> , <urn:bob> .\n",
            "a graph has one owner",
        ),
        (
            "<> a orexis:BeliefGraph ; orexis:ownedBy [] .\n",
            "an owner is an agent, named",
        ),
        (
            "<> a orexis:WorldGraph .\n<urn:someone> a orexis:Self .\n",
            "no self graph",
        ),
        (
            "<> a orexis:SelfGraph , orexis:WorldGraph .\n<urn:ann> a orexis:Self .\n",
            "a self graph is nothing else",
        ),
        ("<> a orexis:SelfGraph .\n", "states 0 selves"),
        (
            "<> a orexis:SelfGraph .\n<urn:ann> a orexis:Self .\n<urn:bob> a orexis:Self .\n",
            "states 2 selves",
        ),
        (
            "<> a orexis:SelfGraph ; orexis:ownedBy <urn:bob> .\n<urn:ann> a orexis:Self .\n",
            "a self graph is its self's",
        ),
        (
            "<> a orexis:SelfGraph , orexis:Self .\n<urn:ann> a orexis:Self .\n",
            "of a graph",
        ),
        (
            "<> a orexis:WorldGraph .\n<urn:g> a orexis:SelfGraph .\n",
            "in its rows",
        ),
    ] {
        let dir = Dir::new();
        let got = refusal(Document::read(&dir.write("bad.ttl", text)));
        assert!(
            got.contains(expected),
            "{text:?}: refused with {got:?}, not {expected:?}"
        );
    }
}

#[test]
fn a_file_says_whose_its_graph_is_and_a_self_graph_is_its_selfs() {
    let dir = Dir::new();
    let whose = |name: &str, text: &str| {
        let path = dir.write(name, text);
        Document::read(&path).unwrap().whose(&uri(&path))
    };
    assert_eq!(
        whose("rose.ttl", "<> a planning:DesireGraph ; orexis:ownedBy <urn:fern> .\n").as_deref(),
        Some("urn:fern")
    );
    assert_eq!(
        whose("who.ttl", "<> a orexis:SelfGraph .\n<urn:fern> a orexis:Self .\n").as_deref(),
        Some("urn:fern")
    );
    assert_eq!(
        whose(
            "both.ttl",
            "<> a orexis:SelfGraph ; orexis:ownedBy <urn:fern> .\n<urn:fern> a orexis:Self .\n"
        )
        .as_deref(),
        Some("urn:fern"),
        "one fact, said twice and agreeing"
    );
    assert_eq!(whose("state.ttl", "<> a orexis:BeliefGraph .\n"), None);
}

#[test]
fn a_document_from_no_file_says_neither_whose_a_graph_is_nor_who_the_self_is() {
    for text in [
        "<urn:g> a orexis:BeliefGraph ; orexis:ownedBy <urn:someone> .\n<urn:g> { <urn:a> <urn:b> <urn:c> }\n",
        "<urn:g> a orexis:BeliefGraph .\n<urn:g> { <urn:someone> a orexis:Self }\n",
        "<urn:g> a orexis:SelfGraph .\n<urn:g> { <urn:someone> a orexis:Self }\n",
    ] {
        let got = refusal(Document::of(format!("{PREFIXES}{text}").as_bytes()));
        assert!(got.contains("only the world's own documents say"), "{text:?}: {got}");
    }
}

#[test]
fn a_trig_row_about_no_graph_the_document_holds_is_refused() {
    let dir = Dir::new();
    let path = dir.write(
        "stray.trig",
        "<#g> a orexis:BeliefGraph .\n<urn:x> <urn:y> <urn:z> .\n<#g> { <urn:a> <urn:b> <urn:c> . }\n",
    );
    assert!(refusal(Document::read(&path)).contains("no graph it holds"));
}

#[test]
fn an_import_by_relative_iri_names_the_graph_the_imported_file_is_loaded_under() {
    let dir = Dir::new();
    let imported = dir.write("domain/ontology.ttl", "<> a orexis:OntologyGraph .\n");
    let path = dir.write(
        "world/world.ttl",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<> a orexis:WorldGraph ; owl:imports \
         <../domain/ontology.ttl> .\n",
    );
    assert_eq!(Document::read(&path).unwrap().imports(), [uri(&imported)]);
    assert_eq!(
        Document::read(&imported).unwrap().kinds(),
        [(uri(&imported), [crate::ontology::ONTOLOGY.to_string()].into())].into()
    );
}

#[test]
fn a_path_is_the_iri_python_makes_of_it() {
    let dir = Dir::new();
    let path = dir.write("a b+ü.ttl", "<> a orexis:BeliefGraph .\n");
    assert!(uri(&path).ends_with("/a%20b%2B%C3%BC.ttl"), "{}", uri(&path));
}
