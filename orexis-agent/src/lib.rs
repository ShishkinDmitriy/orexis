//! ONE AGENT'S PROCESS, as `agent/runtime.py`'s `main` assembles it: the world booted into a store, the parts of the
//! packages its roles load made — each a feature of this binary, so a package an agent does not run is compiled out —
//! and run until nothing holds it. What is each package's at boot is said here, where the packages are known:
//! planning writes the scopes a pass reads.

use std::path::Path;

use std::sync::{Arc, Mutex};

use orexis::Error;
use orexis::boot::{Booting, boot};
use orexis::clock::Clock;
use orexis::events::Watch;
use orexis::journal::Journal;
use orexis::runtime::Runtime;
use orexis::series::Sink;
use orexis::store::Store;

/// Boot `agent` of `world` into `store` from the documents of `tree`: the packages it loads, each one this binary
/// holds — refused where it plays a role whose package this binary was built without.
pub fn booted(
    store: &Store,
    tree: &Path,
    world: &Path,
    agent: &str,
    now: oxsdatatypes::DateTime,
) -> Result<Vec<String>, Error> {
    let loaded = boot(store, &Booting { tree, world, agent })?;
    let held: Vec<&str> = loaded.iter().map(String::as_str).filter(|p| !built(p)).collect();
    if !held.is_empty() {
        return Err(Error::Evaluation(format!(
            "{agent} plays a role whose package this binary was built without: {}",
            held.join(", ")
        )));
    }
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
/// documents of `tree`, and every part its roles load made and started, on a runtime that is never run, over members
/// that reach nothing — no broker, no web, no bot and no model — so every text a part parses at its making is parsed. What it found, or why it would not boot; and,
/// where `boot` names a file, the store as booted, in N-Quads, before any part is made — which is what onboarding
/// holds to the requirements, so the world is booted once, by the agent that will run it.
/// `orexis-onboard` asks it of every agent before anything is granted, and `orexis-agent/tests/check.rs` of every world.
pub fn check(
    tree: &Path,
    world: &Path,
    agent: &str,
    now: oxsdatatypes::DateTime,
    boot: Option<&Path>,
) -> Result<Checked, Error> {
    let namespaces = Arc::new(orexis::namespaces::Namespaces::of_tree(tree)?);
    let store = Store::new(namespaces)?;
    let loaded = booted(&store, tree, world, agent, now)?;
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
    let mut runtime = Runtime::new(&store, agent, clock)?;
    assemble_wired(&mut runtime, &checked.loaded, None, wiring)?;
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

/// Whether this binary holds `package`'s part.
pub fn built(package: &str) -> bool {
    (package == "belief" && cfg!(feature = "belief"))
        || (package == "planning" && cfg!(feature = "planning"))
        || (package == "execution" && cfg!(feature = "execution"))
        || (package == "sensing" && cfg!(feature = "sensing"))
        || (package == "prediction" && cfg!(feature = "prediction"))
        || (package == "transport/mqtt" && cfg!(feature = "mqtt"))
        || (package == "speech" && cfg!(feature = "speech"))
        || (package == "coordination" && cfg!(feature = "coordination"))
        || (package == "translation" && cfg!(feature = "translation"))
        || (package == "transport/http" && cfg!(feature = "http"))
        || (package == "transport/telegram" && cfg!(feature = "telegram"))
        || (package == "transport/email" && cfg!(feature = "email"))
}

/// Have execution ask of a head about to be taken, where planning is loaded to answer: it says `execution:HeadAsked`, and
/// planning's `planning:HeadChecked` answers where the present no longer admits it (#916). No link: a flag, since an
/// executor with nobody to answer must not wait for an answer.
#[cfg(all(feature = "planning", feature = "execution"))]
pub fn judge(execution: &mut orexis_execution::create::Execution) {
    execution.executor.asks = true;
}

/// Hand the planner prediction's foresight, as it is handed the store and the clock: a pure function that integrates
/// the flows from each ground as the grounds are laid (#1000), through the kernel's `Foresight`, so neither package
/// imports the other. It shares nothing with prediction's part, which holds no state, so it is no link.
#[cfg(all(feature = "planning", feature = "prediction"))]
pub fn foresee(planning: &mut orexis_planning::create::Planning, prediction: &orexis_prediction::create::Prediction) {
    planning.planner.foresee = Some(prediction.offered());
}

/// Give execution's part the taker of an agent that carries out its steps, where anything carries them — a transport
/// to send a step's commands, speech to say its documents: each command kept and said `execution:Commanded` where
/// a transport is loaded, each document kept and said `execution:Told` where speech is, the statements kept handed on
/// with what the executor wrote. Nothing is linked: the transport and speech hear the events beneath their triggers.
#[cfg(feature = "execution")]
pub fn take(
    store: &Store,
    clock: Arc<dyn Clock>,
    execution: &mut orexis_execution::create::Execution,
    me: &str,
    watch: Watch,
    commands: bool,
    says: bool,
) {
    if commands || says {
        execution.executor.take = Some(orexis_execution::create::taker(
            store.clone(),
            me,
            clock,
            watch,
            commands,
            says,
        ));
    }
}

/// WHAT WATCHES THE AGENT, where the deployment keeps any of it: the journal, the history sink, the metrics window and
/// the tracer, which hears every activity as a span.
/// The history part is made where a journal is kept or a history sink is loaded, and the metrics part where a metrics
/// window is, as the Python runtime makes its watchers; each hears every event the parts say.
#[derive(Default)]
pub struct Watching {
    pub journal: Option<Arc<Journal>>,
    pub history: Option<Sink>,
    pub metrics: Option<orexis_metrics::Window>,
    /// The tracer's OTLP endpoint.
    pub traces: Option<String>,
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

/// The parts of the packages `loaded` names, made and each started on `runtime`, whose store, agent and clock they
/// are over: belief first, then planning, execution, sensing, prediction, speech and coordination, and the transport
/// last - the order a pass tells them the instant in, and no order between what each then does. `budget` sizes planning's search where a caller states one; none reads the
/// agent's stance.
pub fn assemble(runtime: &mut Runtime, loaded: &[String], budget: Option<usize>) -> Result<(), Error> {
    assemble_wired(runtime, loaded, budget, Wiring::default())
}

/// `assemble`, over the bus `wiring` hands — a test's — where it hands one.
pub fn assemble_wired(
    runtime: &mut Runtime,
    loaded: &[String],
    budget: Option<usize>,
    wiring: Wiring,
) -> Result<(), Error> {
    assembled(runtime, loaded, budget, wiring, false).map(|_| ())
}

/// What a TEST reads of the parts once they started on the runtime: planning's and execution's parts, each lent to
/// its task, kept here too, which no agent's assembly does, and the runtime's watch, which every part says its
/// events to.
#[derive(Default)]
pub struct Seen {
    pub watch: Watch,
    #[cfg(feature = "planning")]
    pub planning: Option<Arc<Mutex<orexis_planning::create::Planning>>>,
    #[cfg(feature = "execution")]
    pub execution: Option<Arc<Mutex<orexis_execution::create::Execution>>>,
}

impl Seen {
    /// Planning's part, lent: where planning is loaded.
    #[cfg(feature = "planning")]
    pub fn planning(&self) -> std::sync::MutexGuard<'_, orexis_planning::create::Planning> {
        self.planning
            .as_ref()
            .expect("planning loaded")
            .lock()
            .expect("a part nobody poisoned")
    }

    /// Execution's part, lent: where execution is loaded.
    #[cfg(feature = "execution")]
    pub fn execution(&self) -> std::sync::MutexGuard<'_, orexis_execution::create::Execution> {
        self.execution
            .as_ref()
            .expect("execution loaded")
            .lock()
            .expect("a part nobody poisoned")
    }
}

/// `assemble_wired`, and what a TEST reads of the parts: planning's and execution's lent to the runtime.
pub fn assemble_seen(
    runtime: &mut Runtime,
    loaded: &[String],
    budget: Option<usize>,
    wiring: Wiring,
) -> Result<Seen, Error> {
    assembled(runtime, loaded, budget, wiring, true)
}

fn assembled(
    runtime: &mut Runtime,
    loaded: &[String],
    budget: Option<usize>,
    wiring: Wiring,
    lend: bool,
) -> Result<Seen, Error> {
    let (store, agent, clock) = (runtime.beliefs.clone(), runtime.id.clone(), runtime.clock());
    let (store, agent) = (&store, agent.as_str());
    #[allow(unused_mut)]
    let mut seen = Seen {
        watch: runtime.watch().clone(),
        ..Seen::default()
    };
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
    let wiring = Wiring {
        watching: Watching::default(),
        mqtt,
        ..Wiring::default()
    };
    //  WHAT A CHAT READS OF WHAT HAPPENED, where it reads it: the journal where it is, and the series as read.
    #[cfg(feature = "translation")]
    let (journal_store, history_reader, metrics_reader) = (
        watching.journal.as_ref().map(|j| j.store.clone()),
        watching.history.as_ref().map(Sink::reader),
        watching.metrics.as_ref().map(|w| w.sink.reader()),
    );
    let watch = seen.watch.clone();
    let history = if watching.journal.is_some() || watching.history.is_some() {
        let incidents = orexis_history::incidents(store)?;
        Some(orexis_history::History::new(
            &watch,
            watching.history,
            watching.journal,
            incidents,
        ))
    } else {
        None
    };
    let metrics = watching
        .metrics
        .map(|window| orexis_metrics::Metrics::new(window, &watch));
    if let Some(endpoint) = &watching.traces {
        orexis_spans::connect(&watch, agent, orexis_spans::post(endpoint));
    }
    let holds = |package: &str| loaded.iter().any(|p| p == package);
    #[cfg(feature = "belief")]
    #[allow(unused_mut)]
    let mut belief = if holds("belief") {
        Some(orexis_belief::create::Belief::new(store, agent)?)
    } else {
        None
    };
    #[cfg(feature = "planning")]
    #[allow(unused_mut)]
    let mut planning = if holds("planning") {
        Some(orexis_planning::create::Planning::new(store, agent, budget)?)
    } else {
        None
    };
    #[cfg(feature = "execution")]
    #[allow(unused_mut)]
    let mut execution = if holds("execution") {
        Some(orexis_execution::create::Execution::new(store, agent, clock.clone())?)
    } else {
        None
    };
    #[cfg(feature = "sensing")]
    let mut sensing = if holds("sensing") {
        Some(orexis_sensing::create::Sensing::new(store, agent)?)
    } else {
        None
    };
    #[cfg(feature = "prediction")]
    let prediction = holds("prediction").then(orexis_prediction::create::Prediction::default);
    #[cfg(all(feature = "planning", feature = "prediction"))]
    if let (Some(planning), Some(prediction)) = (planning.as_mut(), prediction.as_ref()) {
        foresee(planning, prediction);
    }
    #[cfg(feature = "mqtt")]
    #[allow(unused_mut)]
    let mut transport = if holds("transport/mqtt") {
        let member = match wiring.mqtt {
            Some(member) => member,
            None => {
                let me = orexis::boot::selves(store)?.into_iter().next().unwrap_or_default();
                orexis_transport_mqtt::driver::connect(store, &me, &|name| std::env::var(name).ok())?
            }
        };
        Some(orexis_transport_mqtt::create::Transport::new(member))
    } else {
        None
    };
    #[cfg(not(feature = "mqtt"))]
    let _ = wiring;
    let me = orexis::boot::selves(store)?.into_iter().next().unwrap_or_default();
    #[cfg(feature = "speech")]
    #[allow(unused_mut)]
    let mut speech = holds("speech").then(|| orexis_speech::create::Speech::new(store, &me));
    #[cfg(feature = "coordination")]
    let mut coordination = holds("coordination").then(|| orexis_coordination::create::Coordination::new(store, &me));
    #[cfg(feature = "translation")]
    let translation = if holds("translation") {
        let model = model.or_else(|| {
            orexis_translation::model::Anthropic::from_environ(&|n| std::env::var(n).ok())
                .map(|m| Arc::new(m) as Arc<dyn orexis_translation::model::Model>)
        });
        let mut translator = orexis_translation::create::Translator::new(store, &me, model);
        translator.journal = journal_store;
        translator.history = history_reader;
        translator.metrics = metrics_reader;
        translator.watch = watch.clone();
        Some(orexis_translation::create::Translation::new(translator))
    } else {
        None
    };
    #[cfg(feature = "http")]
    let web = if holds("transport/http") {
        let member = http.unwrap_or_else(|| {
            orexis_transport_http::driver::Http::new(store, &me, orexis_transport_http::driver::get())
        });
        Some(orexis_transport_http::create::Transport::new(member))
    } else {
        None
    };
    #[cfg(feature = "telegram")]
    let bot = if holds("transport/telegram") {
        let member = match telegram {
            Some(member) => member,
            None => orexis_transport_telegram::driver::Telegram::connect(store, &me, &|n| std::env::var(n).ok())?,
        };
        Some(orexis_transport_telegram::create::Transport::new(member))
    } else {
        None
    };
    #[cfg(feature = "email")]
    let mailbox = if holds("transport/email") {
        let member = match email {
            Some(member) => member,
            None => orexis_transport_email::driver::Email::connect(store, &me, &|n| std::env::var(n).ok())?,
        };
        Some(orexis_transport_email::create::Transport::new(member))
    } else {
        None
    };
    #[cfg(feature = "execution")]
    if let Some(execution) = execution.as_mut() {
        #[cfg(feature = "mqtt")]
        let commands = transport.is_some();
        #[cfg(not(feature = "mqtt"))]
        let commands = false;
        #[cfg(feature = "speech")]
        let says = speech.is_some();
        #[cfg(not(feature = "speech"))]
        let says = false;
        take(store, clock.clone(), execution, &me, watch.clone(), commands, says);
    }
    #[cfg(all(feature = "planning", feature = "execution"))]
    if let (Some(_), Some(execution)) = (planning.as_ref(), execution.as_mut()) {
        judge(execution);
    }
    #[cfg(feature = "belief")]
    if let Some(belief) = belief.as_mut() {
        belief.deliberator.watch = watch.clone();
    }
    #[cfg(feature = "planning")]
    if let Some(planning) = planning.as_mut() {
        planning.planner.watch = watch.clone();
    }
    #[cfg(feature = "execution")]
    if let Some(execution) = execution.as_mut() {
        execution.executor.watch = watch.clone();
    }
    #[cfg(feature = "sensing")]
    if let Some(sensing) = sensing.as_mut() {
        sensing.watch = watch.clone();
    }
    #[cfg(feature = "speech")]
    if let Some(speech) = speech.as_mut() {
        speech.speaker.watch = watch.clone();
    }
    #[cfg(feature = "coordination")]
    if let Some(coordination) = coordination.as_mut() {
        coordination.watch = watch.clone();
    }
    #[cfg(feature = "belief")]
    if let Some(belief) = belief {
        orexis_belief::create::start(runtime, &Arc::new(Mutex::new(belief)))?;
    }
    #[cfg(feature = "planning")]
    if let Some(planning) = planning {
        let planning = Arc::new(Mutex::new(planning));
        orexis_planning::create::start(runtime, &planning)?;
        if lend {
            seen.planning = Some(planning);
        }
    }
    #[cfg(feature = "execution")]
    if let Some(execution) = execution {
        let execution = Arc::new(Mutex::new(execution));
        orexis_execution::create::start(runtime, &execution)?;
        if lend {
            seen.execution = Some(execution);
        }
    }
    #[cfg(feature = "sensing")]
    if let Some(sensing) = sensing {
        orexis_sensing::create::start(runtime, &Arc::new(Mutex::new(sensing)))?;
    }
    #[cfg(feature = "prediction")]
    if let Some(prediction) = prediction {
        let _ = prediction;
        orexis_prediction::create::start(runtime);
    }
    #[cfg(feature = "speech")]
    if let Some(speech) = speech {
        orexis_speech::create::start(runtime, &Arc::new(Mutex::new(speech)))?;
    }
    #[cfg(feature = "translation")]
    if let Some(translation) = translation {
        orexis_translation::create::start(runtime, &Arc::new(Mutex::new(translation)))?;
    }
    #[cfg(feature = "coordination")]
    if let Some(coordination) = coordination {
        orexis_coordination::create::start(runtime, &Arc::new(Mutex::new(coordination)))?;
    }
    #[cfg(feature = "mqtt")]
    if let Some(transport) = transport {
        orexis_transport_mqtt::create::start(runtime, &Arc::new(Mutex::new(transport)))?;
    }
    #[cfg(feature = "http")]
    if let Some(web) = web {
        orexis_transport_http::create::start(runtime, &Arc::new(Mutex::new(web)))?;
    }
    #[cfg(feature = "telegram")]
    if let Some(bot) = bot {
        orexis_transport_telegram::create::start(runtime, &Arc::new(Mutex::new(bot)))?;
    }
    #[cfg(feature = "email")]
    if let Some(mailbox) = mailbox {
        orexis_transport_email::create::start(runtime, &Arc::new(Mutex::new(mailbox)))?;
    }
    //  WHAT WATCHES THE AGENT, last, so it is stopped first and writes the last window.
    if let Some(history) = history {
        history.start(runtime);
    }
    if let Some(metrics) = metrics {
        metrics.start(runtime);
    }
    let _ = (store, agent, &clock, budget, holds, lend);
    Ok(seen)
}
