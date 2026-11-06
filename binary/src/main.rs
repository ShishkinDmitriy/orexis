//! `orexis-agent <world> <agent> [--volume PATH] [--passes N]`: one agent, booted from a world's files and run until
//! nothing is left to pursue — exit 0 `met` or `planned`, 1 `unreachable`, 2 `unfinished`.

use std::path::PathBuf;
use std::sync::Arc;

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::{Clock, Paced};
use orexis::namespaces::Namespaces;
use orexis::runtime::{MET, PLANNED, Part, Runtime, UNREACHABLE};
use orexis::store::Store;

struct Logger(log::LevelFilter);

impl log::Log for Logger {
    fn enabled(&self, metadata: &log::Metadata<'_>) -> bool {
        metadata.level() <= self.0
    }
    fn log(&self, record: &log::Record<'_>) {
        if self.enabled(record.metadata()) {
            eprintln!("{} {} {}", record.target(), record.level(), record.args());
        }
    }
    fn flush(&self) {}
}

struct Args {
    world: PathBuf,
    agent: String,
    volume: Option<PathBuf>,
    passes: Option<usize>,
}

fn args() -> Result<Args, String> {
    let mut rest = std::env::args().skip(1);
    let (mut positional, mut volume, mut passes) = (Vec::new(), None, None);
    while let Some(arg) = rest.next() {
        match arg.as_str() {
            "--volume" => volume = Some(PathBuf::from(rest.next().ok_or("--volume takes a path")?)),
            "--passes" => {
                passes = Some(
                    rest.next()
                        .ok_or("--passes takes a number")?
                        .parse()
                        .map_err(|_| "--passes takes a number")?,
                )
            }
            "--journal" => {
                rest.next();
                log::warn!("the journal is not ported yet: nothing is journaled");
            }
            other => positional.push(other.to_string()),
        }
    }
    let [world, agent] = positional.as_slice() else {
        return Err("usage: orexis-agent <world> <agent> [--volume PATH] [--passes N]".into());
    };
    Ok(Args {
        world: PathBuf::from(world),
        agent: agent.clone(),
        volume,
        passes,
    })
}

fn run(args: &Args) -> Result<String, Error> {
    let tree = PathBuf::from(std::env::var("OREXIS_TREE").unwrap_or_else(|_| TREE.to_string()));
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
    let clock = Paced::from_env()?;
    let loaded = orexis_agent::booted(&store, &tree, &args.world, &args.agent, clock.now())?;
    let mut parts: Vec<(String, Box<dyn Part + '_>)> = Vec::new();
    for package in &loaded {
        #[cfg(feature = "planning")]
        if package == "planning" {
            parts.push((
                package.clone(),
                Box::new(orexis_planning::create::Planning::new(&store, &args.agent, None)?),
            ));
        }
    }
    let lent: Vec<(String, &mut dyn Part)> = parts
        .iter_mut()
        .map(|(p, part)| (p.clone(), part.as_mut() as &mut dyn Part))
        .collect();
    let mut runtime = Runtime::new(&store, &args.agent, &clock, lent);
    let outcome = runtime.run(args.passes, 1.0);
    runtime.stop();
    outcome
}

fn main() {
    let level = match std::env::var("OREXIS_LOG").as_deref() {
        Ok("debug") => log::LevelFilter::Debug,
        Ok("warning") | Ok("warn") => log::LevelFilter::Warn,
        _ => log::LevelFilter::Info,
    };
    static LOGGER: std::sync::OnceLock<Logger> = std::sync::OnceLock::new();
    let _ = log::set_logger(LOGGER.get_or_init(|| Logger(level))).map(|()| log::set_max_level(level));
    let args = match args() {
        Ok(a) => a,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };
    match run(&args) {
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
