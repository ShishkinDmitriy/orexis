//! `orexis-agent <world> <agent> [--volume PATH] [--journal PATH] [--check [--boot PATH]]`: one agent, booted from a
//! world's files and run until nothing is left to pursue — exit 0 `met` or `planned`, 1 `unreachable`, 2 `unfinished`,
//! and 143 where it was told to stop, as the Python runtime's `main` exits. With `--check` it runs nothing: booted in
//! memory, its parts made over members that reach nothing, it exits 0 printing one line of JSON — the packages it
//! makes, whether it holds a desire and what its world as posed contradicts — or 3 and why not; and with `--boot PATH`
//! it writes the store as booted there, in N-Quads, which is what `orexis-onboard` reads the agent's boot from.
//!
//! THE JOURNAL FIRST, so the log of the boot is in it: a store of its own in memory, its archive on disk where `--journal` says, its log kept
//! for the window the environment says and served read-only where the environment names a port (`JOURNAL_PORT`). A
//! SINK PER PURPOSE the environment names a store for, and the part that writes it made with the rest. A STOP IS AN
//! EXIT: `podman stop` sends SIGTERM, and the run ends before its next pass, every part stopped and the last window of
//! metrics written.

use std::path::{Path, PathBuf};
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex, OnceLock};

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::{Clock, Paced};
use orexis::namespaces::Namespaces;
use orexis::series::{self, HISTORY, METRICS};
use orexis::store::Store;
use orexis::task::{MET, PLANNED, UNREACHABLE};
use orexis_agent::{Watching, Wiring};

/// What keeps a log record: the logger, the level and the message, as a journal remarks it.
type Remark = Box<dyn Fn(&str, log::Level, &str) + Send + Sync>;

/// The log, to the standard error and into the journal where the agent keeps one: every record at its level. Whether
/// it keeps one is known only once its self graph is read, so what is said before is held (`early`) and handed to the
/// journal as it is attached, or dropped where the agent plays no recorder.
struct Logger {
    level: log::LevelFilter,
    remark: OnceLock<Remark>,
    early: Mutex<Option<Vec<(String, log::Level, String)>>>,
}

impl Logger {
    /// Keep every record from here on by `remark`, and what was said before it first.
    fn attach(&self, remark: Remark) {
        for (logger, level, message) in self.early.lock().unwrap().take().unwrap_or_default() {
            remark(&logger, level, &message);
        }
        let _ = self.remark.set(remark);
    }

    /// Nobody keeps the log: what was held is dropped, and nothing more is.
    fn unkept(&self) {
        self.early.lock().unwrap().take();
    }
}

/// A log level as the log names it.
fn level_name(level: log::Level) -> &'static str {
    match level {
        log::Level::Error => "ERROR",
        log::Level::Warn => "WARNING",
        log::Level::Info => "INFO",
        log::Level::Debug | log::Level::Trace => "DEBUG",
    }
}

/// The logger a record is kept under, as the Python packages name theirs: the package of its module.
fn logger_of(target: &str) -> String {
    let crate_name = target.split("::").next().unwrap_or(target);
    match crate_name.strip_prefix("orexis_") {
        Some(package) => package.to_string(),
        None => target.split("::").nth(1).unwrap_or(crate_name).to_string(),
    }
}

impl log::Log for Logger {
    fn enabled(&self, metadata: &log::Metadata<'_>) -> bool {
        //  A CLIENT'S OWN DEBUG names every url it calls, and a Bot API url carries the bot's token: below WARN, the
        //  HTTP client says nothing, whatever the agent's level.
        if metadata.target().starts_with("ureq") && metadata.level() > log::Level::Warn {
            return false;
        }
        metadata.level() <= self.level
    }

    fn log(&self, record: &log::Record<'_>) {
        if !self.enabled(record.metadata()) {
            return;
        }
        let message = record.args().to_string();
        eprintln!(
            "{} {} {message}",
            logger_of(record.target()),
            level_name(record.level())
        );
        //  THE JOURNAL SAYS NOTHING OF ITSELF, and keeps what is said from INFO on.
        if record.level() <= log::Level::Info && !record.target().starts_with("orexis_journal::journal") {
            let logger = logger_of(record.target());
            match self.remark.get() {
                Some(remark) => remark(&logger, record.level(), &message),
                None => {
                    if let Some(early) = self.early.lock().unwrap().as_mut() {
                        early.push((logger, record.level(), message));
                    }
                }
            }
        }
    }

