//! THE RUNTIME: one agent's body, a Tokio runtime its packages' parts run on, each part a task of its own
//! (the-agent-is-a-runtime-of-tasks). A part is started, asks for what it waits for - a timer, `every` so many seconds
//! of the one timeline, a kind of graph written, an event's class - and its task runs it when that comes. The run ends
//! when nothing holds the agent, as the last to let go said: `met`, `planned` or `unreachable`; or when the passes ran
//! out, `unfinished`.
//!
//! A PART HEARS A KIND OF GRAPH WRITTEN (`on`): every graph a job answers it wrote is sent to each part listening for a
//! kind the catalogue says it is, and what that part writes in turn is sent the same way. A PART HEARS AN EVENT BY ITS
//! CLASS (`hears`), the class and every class the vocabulary puts beneath it, in the order its sayer said them; and A
//! PART BEGINS AND ENDS AN ACTIVITY, saying its start and its end (packages-meet-by-events-policies-and-activities). A
//! PART QUEUES A JOB (`submitted`), run by its own task after the message that queued it.
//!
//! RUN FREE (`run(None, …)`), each task waits for a message - an event, a graph, an arrival its `Wake` rang - or for
//! the soonest instant it is due, a timer or what it said by `wake_at`, at the clock's pace; it handles what came, then
//! runs its due timers, its policy among them. The parts run on the runtime's workers at once, and a graph has one
//! writing package, so no two meet on it.
//!
//! RUN BY PASSES (`run(Some(n), …)`, `drain`), what a test does, the runtime ticks each part in turn, in the order the
//! parts were handed, and waits until nothing is busy before ticking the next: a part's policy runs after everything
//! the parts before it said has been heard, as one ordered pass ran them, so a test proves one order. Between passes it
//! waits for an arrival or the soonest instant anything is due, never longer than the longest it is told, nought in a
//! test that sets its clock itself.

use std::collections::{BTreeMap, HashMap};
use std::future::Future;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use oxsdatatypes::DateTime;

use oxigraph::model::{NamedNode, Term};
use tokio::sync::mpsc::{UnboundedReceiver, UnboundedSender, unbounded_channel};
use tokio::sync::{Notify, watch};

use crate::Error;
use crate::activity::{Activity, Ended, Started};
use crate::clock::{Clock, seconds};
use crate::events::{Event, Laps, Mark, Number, Watch, round6};
use crate::store::Store;

pub const MET: &str = "met";
pub const PLANNED: &str = "planned";
pub const UNREACHABLE: &str = "unreachable";
pub const UNFINISHED: &str = "unfinished";

pub const PASS_METRIC: &str = "pass";

/// A pass, or a stretch of the run with something busy, and how long it took: by part, where a part marked laps.
#[derive(Clone, Debug, PartialEq)]
pub struct Passed {
    pub duration_s: f64,
    pub laps: Vec<(String, f64)>,
    pub quads: Option<i64>,
    pub uptime_s: f64,
}

impl Event for Passed {
    fn metric(&self) -> Option<&'static str> {
        Some(PASS_METRIC)
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        let lap = |part: &str| self.laps.iter().find(|(n, _)| n == part).map(|(_, s)| *s);
        vec![
            ("duration_s", Mark::Value(Some(self.duration_s))),
            ("drain_s", Mark::Value(lap("drain_s"))),
            ("plan_s", Mark::Value(lap("plan_s"))),
            ("execute_s", Mark::Value(lap("execute_s"))),
            ("quads", Mark::Level(self.quads.map(Number::Int))),
            ("uptime_s", Mark::Level(Some(Number::Float(self.uptime_s)))),
        ]
    }
}

fn started() -> std::time::Instant {
    static STARTED: std::sync::OnceLock<std::time::Instant> = std::sync::OnceLock::new();
    *STARTED.get_or_init(std::time::Instant::now)
}

thread_local! {
    /// THE EVENTS A PART SAID DURING THE CALL IN PROGRESS on this thread, sent once the call returned and its graphs
    /// were told: a part's graphs are heard before its events, as one queue told them.
    static SAID: std::cell::RefCell<Option<Vec<Heard>>> = const { std::cell::RefCell::new(None) };
}

/// Run `call`, holding back what it says until it returns.
fn holding<T>(call: impl FnOnce() -> T) -> (T, Vec<Heard>) {
    let outer = SAID.with(|said| said.borrow_mut().replace(Vec::new()));
    let out = call();
    let said = SAID
        .with(|said| std::mem::replace(&mut *said.borrow_mut(), outer))
        .unwrap_or_default();
    (out, said)
}

/// What a part's task is sent.
enum Message {
    /// Run the due timers at the instant a pass stands at.
    Tick(DateTime),
    /// Something arrived for the part, which it says it `submitted`.
    Arrived,
    Graph(usize, String),
    Event(usize, Heard),
    /// Wait for itself from now on: run free.
    Free,
    Stop,
}

/// HOW MANY MESSAGES ARE SENT AND NOT YET HANDLED, across every part: nought is idle.
#[derive(Clone)]
struct Busy(Arc<watch::Sender<usize>>);

impl Busy {
    fn new() -> Self {
        Busy(Arc::new(watch::channel(0).0))
    }

    fn up(&self) {
        self.0.send_modify(|n| *n += 1);
    }

    fn down(&self) {
        self.0.send_modify(|n| *n = n.saturating_sub(1));
    }

    async fn idle(&self) {
        let mut rx = self.0.subscribe();
        let _ = rx.wait_for(|n| *n == 0).await;
    }

    async fn active(&self) {
        let mut rx = self.0.subscribe();
        let _ = rx.wait_for(|n| *n > 0).await;
    }
}

