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
    let root = Path::new(TREE).join("world");
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
            match check(&world, &agent, now, None) {
                Ok(checked) => {
                    assert!(!checked.loaded.is_empty(), "{agent} makes no part");
                    assert!(
                        checked.contradictions.is_empty(),
                        "{}/{agent} is posed in a state its constraints say is impossible: {:?}",
                        world.display(),
                        checked.contradictions
                    );
                }
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
    let world = Path::new(TREE).join("world/hanoi");
    let refused = check(&world, "nobody", instant("2026-11-07T12:00:00Z").unwrap(), None).unwrap_err();
    assert!(refused.to_string().contains("nobody"), "{refused}");
}

#[test]
fn the_boot_is_written_as_the_agent_believes_it_and_a_desire_is_told_from_wants_alone() {
    let now = instant("2026-11-07T12:00:00Z").unwrap();
    let dir = std::env::temp_dir().join(format!("orexis-check-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let file = dir.join("hanoi.nq");
    let hanoi = check(&Path::new(TREE).join("world/hanoi"), "hanoi", now, Some(&file)).unwrap();
    assert!(!hanoi.desire, "the mover holds wants alone, and finishes");
    let store = oxigraph::store::Store::new().unwrap();
    store
        .load_from_slice(
            RdfParser::from_format(RdfFormat::NQuads),
            &std::fs::read(&file).unwrap(),
        )
        .unwrap();
    let QueryResults::Boolean(catalogued) = SparqlEvaluator::new()
        .parse_query("ASK { GRAPH ?c { ?c a <http://example.org/orexis#CatalogueGraph> } }")
        .unwrap()
        .on_store(&store)
        .execute()
        .unwrap()
    else {
        unreachable!()
    };
    assert!(catalogued, "the boot written holds no catalogue");
    std::fs::remove_dir_all(&dir).unwrap();
    let world = Path::new(TREE).join("world/greenhouse");
    assert!(
        agents(&world)
            .iter()
            .any(|a| check(&world, a, now, None).unwrap().desire),
        "no agent of the greenhouse holds a desire"
    );
}

#[test]
fn an_agent_in_a_chat_by_email_boots_with_its_mailbox() {
    let world = Path::new(TREE).join("orexis-translation/tests/world");
    let loaded = check(&world, "seeker", instant("2026-11-07T12:00:00Z").unwrap(), None)
        .unwrap()
        .loaded;
    assert!(loaded.iter().any(|p| p == "transport/email"), "{loaded:?}");
}

/// A RECORDER'S ROLE NAMES WHAT IT IS LINKED TO, the world says where that answers, and each housekeeper asks as it
/// starts: the greenhouse's grower is traced by a tracer and archived in an archive, so what ships the activities
/// and what archives the journal both join it; Hanoi's role names an archive and no tracer, so the shipper's start
/// ends there, though its agent keeps a journal too.
#[test]
fn a_housekeeper_of_the_journal_joins_where_the_recorders_role_names_its_service_and_ends_its_start_where_it_names_none()
 {
    let now = oxsdatatypes::DateTime::now();
    let linked = |world: &str, agent: &str| {
        let store =
            orexis::store::Store::new(std::sync::Arc::new(orexis::namespaces::Namespaces::linked().unwrap())).unwrap();
        let loaded = orexis_agent::booted(&store, &Path::new(TREE).join("world").join(world), agent, now).unwrap();
        let joined = |package: &str| loaded.iter().any(|p| p == package);
        (
            orexis_journal_otlp::tracer(&store).unwrap(),
            orexis_journal_oxigraph::archive(&store).unwrap(),
            [joined("journal"), joined("journal-otlp"), joined("journal-oxigraph")],
        )
    };
    let archive = Some(std::path::PathBuf::from("/app/journal"));
    assert_eq!(
        linked("greenhouse", "grower"),
        (
            Some("http://localhost:4318".to_string()),
            archive.clone(),
            [true, true, true]
        )
    );
    assert_eq!(linked("hanoi", "hanoi"), (None, archive, [true, false, true]));
}