    fn flush(&self) {}
}

static LOGGER: OnceLock<Logger> = OnceLock::new();

struct Args {
    world: PathBuf,
    agent: String,
    volume: Option<PathBuf>,
    journal: Option<PathBuf>,
    check: bool,
    boot: Option<PathBuf>,
}

fn args() -> Result<Args, String> {
    let mut rest = std::env::args().skip(1);
    let (mut positional, mut volume, mut journal, mut check) = (Vec::new(), None, None, false);
    let mut boot = None;
    while let Some(arg) = rest.next() {
        match arg.as_str() {
            "--volume" => volume = Some(PathBuf::from(rest.next().ok_or("--volume takes a path")?)),
            "--journal" => journal = Some(PathBuf::from(rest.next().ok_or("--journal takes a path")?)),
            "--check" => check = true,
            "--boot" => boot = Some(PathBuf::from(rest.next().ok_or("--boot takes a path")?)),
            other => positional.push(other.to_string()),
        }
    }
    let [world, agent] = positional.as_slice() else {
        return Err(
            "usage: orexis-agent <world> <agent> [--volume PATH] [--journal PATH] [--check [--boot PATH]]".into(),
        );
    };
    Ok(Args {
        world: PathBuf::from(world),
        agent: agent.clone(),
        volume,
        journal,
        check,
        boot,
    })
}

fn env(name: &str) -> Option<String> {
    std::env::var(name).ok()
}

/// The name of the world's directory, which its buckets, its compose project and its dashboards' folder go by.
fn world_name(world: &Path) -> String {
    let world = world.canonicalize().unwrap_or_else(|_| world.to_path_buf());
    world
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_default()
}

/// What an agent that plays a recorder keeps of what happened: its journal, and the archive what lasts is taken to.
#[cfg(feature = "journal")]
type Kept = (
    Arc<orexis_journal::Journal>,
    Option<Arc<orexis_journal_oxigraph::Archive>>,
);

/// THE ARCHIVE OF AN AGENT THAT PLAYS A RECORDER: a store of its own on disk where `--journal` says, and none
/// otherwise.
#[cfg(feature = "journal")]
fn archive(path: Option<&Path>) -> Result<Option<Arc<orexis_journal_oxigraph::Archive>>, Error> {
    match path {
        #[cfg(feature = "volume")]
        Some(path) => Ok(Some(Arc::new(orexis_journal_oxigraph::Archive::open(path)?))),
        #[cfg(not(feature = "volume"))]
        Some(_) => Err(Error::Evaluation(
            "this binary was built without the volume feature".into(),
        )),
        None => Ok(None),
    }
}

/// THE JOURNAL OF AN AGENT THAT PLAYS A RECORDER: in memory, its log kept from here on with what the boot said
/// before; its archive on disk where `--journal` says; and both served on the loopback where the environment names a
/// port, the archive at `/sparql`, or the journal there where the agent keeps none, and the journal at `/live/sparql`.
#[cfg(feature = "journal")]
fn journal(args: &Args, clock: &Arc<Paced>) -> Result<Kept, Error> {
    use orexis_journal::journal;
    let archive = archive(args.journal.as_deref())?;
    let mut kept = journal::Journal::new(journal::window_s(&env), {
        let clock = clock.clone();
        Arc::new(move || clock.now())
    })?;
    kept.incident_level = journal::incident_level(&env);
    kept.incidents = journal::incidents(&env);
    let kept = Arc::new(kept);
    if let Some(logger) = LOGGER.get() {
        let into = kept.clone();
        logger.attach(Box::new(move |logger, level, message| {
            let _ = into.remark(logger, level, message, None);
        }));
    }
    if let Some(port) = env("JOURNAL_PORT").and_then(|p| p.parse().ok()) {
        let past = archive.as_ref().map_or_else(|| kept.store.clone(), |a| a.store.clone());
        if let Err(e) = journal::serve(
            vec![("/sparql", past), ("/live/sparql", kept.store.clone())],
            "127.0.0.1",
            port,
        ) {
            log::warn!("{}: the journal cannot be served on {port}: {e}", args.agent);
        }
    }
    Ok((kept, archive))
}

