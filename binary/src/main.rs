//! `orexis-agent <world> <agent> [--volume PATH] [--journal PATH] [--passes N] [--check [--boot PATH]]`: one agent, booted from a
//! world's files and run until nothing is left to pursue — exit 0 `met` or `planned`, 1 `unreachable`, 2 `unfinished`,
//! and 143 where it was told to stop, as the Python runtime's `main` exits. With `--check` it runs nothing: booted in
//! memory, its parts made over members that reach nothing, it exits 0 printing one line of JSON — the packages it
//! makes, whether it holds a desire and what its world as posed contradicts — or 3 and why not; and with `--boot PATH`
//! it writes the store as booted there, in N-Quads, which is what `orexis-onboard` reads the agent's boot from.
//!
//! THE JOURNAL FIRST, so the log of the boot is in it: a store of its own, on disk where `--journal` says, its log kept
//! for the window the environment says and served read-only where the environment names a port (`JOURNAL_PORT`). A
//! SINK PER PURPOSE the environment names a store for, and the part that writes it made with the rest. A STOP IS AN
//! EXIT: `podman stop` sends SIGTERM, and the run ends before its next pass, every part stopped and the last window of
//! metrics written.

use std::path::{Path, PathBuf};
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, OnceLock};

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::{Clock, Paced};
use orexis::journal::{self, Journal};
use orexis::namespaces::Namespaces;
use orexis::runtime::{MET, PLANNED, Part, Runtime, UNREACHABLE};
use orexis::series::{self, HISTORY, METRICS};
use orexis::store::Store;
use orexis_agent::{Watching, Wiring};

/// The log, to the standard error and into the journal once one is kept: every record at its level.
struct Logger {
    level: log::LevelFilter,
    journal: OnceLock<Arc<Journal>>,
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
            journal::level_name(record.level())
        );
        //  THE JOURNAL SAYS NOTHING OF ITSELF, and keeps what is said from INFO on.
        if record.level() <= log::Level::Info
            && !record.target().starts_with("orexis::journal")
            && let Some(journal) = self.journal.get()
        {
            let _ = journal.remark(&logger_of(record.target()), record.level(), &message, None);
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
    passes: Option<usize>,
    check: bool,
    boot: Option<PathBuf>,
}

fn args() -> Result<Args, String> {
    let mut rest = std::env::args().skip(1);
    let (mut positional, mut volume, mut journal, mut passes, mut check) = (Vec::new(), None, None, None, false);
    let mut boot = None;
    while let Some(arg) = rest.next() {
        match arg.as_str() {
            "--volume" => volume = Some(PathBuf::from(rest.next().ok_or("--volume takes a path")?)),
            "--journal" => journal = Some(PathBuf::from(rest.next().ok_or("--journal takes a path")?)),
            "--passes" => {
                passes = Some(
                    rest.next()
                        .ok_or("--passes takes a number")?
                        .parse()
                        .map_err(|_| "--passes takes a number")?,
                )
            }
            "--check" => check = true,
            "--boot" => boot = Some(PathBuf::from(rest.next().ok_or("--boot takes a path")?)),
            other => positional.push(other.to_string()),
        }
    }
    let [world, agent] = positional.as_slice() else {
        return Err(
            "usage: orexis-agent <world> <agent> [--volume PATH] [--journal PATH] [--passes N] [--check [--boot PATH]]"
                .into(),
        );
    };
    Ok(Args {
        world: PathBuf::from(world),
        agent: agent.clone(),
        volume,
        journal,
        passes,
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

fn opened(path: Option<&Path>) -> Result<Option<oxigraph::store::Store>, Error> {
    match path {
        #[cfg(feature = "volume")]
        Some(path) => Ok(Some(
            oxigraph::store::Store::open(path).map_err(|e| Error::Evaluation(e.to_string()))?,
        )),
        #[cfg(not(feature = "volume"))]
        Some(_) => Err(Error::Evaluation(
            "this binary was built without the volume feature".into(),
        )),
        None => Ok(None),
    }
}

fn run(args: &Args, clock: &'static Paced, journal: Arc<Journal>, halt: Arc<AtomicBool>) -> Result<String, Error> {
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
    let wiring = Wiring {
        watching: Watching {
            journal: Some(journal),
            history: sinks.remove(HISTORY),
            metrics,
        },
        ..Wiring::default()
    };
    let (mut parts, seen) = orexis_agent::assemble_seen(&store, &args.agent, clock, &loaded, None, wiring)?;
    let lent: Vec<(String, &mut dyn Part)> = parts
        .iter_mut()
        .map(|(p, part)| (p.clone(), part.as_mut() as &mut dyn Part))
        .collect();
    let mut runtime = Runtime::new(&store, &args.agent, clock, lent)?;
    runtime.watch = seen.watch.clone();
    runtime.halt = Some(halt);
    let outcome = runtime.run(args.passes, 1.0);
    if let Err(e) = &outcome {
        //  AN ERROR ESCAPING A PASS is an incident: said at ERROR, it keeps the journal's window before it.
        log::error!("{}: a pass failed, and the agent stops: {e}", args.agent);
    }
    runtime.stop();
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
        journal: OnceLock::new(),
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
    static CLOCK: OnceLock<Paced> = OnceLock::new();
    let clock = match Paced::from_env() {
        Ok(c) => CLOCK.get_or_init(|| c),
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(3);
        }
    };
    let kept = match opened(args.journal.as_deref()).and_then(|store| {
        let mut kept = Journal::new(
            store,
            journal::window_s(&env),
            Arc::new(|| CLOCK.get().map_or_else(oxsdatatypes::DateTime::now, Clock::now)),
        )?;
        kept.incident_level = journal::incident_level(&env);
        kept.incidents = journal::incidents(&env);
        Ok(Arc::new(kept))
    }) {
        Ok(kept) => kept,
        Err(e) => {
            eprintln!("{}: the journal would not open: {e}", args.agent);
            std::process::exit(3);
        }
    };
    let _ = logger.journal.set(kept.clone());
    if let Some(port) = env("JOURNAL_PORT").and_then(|p| p.parse().ok())
        && let Err(e) = journal::serve(kept.clone(), "127.0.0.1", port)
    {
        log::warn!("{}: the journal cannot be served on {port}: {e}", args.agent);
    }
    let halt = Arc::new(AtomicBool::new(false));
    for signal in [signal_hook::consts::SIGTERM, signal_hook::consts::SIGINT] {
        let _ = signal_hook::flag::register(signal, halt.clone());
    }
    let outcome = run(&args, clock, kept.clone(), halt.clone());
    kept.flush();
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
