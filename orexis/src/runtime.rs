//! THE RUNTIME: one agent's body, a Tokio runtime and the watch its packages say their events to
//! (the-agent-is-a-runtime-of-tasks). The runtime knows no package and no word of what one does. A PACKAGE STARTS
//! ITSELF on it: it takes a wait (`Runtime::wait`), says on it what ends it - an event's class, a kind of graph
//! written, a timer `every` so many seconds of the one timeline - and spawns its task (`Runtime::spawn`). THE LOOP IS
//! THE PACKAGE'S: its task awaits `Wait::next`, which answers what woke it, decides, and awaits again, until it is
//! answered nothing and stops. The run ends when nothing holds the agent, as the last to let go said: `met`,
//! `planned` or `unreachable`; or when the passes ran out, `unfinished`.
//!
//! A PACKAGE HEARS AN EVENT BY ITS CLASS (`hears`), the class and every class the vocabulary puts beneath it, and A
//! KIND OF GRAPH WRITTEN (`on`): every graph a package says it wrote is sent to each wait listening for a kind the
//! catalogue says it is. What a package says while it handles what woke it is heard once it has said what it wrote
//! (`Pass::done`), its graphs before its events. After anything it handled a package is woken for what it queued for
//! itself (`Woke::Arrived`) and then, once nothing more waits for it, for its timers due, those of nought - its
//! policy - among them (packages-meet-by-events-policies-and-activities). No order holds between two packages: each
//! waits for what triggers it.
//!
//! RUN FREE (`run(None, …)`), a wait also ends at the soonest instant its package is due, a timer or what it said by
//! `wake_at`, at the clock's pace, and each message is handled at the instant the clock then reads. The tasks run on
//! the runtime's workers at once, and a graph has one writing package, so no two meet on it.
//!
//! RUN BY PASSES (`run(Some(n), …)`, `drain`), what a test does, the runtime says the instant: a pass tells each
//! wait in turn that it is now `now`, waiting until nothing is busy, and everything said in the pass is handled at
//! that instant. BY PASSES A POLICY DECIDES WHEN THE PASS TELLS IT THE INSTANT: what a package hears after that it
//! decides on at the next pass, so a plan published is walked in the pass that published it only because planning
//! started before execution. What a package queued for itself in a pass it does at the pass's end, once. Between
//! passes the runtime waits for an arrival or the soonest instant anything is due, never longer than the longest it
//! is told, nought in a test that sets its clock itself.
use std::collections::{BTreeMap, HashMap};
use std::future::Future;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, RwLock};
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
    /// THE EVENTS A PACKAGE SAID SINCE IT WAS WOKEN on this thread, sent once it says what it wrote: its graphs are
    /// heard before its events, as one queue told them. A task does not leave its thread between two waits.
    static SAID: std::cell::RefCell<Option<Vec<Heard>>> = const { std::cell::RefCell::new(None) };
}

/// Hold back what is said on this thread from now.
fn hold() {
    SAID.with(|said| *said.borrow_mut() = Some(Vec::new()));
}

/// What was held back, and nothing held any more.
fn said() -> Vec<Heard> {
    SAID.with(|said| said.borrow_mut().take()).unwrap_or_default()
}

/// Run `work`, a computation of seconds, so the tasks beside it keep their workers: where the runtime has several,
/// this worker hands its other tasks on and `work` runs in place; on one thread it simply runs.
pub fn long<T>(work: impl FnOnce() -> T) -> T {
    match tokio::runtime::Handle::try_current().map(|h| h.runtime_flavor()) {
        Ok(tokio::runtime::RuntimeFlavor::MultiThread) => tokio::task::block_in_place(work),
        _ => work(),
    }
}

/// What a package's wait is sent.
enum Message {
    /// Run the due timers at the instant a pass stands at.
    Tick(DateTime),
    /// Something arrived for the package, or it may do what it queued for itself.
    Arrived,
    Graph(usize, String),
    Event(usize, Heard),
    /// Wait for itself from now on: run free.
    Free,
    Stop,
}

/// HOW MANY MESSAGES ARE SENT AND NOT YET HANDLED, across every package: nought is idle.
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

/// What ends a package's wait - or the run's, for whoever stops it from outside - when something arrived.
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

