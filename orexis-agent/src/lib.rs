//! ONE AGENT'S PROCESS, as `agent/runtime.py`'s `main` assembles it: the world booted into a store, the parts of the
//! packages its roles load made — each a feature of this binary, so a package an agent does not run is compiled out —
//! and run until nothing holds it. What is each package's at boot is said here, where the packages are known:
//! planning writes the scopes a pass reads.

use std::path::Path;

use std::sync::Arc;

use orexis::Error;
use orexis::boot::{Booting, boot};
use orexis::clock::Clock;
use orexis::series::Sink;
use orexis::store::Store;
use orexis::task::{Outside, Reads, Running};

//  EACH PACKAGE THIS BINARY IS BUILT WITH, LINKED: a crate nothing references is left out, and a package registers
//  itself only where its crate is in. Nothing else here names one.
#[cfg(feature = "belief")]
use orexis_belief as _;
#[cfg(feature = "coordination")]
use orexis_coordination as _;
#[cfg(feature = "execution")]
use orexis_execution as _;
#[cfg(feature = "journal")]
use orexis_journal as _;
#[cfg(feature = "journal")]
use orexis_journal_otlp as _;
#[cfg(feature = "journal")]
use orexis_journal_oxigraph as _;
use orexis_metrics as _;
#[cfg(feature = "planning")]
use orexis_planning as _;
#[cfg(feature = "prediction")]
use orexis_prediction as _;
#[cfg(feature = "sensing")]
use orexis_sensing as _;
#[cfg(feature = "sensing")]
use orexis_sensing_influxdb as _;
#[cfg(feature = "speech")]
use orexis_speech as _;
#[cfg(feature = "translation")]
use orexis_translation as _;
#[cfg(feature = "email")]
use orexis_transport_email as _;
#[cfg(feature = "http")]
use orexis_transport_http as _;
#[cfg(feature = "mqtt")]
use orexis_transport_mqtt as _;
#[cfg(feature = "telegram")]
use orexis_transport_telegram as _;

/// Boot `agent` of `world` into `store` from the world's documents and those its packages bring: the packages that
/// joined it, each deciding in its own start, in the order they start (`orexis::boot::boot`).
pub fn booted(store: &Store, world: &Path, agent: &str, now: oxsdatatypes::DateTime) -> Result<Vec<String>, Error> {
    let loaded = boot(store, &Booting { world, agent })?;
    #[cfg(feature = "planning")]
    if loaded.iter().any(|p| p == "planning") {
        orexis_planning::Planner::scope(store, now)?;
    }
    let _ = now;
    Ok(loaded)
}

/// One row of a violated constraint: the instance, the constraint and what it offended by, as the planner says them.
pub type Broken = (String, Option<String>, Option<String>, Option<String>);

/// What a check found of an agent that boots: the packages it loads, whether it holds a desire, and every constraint
/// it holds that its world as posed violates, with the rows — `orexis-onboard` refuses such a world, since no agent
/// repairs what its own word says is impossible (constraint.md).
#[derive(Debug, Default)]
pub struct Checked {
    pub loaded: Vec<String>,
    pub desire: bool,
    pub contradictions: Vec<(String, Vec<Broken>)>,
}

