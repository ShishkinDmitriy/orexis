//! `orexis-agent <world> <agent> [--volume PATH] [--check [--boot PATH]]`: one agent, booted from a
//! world's files and run until nothing is left to pursue — exit 0 `met` or `planned`, 1 `unreachable`, 2 `unfinished`,
//! and 143 where it was told to stop, as the Python runtime's `main` exits. With `--check` it runs nothing: booted in
//! memory, its parts made over members that reach nothing, it exits 0 printing one line of JSON — the packages it
//! makes, whether it holds a desire and what its world as posed contradicts — or 3 and why not; and with `--boot PATH`
//! it writes the store as booted there, in N-Quads, which is what `orexis-onboard` reads the agent's boot from.
//!
//! IT MAKES NO JOURNAL: the package that keeps one makes its own as it starts, and is handed the process's log, with
//! what the boot said before; what archives it opens its own archive. A
//! series sink is made by the package that writes it, as the rest are. A STOP IS AN
//! EXIT: `podman stop` sends SIGTERM, and the run ends before its next pass, every part stopped and the last window of
//! metrics written.

use std::path::{Path, PathBuf};
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex, OnceLock};

use orexis::Error;
use orexis::clock::Paced;
use orexis::store::Store;
use orexis::task::{MET, PLANNED, UNREACHABLE};

use orexis::task::Remark;

/// The log, to the standard error and into the journal where the agent keeps one: every record at its level. Whether
/// it keeps one is known only once its self graph is read, so what is said before is held (`early`) and handed to the
/// journal as it is attached, or dropped where the agent plays no recorder.
struct Logger {
    level: log::LevelFilter,
    hushed: orexis::task::Hushed,
    remark: OnceLock<Remark>,
    early: Mutex<Option<Vec<Line>>>,
}

/// A line of the log held until somebody keeps it: its target, its logger, its level and its message.
type Line = (String, String, log::Level, String);

impl Logger {
    /// Keep every record from here on by `remark`, and what was said before it first.
    fn attach(&self, remark: Remark) {
        for (target, logger, level, message) in self.early.lock().unwrap().take().unwrap_or_default() {
            remark(&target, &logger, level, &message);
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

impl Logger {
    /// Whether a record of `target` at `level` is said at all, by what the packages hush (`orexis::task::Hushed`).
    fn said(&self, target: &str, level: log::Level) -> bool {
        self.hushed
            .0
            .read()
            .expect("hushes nobody poisoned")
            .iter()
            .all(|(hushed, from)| !target.starts_with(hushed) || level <= *from)
    }
}

impl log::Log for Logger {
    fn enabled(&self, metadata: &log::Metadata<'_>) -> bool {
        //  WHAT A PACKAGE HUSHES is said from where its role says, whatever the agent's level.
        metadata.level() <= self.level && self.said(metadata.target(), metadata.level())
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
        //  KEPT FROM INFO ON, by whichever package keeps the log.
        if record.level() <= log::Level::Info {
            let (target, logger) = (record.target(), logger_of(record.target()));
            match self.remark.get() {
                Some(remark) => remark(target, &logger, record.level(), &message),
                None => {
                    if let Some(early) = self.early.lock().unwrap().as_mut() {
                        early.push((target.to_string(), logger, record.level(), message));
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
    check: bool,
    boot: Option<PathBuf>,
}

fn args() -> Result<Args, String> {
    let mut rest = std::env::args().skip(1);
    let (mut positional, mut volume, mut check) = (Vec::new(), None, false);
    let mut boot = None;
    while let Some(arg) = rest.next() {
        match arg.as_str() {
            "--volume" => volume = Some(PathBuf::from(rest.next().ok_or("--volume takes a path")?)),
            "--check" => check = true,
            "--boot" => boot = Some(PathBuf::from(rest.next().ok_or("--boot takes a path")?)),
            other => positional.push(other.to_string()),
        }
    }
    let [world, agent] = positional.as_slice() else {
        return Err("usage: orexis-agent <world> <agent> [--volume PATH] [--check [--boot PATH]]".into());
    };
    Ok(Args {
        world: PathBuf::from(world),
        agent: agent.clone(),
        volume,
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

fn run(args: &Args, clock: Arc<Paced>, halt: Arc<AtomicBool>) -> Result<String, Error> {
    let store = match &args.volume {
        #[cfg(feature = "volume")]
        Some(path) => Store::open(path)?,
        #[cfg(not(feature = "volume"))]
        Some(_) => {
            return Err(Error::Evaluation(
                "this binary was built without the volume feature".into(),
            ));
        }
        None => Store::new()?,
    };
    //  DEPLOYED: what a package is not handed here it makes for itself from what the world says, its journal, its
    //  archive and its series sinks; and the log is handed to whichever package keeps it.
    let provided = orexis::task::Provided::default().with(orexis::task::Deployed {
        world: world_name(&args.world),
    });
    if let Some(logger) = LOGGER.get() {
        let keep: Box<dyn FnOnce(orexis::task::Remark) + Send> = Box::new(move |remark| logger.attach(remark));
        provided.provide(orexis::task::Said(keep));
        provided.provide(logger.hushed.clone());
    }
    //  BOOTED, each package's start held where it decided, to be run on once the runtime is there.
    let booted = orexis_agent::boot(&store, &args.world, &args.agent, clock.clone(), provided)?;
    //  THE AGENT'S BODY IS A TOKIO RUNTIME, a worker a core, and each package its roles load is a task on it
    //  (a-package-is-a-task-that-awaits-its-events).
    let workers = std::thread::available_parallelism().map_or(1, |n| n.get());
    let tasks = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(workers.max(1))
        .thread_name("orexis-tasks")
        .enable_all()
        .build()
        .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
    tasks.block_on(async {
        let mut running = booted.start().await?;
        //  EVERY PACKAGE HAS MADE ITS CORE: where none kept the log, what was held of it is dropped.
        if let Some(logger) = LOGGER.get() {
            logger.unkept();
        }
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
    })
}

fn main() {
    let level = match env("OREXIS_LOG").as_deref() {
        Some("debug") => log::LevelFilter::Debug,
        Some("warning") | Some("warn") => log::LevelFilter::Warn,
        _ => log::LevelFilter::Info,
    };
    let logger = LOGGER.get_or_init(|| Logger {
        level,
        hushed: orexis::task::Hushed::default(),
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
        match orexis_agent::check(
            &args.world,
            &args.agent,
            oxsdatatypes::DateTime::now(),
            args.boot.as_deref(),
        ) {
            Ok(checked) => {
                //  THE VERDICT AS ONE LINE OF JSON on the standard output, for onboarding to read; what is said for eyes
                //  goes to the log.
                log::info!("{} boots, and makes {}", args.agent, checked.loaded.join(", "));
                println!(
                    "{}",
                    serde_json::json!({
                        "agent": args.agent,
                        "loaded": checked.loaded,
                        "held": checked.held,
                        "refused": checked.refused,
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn what_a_package_hushes_is_said_from_its_level() {
        let logger = Logger {
            level: log::LevelFilter::Debug,
            hushed: orexis::task::Hushed::default(),
            remark: OnceLock::new(),
            early: Mutex::new(None),
        };
        logger.hushed.0.write().unwrap().push(("ureq", log::Level::Warn));
        assert!(logger.said("ureq::unit", log::Level::Warn));
        assert!(
            !logger.said("ureq::unit", log::Level::Debug),
            "quieter than its level, it says nothing"
        );
        assert!(
            logger.said("orexis_planning", log::Level::Debug),
            "a target nobody hushes says everything"
        );
    }
}