/// Who waits on the runtime, and for what.
#[derive(Default)]
struct Waits {
    senders: Vec<UnboundedSender<Message>>,
    /// (wait, kind, tag): who hears a kind of graph written.
    hears: Vec<(usize, String, usize)>,
    /// (wait, class, tag): who hears an event of a class.
    listens: Vec<(usize, String, usize)>,
}

/// WHAT EVERY PACKAGE'S TASK SHARES: the store, the clock, the watch, who holds the agent and who waits for what.
struct Shared {
    beliefs: Store,
    id: String,
    clock: Arc<dyn Clock>,
    held: Mutex<BTreeMap<String, ()>>,
    outcome: Mutex<Option<String>>,
    waits: RwLock<Waits>,
    /// Every class each class said is beneath, asked once.
    closed: Mutex<HashMap<String, Vec<String>>>,
    busy: Busy,
    watch: Watch,
    laps: Mutex<Option<Laps>>,
    /// Run free, each wait ends at the instant its package is due and reads the clock; by passes the runtime says
    /// the instant.
    free: AtomicBool,
    /// By passes, while the waits are told the instant: what a package queued for itself waits for the end of the
    /// pass, so several things heard in one pass queue one piece of work and not one each.
    telling: AtomicBool,
    again: AtomicBool,
    /// The instant the pass in progress stands at, by passes: what every message is handled at, so nothing reads the
    /// clock for it.
    at: Mutex<Option<DateTime>>,
    /// The soonest instant a package said it is next due, or a timer falls due, this pass.
    soonest: Mutex<Option<DateTime>>,
    /// What the packages wrote since the pass began.
    written: Mutex<Vec<String>>,
    error: Mutex<Option<Error>>,
}

impl Shared {
    fn send(&self, wait: usize, message: Message) {
        let to = self
            .waits
            .read()
            .expect("waits nobody poisoned")
            .senders
            .get(wait)
            .cloned();
        if let Some(to) = to {
            self.busy.up();
            if to.send(message).is_err() {
                self.busy.down();
            }
        }
    }