/// CHECK `agent` of `world` as its container would boot it, and run nothing: booted into a store in memory from the
/// world's documents and its packages', and every part its roles load made and started, on a runtime that is never run, over members
/// that reach nothing — no broker, no web, no bot and no model — so every text a part parses at its making is parsed. What it found, or why it would not boot; and,
/// where `boot` names a file, the store as booted, in N-Quads, before any part is made — which is what onboarding
/// holds to the requirements, so the world is booted once, by the agent that will run it.
/// `orexis-onboard` asks it of every agent before anything is granted, and `orexis-agent/tests/check.rs` of every world.
pub fn check(world: &Path, agent: &str, now: oxsdatatypes::DateTime, boot: Option<&Path>) -> Result<Checked, Error> {
    let namespaces = Arc::new(orexis::namespaces::Namespaces::linked()?);
    let store = Store::new(namespaces)?;
    let loaded = booted(&store, world, agent, now)?;
    if let Some(path) = boot {
        let file = std::io::BufWriter::new(std::fs::File::create(path)?);
        store
            .engine()
            .dump_to_writer(
                oxigraph::io::RdfSerializer::from_format(oxigraph::io::RdfFormat::NQuads),
                file,
            )
            .map_err(|e| Error::Evaluation(format!("the boot will not dump: {e}")))?;
    }
    let mut checked = Checked {
        loaded,
        ..Checked::default()
    };
    #[cfg(feature = "planning")]
    if checked.loaded.iter().any(|p| p == "planning") {
        let planner = orexis_planning::Planner::new(&store, agent, None)?;
        checked.desire = planner.holds_a_desire()?;
        checked.contradictions = planner
            .contradictions(now)?
            .into_iter()
            .map(|(c, rows)| (c, rows.into_iter().collect()))
            .collect();
    }
    let clock: Arc<dyn Clock> = Arc::new(orexis::clock::Manual::at(now));
    #[allow(unused_variables)]
    let me = orexis::boot::selves(&store)?.into_iter().next().unwrap_or_default();
    let wiring = Wiring {
        #[cfg(feature = "mqtt")]
        mqtt: Some(orexis_transport_mqtt::driver::Mqtt::new(&store, &me, Vec::new())),
        #[cfg(feature = "http")]
        http: Some(orexis_transport_http::driver::Http::new(
            &store,
            &me,
            Arc::new(|_: &str| Err("a check reaches no web".to_string())),
        )),
        #[cfg(feature = "telegram")]
        telegram: Some(orexis_transport_telegram::driver::Telegram::new(&store, &me, "", "", {
            let call: orexis_transport_telegram::driver::Call =
                Arc::new(|_, _| Err("a check reaches no bot".to_string()));
            call
        })),
        #[cfg(feature = "email")]
        email: Some(orexis_transport_email::driver::Email::new(
            &store,
            &me,
            Arc::new(Unreachable),
        )),
        ..Wiring::default()
    };
    //  STARTED AND NEVER RUN: on a runtime nothing drives, each package makes its core and its task is dropped.
    let tasks = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
    let _entered = tasks.enter();
    start(&store, agent, clock, &checked.loaded, None, wiring)?;
    Ok(checked)
}

/// The mailbox a check reaches: none.
#[cfg(feature = "email")]
struct Unreachable;

#[cfg(feature = "email")]
impl orexis_transport_email::driver::Mailbox for Unreachable {
    fn fetch(&self) -> Result<Vec<(String, String)>, String> {
        Err("a check reaches no mailbox".into())
    }
    fn send(&self, _: &str, _: &str) -> Result<(), String> {
        Err("a check reaches no mailbox".into())
    }
}

/// Whether this binary holds `package`: its crate was built in, and registered itself.
pub fn built(package: &str) -> bool {
    inventory::iter::<orexis::task::Package>().any(|p| p.name == package)
}

/// The package an agent that plays a recorder loads: what keeps its journal.
pub const JOURNAL: &str = "journal";
/// The package that joins where the recorder's role names an archive: what takes the journal's lasting entries there.
pub const ARCHIVE: &str = "journal-oxigraph";

/// WHAT WATCHES THE AGENT, where the deployment keeps any of it: the journal, the series store its readings are
/// archived to, the metrics window and the tracer. Each is used by the package it is for, where the agent loads it:
/// the journal and the tracer where it plays a recorder, the metrics part where a metrics window is.
#[derive(Default)]
pub struct Watching {
    /// The journal a recorder keeps: handed by whoever runs the agent, and kept by nobody where it plays none.
    #[cfg(feature = "journal")]
    pub journal: Option<Arc<orexis_journal::Journal>>,
    /// The archive what the journal keeps for good is taken to, and how often, in the agent's seconds: none, and it
    /// stays in the journal.
    #[cfg(feature = "journal")]
    pub archive: Option<(Arc<orexis_journal_oxigraph::Archive>, f64)>,
    /// The series store sensing's readings are archived to, and a chat reads the past from: none, and every reading
    /// stays in the agent's beliefs.
    pub history: Option<Sink>,
    /// How often the readings are archived there, in the agent's seconds: none, and the archiver's own stretch.
    pub archive_every_s: Option<f64>,
    pub metrics: Option<orexis_metrics::Window>,
}