/// What ends a part's wait - or the run's, for whoever stops it from outside - when something arrived.
#[derive(Clone, Default)]
pub struct Wake {
    to: Option<(UnboundedSender<Message>, Busy)>,
    halt: Option<Arc<Notify>>,
}

impl Wake {
    /// Something arrived.
    pub fn ring(&self) {
        if let Some((to, busy)) = &self.to {
            busy.up();
            if to.send(Message::Arrived).is_err() {
                busy.down();
            }
        }
        if let Some(halt) = &self.halt {
            halt.notify_one();
        }
    }
}

/// What a part asks for as it starts.
pub struct Starting<'c> {
    timers: Vec<(f64, usize)>,
    hears: Vec<(String, usize)>,
    events: Vec<(String, usize)>,
    clock: &'c dyn Clock,
    wake: &'c Wake,
    tasks: &'c tokio::runtime::Handle,
}

impl Starting<'_> {
    /// The instant the part starts at, read off the one timeline - a tick in a test, so read only where needed.
    pub fn now(&self) -> DateTime {
        self.clock.now()
    }

    /// Run the part's `job` for every graph of `kind` written, handed the graph (`Part::heard`).
    pub fn on(&mut self, kind: &str, job: usize) {
        self.hears.push((kind.to_string(), job));
    }

    /// Run the part's `job` for every event of `class` said, or of a class the vocabulary puts beneath it, handed the
    /// event (`Part::heard_event`).
    pub fn hears(&mut self, class: &str, job: usize) {
        self.events.push((class.to_string(), job));
    }

    /// Run the part's `job` at the first pass and again every `seconds` of the one timeline after - at every pass, and
    /// after whatever the part handled, where `seconds` is nought.
    pub fn every(&mut self, seconds: f64, job: usize) {
        self.timers.push((seconds, job));
    }

    /// What ends the part's wait, for whatever hands it an arrival.
    pub fn wake(&self) -> Wake {
        self.wake.clone()
    }

    /// Run `work` among the process's tasks, from now until it ends or the process does. It waits on the outside and
    /// hands the part what arrived: it holds no part and writes no belief.
    pub fn task(&mut self, work: impl Future<Output = ()> + Send + 'static) -> Result<(), Error> {
        self.tasks.spawn(work);
        Ok(())
    }
}

/// WHAT EVERY PART'S TASK SHARES: the store, the clock, who holds the agent, where each part is sent to and what it
/// listens for.
struct Shared {
    beliefs: Store,
    id: String,
    clock: Arc<dyn Clock>,
    held: Mutex<BTreeMap<String, ()>>,
    outcome: Mutex<Option<String>>,
    /// (part, kind, job): who hears a kind of graph written.
    hears: Vec<(usize, String, usize)>,
    /// (part, class, job): who hears an event of a class.
    listens: Vec<(usize, String, usize)>,
    /// Every class each class said is beneath, asked once.
    closed: Mutex<HashMap<String, Vec<String>>>,
    senders: Vec<UnboundedSender<Message>>,
    busy: Busy,
    watch: Watch,
    laps: Mutex<Option<Laps>>,
    /// Run by passes: the runtime ticks the parts and waits between passes; free, each task waits for itself.
    free: AtomicBool,
    /// By passes, while the parts are ticked: what a part queues waits for the end of the pass, as a queue ran it.
    ticking: AtomicBool,
    again: AtomicBool,
    /// The instant the pass in progress stands at, by passes: what every message is handled at, so nothing reads the
    /// clock for it.
    at: Mutex<Option<DateTime>>,
    /// The soonest instant a part said it is next due, or a timer falls due, this pass.
    soonest: Mutex<Option<DateTime>>,
    /// What the parts wrote since the pass began.
    written: Mutex<Vec<String>>,
    error: Mutex<Option<Error>>,
}

impl Shared {
    fn send(&self, part: usize, message: Message) {
        self.busy.up();
        if self.senders[part].send(message).is_err() {
            self.busy.down();
        }
    }

    fn sooner(&self, at: DateTime) {
        let mut soonest = self.soonest.lock().expect("a soonest nobody poisoned");
        if soonest.is_none_or(|s| at < s) {
            *soonest = Some(at);
        }
    }

    fn failed(&self, error: Error) {
        let mut kept = self.error.lock().expect("an error nobody poisoned");
        if kept.is_none() {
            *kept = Some(error);
        }
    }

    /// Say that `graphs` were written, to every part listening for a kind the catalogue says each is.
    fn wrote(&self, graphs: Vec<String>) -> Result<(), Error> {
        for graph in graphs {
            if !self.hears.is_empty() {
                let kinds = self.kinds(&graph)?;
                for (part, kind, job) in &self.hears {
                    if kinds.contains(kind) {
                        self.send(*part, Message::Graph(*job, graph.clone()));
                    }
                }
            }
            self.written.lock().expect("a list nobody poisoned").push(graph);
        }
        Ok(())
    }

    /// Every kind the catalogue says `graph` is.
    fn kinds(&self, graph: &str) -> Result<Vec<String>, Error> {
        let Some(cat) = self.beliefs.catalogue()? else {
            return Ok(Vec::new());
        };
        let text = crate::bind::bind(
            "SELECT ?k WHERE { GRAPH $cat { $g a ?k } }",
            &[
                ("cat", crate::bind::Value::iri(cat)),
                ("g", crate::bind::Value::iri(graph)),
            ],
        )?;
        Ok(self
            .beliefs
            .rows(&text, &[])?
            .iter()
            .filter_map(|r| crate::store::iri(r, "k"))
            .collect())
    }

