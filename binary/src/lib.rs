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
}

/// Link planning's part to execution's, as the Python parts' `link` connects their signals: what a pass reached
/// ends the unbegun intentions pursuing it, what it reconsidered ends after its step in flight, and what it
/// published is adopted, in the order the Python Planner says them; and a head about to be taken is asked of the
/// Planner, which says where the present no longer admits it (#916). Whatever walks what planning publishes makes
/// it hold the agent while something is walked.
#[cfg(all(feature = "planning", feature = "execution"))]
pub fn link<'a>(
    planning: &mut orexis_planning::create::Planning<'a>,
    execution: &orexis_execution::create::Execution<'a>,
) {
    planning.walked = true;
    let executor = execution.executor.clone();
    planning.heard = Some(Box::new(move |planner| {
        let mut executor = executor.borrow_mut();
        let mut written = Vec::new();
        for published in &planner.published {
            if let Some(desire) = &published.desire {
                executor.desires.insert(published.want.clone(), desire.clone());
            }
        }
        for want in &planner.reached {
            written.extend(executor.end_for(want, "reached")?);
        }
        for replaced in &planner.superseded {
            written.extend(executor.supersede_after(&replaced.head, Some(&replaced.by))?);
        }
        for (plan, want) in &planner.handed {
            written.extend(executor.adopt(plan, want)?);
        }
        Ok(written)
    }));
    let planner = planning.planner.clone();
    execution.executor.borrow_mut().taking = Some(Box::new(move |step, at| planner.borrow_mut().check(step, at)));
}

/// Link execution's part to belief's, as the Python executor's `on_write` tells the runtime and execution hears the
/// deliberator's `revised`: every graph the executor writes as the world is revised as it is written, before its
/// walk goes on, and a pass that revised the present queues a walk, since the world may have answered a step.
#[cfg(all(feature = "belief", feature = "execution"))]
pub fn hear<'a>(
    store: &'a Store,
    belief: &orexis_belief::create::Belief<'a>,
    execution: &orexis_execution::create::Execution<'a>,
) {
    execution.executor.borrow_mut().on_write = Some(Box::new(belief.hears()));
    let soon = execution.soon.clone();
    belief.deliberator.borrow_mut().revised = Some(Box::new(move |revised| {
        if orexis_execution::create::present(store, &revised.graphs, &revised.changed)? {
            soon.set(true);
        }
        Ok(())
    }));
}

/// Link sensing's part to belief's, as the Python part's `link` takes belief's: every percept sensing writes, and at
/// start each one nothing was concluded of, is revised by belief's deliberator into sensing's own kind (#944).
#[cfg(all(feature = "belief", feature = "sensing"))]
pub fn observe<'a>(belief: &orexis_belief::create::Belief<'a>, sensing: &mut orexis_sensing::create::Sensing<'a>) {
    let belief = belief.clone();
    sensing.revise = Some(Box::new(move |graphs, kind, at| belief.revise(graphs, kind, at)));
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

/// Link execution's part to whoever carries a step out, as the Python executor's `commanded` is connected to every
/// transport and its `said` to speech: a step's implementation is taken order by order, each command sized from the
/// present and sent where the member reaches the actuator, and each document it says kept by speech and told — the
/// statements speech kept handed on with what the executor wrote.
#[cfg(feature = "execution")]
pub fn take<'a>(
    store: &'a Store,
    clock: &'a dyn Clock,
    execution: &orexis_execution::create::Execution<'a>,
    send: Option<orexis_execution::create::Commands<'a>>,
    say: Option<orexis_execution::create::Sayings<'a>>,
) {
    if send.is_some() || say.is_some() {
        execution.executor.borrow_mut().take = Some(orexis_execution::create::taker(store, clock, send, say));
    }
}

/// WHAT WATCHES THE AGENT, where the deployment keeps any of it: the journal, the history sink and the metrics window.
/// The history part is made where a journal is kept or a history sink is loaded, and the metrics part where a metrics
/// window is, as the Python runtime makes its watchers; each hears every event the parts say.
#[derive(Default)]
pub struct Watching {
    pub journal: Option<Arc<Journal>>,
    pub history: Option<Sink>,
    pub metrics: Option<orexis_metrics::Window>,
}

/// What the agent's bus is, where a test hands one: the MQTT member over a client of its own. None, and a member the
/// agent loads is brought up from the environment. And what watches it.
#[derive(Default)]
pub struct Wiring<'a> {
    pub watching: Watching,
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
    clock: &'a dyn Clock,
    loaded: &[String],
    budget: Option<usize>,
) -> Result<Parts<'a>, Error> {
    assemble_wired(store, agent, clock, loaded, budget, Wiring::default())
}