fn run(args: &Args, clock: Arc<Paced>, halt: Arc<AtomicBool>) -> Result<String, Error> {
    let tree = PathBuf::from(env("OREXIS_TREE").unwrap_or_else(|| TREE.to_string()));
    let namespaces = Arc::new(Namespaces::of_tree(&tree)?);
    let store = match &args.volume {
        #[cfg(feature = "volume")]
        Some(path) => Store::open(path, namespaces)?,
        #[cfg(not(feature = "volume"))]
        Some(_) => {
            return Err(Error::Evaluation(
                "this binary was built without the volume feature".into(),
            ));
        }
        None => Store::new(namespaces)?,
    };
    let loaded = orexis_agent::booted(&store, &tree, &args.world, &args.agent, clock.now())?;
    //  A JOURNAL WHERE THE AGENT PLAYS A RECORDER, and none otherwise: its packages say what happens either way.
    #[cfg(feature = "journal")]
    let (kept, archive) = if loaded.iter().any(|p| p == orexis_agent::JOURNAL) {
        let (kept, archive) = journal(args, &clock)?;
        (Some(kept), archive)
    } else {
        log::info!("{} plays no recorder, and keeps no journal", args.agent);
        (None, None)
    };
    #[cfg(feature = "journal")]
    let archive_journal_every_s = orexis_journal_oxigraph::interval(&env);
    #[cfg(feature = "journal")]
    if archive.is_some() {
        log::info!(
            "{} archives what its journal keeps for good every {archive_journal_every_s}s",
            args.agent
        );
    }
    if let Some(logger) = LOGGER.get() {
        logger.unkept();
    }
    let mut sinks = series::load(&env);
    let told: Vec<String> = sinks.keys().map(|p| p.to_lowercase()).collect();
    if told.is_empty() {
        log::info!("{} writes no series", args.agent);
    } else {
        log::info!("{} writes {} to a series store", args.agent, told.join(", "));
    }
    let metrics = sinks.remove(METRICS).map(|sink| {
        let interval = orexis_metrics::load(&env);
        log::info!("{} writes its metrics every {interval}s", args.agent);
        orexis_metrics::Window::new(sink, interval, Some(&world_name(&args.world)), Some(&args.agent))
    });
    //  WHERE THE HISTORY BUCKET IS, sensing's readings are archived, and how often is the environment's to say.
    #[cfg(feature = "sensing")]
    let archive_every_s = Some(orexis_sensing_influxdb::interval(&env));
    #[cfg(not(feature = "sensing"))]
    let archive_every_s = None;
    #[cfg(feature = "journal")]
    let traces = orexis_journal_otlp::from_environment(&env).filter(|_| kept.is_some());
    #[cfg(feature = "journal")]
    if let Some(tracing) = &traces {
        log::info!(
            "{} ships its activities as spans to {} every {}s",
            args.agent,
            tracing.endpoint,
            tracing.every_s
        );
    }
    let wiring = Wiring {
        watching: Watching {
            #[cfg(feature = "journal")]
            journal: kept.clone(),
            #[cfg(feature = "journal")]
            archive: archive.clone().map(|a| (a, archive_journal_every_s)),
            history: sinks.remove(HISTORY),
            archive_every_s,
            metrics,
            #[cfg(feature = "journal")]
            traces,
        },
        ..Wiring::default()
    };
    //  THE AGENT'S BODY IS A TOKIO RUNTIME, a worker a core, and each package its roles load is a task on it
    //  (a-package-is-a-task-that-awaits-its-events).
    let workers = std::thread::available_parallelism().map_or(1, |n| n.get());
    let tasks = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(workers.max(1))
        .thread_name("orexis-tasks")
        .enable_all()
        .build()
        .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
    let outcome = tasks.block_on(async {
        let mut running = orexis_agent::start(&store, &args.agent, clock.clone(), &loaded, None, wiring)?;
        //  A SIGNAL ENDS THE RUN'S WAIT, which may be long since nothing polls: the flag is raised and the wake rung.
        if let Ok(mut signals) =
            signal_hook::iterator::Signals::new([signal_hook::consts::SIGTERM, signal_hook::consts::SIGINT])
        {
            let (wake, raised) = (running.wake(), halt.clone());
            std::thread::spawn(move || {
                for _ in signals.forever() {
                    raised.store(true, std::sync::atomic::Ordering::Relaxed);
                    wake.ring();
                }
            });
        }
        running.halt = Some(halt);
        let outcome = running.released().await;
        if let Err(e) = &outcome {
            //  AN ERROR ESCAPING A TASK is an incident: said at ERROR, it keeps the journal's window before it.
            log::error!("{}: a task failed, and the agent stops: {e}", args.agent);
        }
        running.stop().await;
        outcome
    });
    //  THE LAST WORD: what was said after the archiver's last turn is taken too, and reaches the disk.
    #[cfg(feature = "journal")]
    if let (Some(kept), Some(archive)) = (&kept, &archive) {
        if let Err(e) = archive.take(kept) {
            eprintln!("{}: the journal's last entries were not archived: {e}", args.agent);
        }
        archive.flush();
    }
    outcome
}