    /// Send `event` to every part hearing a class it is beneath.
    fn tell(&self, event: Heard) {
        let classes = {
            let mut closed = self.closed.lock().expect("a closure nobody poisoned");
            if !closed.contains_key(&event.kind) {
                match self.beliefs.closed(&event.kind) {
                    Ok(c) => {
                        closed.insert(event.kind.clone(), c);
                    }
                    Err(e) => {
                        drop(closed);
                        self.failed(e);
                        return;
                    }
                }
            }
            closed[&event.kind].clone()
        };
        for (part, class, job) in &self.listens {
            if classes.contains(class) {
                self.send(*part, Message::Event(*job, event.clone()));
            }
        }
    }
}

/// What a part is handed when it runs: the instant it stands at, and the agent's life to keep or let go.
pub struct Pass<'r> {
    pub now: DateTime,
    pub agent: &'r str,
    shared: &'r Shared,
    soonest: &'r mut Option<DateTime>,
}

impl Pass<'_> {
    /// The part is next due at `at`, with nothing heard: its task waits no longer than that.
    pub fn wake_at(&mut self, at: DateTime) {
        if self.soonest.is_none_or(|s| at < s) {
            *self.soonest = Some(at);
        }
    }

    /// Begin an activity of `kind`, triggered by the entities `triggers` names - what the events heard were about -
    /// and say that it started.
    pub fn begin(&mut self, kind: &'static str, triggers: &[NamedNode]) -> Activity {
        let activity = Activity::begin(kind);
        if self.shared.watch.connected() {
            self.shared.watch.emit(&Started {
                activity: activity.node.clone(),
                kind,
                triggers: triggers.to_vec(),
                at: self.now,
            });
        }
        activity
    }

    /// Say `event` happened, to whoever watches the agent.
    pub fn emit(&self, event: &dyn crate::events::Event) {
        self.shared.watch.emit(event);
    }

    /// End `activity`, and say that it ended.
    pub fn end(&mut self, activity: Activity) {
        if self.shared.watch.connected() {
            self.shared.watch.emit(&Ended {
                activity: activity.node.clone(),
                kind: activity.kind,
                at: self.now,
                duration_s: activity.took(),
            });
        }
    }

    /// Mark the end of a part of the pass, for the pass's event, where anybody watches.
    pub fn lap(&mut self, part: &str) {
        if let Some(laps) = self.shared.laps.lock().expect("laps nobody poisoned").as_mut() {
            laps.lap(part);
        }
    }

    /// `who` keeps the agent running.
    pub fn hold(&mut self, who: &str) {
        self.shared
            .held
            .lock()
            .expect("holders nobody poisoned")
            .insert(who.to_string(), ());
    }

    /// `who` no longer keeps the agent running, and says how its part ended.
    pub fn release(&mut self, who: &str, outcome: Option<&str>) {
        self.shared.held.lock().expect("holders nobody poisoned").remove(who);
        if let Some(outcome) = outcome {
            *self.shared.outcome.lock().expect("an outcome nobody poisoned") = Some(outcome.to_string());
        }
    }

    /// Run the parts' timers once more at once: by passes, the next pass without waiting; free, every part now.
    pub fn again(&mut self) {
        self.shared.again.store(true, Ordering::SeqCst);
    }
}

/// A package's part: started once, run by its own task when what it asked for comes, stopped at the end, the last
/// first.
pub trait Part: Send {
    fn start(&mut self, _starting: &mut Starting) -> Result<(), Error> {
        Ok(())
    }

    /// Run `job` at the pass; the graphs written.
    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error>;

    /// Run `job` for `graph`, written and of a kind the part listens for; the graphs written in turn.
    fn heard(&mut self, _job: usize, _graph: &str, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        Ok(Vec::new())
    }

    /// Run `job` for `event`, said and of a class the part hears; the graphs written in turn.
    fn heard_event(&mut self, _job: usize, _event: &Heard, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        Ok(Vec::new())
    }

    /// The jobs the part queued since it was last asked, to run after the message that queued them.
    fn submitted(&mut self) -> Vec<usize> {
        Vec::new()
    }

    /// The watch the part says its events to, where it says any: the runtime listens on that one, so what a part says
    /// is heard by the parts that listen whoever assembled them.
    fn watch(&self) -> Option<Watch> {
        None
    }

    fn stop(&mut self) {}
}

/// An event as a part hears it: the name it was said under, its class, and the activity it starts or ends.
#[derive(Clone, Debug, PartialEq)]
pub struct Heard {
    pub node: NamedNode,
    pub kind: String,
    pub activity: Option<(NamedNode, String)>,
    /// What it is about, each under the predicate that says its part (`Event::about`).
    pub about: Vec<(String, Term)>,
}

impl Heard {
    /// The first thing it is about under `predicate`, where it names a node there.
    pub fn named(&self, predicate: &str) -> Option<&NamedNode> {
        self.about.iter().find_map(|(p, t)| match t {
            Term::NamedNode(n) if p == predicate => Some(n),
            _ => None,
        })
    }

    /// Every node it is about under `predicate`, in the order said.
    pub fn all(&self, predicate: &str) -> Vec<&NamedNode> {
        self.about
            .iter()
            .filter_map(|(p, t)| match t {
                Term::NamedNode(n) if p == predicate => Some(n),
                _ => None,
            })
            .collect()
    }
}

/// A PART LENT, for whoever keeps it between runs and reads or changes it in between - a test: the runtime runs it
/// through the handle, as it runs a part it owns.
pub struct Lent<P>(pub Arc<Mutex<P>>);

impl<P: Part> Lent<P> {
    pub fn of(part: &Arc<Mutex<P>>) -> Box<dyn Part>
    where
        P: 'static,
    {
        Box::new(Lent(part.clone()))
    }
}

