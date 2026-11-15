//! ONE AGENT'S PROCESS, as `agent/runtime.py`'s `main` assembles it: the world booted into a store, the parts of the
//! packages its roles load made — each a feature of this binary, so a package an agent does not run is compiled out —
//! and run until nothing holds it. What is each package's at boot is said here, where the packages are known:
//! planning writes the scopes a pass reads.

use std::path::Path;

use std::sync::Arc;

use orexis::Error;
use orexis::boot::Booting;
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
#[cfg(feature = "metrics")]
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

/// Boot `agent` of `world` into `store` from the world's documents and those of every package this binary holds, and
/// start nothing (`orexis::boot::boot`).
pub fn booted(store: &Store, world: &Path, agent: &str, now: oxsdatatypes::DateTime) -> Result<(), Error> {
    let _ = now;
    orexis::boot::boot(store, &Booting { world, agent })
}

/// BOOT `agent` of `world` into `store`, handed what `wiring` says, and hold it ready to start (`orexis::task::boot`).
/// What a deployed agent and a check do; `booted` is for a caller that starts nothing.
pub fn boot(
    store: &Store,
    world: &Path,
    agent: &str,
    clock: Arc<dyn Clock>,
    budget: Option<usize>,
    wiring: Wiring,
) -> Result<orexis::task::Booted, Error> {
    orexis::task::boot(store, &Booting { world, agent }, clock, outside(wiring, budget))
}

/// What a check found of an agent that boots: the packages it loads, and what they said as each made its core
/// (`orexis::task::Checking`) — which hold the agent, so it runs for as long as its process does, and why any
/// refuses the world as posed; `orexis-onboard` refuses such a world.
#[derive(Debug, Default)]
pub struct Checked {
    pub loaded: Vec<String>,
    pub held: Vec<String>,
    pub refused: Vec<String>,
}

/// CHECK `agent` of `world` as its container would boot it, and run nothing: booted into a store in memory from the
/// world's documents and its packages', and every part its roles load made, each package ending its start there as it is checked, over members
/// that reach nothing — no broker, no web, no bot and no model — so every text a part parses at its making is parsed. What it found, or why it would not boot; and,
/// where `boot` names a file, the store as booted, in N-Quads, before any part is made — which is what onboarding
/// holds to the requirements, so the world is booted once, by the agent that will run it.
/// `orexis-onboard` asks it of every agent before anything is granted, and `orexis-agent/tests/check.rs` of every world.
pub fn check(world: &Path, agent: &str, now: oxsdatatypes::DateTime, boot: Option<&Path>) -> Result<Checked, Error> {
    let namespaces = Arc::new(orexis::namespaces::Namespaces::linked()?);
    let store = Store::new(namespaces)?;
    let checking = orexis::task::Checking::default();
    let clock: Arc<dyn Clock> = Arc::new(orexis::clock::Manual::at(now));
    //  A CHECK HANDS NOTHING BUT THAT IT IS ONE: each package handed no connector and not deployed makes one that
    //  reaches nothing, so no broker, no web, no bot and no model is dialled.
    let wiring = Wiring {
        checking: Some(checking.clone()),
        ..Wiring::default()
    };
    let booted = self::boot(&store, world, agent, clock, None, wiring)?;
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
    //  EACH PACKAGE CHECKS ITS OWN: told it is checked, it decides whether it runs, makes its core, says what it found
    //  and that it started, and ends. The runtime is driven until every start has ended or waits.
    let tasks = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
    let loaded = tasks.block_on(async {
        let running = booted.start().await?;
        running.settled().await?;
        tokio::task::yield_now().await;
        //  A PACKAGE THAT WENT ON TO ITS TASK did not check its own, and would run as it is checked.
        let going_on = running.going_on();
        if !going_on.is_empty() {
            return Err(Error::Evaluation(format!(
                "{} went on to run as it was checked: a package being checked ends its start once its core is made",
                going_on.join(", ")
            )));
        }
        let loaded = running.parts();
        running.stop().await;
        Ok::<_, Error>(loaded)
    })?;
    //  WHAT EACH PACKAGE SAID AS IT MADE ITS CORE: the binary asks none of them by name.
    let found = checking.found();
    let checked = Checked {
        loaded,
        held: found.held,
        refused: found.refused,
    };
    Ok(checked)
}

/// Whether this binary holds `package`: its crate was built in, and registered itself.
pub fn built(package: &str) -> bool {
    inventory::iter::<orexis::task::Package>().any(|p| p.name == package)
}

