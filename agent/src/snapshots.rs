//! THE SNAPSHOT RUNNER: a package's cases read as `agent/conftest.py` reads them, so the Python suite and this
//! crate are held to the SAME files — the conformance suite of the port
//! (the-agent-moves-to-rust-one-package-at-a-time).
//!
//! A case is `<function>/<case>.trig`, the store before, and `<case>.diff`, what the function changes; what the
//! function must leave is the case with the diff applied, compared quad by quad, blank nodes by their shape, and a
//! mismatch reported graph by graph. The
//! diff is the Python suite's to WRITE (`pytest --update-snapshots`) and this runner's only to hold a store to: a
//! case regenerated here would be a second writer of one claim, and two writers of a canonical form drift.

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, LazyLock};

use oxigraph::model::dataset::CanonicalizationAlgorithm;
use oxigraph::model::{Dataset, Graph};
use oxsdatatypes::DateTime;
use regex::Regex;

use crate::namespaces::Namespaces;
use crate::ontology::ONTOLOGY;
use crate::store::{Store, Within};

/// Where a case's default graph goes: the world's graph, as the Python stand-in names it.
pub const WORLD: &str = "http://example.org/test#world";
/// The agent a case is about, and its id.
pub const ME: &str = "http://example.org/test#keeper";
pub const AGENT: &str = "keeper";

const REGENERATE: &str = "pytest --update-snapshots";

static HUNK: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@").expect("a valid pattern"));

/// The one instant a case stands at: no case reads a clock.
pub fn now() -> DateTime {
    crate::clock::instant("2026-01-01T12:00:00Z").expect("a valid instant")
}

/// The agent's tree, whose ontologies say what a text may spell.
pub fn tree() -> &'static Path {
    Path::new(env!("CARGO_MANIFEST_DIR"))
}

/// The namespaces of the tree, read once a test process.
pub fn namespaces() -> Arc<Namespaces> {
    static FOUND: LazyLock<Arc<Namespaces>> =
        LazyLock::new(|| Arc::new(Namespaces::of_tree(tree()).expect("the tree's prefixes agree")));
    FOUND.clone()
}

/// The cases of one directory, sorted: `<case>.trig`, never a `<case>.actual.trig`.
pub fn cases_in(directory: &Path) -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = fs::read_dir(directory)
        .unwrap_or_else(|e| panic!("{}: {e}", directory.display()))
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e == "trig"))
        .filter(|p| p.file_stem().and_then(|s| s.to_str()).is_some_and(|s| !s.contains('.')))
        .collect();
    out.sort();
    out
}

/// The store a case describes, its rows closed: refused where it names no catalogue or types no vocabulary graph,
/// since a case says what its graphs are and what it is loaded with.
pub fn stand_in(case: &Path) -> Store {
    let store = Store::new(namespaces()).expect("an empty store");
    store
        .put_trig(WORLD, &read(case))
        .unwrap_or_else(|e| panic!("{}: {e}", name(case)));
    assert!(
        store.catalogue().expect("one catalogue").is_some(),
        "{} names no graph that describes itself as the catalogue",
        name(case)
    );
    assert!(
        !store
            .graphs_of(&[ONTOLOGY], &Within::default())
            .expect("graphs by kind")
            .is_empty(),
        "{} types no graph as the vocabulary's",
        name(case)
    );
    store.close_catalogue().expect("the rows closed");
    store
}

/// The lines that say something: a comment is never what a case is held to.
pub fn without_comments(text: &str) -> String {
    text.split_inclusive('\n')
        .filter(|l| !l.trim_start().starts_with('#'))
        .collect()
}

/// `case` with `diff` applied, strictly, by line number: a hunk that does not land where it says is a stale
/// diff, refused rather than guessed at.
pub fn patched(case: &str, diff: &str) -> String {
    let stripped = without_comments(case);
    let lines: Vec<&str> = stripped.split_inclusive('\n').collect();
    let mut out: Vec<&str> = Vec::new();
    let (mut at, mut started) = (0usize, false);
    for line in diff.split_inclusive('\n') {
        if let Some(head) = HUNK.captures(line) {
            started = true;
            let start: usize = head[1].parse::<usize>().expect("a line number") - 1;
            out.extend(&lines[at..start]);
            at = start;
            continue;
        }
        if !started {
            continue;
        }
        if let Some(added) = line.strip_prefix('+') {
            out.push(added);
        } else if let Some(said) = line.strip_prefix('-').or_else(|| line.strip_prefix(' ')) {
            assert_eq!(lines.get(at).copied(), Some(said), "stale diff at line {}", at + 1);
            if line.starts_with(' ') {
                out.push(lines[at]);
            }
            at += 1;
        }
    }
    out.extend(&lines[at..]);
    out.concat()
}

/// Hold what `function` left in `store` to `<case>.diff` beside the case: every quad of every named graph, blank
/// nodes by their shape. A mismatch names the quads left that the diff does not say and the quads it says that
/// were not left.
pub fn held_to_diff(case: &Path, store: &Store, function: &str) {
    let path = case.with_extension("diff");
    assert!(
        path.exists(),
        "{} has no diff: run `{REGENERATE}` and review {}",
        name(case),
        name(&path)
    );
    let expected = Store::new(namespaces()).expect("an empty store");
    expected
        .put_trig(WORLD, &patched(&read(case), &read(&path)))
        .unwrap_or_else(|e| panic!("{} with its diff: {e}", name(case)));
    if dataset(store) == dataset(&expected) {
        return;
    }
    panic!(
        "{}: the store `{function}` left differs from case + {}\n{}  where the Python kernel agrees, `{REGENERATE}` \
         rewrites the diff; where it does not, the port is wrong",
        name(case),
        name(&path),
        by_graph(store, &expected),
    );
}