impl<P: Part> Part for Lent<P> {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        self.0.lock().expect("a part nobody poisoned").start(starting)
    }
    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        self.0.lock().expect("a part nobody poisoned").run(job, pass)
    }
    fn heard(&mut self, job: usize, graph: &str, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        self.0.lock().expect("a part nobody poisoned").heard(job, graph, pass)
    }
    fn heard_event(&mut self, job: usize, event: &Heard, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        self.0
            .lock()
            .expect("a part nobody poisoned")
            .heard_event(job, event, pass)
    }
    fn submitted(&mut self) -> Vec<usize> {
        self.0.lock().expect("a part nobody poisoned").submitted()
    }
    fn watch(&self) -> Option<Watch> {
        self.0.lock().expect("a part nobody poisoned").watch()
    }
    fn stop(&mut self) {
        self.0.lock().expect("a part nobody poisoned").stop()
    }
}

struct Timer {
    seconds: f64,
    due: Option<DateTime>,
    job: usize,
}

/// ONE PART'S TASK: the part, its timers, and when it said it is next due.
struct Running {
    part: Box<dyn Part>,
    timers: Vec<Timer>,
    soonest: Option<DateTime>,
}

impl Running {
    fn pass<'r>(&'r mut self, shared: &'r Shared, now: DateTime) -> (&'r mut Box<dyn Part>, Pass<'r>) {
        (
            &mut self.part,
            Pass {
                now,
                agent: &shared.id,
                shared,
                soonest: &mut self.soonest,
            },
        )
    }

    /// Run `job`, then whatever the part queued, and say what each wrote.
    fn job(&mut self, shared: &Shared, job: usize, now: DateTime) -> Result<(), Error> {
        self.call(shared, now, |part, pass| part.run(job, pass))?;
        self.submitted(shared, now)
    }

    /// One call of the part: the graphs it wrote told, then the events it said.
    fn call(
        &mut self,
        shared: &Shared,
        now: DateTime,
        call: impl FnOnce(&mut Box<dyn Part>, &mut Pass<'_>) -> Result<Vec<String>, Error>,
    ) -> Result<(), Error> {
        let (wrote, said) = holding(|| {
            let (part, mut pass) = self.pass(shared, now);
            call(part, &mut pass)
        });
        let told = wrote.and_then(|wrote| shared.wrote(wrote));
        for heard in said {
            shared.tell(heard);
        }
        told
    }

    fn submitted(&mut self, shared: &Shared, now: DateTime) -> Result<(), Error> {
        //  BY PASSES, WHAT A PART QUEUES WHILE THE PARTS ARE TICKED runs once every part was: the end of the pass.
        if shared.ticking.load(Ordering::SeqCst) {
            return Ok(());
        }
        loop {
            let jobs = self.part.submitted();
            if jobs.is_empty() {
                return Ok(());
            }
            for job in jobs {
                self.call(shared, now, |part, pass| part.run(job, pass))?;
            }
        }
    }

    /// Run every timer due at `now`, each set due again `seconds` on.
    fn tick(&mut self, shared: &Shared, now: DateTime) -> Result<(), Error> {
        self.submitted(shared, now)?;
        for t in 0..self.timers.len() {
            let timer = &mut self.timers[t];
            if timer.due.is_some_and(|due| now < due) {
                continue;
            }
            timer.due = Some(now.checked_add_day_time_duration(seconds(timer.seconds)).unwrap_or(now));
            let job = timer.job;
            self.job(shared, job, now)?;
        }
        Ok(())
    }

    fn handle(&mut self, shared: &Shared, message: Message) -> Result<bool, Error> {
        let free = shared.free.load(Ordering::SeqCst);
        let at = *shared.at.lock().expect("an instant nobody poisoned");
        let now = match (free, at) {
            (false, Some(at)) => at,
            _ => shared.clock.now(),
        };
        match message {
            Message::Tick(at) => {
                self.soonest = None;
                self.tick(shared, at)?;
                self.report(shared);
                return Ok(true);
            }
            Message::Stop => {
                self.part.stop();
                return Ok(false);
            }
            Message::Free => return Ok(true),
            Message::Arrived => self.submitted(shared, now)?,
            Message::Graph(job, graph) => {
                self.call(shared, now, |part, pass| part.heard(job, &graph, pass))?;
                self.submitted(shared, now)?;
            }
            Message::Event(job, event) => {
                self.call(shared, now, |part, pass| part.heard_event(job, &event, pass))?;
                self.submitted(shared, now)?;
            }
        }
        //  RUN FREE, A PART'S POLICY DECIDES AFTER WHAT IT HANDLED: its timers due, those of nought among them.
        if free {
            self.soonest = None;
            self.tick(shared, now)?;
        }
        self.report(shared);
        Ok(true)
    }

    /// Say when the part is next due, by passes to the runtime.
    fn report(&self, shared: &Shared) {
        if let Some(due) = self.due() {
            shared.sooner(due);
        }
    }

    /// The soonest instant the part is due: what it said, or a timer of more than nought.
    fn due(&self) -> Option<DateTime> {
        self.timers
            .iter()
            .filter(|t| t.seconds > 0.0)
            .filter_map(|t| t.due)
            .chain(self.soonest)
            .reduce(|a, b| if b < a { b } else { a })
    }

    async fn run(mut self, shared: Arc<Shared>, mut inbox: UnboundedReceiver<Message>) {
        loop {
            let wait = if shared.free.load(Ordering::SeqCst) {
                self.due().map(|due| {
                    let ahead = due
                        .checked_sub(shared.clock.now())
                        .map_or(0.0, crate::clock::seconds_of);
                    shared.clock.real_delay(ahead.max(0.0))
                })
            } else {
                None
            };
            let message = match wait {
                Some(wait) => tokio::select! {
                    m = inbox.recv() => m,
                    _ = tokio::time::sleep(wait) => {
                        shared.busy.up();
                        Some(Message::Tick(shared.clock.now()))
                    }
                },
                None => inbox.recv().await,
            };
            let Some(message) = message else { return };
            let going = match self.handle(&shared, message) {
                Ok(going) => going,
                Err(e) => {
                    shared.failed(e);
                    true
                }
            };
            if shared.free.load(Ordering::SeqCst) && shared.again.swap(false, Ordering::SeqCst) {
                let now = shared.clock.now();
                for part in 0..shared.senders.len() {
                    shared.send(part, Message::Tick(now));
                }
            }
            shared.busy.down();
            if !going {
                return;
            }
        }
    }
}