/// WHAT WATCHES THE AGENT, where the deployment keeps any of it: the journal, the series store its readings are
/// archived to, the metrics window and the tracer. Each is used by the package it is for, where the agent loads it:
/// the journal and the tracer where it plays a recorder, the metrics part where a metrics window is.
#[derive(Default)]
pub struct Watching {
    /// The journal a recorder keeps, handed by a test that reads it: none, and a deployed agent's package makes its
    /// own, and any other keeps none.
    #[cfg(feature = "journal")]
    pub journal: Option<Arc<orexis_journal::Journal>>,
    /// The archive what the journal keeps for good is taken to, and how often, in the agent's seconds, handed by a
    /// test that reads it: none, and a deployed agent's package opens its own where its role names one.
    #[cfg(feature = "journal")]
    pub archive: Option<(Arc<orexis_journal_oxigraph::Archive>, f64)>,
    /// The series store sensing's readings are archived to, and a chat reads the past from, handed by a test that
    /// reads it: none, and a deployed agent's packages make their own where the world names one.
    pub history: Option<Sink>,
    /// How often the readings are archived there, in the agent's seconds: none, and the archiver's own stretch.
    pub archive_every_s: Option<f64>,
    /// The window a meter's tallies are written in, handed by a test that reads the points: none, and a deployed
    /// agent's package makes its own where its role names a store.
    #[cfg(feature = "metrics")]
    pub metrics: Option<orexis_metrics::Window>,
}

/// What the agent's bus is, where a test hands one: the MQTT member over a client of its own, the HTTP member over a
/// web of its own, the Telegram member over a Bot API of its own, the email member over a mailbox of its own, translation's model. None, and a member the agent
/// loads is brought up from the environment where the agent is deployed, and reaches nothing where it is not. And what watches it.
#[derive(Default)]
pub struct Wiring {
    pub watching: Watching,
    /// THE AGENT IS DEPLOYED, the binary's run alone, in the world of this name: a package makes for itself what it
    /// is not handed here (`orexis::task::Deployed`). A check and a test leave it unsaid.
    pub deployed: Option<String>,
    /// The process's log, for the package that keeps it (`orexis::task::Said`).
    pub said: Option<orexis::task::Said>,
    /// THE AGENT IS BEING CHECKED, a check alone: what each package says of it as it makes its core
    /// (`orexis::task::Checking`).
    pub checking: Option<orexis::task::Checking>,
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
/// itself: from the environment where the agent is deployed, and reaching nothing where it is not.
pub fn outside(wiring: Wiring, budget: Option<usize>) -> Outside {
    let outside = Outside::default();
    let Wiring {
        watching,
        deployed,
        said,
        checking,
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
    if let Some(world) = deployed {
        outside.hand(orexis::task::Deployed { world });
    }
    if let Some(said) = said {
        outside.hand(said);
    }
    if let Some(checking) = checking {
        outside.hand(checking);
    }
    //  WHAT A CHAT READS OF WHAT HAPPENED: the two series as read, and the journal once what keeps it has started
    //  and said where it lies.
    outside.hand(Reads {
        journal: orexis::task::Journaled::default(),
        history: watching.history.as_ref().map(Sink::reader),
        #[cfg(feature = "metrics")]
        metrics: watching.metrics.as_ref().map(|w| w.sink.reader()),
        #[cfg(not(feature = "metrics"))]
        metrics: None,
    });
    //  AND WHAT IT KEEPS FOR GOOD, taken to the archive a test hands.
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
        outside.hand(orexis_planning::Budget(budget));
    }
    //  AND SENSING'S READINGS, archived where the deployment keeps a series store and left in the beliefs otherwise.
    #[cfg(feature = "sensing")]
    if let Some(sink) = watching.history {
        outside.hand(orexis_sensing_influxdb::Archives {
            sink: Arc::new(sink),
            every_s: match watching.archive_every_s {
                Some(every_s) => every_s,
                None => orexis_sensing_influxdb::archived_every_s().expect("sensing's ontology states how often"),
            },
        });
    }
    //  AND THE JOURNAL ITSELF, where a test hands one: every event as it is said, every activity as it ends.
    #[cfg(feature = "journal")]
    outside.hand(orexis_journal::Keeps {
        journal: watching.journal,
    });
    #[cfg(feature = "metrics")]
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

/// START THE AGENT `agent` over `store`, for a test, on the Tokio runtime this is called in: every package this binary
/// holds, those `order` names first and in that order, each deciding for itself whether it runs.
pub async fn start(
    store: &Store,
    agent: &str,
    clock: Arc<dyn Clock>,
    order: &[String],
    budget: Option<usize>,
    wiring: Wiring,
) -> Result<Running, Error> {
    orexis::task::start(store, agent, clock, outside(wiring, budget), order).await
}