/// What every suite asks of its directory: at least `least` cases are read, and no diff is left whose case was
/// deleted or renamed.
pub fn all_read(directory: &Path, least: usize) {
    let found = cases_in(directory);
    assert!(
        found.len() >= least,
        "{}: {} case(s), fewer than {least}",
        directory.display(),
        found.len()
    );
    let orphans = orphans_in(directory);
    assert!(
        orphans.is_empty(),
        "{}: orphaned diffs {orphans:?}",
        directory.display()
    );
}

/// Diffs whose case was deleted or renamed.
pub fn orphans_in(directory: &Path) -> Vec<String> {
    let mut out: Vec<String> = fs::read_dir(directory)
        .expect("a directory")
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e == "diff") && !p.with_extension("trig").exists())
        .map(|p| name(&p))
        .collect();
    out.sort();
    out
}

/// Every quad of every named graph — the default graph is nothing a case holds a function to — canonical as one
/// dataset, so a blank node two graphs share is held to being shared.
fn dataset(store: &Store) -> Dataset {
    let mut out = Dataset::new();
    for graph in store.graph_names().expect("the graphs") {
        for quad in store.quads(&graph).expect("a graph's quads") {
            out.insert(&quad);
        }
    }
    out.canonicalize(CanonicalizationAlgorithm::Unstable);
    out
}

/// One graph's triples, canonical alone: a graph that differs is reported by itself, and a blank node relabelled
/// in it relabels nothing in another.
fn triples(store: &Store, graph: &str) -> BTreeSet<String> {
    let mut out = Graph::new();
    for triple in store.triples(graph).expect("a graph's triples") {
        out.insert(&triple);
    }
    out.canonicalize(CanonicalizationAlgorithm::Unstable);
    out.iter().map(|t| t.to_string()).collect()
}

/// The report of two stores that differ: per graph either holds, what it has that the other lacks, one triple a
/// line. Where every graph agrees alone, what differs is which blank nodes the graphs share.
fn by_graph(left: &Store, expected: &Store) -> String {
    let mut graphs: BTreeSet<String> = left.graph_names().expect("the graphs").into_iter().collect();
    graphs.extend(expected.graph_names().expect("the graphs"));
    let mut out = String::new();
    for graph in &graphs {
        let (l, e) = (triples(left, graph), triples(expected, graph));
        if l == e {
            continue;
        }
        out += &format!("  <{graph}>\n");
        for t in l.difference(&e) {
            out += &format!("    left, unexpected:         {t}\n");
        }
        for t in e.difference(&l) {
            out += &format!("    the diff says, missing:  {t}\n");
        }
    }
    if out.is_empty() {
        out += "  every graph agrees alone: the blank nodes two graphs share differ\n";
    }
    out
}

fn read(path: &Path) -> String {
    fs::read_to_string(path).unwrap_or_else(|e| panic!("{}: {e}", path.display()))
}

fn name(path: &Path) -> String {
    path.file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_diff_applies_by_line_number_and_comments_are_no_lines() {
        let case = "# a header\n@prefix : <urn:> .\nGRAPH :g {\n  :a :b :c .\n}\n";
        let diff =
            "--- case\n+++ expected\n@@ -1,3 +1,4 @@\n @prefix : <urn:> .\n GRAPH :g {\n   :a :b :c .\n+  :a :b :d .\n";
        assert_eq!(
            patched(case, diff),
            "@prefix : <urn:> .\nGRAPH :g {\n  :a :b :c .\n  :a :b :d .\n}\n"
        );
    }

    fn store_of(trig: &str) -> Store {
        let store = Store::new(namespaces()).expect("an empty store");
        store.put_trig(WORLD, trig).expect("the case");
        store
    }

    #[test]
    fn a_report_names_the_graph_that_differs_and_no_other() {
        let left = store_of("@prefix : <urn:> .\nGRAPH :g { :a :b [ :c 1 ] }\nGRAPH :h { :a :b :c }\n");
        let expected = store_of("@prefix : <urn:> .\nGRAPH :g { :a :b [ :c 1 ] }\nGRAPH :h { :a :b :d }\n");
        assert_ne!(dataset(&left), dataset(&expected));
        let report = by_graph(&left, &expected);
        assert!(!report.contains("<urn:g>"), "{report}");
        assert!(report.contains("<urn:h>"), "{report}");
        assert!(
            report.contains("left, unexpected:         <urn:a> <urn:b> <urn:c>"),
            "{report}"
        );
        assert!(
            report.contains("the diff says, missing:  <urn:a> <urn:b> <urn:d>"),
            "{report}"
        );
    }

    #[test]
    fn a_blank_node_two_graphs_share_is_held_to_being_shared() {
        let left = store_of("@prefix : <urn:> .\nGRAPH :g { :a :b _:x }\nGRAPH :h { _:x :c 1 }\n");
        let expected = store_of("@prefix : <urn:> .\nGRAPH :g { :a :b _:x }\nGRAPH :h { _:y :c 1 }\n");
        assert_ne!(dataset(&left), dataset(&expected));
        assert!(by_graph(&left, &expected).contains("the blank nodes two graphs share differ"));
    }

    #[test]
    #[should_panic(expected = "stale diff at line 2")]
    fn a_hunk_that_does_not_land_where_it_says_is_refused() {
        patched("a\nb\n", "@@ -1,2 +1,2 @@\n a\n-c\n+d\n");
    }
}