    fn count(&self) -> usize {
        self.waits.read().expect("waits nobody poisoned").senders.len()
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

    /// Say that `graphs` were written, to every wait listening for a kind the catalogue says each is.
    fn wrote(&self, graphs: Vec<String>) -> Result<(), Error> {
        let hears = self.waits.read().expect("waits nobody poisoned").hears.clone();
        for graph in graphs {
            if !hears.is_empty() {
                let kinds = self.kinds(&graph)?;
                for (wait, kind, tag) in &hears {
                    if kinds.contains(kind) {
                        self.send(*wait, Message::Graph(*tag, graph.clone()));
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

    /// Send `event` to every wait hearing a class it is beneath.
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
        let listens = self.waits.read().expect("waits nobody poisoned").listens.clone();
        for (wait, class, tag) in &listens {
            if classes.contains(class) {
                self.send(*wait, Message::Event(*tag, event.clone()));
            }
        }
    }
}

/// What a package is handed with what woke it: the instant it stands at, and the agent's life to keep or let go.
pub struct Pass<'r> {
    pub now: DateTime,
    pub agent: &'r str,
    shared: &'r Shared,
    soonest: &'r mut Option<DateTime>,
    failed: &'r mut bool,
}

impl Pass<'_> {
    /// WHAT THE PACKAGE DID OF WHAT WOKE IT: the graphs it wrote told to whoever listens for their kinds, then the
    /// events it said, as one queue told them. A failure is the run's, and drops what was left of the message in hand.
    pub fn done(self, wrote: Result<Vec<String>, Error>) {
        let told = wrote.and_then(|wrote| self.shared.wrote(wrote));
        for heard in said() {
            self.shared.tell(heard);
        }
        if let Err(e) = told {
            *self.failed = true;
            self.shared.failed(e);
        }
    }

    /// One thing done of several in this pass - what a package queued for itself, each in turn: the graphs it wrote
    /// told, then the events it said, before the next is done.
    pub fn told(&mut self, wrote: Vec<String>) -> Result<(), Error> {
        let told = self.shared.wrote(wrote);
        for heard in said() {
            self.shared.tell(heard);
        }
        hold();
        told
    }

    /// The package is next due at `at`, with nothing heard: its task waits no longer than that.
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

    /// `who` no longer keeps the agent running, and says how it ended.
    pub fn release(&mut self, who: &str, outcome: Option<&str>) {
        self.shared.held.lock().expect("holders nobody poisoned").remove(who);
        if let Some(outcome) = outcome {
            *self.shared.outcome.lock().expect("an outcome nobody poisoned") = Some(outcome.to_string());
        }
    }

    /// Tell every package the instant once more: by passes, the next pass without waiting; free, at once.
    pub fn again(&mut self) {
        self.shared.again.store(true, Ordering::SeqCst);
    }
}

/// An event as a package hears it: the name it was said under, its class, and the activity it starts or ends.
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

struct Timer {
    seconds: f64,
    due: Option<DateTime>,
    tag: usize,
}

/// What woke a package's task, with the tag it asked under.
#[derive(Clone, Debug, PartialEq)]
pub enum Woke {
    /// A timer it asked for fell due.
    Due(usize),
    /// A graph of a kind it listens for was written.
    Graph(usize, String),
    /// An event of a class it hears was said.
    Event(usize, Heard),
    /// Something arrived for it - its `Wake` rang - or it may now do what it queued for itself: it does all of it,
    /// saying what each wrote (`Pass::told`).
    Arrived,
}

/// A PACKAGE'S WAIT: what its task waits on, and where the package says what ends it. The package's loop awaits
/// `next`, handles what woke it and says what it wrote (`Pass::done`), until `next` answers nothing: the run is over,
/// and the package stops itself.
pub struct Wait {
    shared: Arc<Shared>,
    index: usize,
    inbox: UnboundedReceiver<Message>,
    timers: Vec<Timer>,
    /// When the package said it is next due.
    soonest: Option<DateTime>,
    /// What is left to wake the package for of the message in hand, in order.
    left: std::collections::VecDeque<Woke>,
    /// The instant the message in hand is handled at.
    now: DateTime,
    /// Whether a message is in hand: counted busy until everything it asks was done.
    in_hand: bool,
    /// Whether what the package last did failed: the rest of the message in hand is dropped.
    failed: bool,
    tasks: tokio::runtime::Handle,
}

impl Wait {
    /// The instant the package starts at, read off the one timeline - a tick in a test, so read only where needed.
    pub fn now(&self) -> DateTime {
        self.shared.clock.now()
    }

    /// The watch the agent's packages say their events to.
    pub fn watch(&self) -> Watch {
        self.shared.watch.clone()
    }

    /// End the wait for every event of `class` said, or of a class the vocabulary puts beneath it, with `tag` and
    /// the event (`Woke::Event`).
    pub fn hears(&mut self, class: &str, tag: usize) {
        let mut waits = self.shared.waits.write().expect("waits nobody poisoned");
        waits.listens.push((self.index, class.to_string(), tag));
    }

    /// End the wait for every graph of `kind` written, with `tag` and the graph (`Woke::Graph`).
    pub fn on(&mut self, kind: &str, tag: usize) {
        let mut waits = self.shared.waits.write().expect("waits nobody poisoned");
        waits.hears.push((self.index, kind.to_string(), tag));
    }

    /// Wake the package with `tag` when the run begins and again every `seconds` of the one timeline after
    /// (`Woke::Due`) - after whatever the package handled, once nothing more waits for it, where `seconds` is nought.
    pub fn every(&mut self, seconds: f64, tag: usize) {
        self.timers.push(Timer {
            seconds,
            due: None,
            tag,
        });
    }

    /// What ends the wait, for whatever hands the package an arrival.
    pub fn wake(&self) -> Wake {
        let to = self.shared.waits.read().expect("waits nobody poisoned").senders[self.index].clone();
        Wake {
            to: Some((to, self.shared.busy.clone())),
            halt: None,
        }
    }

    /// Run `work` among the process's tasks, from now until it ends or the process does. It waits on the outside and
    /// hands the package what arrived: it writes no belief.
    pub fn task(&mut self, work: impl Future<Output = ()> + Send + 'static) -> Result<(), Error> {
        self.tasks.spawn(work);
        Ok(())
    }

    /// WAIT FOR WHAT WAKES THE PACKAGE NEXT, and the pass it is handled in; nothing once the run is over. Run free,
    /// the wait ends at the soonest instant the package is due where no message comes first.
    pub async fn next(&mut self) -> Option<(Woke, Pass<'_>)> {
        for heard in said() {
            self.shared.tell(heard);
        }
        if std::mem::take(&mut self.failed) {
            self.left.clear();
        }
        let woke = loop {
            if let Some(woke) = self.left.pop_front() {
                break woke;
            }
            self.handled();
            let message = self.receive().await?;
            self.in_hand = true;
            if !self.take(message) {
                self.handled();
                return None;
            }
        };
        hold();
        Some((
            woke,
            Pass {
                now: self.now,
                agent: &self.shared.id,
                shared: &self.shared,
                soonest: &mut self.soonest,
                failed: &mut self.failed,
            },
        ))
    }

    /// The message in hand is done with: the runtime told when the package is next due, and no longer busy. Run free,
    /// every wait is told the instant where a package asked.
    fn handled(&mut self) {
        if !std::mem::take(&mut self.in_hand) {
            return;
        }
        let shared = &self.shared;
        if let Some(due) = self.due() {
            shared.sooner(due);
        }
        if shared.free.load(Ordering::SeqCst) && shared.again.swap(false, Ordering::SeqCst) {
            let now = shared.clock.now();
            for wait in 0..shared.count() {
                shared.send(wait, Message::Tick(now));
            }
        }
        shared.busy.down();
    }

    /// The next message: run free, the instant itself at the soonest the package is due where none comes before it.
    async fn receive(&mut self) -> Option<Message> {
        let shared = &self.shared;
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
        match wait {
            Some(wait) => tokio::select! {
                m = self.inbox.recv() => m,
                _ = tokio::time::sleep(wait) => {
                    self.shared.busy.up();
                    Some(Message::Tick(self.shared.clock.now()))
                }
            },
            None => self.inbox.recv().await,
        }
    }

    /// Lay out what `message` wakes the package for, in order; false where it stops the package.
    fn take(&mut self, message: Message) -> bool {
        let shared = &self.shared;
        let stands = || match (
            shared.free.load(Ordering::SeqCst),
            *shared.at.lock().expect("an instant nobody poisoned"),
        ) {
            (false, Some(at)) => at,
            _ => shared.clock.now(),
        };
        let told = matches!(message, Message::Tick(_));
        match message {
            Message::Stop => return false,
            Message::Free => return true,
            Message::Tick(at) => self.now = at,
            Message::Arrived => self.now = stands(),
            Message::Graph(tag, graph) => {
                self.now = stands();
                self.left.push_back(Woke::Graph(tag, graph));
            }
            Message::Event(tag, event) => {
                self.now = stands();
                self.left.push_back(Woke::Event(tag, event));
            }
        }
        let queued = !shared.telling.load(Ordering::SeqCst);
        if queued {
            self.left.push_back(Woke::Arrived);
        }
        //  A PACKAGE'S POLICY DECIDES ONCE NOTHING MORE WAITS FOR IT: its timers due, those of nought among them, and
        //  it says again when it is next due. BY PASSES IT DECIDES WHEN THE PASS TELLS IT THE INSTANT, and what it
        //  hears after that it decides on at the next pass.
        if self.inbox.is_empty() {
            let now = self.now;
            let decides = told || shared.free.load(Ordering::SeqCst);
            for timer in &mut self.timers {
                if timer.due.is_some_and(|due| now < due) || (timer.seconds <= 0.0 && !decides) {
                    continue;
                }
                if timer.seconds <= 0.0 {
                    self.soonest = None;
                }
                timer.due = Some(now.checked_add_day_time_duration(seconds(timer.seconds)).unwrap_or(now));
                self.left.push_back(Woke::Due(timer.tag));
                if queued {
                    self.left.push_back(Woke::Arrived);
                }
            }
        }
        true
    }

    /// The soonest instant the package is due: what it said, or a timer of more than nought.
    fn due(&self) -> Option<DateTime> {
        self.timers
            .iter()
            .filter(|t| t.seconds > 0.0)
            .filter_map(|t| t.due)
            .chain(self.soonest)
            .reduce(|a, b| if b < a { b } else { a })
    }
}

impl Drop for Wait {
    /// A task that ended holds nothing busy: neither the message in hand nor any it was sent and never took.
    fn drop(&mut self) {
        for heard in said() {
            self.shared.tell(heard);
        }
        if std::mem::take(&mut self.in_hand) {
            self.shared.busy.down();
        }
        self.inbox.close();
        while self.inbox.try_recv().is_ok() {
            self.shared.busy.down();
        }
    }
}

/// One agent's process over its beliefs: a Tokio runtime, the watch its packages say their events to, and the tasks
/// they spawned on it.
pub struct Runtime {
    pub beliefs: Store,
    pub id: String,
    clock: Arc<dyn Clock>,
    names: Vec<String>,
    shared: Arc<Shared>,
    /// Each wait's task, where its package spawned one.
    joins: Vec<Option<tokio::task::JoinHandle<()>>>,
    /// Whether the run began: what the packages say is told to those that hear it from then on.
    begun: bool,
    /// RAISED TO STOP THE RUN, by a signal the process was sent: the run ends before its next pass, `unfinished`, so
    /// whoever runs it stops every task and the last window is written.
    pub halt: Option<Arc<AtomicBool>>,
    halted: Arc<Notify>,
    tasks: tokio::runtime::Runtime,
}

impl Runtime {
    /// The runtime of `id` over `beliefs`, reading the one timeline off `clock`, on ONE thread: what a test runs, by
    /// passes.
    pub fn new(beliefs: &Store, id: &str, clock: Arc<dyn Clock>) -> Result<Self, Error> {
        let tasks = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
        Ok(Self::on(tasks, beliefs, id, clock))
    }

    /// The runtime of `id`, its packages' tasks on `workers` threads of their own: what an agent runs.
    pub fn threaded(workers: usize, beliefs: &Store, id: &str, clock: Arc<dyn Clock>) -> Result<Self, Error> {
        let tasks = tokio::runtime::Builder::new_multi_thread()
            .worker_threads(workers.max(1))
            .thread_name("orexis-tasks")
            .enable_all()
            .build()
            .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
        Ok(Self::on(tasks, beliefs, id, clock))
    }

    fn on(tasks: tokio::runtime::Runtime, beliefs: &Store, id: &str, clock: Arc<dyn Clock>) -> Self {
        started();
        let shared = Arc::new(Shared {
            beliefs: beliefs.clone(),
            id: id.to_string(),
            clock: clock.clone(),
            held: Mutex::new(BTreeMap::new()),
            outcome: Mutex::new(None),
            waits: RwLock::new(Waits::default()),
            closed: Mutex::new(HashMap::new()),
            busy: Busy::new(),
            watch: Watch::default(),
            laps: Mutex::new(None),
            free: AtomicBool::new(false),
            telling: AtomicBool::new(false),
            again: AtomicBool::new(false),
            at: Mutex::new(None),
            soonest: Mutex::new(None),
            written: Mutex::new(Vec::new()),
            error: Mutex::new(None),
        });
        Runtime {
            beliefs: beliefs.clone(),
            id: id.to_string(),
            clock,
            names: Vec::new(),
            shared,
            joins: Vec::new(),
            begun: false,
            halt: None,
            halted: Arc::new(Notify::new()),
            tasks,
        }
    }

    /// THE WATCH THE AGENT'S PACKAGES SAY THEIR EVENTS TO, and whoever watches the agent hears them on: the one
    /// thing its packages share.
    pub fn watch(&self) -> &Watch {
        &self.shared.watch
    }

    /// The one timeline.
    pub fn clock(&self) -> Arc<dyn Clock> {
        self.clock.clone()
    }

    /// A wait for the package starting itself as `name`: it says on it what ends it, and hands it to its task.
    pub fn wait(&mut self, name: &str) -> Wait {
        let (to, inbox) = unbounded_channel();
        let index = {
            let mut waits = self.shared.waits.write().expect("waits nobody poisoned");
            waits.senders.push(to);
            waits.senders.len() - 1
        };
        self.names.push(name.to_string());
        self.joins.push(None);
        Wait {
            shared: self.shared.clone(),
            index,
            inbox,
            timers: Vec::new(),
            soonest: None,
            left: std::collections::VecDeque::new(),
            //  NO READ OF THE CLOCK: a wait stands at an instant once a message says one.
            now: DateTime::MIN,
            in_hand: false,
            failed: false,
            tasks: self.tasks.handle().clone(),
        }
    }

    /// SPAWN A PACKAGE'S TASK, the loop that is its policy, over its wait. Packages are told the instant in the
    /// order they took their waits, and stopped the last first.
    pub fn spawn<F, Fut>(&mut self, wait: Wait, task: F)
    where
        F: FnOnce(Wait) -> Fut,
        Fut: Future<Output = ()> + Send + 'static,
    {
        let index = wait.index;
        self.joins[index] = Some(self.tasks.spawn(task(wait)));
    }

    /// What ends the run's wait, for whoever stops the run from outside it.
    pub fn wake(&self) -> Wake {
        Wake {
            to: None,
            halt: Some(self.halted.clone()),
        }
    }

    /// The packages that wait on it, in the order they started.
    pub fn parts(&self) -> Vec<&str> {
        self.names.iter().map(String::as_str).collect()
    }

    /// The run begins: from here on what is said on the watch is told to the packages that hear it.
    fn begin(&mut self) {
        if std::mem::replace(&mut self.begun, true) {
            return;
        }
        let shared = &self.shared;
        if shared.waits.read().expect("waits nobody poisoned").listens.is_empty() {
            return;
        }
        let weak = Arc::downgrade(shared);
        shared.watch.connect(move |event, named| {
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

    fn checked(shared: &Shared) -> Result<(), Error> {
        match shared.error.lock().expect("an error nobody poisoned").take() {
            Some(e) => Err(e),
            None => Ok(()),
        }
    }

    /// One pass at `now`: each wait told the instant in turn, each after nothing is busy. The graphs written.
    pub fn drain(&mut self, now: DateTime) -> Result<Vec<String>, Error> {
        self.begin();
        let shared = self.shared.clone();
        shared.watch.stand(now);
        shared.written.lock().expect("a list nobody poisoned").clear();
        *shared.at.lock().expect("an instant nobody poisoned") = Some(now);
        let telling = shared.clone();
        self.tasks.block_on(async move {
            telling.busy.idle().await;
            if let Some(laps) = telling.laps.lock().expect("laps nobody poisoned").as_mut() {
                laps.lap("drain");
            }
            telling.telling.store(true, Ordering::SeqCst);
            for wait in 0..telling.count() {
                telling.send(wait, Message::Tick(now));
                telling.busy.idle().await;
                if telling.error.lock().expect("an error nobody poisoned").is_some() {
                    break;
                }
            }
            telling.telling.store(false, Ordering::SeqCst);
            //  WHAT THE PACKAGES QUEUED FOR THEMSELVES IN THE PASS, each in turn.
            for wait in 0..telling.count() {
                telling.send(wait, Message::Arrived);
                telling.busy.idle().await;
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

    /// Until nobody holds the agent, ending as the last to let go said, or `passes` ran out. BY PASSES, each pass
    /// tells every wait the instant and then waits for the next arrival or the soonest instant anything is due, unless
    /// a package asked to go again, never longer than `longest_s` real seconds: nought in a test, which steps the
    /// clock itself. FREE (no passes), one pass starts every package and each task then waits for itself; the run
    /// waits until nobody holds the agent or it is halted.
    pub fn run(&mut self, passes: Option<usize>, longest_s: f64) -> Result<String, Error> {
        let Some(passes) = passes else {
            return self.free();
        };
        let shared = self.shared.clone();
        let mut n = 0;
        while n < passes {
            if self.halted() {
                log::info!("{}: stopped, after {n} pass(es)", self.id);
                return Ok(UNFINISHED.to_string());
            }
            n += 1;
            let now = self.clock.now();
            let began = std::time::Instant::now();
            *shared.laps.lock().expect("laps nobody poisoned") = shared.watch.connected().then(Laps::default);
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
                let busy = shared.busy.clone();
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
        let shared = self.shared.clone();
        *shared.laps.lock().expect("laps nobody poisoned") = shared.watch.connected().then(Laps::default);
        self.drain(now)?;
        shared.free.store(true, Ordering::SeqCst);
        self.passed(&shared, began.elapsed().as_secs_f64())?;
        //  EACH TASK NOW WAITS FOR ITSELF, told so at once.
        for wait in 0..shared.count() {
            shared.send(wait, Message::Free);
        }
        //  ONE RECEIVER, so a task that woke and finished between the run's looks is still a change it sees.
        let mut seen = shared.busy.0.subscribe();
        loop {
            let began = std::time::Instant::now();
            //  UNTIL NOTHING IS BUSY, OR THE RUN IS HALTED WHILE SOMETHING STILL IS: a signal stops an agent that
            //  never comes to rest.
            let halted = self.halted.clone();
            self.tasks.block_on(async {
                tokio::select! {
                    _ = seen.wait_for(|n| *n == 0) => {}
                    _ = halted.notified() => {}
                }
            });
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
            *shared.laps.lock().expect("laps nobody poisoned") = shared.watch.connected().then(Laps::default);
        }
    }

    /// How long the run waits between passes with nothing arriving: until the soonest a package is due, in real
    /// seconds at the clock's pace, and never longer than `longest_s`.
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
        shared.watch.emit(&Passed {
            duration_s: round6(took),
            laps: laps.spent,
            quads,
            uptime_s: (started().elapsed().as_secs_f64() * 1000.0).round() / 1000.0,
        });
        Ok(())
    }

    /// Stop every package's task, the last started first, each after the one after it: its wait answers nothing, and
    /// it stops itself.
    pub fn stop(&mut self) {
        let shared = self.shared.clone();
        let joins = std::mem::take(&mut self.joins);
        self.tasks.block_on(async move {
            for (wait, join) in joins.into_iter().enumerate().rev() {
                shared.send(wait, Message::Stop);
                if let Some(join) = join {
                    let _ = join.await;
                }
            }
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::clock::Manual;
    use crate::transport::Inbox;

    fn manual(at: &str) -> Arc<dyn Clock> {
        Arc::new(Manual::at(at.parse().unwrap()))
    }

    /// A package of a test starting itself: what ends its wait, and what it does of each thing that wakes it.
    fn start(
        runtime: &mut Runtime,
        name: &'static str,
        asks: impl FnOnce(&mut Wait),
        mut does: impl FnMut(Woke, &mut Pass<'_>) + Send + 'static,
    ) {
        let mut wait = runtime.wait(name);
        asks(&mut wait);
        runtime.spawn(wait, move |mut wait| async move {
            while let Some((woke, mut pass)) = wait.next().await {
                does(woke, &mut pass);
                pass.done(Ok(Vec::new()));
            }
        });
    }

    /// Holds the agent at its first run and lets go at the second; a task delivers a message soon after it starts.
    #[test]
    fn run_free_an_arrival_from_a_task_wakes_the_package_at_once() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let inbox = Inbox::default();
        let mut runs = 0;
        let mut runtime = Runtime::threaded(2, &store, "urn:test:me", manual("2026-11-09T12:00:00Z")).unwrap();
        start(
            &mut runtime,
            "waiting",
            move |wait| {
                inbox.wakes(wait.wake());
                wait.every(0.0, 0);
                wait.task(async move {
                    tokio::time::sleep(Duration::from_millis(50)).await;
                    inbox.deliver("topic", b"payload", None);
                })
                .unwrap();
            },
            move |woke, pass| {
                if woke == Woke::Due(0) {
                    runs += 1;
                    if runs == 1 {
                        pass.hold("waiting");
                    } else {
                        pass.release("waiting", None);
                    }
                }
            },
        );
        let began = std::time::Instant::now();
        assert_eq!(runtime.run(None, 60.0).unwrap(), MET);
        assert!(
            began.elapsed() < Duration::from_secs(30),
            "the arrival was slept through"
        );
        runtime.stop();
    }

    /// Holds the agent, and says it is next due a fifth of a second on.
    #[test]
    fn a_pass_waits_until_the_soonest_a_package_is_due_and_no_longer() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let mut runtime = Runtime::new(&store, "urn:test:me", manual("2026-11-11T12:00:00Z")).unwrap();
        start(
            &mut runtime,
            "due",
            |wait| wait.every(0.0, 0),
            |woke, pass| {
                if woke == Woke::Due(0) {
                    pass.hold("due");
                    let at = pass.now.checked_add_day_time_duration(seconds(0.2)).unwrap();
                    pass.wake_at(at);
                }
            },
        );
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
    #[test]
    fn run_free_a_task_wakes_itself_at_the_instant_it_said() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let runs = Arc::new(Mutex::new(0));
        let clock: Arc<dyn Clock> = Arc::new(crate::clock::Paced::wall());
        let counted = runs.clone();
        let mut runtime = Runtime::threaded(2, &store, "urn:test:me", clock).unwrap();
        start(
            &mut runtime,
            "wakes",
            |wait| wait.every(0.0, 0),
            move |woke, pass| {
                if woke != Woke::Due(0) {
                    return;
                }
                let mut runs = counted.lock().unwrap();
                *runs += 1;
                if *runs < 3 {
                    pass.hold("wakes");
                    pass.wake_at(pass.now.checked_add_day_time_duration(seconds(0.1)).unwrap());
                } else {
                    pass.release("wakes", None);
                }
            },
        );
        let began = std::time::Instant::now();
        assert_eq!(runtime.run(None, 60.0).unwrap(), MET);
        assert!(began.elapsed() >= Duration::from_millis(150), "it did not wait");
        assert!(began.elapsed() < Duration::from_secs(30), "it waited too long");
        assert_eq!(*runs.lock().unwrap(), 3);
    }

    const STEP: &str = "http://example.org/test#Stepping";

    /// Begins and ends an activity the first time it is woken for its timer.
    fn begins(runtime: &mut Runtime) {
        let mut begun = false;
        start(
            runtime,
            "begins",
            |wait| wait.every(0.0, 0),
            move |woke, pass| {
                if woke == Woke::Due(0) && !std::mem::replace(&mut begun, true) {
                    let activity = pass.begin(STEP, &[]);
                    pass.end(activity);
                }
            },
        );
    }

    #[test]
    fn an_activitys_start_is_heard_by_class_under_the_name_it_was_said_with() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = manual("2026-11-10T12:00:00Z");
        let heard: Arc<Mutex<Vec<Heard>>> = Arc::default();
        let said: Arc<Mutex<Vec<NamedNode>>> = Arc::default();
        let into = heard.clone();
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone()).unwrap();
        begins(&mut runtime);
        //  HEARS EVERY START it is told of.
        start(
            &mut runtime,
            "hears",
            |wait| wait.hears(crate::activity::STARTED, 0),
            move |woke, _| {
                if let Woke::Event(_, event) = woke {
                    into.lock().unwrap().push(event);
                }
            },
        );
        let kept = said.clone();
        runtime.watch().connect(move |event, named| {
            if event.kind() == Some(crate::activity::STARTED) {
                kept.lock().unwrap().push(named.clone());
            }
        });
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
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone()).unwrap();
        begins(&mut runtime);
        runtime.drain(clock.now()).unwrap();
        assert!(
            !runtime.watch().connected(),
            "an emitter that asks whether anybody watches is still told no"
        );
    }

    /// One package says an activity's start; the other hears it at once, and is woken for its timer of nought when
    /// the pass tells it the instant.
    #[test]
    fn a_package_decides_after_what_it_heard() {
        let seen: Arc<Mutex<Vec<&'static str>>> = Arc::default();
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = manual("2026-11-11T12:00:00Z");
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone()).unwrap();
        begins(&mut runtime);
        let into = seen.clone();
        start(
            &mut runtime,
            "second",
            |wait| {
                wait.every(0.0, 0);
                wait.hears(crate::activity::STARTED, 1);
            },
            move |woke, _| match woke {
                Woke::Due(_) => into.lock().unwrap().push("decided"),
                Woke::Event(..) => into.lock().unwrap().push("heard"),
                _ => {}
            },
        );
        assert_eq!(runtime.parts(), ["begins", "second"]);
        runtime.drain(clock.now()).unwrap();
        assert_eq!(*seen.lock().unwrap(), ["heard", "decided"]);
    }

    /// A package whose task ended is never waited for.
    #[test]
    fn a_task_that_ended_holds_nothing_busy() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = manual("2026-11-11T12:00:00Z");
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone()).unwrap();
        let mut wait = runtime.wait("gone");
        wait.every(0.0, 0);
        runtime.spawn(wait, |mut wait| async move {
            let _ = wait.next().await;
        });
        runtime.drain(clock.now()).unwrap();
        runtime.drain(clock.now()).unwrap();
        runtime.stop();
    }
}