/// `assemble`, over the bus `wiring` hands — a test's — where it hands one.
pub fn assemble_wired<'a>(
    store: &'a Store,
    agent: &str,
    clock: &'a dyn Clock,
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
    clock: &'a dyn Clock,
    loaded: &[String],
    budget: Option<usize>,
    wiring: Wiring<'a>,
) -> Result<(Parts<'a>, Seen<'a>), Error> {
    #[allow(unused_mut)]
    let mut seen = Seen::default();
    let mut parts: Parts<'a> = Vec::new();
    let Wiring { watching, mqtt } = wiring;
    let wiring = Wiring {
        watching: Watching::default(),
        mqtt,
    };
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
    let holds = |package: &str| loaded.iter().any(|p| p == package);
    #[cfg(feature = "belief")]
    let belief = if holds("belief") {
        Some(orexis_belief::create::Belief::new(store, agent)?)
    } else {
        None
    };
    #[cfg(feature = "planning")]
    let mut planning = if holds("planning") {
        Some(orexis_planning::create::Planning::new(store, agent, budget)?)
    } else {
        None
    };
    #[cfg(feature = "execution")]
    let execution = if holds("execution") {
        Some(orexis_execution::create::Execution::new(store, agent, clock)?)
    } else {
        None
    };
    #[cfg(feature = "sensing")]
    let mut sensing = if holds("sensing") {
        Some(orexis_sensing::create::Sensing::new(store, agent)?)
    } else {
        None
    };
    #[cfg(all(feature = "belief", feature = "sensing"))]
    if let (Some(belief), Some(sensing)) = (belief.as_ref(), sensing.as_mut()) {
        observe(belief, sensing);
    }
    #[cfg(feature = "prediction")]
    let prediction = holds("prediction").then(orexis_prediction::create::Prediction::default);
    #[cfg(all(feature = "planning", feature = "prediction"))]
    if let (Some(planning), Some(prediction)) = (planning.as_ref(), prediction.as_ref()) {
        foresee(planning, prediction);
    }
    #[cfg(feature = "mqtt")]
    let transport = if holds("transport/mqtt") {
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
    #[cfg(all(feature = "speech", feature = "mqtt"))]
    if let (Some(speech), Some(transport)) = (speech.as_ref(), transport.as_ref()) {
        let member = transport.member.clone();
        *speech.speaker.tell.borrow_mut() = Some(Box::new(move |to, document| {
            member.borrow_mut().tell(to, document).map(|_| ())
        }));
    }
    #[cfg(all(feature = "speech", feature = "coordination"))]
    if let (Some(speech), Some(coordination)) = (speech.as_ref(), coordination.as_mut()) {
        let speaker = speech.speaker.clone();
        coordination.say = Some(Box::new(move |peer, document| {
            speaker.say(document, &[peer.to_string()])
        }));
    }
    #[cfg(all(feature = "planning", feature = "coordination"))]
    if let (Some(planning), Some(coordination)) = (planning.as_ref(), coordination.as_mut()) {
        let planner = planning.planner.clone();
        coordination.reopen = Some(Box::new(move |wants| planner.borrow_mut().reopen(wants)));
    }
    #[cfg(feature = "execution")]
    if let Some(execution) = execution.as_ref() {
        #[allow(unused_mut)]
        let mut send: Option<orexis_execution::create::Commands<'a>> = None;
        #[allow(unused_mut)]
        let mut say: Option<orexis_execution::create::Sayings<'a>> = None;
        #[cfg(feature = "mqtt")]
        if let Some(transport) = transport.as_ref() {
            let member = transport.member.clone();
            send = Some(Box::new(move |actuator, payload| {
                member.borrow_mut().command(actuator, payload)
            }));
        }
        #[cfg(feature = "speech")]
        if let Some(speech) = speech.as_ref() {
            let (speaker, said) = (speech.speaker.clone(), execution.said.clone());
            say = Some(Box::new(move |agents, document| {
                let kept = speaker.say(document, agents)?;
                said.borrow_mut().extend(kept);
                Ok(())
            }));
        }
        take(store, clock, execution, send, say);
    }
    #[cfg(all(feature = "planning", feature = "execution"))]
    if let (Some(planning), Some(execution)) = (planning.as_mut(), execution.as_ref()) {
        link(planning, execution);
    }
    #[cfg(all(feature = "belief", feature = "execution"))]
    if let (Some(belief), Some(execution)) = (belief.as_ref(), execution.as_ref()) {
        hear(store, belief, execution);
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
    #[cfg(feature = "coordination")]
    if let Some(coordination) = coordination {
        parts.push(("coordination".into(), Box::new(coordination)));
    }
    #[cfg(feature = "mqtt")]
    if let Some(transport) = transport {
        parts.push(("transport/mqtt".into(), Box::new(transport)));
    }
    //  WHAT WATCHES THE AGENT, last, so it is stopped first and writes the last window.
    parts.extend(watchers);
    let _ = (store, agent, clock, budget, holds);
    Ok((parts, seen))
}
