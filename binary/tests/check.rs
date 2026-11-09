//! EVERY AGENT OF EVERY WORLD CHECKED, as `orexis-onboard` checks a world before it grants anything: booted in memory
//! from the documents its container is handed, and every part its roles load made over members that reach nothing. A
//! world whose store will not initialise — a document that will not parse, a self stated twice, a role whose package
//! this binary lacks, a text a part refuses at its making — is red here, before any container is built of it.

use std::path::{Path, PathBuf};

use oxigraph::io::{RdfFormat, RdfParser};
use oxigraph::model::Term;
use oxigraph::sparql::{QueryResults, SparqlEvaluator};

use orexis::boot::TREE;
use orexis::clock::instant;
use orexis_agent::check;

const LOCAL_ID: &str = "http://example.org/orexis#localId";
const AGENT: &str = "http://example.org/orexis#Agent";

/// Every world of the tree: each directory of `world/` holding a world graph's document.
fn worlds() -> Vec<PathBuf> {
    let root = Path::new(TREE).join("../world");
    let mut out: Vec<PathBuf> = std::fs::read_dir(&root)
        .unwrap()
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.join("world.ttl").is_file())
        .collect();
    out.sort();
    out
}

/// The ids the world's documents state its agents by, as onboarding's roster reads them (`?a a orexis:Agent ;
/// orexis:localId ?id`), asked of every document beside the world graph and under
/// `beliefs/` — never by a file's name, which is for eyes.
fn agents(world: &Path) -> Vec<String> {
    let store = oxigraph::store::Store::new().unwrap();
    let mut files: Vec<PathBuf> = Vec::new();
    for dir in [world.to_path_buf(), world.join("beliefs")] {
        if let Ok(entries) = std::fs::read_dir(&dir) {
            files.extend(entries.flatten().map(|e| e.path()));
        }
    }
    for file in files {
        if !matches!(file.extension().and_then(|e| e.to_str()), Some("ttl" | "trig")) {
            continue;
        }
        //  TriG reads a Turtle document too, and a relative IRI against the file it is in.
        let base = format!("file://{}", file.canonicalize().unwrap().display());
        let parser = RdfParser::from_format(RdfFormat::TriG).with_base_iri(&base).unwrap();
        store
            .load_from_slice(parser, &std::fs::read(&file).unwrap())
            .unwrap_or_else(|e| panic!("{} will not parse: {e}", file.display()));
    }
    let query =
        format!("SELECT DISTINCT ?id WHERE {{ GRAPH ?g {{ ?a a <{AGENT}> ; <{LOCAL_ID}> ?id }} }} ORDER BY ?id");
    let mut found = Vec::new();
    let default = format!("SELECT DISTINCT ?id WHERE {{ ?a a <{AGENT}> ; <{LOCAL_ID}> ?id }} ORDER BY ?id");
    for text in [query, default] {
        let QueryResults::Solutions(rows) = SparqlEvaluator::new()
            .parse_query(&text)
            .unwrap()
            .on_store(&store)
            .execute()
            .unwrap()
        else {
            unreachable!()
        };
        for row in rows {
            if let Some(Term::Literal(id)) = row.unwrap().get("id") {
                found.push(id.value().to_string());
            }
        }
    }
    found.sort();
    found.dedup();
    found
}

#[test]
fn every_agent_of_every_world_boots_and_makes_its_parts() {
    let now = instant("2026-11-07T12:00:00Z").unwrap();
    let mut checked = 0;
    let mut refused = Vec::new();
    for world in worlds() {
        let ids = agents(&world);
        assert!(
            !ids.is_empty(),
            "{} states no agent — the guard reads nothing of it",
            world.display()
        );
        for agent in ids {
            match check(Path::new(TREE), &world, &agent, now) {
                Ok(loaded) => assert!(!loaded.is_empty(), "{agent} makes no part"),
                Err(e) => refused.push(format!("{}/{agent}: {e}", world.display())),
            }
            checked += 1;
        }
    }
    assert!(refused.is_empty(), "{}", refused.join("\n"));
    assert!(
        checked > 10,
        "only {checked} agents checked — the guard reads almost nothing"
    );
}

#[test]
fn an_agent_the_world_does_not_state_is_refused() {
    let world = Path::new(TREE).join("../world/hanoi");
    let refused = check(
        Path::new(TREE),
        &world,
        "nobody",
        instant("2026-11-07T12:00:00Z").unwrap(),
    )
    .unwrap_err();
    assert!(refused.to_string().contains("nobody"), "{refused}");
}

#[test]
fn an_agent_in_a_chat_by_email_boots_with_its_mailbox() {
    let world = Path::new(TREE).join("translation/tests/world");
    let loaded = check(
        Path::new(TREE),
        &world,
        "seeker",
        instant("2026-11-07T12:00:00Z").unwrap(),
    )
    .unwrap();
    assert!(loaded.iter().any(|p| p == "transport/email"), "{loaded:?}");
}
