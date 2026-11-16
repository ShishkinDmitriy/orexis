//! ONE AGENT'S PROCESS: the world booted into a store, the packages its roles load started — each a feature of this
//! binary, so a package an agent does not run is compiled out — and run until nothing holds it. It links the packages
//! and names none: what a caller provides one (`orexis::task::Provided`) is that package's own type, and
//! what each makes of it, and of what it is not handed, is the package's to say.

use std::path::Path;

use std::sync::Arc;

use orexis::Error;
use orexis::boot::Booting;
use orexis::clock::Clock;
use orexis::store::Store;
use orexis::task::{Provided, Running};

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

/// Boot `agent` of `world` into `store` from the world's documents and those of every package this binary holds, run
/// or not, and start nothing (`orexis::boot::boot`): for a test that calls a package's core itself.
pub fn booted(store: &Store, world: &Path, agent: &str) -> Result<(), Error> {
    orexis::boot::boot(store, &Booting { world, agent })
}

/// BOOT `agent` of `world` into `store`, handed `provided`, and hold it ready to start (`orexis::task::boot`). What a
/// deployed agent and a check do; `booted` is for a caller that starts nothing.
pub fn boot(
    store: &Store,
    world: &Path,
    agent: &str,
    clock: Arc<dyn Clock>,
    provided: Provided,
) -> Result<orexis::task::Booted, Error> {
    orexis::task::boot(store, &Booting { world, agent }, clock, provided)
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
/// where `boot` names a file, the store as booted, in N-Quads, once every part is made and before any runs — which is what onboarding
/// holds to the requirements, so the world is booted once, by the agent that will run it.
/// `orexis-onboard` asks it of every agent before anything is granted, and `orexis-agent/tests/check.rs` of every world.
pub fn check(world: &Path, agent: &str, now: oxsdatatypes::DateTime, boot: Option<&Path>) -> Result<Checked, Error> {
    let namespaces = Arc::new(orexis::namespaces::Namespaces::linked()?);
    let store = Store::new(namespaces)?;
    let checking = orexis::task::Checking::default();
    let clock: Arc<dyn Clock> = Arc::new(orexis::clock::Manual::at(now));
    //  A CHECK HANDS NOTHING BUT THAT IT IS ONE: each package handed no connector and not deployed makes one that
    //  reaches nothing, so no broker, no web, no bot and no model is dialled.
    let booted = self::boot(&store, world, agent, clock, Provided::default().with(checking.clone()))?;
    //  EACH PACKAGE CHECKS ITS OWN: told it is checked, it decides whether it runs, makes its core, says what it found
    //  and that it started, and ends. The runtime is driven until every start has ended or waits.
    let tasks = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
    let loaded = tasks.block_on(async {
        let running = booted.start().await?;
        //  THE BOOT IS FINISHED ONCE EVERY START HAS DECIDED, each package that joins having brought its documents
        //  (`Handed::joins`): the store is written there, with every core made and none run.
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

/// START THE AGENT `agent` over `store`, for a test, on the Tokio runtime this is called in, handed `provided`: every
/// package this binary holds, those `order` names first and in that order, each deciding for itself whether it runs.
pub async fn start(
    store: &Store,
    agent: &str,
    clock: Arc<dyn Clock>,
    order: &[String],
    provided: Provided,
) -> Result<Running, Error> {
    orexis::task::start(store, agent, clock, provided, order).await
}