fn main() {
    let level = match env("OREXIS_LOG").as_deref() {
        Some("debug") => log::LevelFilter::Debug,
        Some("warning") | Some("warn") => log::LevelFilter::Warn,
        _ => log::LevelFilter::Info,
    };
    let logger = LOGGER.get_or_init(|| Logger {
        level,
        remark: OnceLock::new(),
        early: Mutex::new(Some(Vec::new())),
    });
    let _ = log::set_logger(logger).map(|()| log::set_max_level(level));
    let args = match args() {
        Ok(a) => a,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };
    if args.check {
        //  A CHECK RUNS NOTHING: no journal, no series, no bus — the boot and the parts' making, and the verdict.
        let tree = PathBuf::from(env("OREXIS_TREE").unwrap_or_else(|| TREE.to_string()));
        match orexis_agent::check(
            &tree,
            &args.world,
            &args.agent,
            oxsdatatypes::DateTime::now(),
            args.boot.as_deref(),
        ) {
            Ok(checked) => {
                //  THE VERDICT AS ONE LINE OF JSON on the standard output, for onboarding to read; what is said for eyes
                //  goes to the log.
                log::info!("{} boots, and makes {}", args.agent, checked.loaded.join(", "));
                let contradictions: Vec<serde_json::Value> = checked
                    .contradictions
                    .iter()
                    .map(|(c, rows)| serde_json::json!([c, rows]))
                    .collect();
                println!(
                    "{}",
                    serde_json::json!({
                        "agent": args.agent,
                        "loaded": checked.loaded,
                        "desire": checked.desire,
                        "contradictions": contradictions,
                    })
                );
                std::process::exit(0);
            }
            Err(e) => {
                eprintln!("{}: {e}", args.agent);
                std::process::exit(3);
            }
        }
    }
    let clock = match Paced::from_env() {
        Ok(c) => Arc::new(c),
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(3);
        }
    };
    let halt = Arc::new(AtomicBool::new(false));
    for signal in [signal_hook::consts::SIGTERM, signal_hook::consts::SIGINT] {
        let _ = signal_hook::flag::register(signal, halt.clone());
    }
    let outcome = run(&args, clock, halt.clone());
    let halted = halt.load(std::sync::atomic::Ordering::Relaxed);
    match outcome {
        Ok(_) if halted => std::process::exit(128 + signal_hook::consts::SIGTERM),
        Ok(outcome) => std::process::exit(match outcome.as_str() {
            MET | PLANNED => 0,
            UNREACHABLE => 1,
            _ => 2,
        }),
        Err(e) => {
            log::error!("{}: {e}", args.agent);
            std::process::exit(3);
        }
    }
}
