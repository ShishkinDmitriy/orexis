//! ONE AGENT'S PROCESS, as `agent/runtime.py`'s `main` assembles it: the world booted into a store, the parts of the
//! packages its roles load made — each a feature of this binary, so a package an agent does not run is compiled out —
//! and run until nothing holds it. What is each package's at boot is said here, where the packages are known:
//! planning writes the scopes a pass reads.

use std::path::Path;

use std::sync::Arc;

use orexis::Error;
use orexis::boot::{Booting, boot};
use orexis::clock::Clock;
use orexis::events::Watch;
use orexis::journal::Journal;
use orexis::runtime::Part;
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
/// documents of `tree`, and every part its roles load made over members that reach nothing — no broker, no web, no bot
/// and no model — so every text a part parses at its making is parsed. What it found, or why it would not boot; and,
/// where `boot` names a file, the store as booted, in N-Quads, before any part is made — which is what onboarding
/// holds to the requirements, so the world is booted once, by the agent that will run it.
/// `orexis-onboard` asks it of every agent before anything is granted, and `binary/tests/check.rs` of every world.
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
        mqtt: Some(orexis_mqtt::driver::Mqtt::new(&store, &me, Vec::new())),
        #[cfg(feature = "http")]
        http: Some(orexis_http::driver::Http::new(
            &store,
            &me,
            Arc::new(|_: &str| Err("a check reaches no web".to_string())),
        )),
        #[cfg(feature = "telegram")]
        telegram: Some(orexis_telegram::driver::Telegram::new(&store, &me, "", "", {
            let call: orexis_telegram::driver::Call = Arc::new(|_, _| Err("a check reaches no bot".to_string()));
            call
        })),
        #[cfg(feature = "email")]
        email: Some(orexis_email::driver::Email::new(&store, &me, Arc::new(Unreachable))),
        ..Wiring::default()
    };
    assemble_seen(&store, agent, clock, &checked.loaded, None, wiring)?;
    Ok(checked)
}

/// The mailbox a check reaches: none.
#[cfg(feature = "email")]
struct Unreachable;

#[cfg(feature = "email")]
impl orexis_email::driver::Mailbox for Unreachable {
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

/// Hand execution planning's judgment of a head about to be taken: the Planner says where the present no longer
/// admits it (#916). The one link left between them — what a pass published, reached and reconsidered execution
/// hears as events — until a hearer may hold a reader of the store and the judgment is asked as an event (#1119).
#[cfg(all(feature = "planning", feature = "execution"))]
pub fn judge<'a>(
    planning: &orexis_planning::create::Planning<'a>,
    execution: &orexis_execution::create::Execution<'a>,
) {
    let planner = planning.planner.clone();
    execution.executor.borrow_mut().taking = Some(Box::new(move |step, at| planner.borrow_mut().check(step, at)));
}

/// Link planning's part to prediction's, as the Python planner takes the predictor's `foresee` at link: every pass
/// the flows are integrated from each ground as the grounds are laid (#1000), through the kernel's `Foresight`,
/// neither package importing the other.
#[cfg(all(feature = "planning", feature = "prediction"))]
pub fn foresee<'a>(
    planning: &orexis_planning::create::Planning<'a>,
    prediction: &orexis_prediction::create::Prediction,
) {
    planning.planner.borrow_mut().foresee = Some(prediction.offered());
}

/// Give execution's part the taker of an agent that carries out its steps, where anything carries them — a transport
/// to send a step's commands, speech to say its documents: each command kept and said `execution:Commanded` where
/// a transport is loaded, each document kept and said `execution:Told` where speech is, the statements kept handed on
/// with what the executor wrote. Nothing is linked: the transport and speech hear the events beneath their triggers.
#[cfg(feature = "execution")]
pub fn take<'a>(
    store: &'a Store,
    clock: Arc<dyn Clock>,
    execution: &orexis_execution::create::Execution<'a>,
    me: &str,
    watch: Watch,
    commands: bool,
    says: bool,
) {
    if commands || says {
        execution.executor.borrow_mut().take = Some(orexis_execution::create::taker(
            store,
            me,
            clock,
            watch,
            commands,
            says,
            execution.said.clone(),
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
pub struct Wiring<'a> {
    pub watching: Watching,
    #[cfg(feature = "http")]
    pub http: Option<orexis_http::driver::Http>,
    #[cfg(feature = "telegram")]
    pub telegram: Option<orexis_telegram::driver::Telegram>,
    #[cfg(feature = "email")]
    pub email: Option<orexis_email::driver::Email>,
    #[cfg(feature = "translation")]
    pub model: Option<Arc<dyn orexis_translation::model::Model>>,
    #[cfg(feature = "mqtt")]
    pub mqtt: Option<orexis_mqtt::driver::Mqtt<'a>>,
    #[cfg(not(feature = "mqtt"))]
    pub mqtt: Option<std::marker::PhantomData<&'a ()>>,
}

/// The parts an agent runs, each named by its package, in the order a pass runs them.
pub type Parts<'a> = Vec<(String, Box<dyn Part + 'a>)>;

/// The parts of the packages `loaded` names, made, linked and in the order a pass runs them: belief, so its rules
/// have concluded of a graph written before anything else hears it, then planning, then execution walking what it
/// adopted, then sensing, prediction, speech and coordination, and the transport last. `budget` sizes planning's search where a caller states one; none reads the
/// agent's stance.
pub fn assemble<'a>(
    store: &'a Store,
    agent: &str,
    clock: Arc<dyn Clock>,
    loaded: &[String],
    budget: Option<usize>,
) -> Result<Parts<'a>, Error> {
    assemble_wired(store, agent, clock, loaded, budget, Wiring::default())
}