/// One agent's process over its beliefs: its parts, each started, waiting to be run as tasks.
pub struct Runtime {
    pub beliefs: Store,
    pub id: String,
    clock: Arc<dyn Clock>,
    names: Vec<String>,
    /// What the parts were started with, until the first run makes them tasks.
    pending: Option<Pending>,
    shared: Option<Arc<Shared>>,
    joins: Vec<tokio::task::JoinHandle<()>>,
    busy: Busy,
    /// WHOEVER WATCHES THE AGENT, hearing each pass where anybody does: the one the first run finds here.
    pub watch: Watch,
    /// RAISED TO STOP THE RUN, by a signal the process was sent: the run ends before its next pass, `unfinished`, so
    /// whoever runs it stops every part and the last window is written.
    pub halt: Option<Arc<AtomicBool>>,
    halted: Arc<Notify>,
    tasks: tokio::runtime::Runtime,
}

struct Pending {
    running: Vec<Running>,
    inboxes: Vec<UnboundedReceiver<Message>>,
    senders: Vec<UnboundedSender<Message>>,
    hears: Vec<(usize, String, usize)>,
    listens: Vec<(usize, String, usize)>,
}

impl Runtime {
    /// The runtime of `id` over `beliefs`, reading the one timeline off `clock`, its parts each started, on ONE thread:
    /// what a test runs, by passes, so it proves one order.
    pub fn new(
        beliefs: &Store,
        id: &str,
        clock: Arc<dyn Clock>,
        parts: Vec<(String, Box<dyn Part>)>,
    ) -> Result<Self, Error> {
        let tasks = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
        Self::on(tasks, beliefs, id, clock, parts)
    }

    /// The runtime of `id`, its parts each a task on `workers` threads of their own beside the blocking pool: what an
    /// agent runs.
    pub fn threaded(
        workers: usize,
        beliefs: &Store,
        id: &str,
        clock: Arc<dyn Clock>,
        parts: Vec<(String, Box<dyn Part>)>,
    ) -> Result<Self, Error> {
        let tasks = tokio::runtime::Builder::new_multi_thread()
            .worker_threads(workers.max(1))
            .thread_name("orexis-tasks")
            .enable_all()
            .build()
            .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
        Self::on(tasks, beliefs, id, clock, parts)
    }

    fn on(
        tasks: tokio::runtime::Runtime,
        beliefs: &Store,
        id: &str,
        clock: Arc<dyn Clock>,
        parts: Vec<(String, Box<dyn Part>)>,
    ) -> Result<Self, Error> {
        started();
        let busy = Busy::new();
        let mut watch = Watch::default();
        if let Some(found) = parts.iter().find_map(|(_, part)| part.watch()) {
            watch = found;
        }
        let mut pending = Pending {
            running: Vec::new(),
            inboxes: Vec::new(),
            senders: Vec::new(),
            hears: Vec::new(),
            listens: Vec::new(),
        };
        let mut names = Vec::new();
        let handle = tasks.handle().clone();
        for (i, (name, mut part)) in parts.into_iter().enumerate() {
            let (to, inbox) = unbounded_channel();
            let wake = Wake {
                to: Some((to.clone(), busy.clone())),
                halt: None,
            };
            let mut starting = Starting {
                timers: Vec::new(),
                hears: Vec::new(),
                events: Vec::new(),
                clock: clock.as_ref(),
                wake: &wake,
                tasks: &handle,
            };
            part.start(&mut starting)?;
            pending
                .hears
                .extend(starting.hears.into_iter().map(|(kind, job)| (i, kind, job)));
            pending
                .listens
                .extend(starting.events.into_iter().map(|(class, job)| (i, class, job)));
            let timers = starting
                .timers
                .into_iter()
                .map(|(seconds, job)| Timer {
                    seconds,
                    due: None,
                    job,
                })
                .collect();
            pending.running.push(Running {
                part,
                timers,
                soonest: None,
            });
            pending.inboxes.push(inbox);
            pending.senders.push(to);
            names.push(name);
        }
        Ok(Runtime {
            beliefs: beliefs.clone(),
            id: id.to_string(),
            clock,
            names,
            pending: Some(pending),
            shared: None,
            joins: Vec::new(),
            busy,
            watch,
            halt: None,
            halted: Arc::new(Notify::new()),
            tasks,
        })
    }

    /// What ends the run's wait, for whoever stops the run from outside it.
    pub fn wake(&self) -> Wake {
        Wake {
            to: None,
            halt: Some(self.halted.clone()),
        }
    }

    /// The parts it runs, in the order it ticks them.
    pub fn parts(&self) -> Vec<&str> {
        self.names.iter().map(String::as_str).collect()
    }

