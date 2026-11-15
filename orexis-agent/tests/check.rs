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
                        checked.refused.is_empty(),
                        "{}/{agent} is posed in a state its constraints say is impossible: {:?}",
                        world.display(),
                        checked.refused
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
    assert!(hanoi.held.is_empty(), "the mover holds wants alone, and finishes");
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
        agents(&world).iter().any(|a| check(&world, a, now, None)
            .unwrap()
            .held
            .iter()
            .any(|p| p == "planning")),
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
    //  AND ITS MAILBOX HOLDS IT, said by the transport itself, which made a mailbox that reaches nothing.
    let held = check(&world, "seeker", instant("2026-11-07T12:00:00Z").unwrap(), None)
        .unwrap()
        .held;
    assert!(held.iter().any(|p| p == "transport/email"), "{held:?}");
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
        let recorder = orexis_journal::Recorder::new(&store).unwrap();
        (
            recorder.traced_by,
            recorder.archived_in,
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

/// A DEPLOYED AGENT'S JOURNAL PACKAGE MAKES ITS OWN JOURNAL, and one that is not deployed and handed none keeps
/// none: Hanoi's agent, started deployed, hands its journal on to its housekeepers with the packages' starts
/// already in it, and started as a check starts it, hands nothing on.
#[test]
fn the_journal_package_makes_its_own_journal_where_the_agent_is_deployed_and_none_where_it_is_not() {
    let now = oxsdatatypes::DateTime::now();
    let kept = |deployed: bool| {
        let store =
            orexis::store::Store::new(std::sync::Arc::new(orexis::namespaces::Namespaces::linked().unwrap())).unwrap();
        let tasks = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        let _entered = tasks.enter();
        let clock: std::sync::Arc<dyn orexis::clock::Clock> = std::sync::Arc::new(orexis::clock::Manual::at(now));
        let wiring = orexis_agent::Wiring {
            deployed: deployed.then(|| "hanoi".to_string()),
            ..orexis_agent::Wiring::default()
        };
        //  BOOTED AND STARTED AS THE BINARY DOES: each start run once, from its decision on.
        let world = Path::new(TREE).join("world/hanoi");
        let running = orexis_agent::boot(&store, &world, "hanoi", clock, None, wiring)
            .unwrap()
            .start()
            .unwrap();
        running
            .handed
            .outside
            .take::<orexis_journal::Traced>()
            .map(|traced| traced.0.store.named_graphs().count())
    };
    assert!(
        kept(true).is_some_and(|entries| entries > 0),
        "deployed, it keeps what the packages said as they started"
    );
    assert_eq!(kept(false), None, "a check keeps no journal");
}

/// A PACKAGE READS ITS OWN ROLE, into a struct with a field for each thing the role may say: the terrace's agent
/// plays a recorder, an observer, a meter and a translator, each linked to its services and stating no figure, so
/// each reads with its links and the defaults its package's ontology states; a figure said on a role is what is read; and Hanoi's
/// agent, which plays a recorder alone, holds no ontology of the metrics or of sensing, so neither is read.
#[test]
fn a_package_reads_its_own_role_into_a_struct_with_a_field_for_each_thing_the_role_may_say() {
    let now = oxsdatatypes::DateTime::now();
    let booted = |world: &str, agent: &str| {
        let store =
            orexis::store::Store::new(std::sync::Arc::new(orexis::namespaces::Namespaces::linked().unwrap())).unwrap();
        orexis_agent::booted(&store, &Path::new(TREE).join("world").join(world), agent, now).unwrap();
        store
    };
    let store = booted("terrace", "terrace");
    let series = Some("http://localhost:8086".to_string());
    let recorder = orexis_journal::Recorder {
        window_s: 600.0,
        incident_from: log::Level::Warn,
        incidents: Default::default(),
        served_at: Some(7889),
        archived_in: Some(std::path::PathBuf::from("/app/journal")),
        archived_every_s: 2.0,
        traced_by: Some("http://localhost:4318".to_string()),
        traced_every_s: 10.0,
    };
    assert_eq!(orexis_journal::Recorder::new(&store).unwrap(), recorder);
    let observer = orexis_sensing_influxdb::Observer {
        archived_in: series.clone(),
        archived_every_s: 10.0,
    };
    assert_eq!(orexis_sensing_influxdb::Observer::new(&store).unwrap(), observer);
    let meter = orexis_metrics::Meter {
        written_to: series,
        window_s: 60.0,
    };
    assert_eq!(orexis_metrics::Meter::new(&store).unwrap(), meter);
    //  AND THE ROLES THAT STATE FIGURES ALONE read the same way, each its struct.
    assert_eq!(
        orexis_prediction::Predictor::new(&store).unwrap(),
        orexis_prediction::Predictor {
            horizon_s: 86400.0,
            rate_held_s: 3600.0
        }
    );
    assert_eq!(
        orexis_coordination::Coordinator::new(&store).unwrap(),
        orexis_coordination::Coordinator {
            patience_s: 60.0,
            rounds: 3.0,
            lookahead: 2
        }
    );
    let sensed = orexis_sensing::Observer::new(&store).unwrap();
    assert!(!sensed.sensors.is_empty() && sensed.asked_every_s == 60.0);
    let translator = orexis_translation::Translator::new(&store, "", None);
    assert_eq!(
        (translator.turns, translator.rows, translator.retries),
        (8, 50, 3),
        "the translator holds what its role says of talking with the model"
    );
    assert_eq!((translator.answered_within_s, translator.called_within_s), (60.0, 60.0));
    assert_eq!(
        orexis_translation::Translator::new(&store, "", None).translated_by,
        Some("https://api.anthropic.com".to_string())
    );
    assert_eq!(orexis_transport_telegram::driver::polled_every_s(&store).unwrap(), 3.0);
    //  SAID ON THE ROLE, each figure is what is read, and nothing else of the struct changes.
    for (link, figure, said) in [
        ("sensing#archivedIn", "sensing#archivedEveryS", 30),
        ("journal#archivedIn", "journal#archivedEveryS", 5),
        ("journal#tracedBy", "journal#tracedEveryS", 20),
        ("journal#servedAt", "journal#windowS", 90),
        ("metrics#writtenTo", "metrics#windowS", 300),
        ("translation#translatedBy", "telegram#polledEveryS", 7),
    ] {
        store
            .update(&format!(
                "INSERT {{ GRAPH ?g {{ ?role <http://example.org/orexis/{figure}> {said} }} }} WHERE {{ GRAPH ?g {{ \
                 ?me a <http://example.org/orexis#Self> ; <http://example.org/orexis#plays> ?role . \
                 ?role <http://example.org/orexis/{link}> ?service }} }}"
            ))
            .unwrap();
    }
    assert_eq!(
        orexis_journal::Recorder::new(&store).unwrap(),
        orexis_journal::Recorder {
            window_s: 90.0,
            archived_every_s: 5.0,
            traced_every_s: 20.0,
            ..recorder
        }
    );
    assert_eq!(
        orexis_sensing_influxdb::Observer::new(&store).unwrap(),
        orexis_sensing_influxdb::Observer {
            archived_every_s: 30.0,
            ..observer
        }
    );
    assert_eq!(
        orexis_metrics::Meter::new(&store).unwrap(),
        orexis_metrics::Meter {
            window_s: 300.0,
            ..meter
        }
    );
    assert_eq!(orexis_transport_telegram::driver::polled_every_s(&store).unwrap(), 7.0);
    //  AN AGENT PLAYS ONE OF EACH: a second role of the class is a second answer to what its package is told once,
    //  and is refused, never merged or picked between; the same figure said by two roles is one answer.
    for (class, figure) in [
        ("sensing#Observer", "sensing#askedEveryS"),
        ("journal#Recorder", "journal#windowS"),
        ("metrics#Meter", "metrics#windowS"),
    ] {
        store
            .update(&format!(
                "INSERT {{ GRAPH ?g {{ ?me <http://example.org/orexis#plays> [ a <http://example.org/orexis/{class}> ; \
                 <http://example.org/orexis/{figure}> 1 ] }} }} WHERE {{ GRAPH ?g {{ ?me a <http://example.org/orexis#Self> }} }}"
            ))
            .unwrap();
    }
    for refused in [
        orexis_sensing::Observer::new(&store).map(|_| ()),
        orexis_sensing_influxdb::Observer::new(&store).map(|_| ()),
        orexis_journal::Recorder::new(&store).map(|_| ()),
        orexis_metrics::Meter::new(&store).map(|_| ()),
    ] {
        assert!(format!("{refused:?}").contains("and an agent plays one"), "{refused:?}");
    }
    //  AND A ROLE THE SELF DOES NOT PLAY SAYS NOTHING.
    let store = booted("hanoi", "hanoi");
    assert!(orexis_journal::Recorder::new(&store).unwrap().archived_in.is_some());
    //  A PACKAGE THAT DID NOT JOIN BROUGHT NO ONTOLOGY, so its role's figures have no default and it is refused.
    assert!(orexis_sensing_influxdb::Observer::new(&store).is_err());
    assert!(orexis_metrics::Meter::new(&store).is_err());
    assert_eq!(
        orexis_translation::Translator::new(&store, "", None).translated_by,
        None
    );
}

/// WHERE A BROKER, A BOT AND A MODEL ANSWER IS THE WORLD'S TO SAY, and no environment's: the terrace's agent is
/// connected to its broker by the society and reads where that answers off the derived deployment, as it reads
/// where the bot it speaks through and the model its translator's role names answer; Hanoi's is connected to none.
#[test]
fn the_world_says_where_each_broker_bot_and_model_an_agent_reaches_answers() {
    let now = oxsdatatypes::DateTime::now();
    let booted = |world: &str, agent: &str| {
        let store =
            orexis::store::Store::new(std::sync::Arc::new(orexis::namespaces::Namespaces::linked().unwrap())).unwrap();
        orexis_agent::booted(&store, &Path::new(TREE).join("world").join(world), agent, now).unwrap();
        let me = orexis::boot::selves(&store).unwrap().remove(0);
        (store, me)
    };
    let (store, me) = booted("terrace", "terrace");
    assert_eq!(
        orexis_transport_mqtt::driver::reached(&store, &me).unwrap(),
        [(
            "http://example.org/orexis/world/terrace#broker".to_string(),
            "mqtts://localhost:8888".to_string()
        )]
    );
    assert_eq!(
        orexis_transport_telegram::driver::answers(&store, &me).unwrap(),
        Some("https://api.telegram.org".to_string())
    );
    assert_eq!(
        orexis_translation::Translator::new(&store, "", None).translated_by,
        Some("https://api.anthropic.com".to_string())
    );
    let (store, me) = booted("hanoi", "hanoi");
    assert!(orexis_transport_mqtt::driver::reached(&store, &me).unwrap().is_empty());
    assert_eq!(
        orexis_translation::Translator::new(&store, "", None).translated_by,
        None
    );
}

/// WHERE A SERIES IS WRITTEN IS THE WORLD'S TO SAY, of each store a role names: the terrace's agent plays an observer
/// whose readings are archived in one and a meter whose windows are written to it, so the deployment states the store
/// for history and for metrics; Hanoi's agent plays neither, so it states none, and neither
/// what archives readings nor the metrics joins it.
#[test]
fn the_world_names_the_series_store_for_each_purpose_its_agents_write() {
    let now = oxsdatatypes::DateTime::now();
    let served = |world: &str, agent: &str, purpose: &str| {
        let store =
            orexis::store::Store::new(std::sync::Arc::new(orexis::namespaces::Namespaces::linked().unwrap())).unwrap();
        orexis_agent::booted(&store, &Path::new(TREE).join("world").join(world), agent, now).unwrap();
        orexis::series::store(&store, purpose).unwrap()
    };
    let at = Some(orexis::series::Served {
        url: "http://localhost:8086".to_string(),
        organisation: "orexis".to_string(),
    });
    assert_eq!(served("terrace", "terrace", orexis::series::HISTORY), at);
    assert_eq!(served("terrace", "terrace", orexis::series::METRICS), at);
    assert_eq!(served("hanoi", "hanoi", orexis::series::HISTORY), None);
    assert_eq!(served("hanoi", "hanoi", orexis::series::METRICS), None);

    //  AND A SINK IS MADE WHERE THE WORLD NAMES THE STORE AND THE AGENT'S OWN CREDENTIAL OPENS IT: each purpose by its
    //  own bucket, none where the credential is missing or named in part, and none where the world names no store,
    //  whatever the credential says.
    let sink = |world: &str, agent: &str, purpose: &'static str, told: &[(&str, &str)]| {
        let store =
            orexis::store::Store::new(std::sync::Arc::new(orexis::namespaces::Namespaces::linked().unwrap())).unwrap();
        orexis_agent::booted(&store, &Path::new(TREE).join("world").join(world), agent, now).unwrap();
        let env = |key: &str| told.iter().find(|(k, _)| *k == key).map(|(_, v)| v.to_string());
        orexis::series::Sink::deployed(&store, purpose, &env)
            .unwrap()
            .map(|(sink, _)| sink.bucket)
    };
    let both = [
        ("INFLUX_HISTORY_BUCKET", "terrace-terrace"),
        ("INFLUX_HISTORY_TOKEN", "t"),
        ("INFLUX_METRICS_BUCKET", "terrace-terrace-metrics"),
        ("INFLUX_METRICS_TOKEN", "t"),
    ];
    assert_eq!(
        sink("terrace", "terrace", orexis::series::HISTORY, &both).as_deref(),
        Some("terrace-terrace")
    );
    assert_eq!(
        sink("terrace", "terrace", orexis::series::METRICS, &both).as_deref(),
        Some("terrace-terrace-metrics")
    );
    assert_eq!(sink("terrace", "terrace", orexis::series::HISTORY, &[]), None);
    assert_eq!(sink("terrace", "terrace", orexis::series::HISTORY, &both[..1]), None);
    assert_eq!(sink("hanoi", "hanoi", orexis::series::METRICS, &both), None);
}