/// What the agent's bus is, where a test hands one: the MQTT member over a client of its own, the HTTP member over a
/// web of its own, the Telegram member over a Bot API of its own, the email member over a mailbox of its own, translation's model. None, and a member the agent
/// loads is brought up from the environment. And what watches it.
#[derive(Default)]
pub struct Wiring {
    pub watching: Watching,
    #[cfg(feature = "http")]
    pub http: Option<orexis_transport_http::driver::Http>,
    #[cfg(feature = "telegram")]
    pub telegram: Option<orexis_transport_telegram::driver::Telegram>,
    #[cfg(feature = "email")]
    pub email: Option<orexis_transport_email::driver::Email>,
    #[cfg(feature = "translation")]
    pub model: Option<Arc<dyn orexis_translation::model::Model>>,
    #[cfg(feature = "mqtt")]
    pub mqtt: Option<orexis_transport_mqtt::driver::Mqtt>,
    #[cfg(not(feature = "mqtt"))]
    pub mqtt: Option<()>,
}

/// WHAT REACHES OUTSIDE, handed to the packages that take it: each connector `wiring` brings, what watches the agent,
/// and `budget`, which sizes planning's search where a caller states one. What it leaves out a package makes for
/// itself from the environment.
pub fn outside(wiring: Wiring, budget: Option<usize>) -> Outside {
    let outside = Outside::default();
    let Wiring {
        watching,
        mqtt,
        #[cfg(feature = "http")]
        http,
        #[cfg(feature = "telegram")]
        telegram,
        #[cfg(feature = "email")]
        email,
        #[cfg(feature = "translation")]
        model,
    } = wiring;
    //  WHAT A CHAT READS OF WHAT HAPPENED, where it reads it: the journal's archive where the agent keeps one and the
    //  journal itself where it keeps none, and the series as read.
    #[cfg(feature = "journal")]
    let journal = match (&watching.archive, &watching.journal) {
        (Some((archive, _)), Some(_)) => Some(archive.store.clone()),
        (_, journal) => journal.as_ref().map(|j| j.store.clone()),
    };
    #[cfg(not(feature = "journal"))]
    let journal = None;
    outside.hand(Reads {
        journal,
        history: watching.history.as_ref().map(Sink::reader),
        metrics: watching.metrics.as_ref().map(|w| w.sink.reader()),
    });
    //  AND WHAT IT KEEPS FOR GOOD, taken to its archive where the deployment keeps one.
    #[cfg(feature = "journal")]
    if let (Some((archive, every_s)), Some(journal)) = (watching.archive, &watching.journal) {
        outside.hand(orexis_journal_oxigraph::Archives {
            journal: journal.clone(),
            archive,
            every_s,
        });
    }
    #[cfg(feature = "planning")]
    if let Some(budget) = budget {
        outside.hand(orexis_planning::create::Budget(budget));
    }
    //  AND SENSING'S READINGS, archived where the deployment keeps a series store and left in the beliefs otherwise.
    #[cfg(feature = "sensing")]
    if let Some(sink) = watching.history {
        outside.hand(orexis_sensing_influxdb::Archives {
            sink: Arc::new(sink),
            every_s: watching.archive_every_s.unwrap_or(orexis_sensing_influxdb::INTERVAL_S),
        });
    }
    //  AND THE JOURNAL ITSELF, kept where the deployment keeps one: every event as it is said, every activity as it ends.
    #[cfg(feature = "journal")]
    outside.hand(orexis_journal::Keeps {
        journal: watching.journal,
    });
    if let Some(window) = watching.metrics {
        outside.hand(window);
    }
    #[cfg(feature = "mqtt")]
    if let Some(member) = mqtt {
        outside.hand(member);
    }
    #[cfg(feature = "http")]
    if let Some(member) = http {
        outside.hand(member);
    }
    #[cfg(feature = "telegram")]
    if let Some(member) = telegram {
        outside.hand(member);
    }
    #[cfg(feature = "email")]
    if let Some(member) = email {
        outside.hand(member);
    }
    #[cfg(feature = "translation")]
    if let Some(model) = model {
        outside.hand(model);
    }
    #[cfg(not(feature = "mqtt"))]
    let _ = mqtt;
    let _ = budget;
    outside
}

/// START THE AGENT `agent` over `store`, on the Tokio runtime this is called in: what watches it first, so it hears
/// what a package says as it starts, then each package `loaded` names, in that order. Every one registered itself;
/// this names none.
pub fn start(
    store: &Store,
    agent: &str,
    clock: Arc<dyn Clock>,
    loaded: &[String],
    budget: Option<usize>,
    wiring: Wiring,
) -> Result<Running, Error> {
    //  THE PACKAGES THAT JOINED, in the order they start: what keeps the journal and what watches first, so what the
    //  others say as they start is heard (`orexis::boot::PASS`).
    orexis::task::start(store, agent, clock, outside(wiring, budget), loaded)
}