    /// The parts made tasks, the first time anything runs: the watch found here is the one every task says to, and
    /// what it hears is told to the parts listening.
    fn spawned(&mut self) -> Arc<Shared> {
        if let Some(shared) = &self.shared {
            return shared.clone();
        }
        let pending = self.pending.take().expect("parts pending until they are spawned");
        let shared = Arc::new(Shared {
            beliefs: self.beliefs.clone(),
            id: self.id.clone(),
            clock: self.clock.clone(),
            held: Mutex::new(BTreeMap::new()),
            outcome: Mutex::new(None),
            hears: pending.hears,
            listens: pending.listens,
            closed: Mutex::new(HashMap::new()),
            senders: pending.senders,
            busy: self.busy.clone(),
            watch: self.watch.clone(),
            laps: Mutex::new(None),
            free: AtomicBool::new(false),
            ticking: AtomicBool::new(false),
            again: AtomicBool::new(false),
            at: Mutex::new(None),
            soonest: Mutex::new(None),
            written: Mutex::new(Vec::new()),
            error: Mutex::new(None),
        });
        if !shared.listens.is_empty() {
            let weak = Arc::downgrade(&shared);
            self.watch.connect(move |event, named| {
                if let (Some(kind), Some(shared)) = (event.kind(), weak.upgrade()) {
                    let heard = Heard {
                        node: named.clone(),
                        kind: kind.to_string(),
                        activity: event.activity().map(|(a, k)| (a.clone(), k.to_string())),
                        about: event.about().into_iter().map(|(p, t)| (p.to_string(), t)).collect(),
                    };
                    let held = SAID.with(|said| match said.borrow_mut().as_mut() {
                        Some(held) => {
                            held.push(heard.clone());
                            true
                        }
                        None => false,
                    });
                    if !held {
                        shared.tell(heard);
                    }
                }
            });
        }
        for (running, inbox) in pending.running.into_iter().zip(pending.inboxes) {
            let task = shared.clone();
            self.joins.push(self.tasks.spawn(running.run(task, inbox)));
        }
        self.shared = Some(shared.clone());
        shared
    }

    fn checked(shared: &Shared) -> Result<(), Error> {
        match shared.error.lock().expect("an error nobody poisoned").take() {
            Some(e) => Err(e),
            None => Ok(()),
        }
    }

    /// One pass at `now`: each part ticked in turn, each after nothing is busy. The graphs written.
    pub fn drain(&mut self, now: DateTime) -> Result<Vec<String>, Error> {
        let shared = self.spawned();
        self.watch.stand(now);
        shared.written.lock().expect("a list nobody poisoned").clear();
        let busy = self.busy.clone();
        let parts = shared.senders.len();
        let ticking = shared.clone();
        *shared.at.lock().expect("an instant nobody poisoned") = Some(now);
        self.tasks.block_on(async move {
            busy.idle().await;
            if let Some(laps) = ticking.laps.lock().expect("laps nobody poisoned").as_mut() {
                laps.lap("drain");
            }
            ticking.ticking.store(true, Ordering::SeqCst);
            for part in 0..parts {
                ticking.send(part, Message::Tick(now));
                busy.idle().await;
                if ticking.error.lock().expect("an error nobody poisoned").is_some() {
                    break;
                }
            }
            ticking.ticking.store(false, Ordering::SeqCst);
            //  WHAT THE PARTS QUEUED WHILE TICKED, each part's in turn.
            for part in 0..parts {
                ticking.send(part, Message::Arrived);
                busy.idle().await;
            }
        });
        Self::checked(&shared)?;
        Ok(std::mem::take(
            &mut *shared.written.lock().expect("a list nobody poisoned"),
        ))
    }

    fn halted(&self) -> bool {
        self.halt.as_ref().is_some_and(|h| h.load(Ordering::Relaxed))
    }

    fn held(shared: &Shared) -> bool {
        !shared.held.lock().expect("holders nobody poisoned").is_empty()
    }

    fn outcome(shared: &Shared) -> String {
        shared
            .outcome
            .lock()
            .expect("an outcome nobody poisoned")
            .clone()
            .unwrap_or_else(|| MET.to_string())
    }

    /// Until nobody holds the agent, ending as the last to let go said, or `passes` ran out. BY PASSES, each pass ticks
    /// every part and then waits for the next arrival or the soonest instant anything is due, unless a part asked to go
    /// again, never longer than `longest_s` real seconds: nought in a test, which steps the clock itself. FREE (no
    /// passes), one pass starts every part and each task then waits for itself; the run waits until nobody holds the
    /// agent or it is halted.
    pub fn run(&mut self, passes: Option<usize>, longest_s: f64) -> Result<String, Error> {
        let Some(passes) = passes else {
            return self.free();
        };
        let mut n = 0;
        while n < passes {
            if self.halted() {
                log::info!("{}: stopped, after {n} pass(es)", self.id);
                return Ok(UNFINISHED.to_string());
            }
            n += 1;
            let now = self.clock.now();
            let began = std::time::Instant::now();
            let shared = self.spawned();
            *shared.laps.lock().expect("laps nobody poisoned") = self.watch.connected().then(Laps::default);
            shared.again.store(false, Ordering::SeqCst);
            *shared.soonest.lock().expect("a soonest nobody poisoned") = None;
            self.drain(now)?;
            self.passed(&shared, began.elapsed().as_secs_f64())?;
            if !Self::held(&shared) {
                log::info!("{}: nothing holds it, after {n} pass(es)", self.id);
                return Ok(Self::outcome(&shared));
            }
            if !shared.again.load(Ordering::SeqCst) {
                let wait = self.until_due(&shared, now, began.elapsed(), longest_s);
                let busy = self.busy.clone();
                let halted = self.halted.clone();
                self.tasks.block_on(async move {
                    tokio::select! {
                        _ = tokio::time::sleep(wait) => {}
                        _ = busy.active() => {}
                        _ = halted.notified() => {}
                    }
                });
            }
        }
        Ok(UNFINISHED.to_string())
    }