/// `assemble`, over the bus `wiring` hands — a test's — where it hands one.
pub fn assemble_wired<'a>(
    store: &'a Store,
    agent: &str,
    clock: Arc<dyn Clock>,
    loaded: &[String],
    budget: Option<usize>,
    wiring: Wiring<'a>,
) -> Result<Parts<'a>, Error> {
    Ok(assemble_seen(store, agent, clock, loaded, budget, wiring)?.0)
}

/// What a test reads of the parts once they are lent to the runtime: the planner and the executor they share, and the
/// watch every part says its events to, which the runtime is handed too.
#[derive(Default)]
pub struct Seen<'a> {
    pub watch: Watch,
    #[cfg(feature = "planning")]
    pub planner: Option<std::rc::Rc<std::cell::RefCell<orexis_planning::Planner<'a>>>>,
    #[cfg(feature = "execution")]
    pub executor: Option<std::rc::Rc<std::cell::RefCell<orexis_execution::Executor<'a>>>>,
    #[cfg(not(any(feature = "planning", feature = "execution")))]
    pub none: Option<std::marker::PhantomData<&'a ()>>,
}

/// `assemble_wired`, and what a test reads of the parts.
pub fn assemble_seen<'a>(
    store: &'a Store,
    agent: &str,
    clock: Arc<dyn Clock>,
    loaded: &[String],
    budget: Option<usize>,
    wiring: Wiring<'a>,
) -> Result<(Parts<'a>, Seen<'a>), Error> {
    #[allow(unused_mut)]
    let mut seen = Seen::default();
    let mut parts: Parts<'a> = Vec::new();
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
    let mut watchers: Parts<'a> = Vec::new();
    if watching.journal.is_some() || watching.history.is_some() {
        let incidents = orexis_history::incidents(store)?;
        let history = orexis_history::History::new(&watch, watching.history, watching.journal, incidents);
        watchers.push(("history".into(), Box::new(history)));
    }
    if let Some(window) = watching.metrics {
        watchers.push(("metrics".into(), Box::new(orexis_metrics::Metrics::new(window, &watch))));
    }
    if let Some(endpoint) = &watching.traces {
        orexis_spans::connect(&watch, agent, orexis_spans::post(endpoint));
    }
    let holds = |package: &str| loaded.iter().any(|p| p == package);
    #[cfg(feature = "belief")]
    let belief = if holds("belief") {
        Some(orexis_belief::create::Belief::new(store, agent)?)
    } else {
        None
    };
    #[cfg(feature = "planning")]
    let planning = if holds("planning") {
        Some(orexis_planning::create::Planning::new(store, agent, budget)?)
    } else {
        None
    };
    #[cfg(feature = "execution")]
    let execution = if holds("execution") {
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
    if let (Some(planning), Some(prediction)) = (planning.as_ref(), prediction.as_ref()) {
        foresee(planning, prediction);
    }
    #[cfg(feature = "mqtt")]
    #[allow(unused_mut)]
    let mut transport = if holds("transport/mqtt") {
        let member = match wiring.mqtt {
            Some(member) => member,
            None => {
                let me = orexis::boot::selves(store)?.into_iter().next().unwrap_or_default();
                orexis_mqtt::driver::connect(store, &me, &|name| std::env::var(name).ok())?
            }
        };
        Some(orexis_mqtt::create::Transport::new(member))
    } else {
        None
    };
    #[cfg(not(feature = "mqtt"))]
    let _ = wiring;
    let me = orexis::boot::selves(store)?.into_iter().next().unwrap_or_default();
    #[cfg(feature = "speech")]
    let speech = holds("speech").then(|| orexis_speech::create::Speech::new(store, &me));
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
        let member = http.unwrap_or_else(|| orexis_http::driver::Http::new(store, &me, orexis_http::driver::get()));
        Some(orexis_http::create::Transport::new(member))
    } else {
        None
    };
    #[cfg(feature = "telegram")]
    let bot = if holds("transport/telegram") {
        let member = match telegram {
            Some(member) => member,
            None => orexis_telegram::driver::Telegram::connect(store, &me, &|n| std::env::var(n).ok())?,
        };
        Some(orexis_telegram::create::Transport::new(member))
    } else {
        None
    };
    #[cfg(feature = "email")]
    let mailbox = if holds("transport/email") {
        let member = match email {
            Some(member) => member,
            None => orexis_email::driver::Email::connect(store, &me, &|n| std::env::var(n).ok())?,
        };
        Some(orexis_email::create::Transport::new(member))
    } else {
        None
    };
    #[cfg(feature = "execution")]
    if let Some(execution) = execution.as_ref() {
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
    if let (Some(planning), Some(execution)) = (planning.as_ref(), execution.as_ref()) {
        judge(planning, execution);
    }
    #[cfg(feature = "belief")]
    if let Some(belief) = belief.as_ref() {
        belief.deliberator.borrow_mut().watch = watch.clone();
    }
    #[cfg(feature = "planning")]
    if let Some(planning) = planning.as_ref() {
        planning.planner.borrow_mut().watch = watch.clone();
    }
    #[cfg(feature = "execution")]
    if let Some(execution) = execution.as_ref() {
        execution.executor.borrow_mut().watch = watch.clone();
    }
    #[cfg(feature = "sensing")]
    if let Some(sensing) = sensing.as_mut() {
        sensing.watch = watch.clone();
    }
    #[cfg(feature = "speech")]
    if let Some(speech) = speech.as_ref() {
        *speech.speaker.watch.borrow_mut() = watch.clone();
    }
    #[cfg(feature = "coordination")]
    if let Some(coordination) = coordination.as_mut() {
        coordination.watch = watch.clone();
    }
    #[cfg(feature = "planning")]
    {
        seen.planner = planning.as_ref().map(|p| p.planner.clone());
    }
    #[cfg(feature = "execution")]
    {
        seen.executor = execution.as_ref().map(|e| e.executor.clone());
    }
    #[cfg(feature = "belief")]
    if let Some(belief) = belief {
        parts.push(("belief".into(), Box::new(belief)));
    }
    #[cfg(feature = "planning")]
    if let Some(planning) = planning {
        parts.push(("planning".into(), Box::new(planning)));
    }
    #[cfg(feature = "execution")]
    if let Some(execution) = execution {
        parts.push(("execution".into(), Box::new(execution)));
    }
    #[cfg(feature = "sensing")]
    if let Some(sensing) = sensing {
        parts.push(("sensing".into(), Box::new(sensing)));
    }
    #[cfg(feature = "prediction")]
    if let Some(prediction) = prediction {
        parts.push(("prediction".into(), Box::new(prediction)));
    }
    #[cfg(feature = "speech")]
    if let Some(speech) = speech {
        parts.push(("speech".into(), Box::new(speech)));
    }
    #[cfg(feature = "translation")]
    if let Some(translation) = translation {
        parts.push(("translation".into(), Box::new(translation)));
    }
    #[cfg(feature = "coordination")]
    if let Some(coordination) = coordination {
        parts.push(("coordination".into(), Box::new(coordination)));
    }
    #[cfg(feature = "mqtt")]
    if let Some(transport) = transport {
        parts.push(("transport/mqtt".into(), Box::new(transport)));
    }
    #[cfg(feature = "http")]
    if let Some(web) = web {
        parts.push(("transport/http".into(), Box::new(web)));
    }
    #[cfg(feature = "telegram")]
    if let Some(bot) = bot {
        parts.push(("transport/telegram".into(), Box::new(bot)));
    }
    #[cfg(feature = "email")]
    if let Some(mailbox) = mailbox {
        parts.push(("transport/email".into(), Box::new(mailbox)));
    }
    //  WHAT WATCHES THE AGENT, last, so it is stopped first and writes the last window.
    parts.extend(watchers);
    let _ = (store, agent, &clock, budget, holds);
    Ok((parts, seen))
}