    /// Run free: one pass, then every task waits for itself, and the run for nobody holding the agent.
    fn free(&mut self) -> Result<String, Error> {
        let now = self.clock.now();
        let began = std::time::Instant::now();
        let shared = self.spawned();
        *shared.laps.lock().expect("laps nobody poisoned") = self.watch.connected().then(Laps::default);
        self.drain(now)?;
        shared.free.store(true, Ordering::SeqCst);
        self.passed(&shared, began.elapsed().as_secs_f64())?;
        //  EACH TASK NOW WAITS FOR ITSELF, told so at once.
        for part in 0..shared.senders.len() {
            shared.send(part, Message::Free);
        }
        //  ONE RECEIVER, so a task that woke and finished between the run's looks is still a change it sees.
        let mut seen = self.busy.0.subscribe();
        loop {
            let began = std::time::Instant::now();
            self.tasks.block_on(async { drop(seen.wait_for(|n| *n == 0).await) });
            Self::checked(&shared)?;
            self.passed(&shared, began.elapsed().as_secs_f64())?;
            if self.halted() {
                log::info!("{}: stopped", self.id);
                return Ok(UNFINISHED.to_string());
            }
            if !Self::held(&shared) {
                log::info!("{}: nothing holds it", self.id);
                return Ok(Self::outcome(&shared));
            }
            let halted = self.halted.clone();
            let halt = self.halt.clone();
            self.tasks.block_on(async {
                tokio::select! {
                    _ = seen.changed() => {}
                    _ = halted.notified() => {}
                }
            });
            if halt.is_some_and(|h| h.load(Ordering::Relaxed)) {
                log::info!("{}: stopped", self.id);
                return Ok(UNFINISHED.to_string());
            }
            *shared.laps.lock().expect("laps nobody poisoned") = self.watch.connected().then(Laps::default);
        }
    }

    /// How long the run waits between passes with nothing arriving: until the soonest a part is due, in real seconds at
    /// the clock's pace, and never longer than `longest_s`.
    fn until_due(&self, shared: &Shared, now: DateTime, took: Duration, longest_s: f64) -> Duration {
        let longest = Duration::from_secs_f64(longest_s);
        if longest.is_zero() {
            return longest;
        }
        let Some(soonest) = *shared.soonest.lock().expect("a soonest nobody poisoned") else {
            return longest;
        };
        //  FROM THE INSTANT THE PASS STOOD AT, less the real time it took: a wait reads no clock.
        let ahead = soonest.checked_sub(now).map_or(0.0, crate::clock::seconds_of).max(0.0);
        self.clock.real_delay(ahead).saturating_sub(took).min(longest)
    }

    /// Say the pass, where anybody watches.
    fn passed(&self, shared: &Shared, took: f64) -> Result<(), Error> {
        let Some(laps) = shared.laps.lock().expect("laps nobody poisoned").take() else {
            return Ok(());
        };
        let quads = i64::try_from(self.beliefs.len()?).ok();
        self.watch.emit(&Passed {
            duration_s: round6(took),
            laps: laps.spent,
            quads,
            uptime_s: (started().elapsed().as_secs_f64() * 1000.0).round() / 1000.0,
        });
        Ok(())
    }

    /// Stop every part, the last first, each after the one after it.
    pub fn stop(&mut self) {
        let Some(shared) = self.shared.clone() else {
            if let Some(pending) = self.pending.as_mut() {
                for running in pending.running.iter_mut().rev() {
                    running.part.stop();
                }
            }
            return;
        };
        let busy = self.busy.clone();
        let joins = std::mem::take(&mut self.joins);
        self.tasks.block_on(async move {
            let mut joins: Vec<_> = joins.into_iter().enumerate().collect();
            joins.reverse();
            for (part, join) in joins {
                shared.send(part, Message::Stop);
                let _ = join.await;
            }
            let _ = busy;
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::clock::Manual;
    use crate::transport::Inbox;

    /// Holds the agent at its first run and lets go at the second; a task delivers a message soon after it starts.
    struct Waiting {
        inbox: Inbox,
        runs: usize,
    }

    impl Part for Waiting {
        fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
            self.inbox.wakes(starting.wake());
            let inbox = self.inbox.clone();
            starting.every(0.0, 0);
            starting.task(async move {
                tokio::time::sleep(Duration::from_millis(50)).await;
                inbox.deliver("topic", b"payload", None);
            })
        }

        fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
            self.runs += 1;
            if self.runs == 1 {
                pass.hold("waiting");
            } else {
                pass.release("waiting", None);
            }
            Ok(Vec::new())
        }
    }

    fn manual(at: &str) -> Arc<dyn Clock> {
        Arc::new(Manual::at(at.parse().unwrap()))
    }

    fn one(name: &str, part: impl Part + 'static) -> Vec<(String, Box<dyn Part>)> {
        vec![(name.to_string(), Box::new(part))]
    }

    #[test]
    fn run_free_an_arrival_from_a_task_runs_the_part_at_once() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let part = Waiting {
            inbox: Inbox::default(),
            runs: 0,
        };
        let mut runtime = Runtime::threaded(
            2,
            &store,
            "urn:test:me",
            manual("2026-11-09T12:00:00Z"),
            one("waiting", part),
        )
        .unwrap();
        let began = std::time::Instant::now();
        assert_eq!(runtime.run(None, 60.0).unwrap(), MET);
        assert!(
            began.elapsed() < Duration::from_secs(30),
            "the arrival was slept through"
        );
        runtime.stop();
    }

    /// Holds the agent, and says it is next due a fifth of a second on.
    struct Due;
    impl Part for Due {
        fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
            starting.every(0.0, 0);
            Ok(())
        }
        fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
            pass.hold("due");
            let at = pass.now.checked_add_day_time_duration(seconds(0.2)).unwrap();
            pass.wake_at(at);
            Ok(Vec::new())
        }
    }

    #[test]
    fn a_pass_waits_until_the_soonest_a_part_is_due_and_no_longer() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let mut runtime = Runtime::new(&store, "urn:test:me", manual("2026-11-11T12:00:00Z"), one("due", Due)).unwrap();
        let began = std::time::Instant::now();
        assert_eq!(runtime.run(Some(2), 60.0).unwrap(), UNFINISHED);
        let took = began.elapsed();
        assert!(
            took >= Duration::from_millis(150),
            "it did not wait for the instant: {took:?}"
        );
        assert!(took < Duration::from_secs(30), "it waited the longest out: {took:?}");
    }

    /// Lets go once its task has run free to the instant it said it is due.
    struct Wakes {
        runs: Arc<Mutex<usize>>,
    }
    impl Part for Wakes {
        fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
            starting.every(0.0, 0);
            Ok(())
        }
        fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
            let mut runs = self.runs.lock().unwrap();
            *runs += 1;
            if *runs < 3 {
                pass.hold("wakes");
                pass.wake_at(pass.now.checked_add_day_time_duration(seconds(0.1)).unwrap());
            } else {
                pass.release("wakes", None);
            }
            Ok(Vec::new())
        }
    }

    #[test]
    fn run_free_a_task_wakes_itself_at_the_instant_it_said() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let runs = Arc::new(Mutex::new(0));
        let clock: Arc<dyn Clock> = Arc::new(crate::clock::Paced::wall());
        let part = Wakes { runs: runs.clone() };
        let mut runtime = Runtime::threaded(2, &store, "urn:test:me", clock, one("wakes", part)).unwrap();
        let began = std::time::Instant::now();
        assert_eq!(runtime.run(None, 60.0).unwrap(), MET);
        assert!(began.elapsed() >= Duration::from_millis(150), "it did not wait");
        assert!(began.elapsed() < Duration::from_secs(30), "it waited too long");
        assert_eq!(*runs.lock().unwrap(), 3);
    }

    const STEP: &str = "http://example.org/test#Stepping";

    /// Begins and ends an activity at every pass.
    struct Begins;
    impl Part for Begins {
        fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
            starting.every(0.0, 0);
            Ok(())
        }
        fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
            let activity = pass.begin(STEP, &[]);
            pass.end(activity);
            Ok(Vec::new())
        }
    }

    /// Hears every event beneath `orexis:Event`'s kernel classes it is told of: here, a start.
    struct Hears(Arc<Mutex<Vec<Heard>>>);
    impl Part for Hears {
        fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
            starting.hears(crate::activity::STARTED, 0);
            Ok(())
        }
        fn run(&mut self, _job: usize, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
            Ok(Vec::new())
        }
        fn heard_event(&mut self, _job: usize, event: &Heard, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
            self.0.lock().unwrap().push(event.clone());
            Ok(Vec::new())
        }
    }

    #[test]
    fn an_activitys_start_is_heard_by_class_under_the_name_it_was_said_with() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = manual("2026-11-10T12:00:00Z");
        let heard = Arc::new(Mutex::new(Vec::new()));
        let said: Arc<Mutex<Vec<NamedNode>>> = Arc::default();
        let parts: Vec<(String, Box<dyn Part>)> = vec![
            ("begins".into(), Box::new(Begins)),
            ("hears".into(), Box::new(Hears(heard.clone()))),
        ];
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone(), parts).unwrap();
        let watch = Watch::default();
        let kept = said.clone();
        watch.connect(move |event, named| {
            if event.kind() == Some(crate::activity::STARTED) {
                kept.lock().unwrap().push(named.clone());
            }
        });
        runtime.watch = watch;
        runtime.drain(clock.now()).unwrap();
        let heard = heard.lock().unwrap();
        assert_eq!(heard.len(), 1, "one start, and the end is no start: {heard:?}");
        assert_eq!(
            heard[0].node,
            said.lock().unwrap()[0],
            "heard under the name it was said with"
        );
        assert_eq!(heard[0].activity.as_ref().map(|(_, k)| k.as_str()), Some(STEP));
    }

    #[test]
    fn nobody_listening_connects_nothing() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = manual("2026-11-10T12:00:00Z");
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone(), one("begins", Begins)).unwrap();
        runtime.drain(clock.now()).unwrap();
        assert!(
            !runtime.watch.connected(),
            "an emitter that asks whether anybody watches is still told no"
        );
    }

    /// Says an activity's start to whoever hears it, and the hearer writes it down: by passes, the part after it is
    /// ticked only once the start was heard.
    #[test]
    fn by_passes_a_part_is_ticked_after_everything_the_parts_before_it_said_was_heard() {
        struct Order(Arc<Mutex<Vec<&'static str>>>, &'static str);
        impl Part for Order {
            fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
                starting.every(0.0, 0);
                starting.hears(crate::activity::STARTED, 1);
                Ok(())
            }
            fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
                self.0.lock().unwrap().push(self.1);
                if self.1 == "first" {
                    let activity = pass.begin(STEP, &[]);
                    pass.end(activity);
                }
                Ok(Vec::new())
            }
            fn heard_event(&mut self, _job: usize, _event: &Heard, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
                self.0.lock().unwrap().push(if self.1 == "first" {
                    "first heard"
                } else {
                    "second heard"
                });
                Ok(Vec::new())
            }
        }
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = manual("2026-11-11T12:00:00Z");
        let seen = Arc::new(Mutex::new(Vec::new()));
        let parts: Vec<(String, Box<dyn Part>)> = vec![
            ("first".into(), Box::new(Order(seen.clone(), "first"))),
            ("second".into(), Box::new(Order(seen.clone(), "second"))),
        ];
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone(), parts).unwrap();
        runtime.drain(clock.now()).unwrap();
        assert_eq!(
            *seen.lock().unwrap(),
            ["first", "first heard", "second heard", "second"]
        );
    }
}
