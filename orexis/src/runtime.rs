//! THE RUNTIME: one agent's body, a Tokio runtime its packages register their tasks on
//! (the-agent-is-a-runtime-of-tasks). The runtime knows no package and no word of what one does: A PACKAGE REGISTERS
//! ITSELF - it says what it waits for (`Starting`: a timer, `every` so many seconds of the one timeline, a kind of
//! graph written, an event's class) and hands the task that is its policy - and THE LOOP IS THE PACKAGE'S: its task
//! awaits `Seat::next`, which answers what woke it, decides, and awaits again, until it is answered nothing and stops.
//! The run ends when nothing holds the agent, as the last to let go said: `met`, `planned` or `unreachable`; or when
//! the passes ran out, `unfinished`.
//!
//! A PACKAGE HEARS A KIND OF GRAPH WRITTEN (`on`): every graph a package says it wrote is sent to each seat listening
//! for a kind the catalogue says it is. A PACKAGE HEARS AN EVENT BY ITS CLASS (`hears`), the class and every class the
//! vocabulary puts beneath it, in the order its sayer said them; and IT BEGINS AND ENDS AN ACTIVITY, saying its start
//! and its end (packages-meet-by-events-policies-and-activities). What a package queued for itself it is woken for
//! (`Woke::Arrived`) after whatever queued it.
//!
//! RUN FREE (`run(None, …)`), each seat's wait ends with a message - an event, a graph, an arrival its `Wake` rang -
//! or at the soonest instant it is due, a timer or what it said by `wake_at`, at the clock's pace; the package handles
//! what came, and is then woken for its due timers, its policy among them. The tasks run on the runtime's workers at
//! once, and a graph has one writing package, so no two meet on it.
//!
//! RUN BY PASSES (`run(Some(n), …)`, `drain`), what a test does, the runtime ticks each seat in turn, in the order the
//! packages registered, and waits until nothing is busy before ticking the next: a package's policy runs after
//! everything the packages before it said has been heard, as one ordered pass ran them, so a test proves one order.
//! Between passes it waits for an arrival or the soonest instant anything is due, never longer than the longest it is
//! told, nought in a test that sets its clock itself.

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

/// What a package's seat is sent.
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

/// What a package asks for as it registers, by a tag of its own it is woken with.
pub struct Starting {
    name: String,
    timers: Vec<(f64, usize)>,
    hears: Vec<(String, usize)>,
    events: Vec<(String, usize)>,
    says: Option<Watch>,
    clock: Arc<dyn Clock>,
    wake: Wake,
    to: UnboundedSender<Message>,
    inbox: UnboundedReceiver<Message>,
    tasks: tokio::runtime::Handle,
}

impl Starting {
    /// The instant the package starts at, read off the one timeline - a tick in a test, so read only where needed.
    pub fn now(&self) -> DateTime {
        self.clock.now()
    }

    /// Wake the package for every graph of `kind` written, with `tag` and the graph (`Woke::Graph`).
    pub fn on(&mut self, kind: &str, tag: usize) {
        self.hears.push((kind.to_string(), tag));
    }

    /// Wake the package for every event of `class` said, or of a class the vocabulary puts beneath it, with `tag` and
    /// the event (`Woke::Event`).
    pub fn hears(&mut self, class: &str, tag: usize) {
        self.events.push((class.to_string(), tag));
    }

    /// Wake the package with `tag` at the first pass and again every `seconds` of the one timeline after
    /// (`Woke::Due`) - at every pass, and after whatever the package handled, where `seconds` is nought.
    pub fn every(&mut self, seconds: f64, tag: usize) {
        self.timers.push((seconds, tag));
    }

    /// The watch the package says its events to: the runtime listens on the first one said, so what a package says
    /// is heard by the packages that listen whoever assembled them.
    pub fn says(&mut self, watch: &Watch) {
        self.says = Some(watch.clone());
    }

    /// What ends the package's wait, for whatever hands it an arrival.
    pub fn wake(&self) -> Wake {
        self.wake.clone()
    }

    /// Run `work` among the process's tasks, from now until it ends or the process does. It waits on the outside and
    /// hands the package what arrived: it writes no belief.
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

/// What is left to do of the message in hand, in order.
enum Step {
    /// Forget when the package said it is next due: it says again.
    Reset,
    /// Every timer due at the instant in hand, each followed by what the package queued.
    Timers,
    /// What the package queued for itself - not while the runtime ticks the seats, when it waits for the end of the
    /// pass.
    Arrived,
    Woke(Woke),
    /// Say when the package is next due, by passes to the runtime.
    Report,
}

/// A PACKAGE'S SEAT ON THE RUNTIME: what its task waits on. The package's loop awaits `next`, handles what woke it and
/// says what it wrote (`Pass::done`), until `next` answers nothing: the run is over, and the package stops itself.
pub struct Seat {
    shared: Arc<Shared>,
    inbox: UnboundedReceiver<Message>,
    timers: Vec<Timer>,
    /// When the package said it is next due.
    soonest: Option<DateTime>,
    left: std::collections::VecDeque<Step>,
    /// The instant the message in hand is handled at.
    now: DateTime,
    /// Whether a message is in hand: counted busy until everything it asks was done.
    in_hand: bool,
    /// Whether what the package last did failed: the rest of the message in hand is dropped.
    failed: bool,
}

impl Seat {
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
            match self.left.pop_front() {
                Some(Step::Reset) => self.soonest = None,
                Some(Step::Report) => {
                    if let Some(due) = self.due() {
                        self.shared.sooner(due);
                    }
                }
                Some(Step::Timers) => {
                    let now = self.now;
                    let mut due = Vec::new();
                    for timer in &mut self.timers {
                        if timer.due.is_some_and(|due| now < due) {
                            continue;
                        }
                        timer.due = Some(now.checked_add_day_time_duration(seconds(timer.seconds)).unwrap_or(now));
                        due.push(timer.tag);
                    }
                    for tag in due.into_iter().rev() {
                        self.left.push_front(Step::Arrived);
                        self.left.push_front(Step::Woke(Woke::Due(tag)));
                    }
                }
                //  BY PASSES, WHAT A PACKAGE QUEUES WHILE THE SEATS ARE TICKED waits until every seat was: the end of
                //  the pass.
                Some(Step::Arrived) => {
                    if !self.shared.ticking.load(Ordering::SeqCst) {
                        break Woke::Arrived;
                    }
                }
                Some(Step::Woke(woke)) => break woke,
                None => {
                    self.handled();
                    let message = self.receive().await?;
                    self.in_hand = true;
                    if !self.take(message) {
                        self.handled();
                        return None;
                    }
                }
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

    /// The message in hand is done with: no longer busy, and run free every seat is ticked where a package asked.
    fn handled(&mut self) {
        if !std::mem::take(&mut self.in_hand) {
            return;
        }
        let shared = &self.shared;
        if shared.free.load(Ordering::SeqCst) && shared.again.swap(false, Ordering::SeqCst) {
            let now = shared.clock.now();
            for seat in 0..shared.senders.len() {
                shared.send(seat, Message::Tick(now));
            }
        }
        shared.busy.down();
    }

    /// The next message: run free, a tick at the soonest instant the package is due where none comes before it.
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

    /// Lay out what `message` asks, in order; false where it stops the package.
    fn take(&mut self, message: Message) -> bool {
        let shared = &self.shared;
        let free = shared.free.load(Ordering::SeqCst);
        let at = *shared.at.lock().expect("an instant nobody poisoned");
        let woke = match message {
            Message::Tick(at) => {
                self.now = at;
                self.left
                    .extend([Step::Reset, Step::Arrived, Step::Timers, Step::Report]);
                return true;
            }
            Message::Stop => return false,
            Message::Free => return true,
            Message::Arrived => None,
            Message::Graph(tag, graph) => Some(Woke::Graph(tag, graph)),
            Message::Event(tag, event) => Some(Woke::Event(tag, event)),
        };
        self.now = match (free, at) {
            (false, Some(at)) => at,
            _ => shared.clock.now(),
        };
        self.left.extend(woke.map(Step::Woke));
        self.left.push_back(Step::Arrived);
        //  RUN FREE, A PACKAGE'S POLICY DECIDES AFTER WHAT IT HANDLED: its timers due, those of nought among them.
        if free {
            self.left.extend([Step::Reset, Step::Arrived, Step::Timers]);
        }
        self.left.push_back(Step::Report);
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

impl Drop for Seat {
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

/// A package registering itself on a runtime: what whoever assembles an agent collects, and the runtime calls in
/// order.
pub type Registers = Box<dyn FnOnce(&mut Runtime) -> Result<(), Error>>;

type Task = Box<dyn FnOnce(Seat) -> std::pin::Pin<Box<dyn Future<Output = ()> + Send>> + Send>;

/// One agent's process over its beliefs: the tasks its packages registered, waiting to be run.
pub struct Runtime {
    pub beliefs: Store,
    pub id: String,
    clock: Arc<dyn Clock>,
    names: Vec<String>,
    /// What the packages registered, until the first run makes them tasks.
    pending: Option<Pending>,
    shared: Option<Arc<Shared>>,
    joins: Vec<tokio::task::JoinHandle<()>>,
    busy: Busy,
    /// WHOEVER WATCHES THE AGENT, hearing each pass where anybody does: the one the first run finds here.
    pub watch: Watch,
    said: bool,
    /// RAISED TO STOP THE RUN, by a signal the process was sent: the run ends before its next pass, `unfinished`, so
    /// whoever runs it stops every task and the last window is written.
    pub halt: Option<Arc<AtomicBool>>,
    halted: Arc<Notify>,
    tasks: tokio::runtime::Runtime,
}

#[derive(Default)]
struct Pending {
    tasks: Vec<Task>,
    timers: Vec<Vec<Timer>>,
    inboxes: Vec<UnboundedReceiver<Message>>,
    senders: Vec<UnboundedSender<Message>>,
    hears: Vec<(usize, String, usize)>,
    listens: Vec<(usize, String, usize)>,
}

impl Runtime {
    /// The runtime of `id` over `beliefs`, reading the one timeline off `clock`, on ONE thread, each of `packages`
    /// registered in order: what a test runs, by passes, so it proves one order.
    pub fn new(
        beliefs: &Store,
        id: &str,
        clock: Arc<dyn Clock>,
        packages: Vec<(String, Registers)>,
    ) -> Result<Self, Error> {
        let tasks = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
        Self::on(tasks, beliefs, id, clock, packages)
    }

    /// The runtime of `id`, its packages' tasks on `workers` threads of their own: what an agent runs.
    pub fn threaded(
        workers: usize,
        beliefs: &Store,
        id: &str,
        clock: Arc<dyn Clock>,
        packages: Vec<(String, Registers)>,
    ) -> Result<Self, Error> {
        let tasks = tokio::runtime::Builder::new_multi_thread()
            .worker_threads(workers.max(1))
            .thread_name("orexis-tasks")
            .enable_all()
            .build()
            .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
        Self::on(tasks, beliefs, id, clock, packages)
    }

    fn on(
        tasks: tokio::runtime::Runtime,
        beliefs: &Store,
        id: &str,
        clock: Arc<dyn Clock>,
        packages: Vec<(String, Registers)>,
    ) -> Result<Self, Error> {
        started();
        let mut runtime = Runtime {
            beliefs: beliefs.clone(),
            id: id.to_string(),
            clock,
            names: Vec::new(),
            pending: Some(Pending::default()),
            shared: None,
            joins: Vec::new(),
            busy: Busy::new(),
            watch: Watch::default(),
            said: false,
            halt: None,
            halted: Arc::new(Notify::new()),
            tasks,
        };
        for (_, registers) in packages {
            registers(&mut runtime)?;
        }
        Ok(runtime)
    }

    /// What a package registering as `name` asks with: its mailbox made, so whatever hands it an arrival may ring.
    pub fn starting(&self, name: &str) -> Starting {
        let (to, inbox) = unbounded_channel();
        Starting {
            name: name.to_string(),
            timers: Vec::new(),
            hears: Vec::new(),
            events: Vec::new(),
            says: None,
            clock: self.clock.clone(),
            wake: Wake {
                to: Some((to.clone(), self.busy.clone())),
                halt: None,
            },
            to,
            inbox,
            tasks: self.tasks.handle().clone(),
        }
    }

    /// REGISTER A PACKAGE'S TASK: what it asked for, and the loop that is its policy, handed its seat when the run
    /// begins. Packages are ticked in the order they register, and stopped the last first.
    pub fn register<F, Fut>(&mut self, starting: Starting, task: F)
    where
        F: FnOnce(Seat) -> Fut + Send + 'static,
        Fut: Future<Output = ()> + Send + 'static,
    {
        let pending = self.pending.as_mut().expect("a package registers before the first run");
        let seat = pending.tasks.len();
        pending
            .hears
            .extend(starting.hears.into_iter().map(|(kind, tag)| (seat, kind, tag)));
        pending
            .listens
            .extend(starting.events.into_iter().map(|(class, tag)| (seat, class, tag)));
        pending.timers.push(
            starting
                .timers
                .into_iter()
                .map(|(seconds, tag)| Timer {
                    seconds,
                    due: None,
                    tag,
                })
                .collect(),
        );
        pending.inboxes.push(starting.inbox);
        pending.senders.push(starting.to);
        pending.tasks.push(Box::new(move |seat| Box::pin(task(seat))));
        self.names.push(starting.name);
        if let Some(watch) = starting.says
            && !std::mem::replace(&mut self.said, true)
        {
            self.watch = watch;
        }
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

    /// The packages' tasks spawned, each handed its seat, the first time anything runs: the watch found here is the
    /// one every task says to, and
    /// what it hears is told to the parts listening.
    fn spawned(&mut self) -> Arc<Shared> {
        if let Some(shared) = &self.shared {
            return shared.clone();
        }
        let pending = self.pending.take().expect("tasks pending until they are spawned");
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
        //  NO READ OF THE CLOCK: a seat stands at an instant once a message says one.
        let now = DateTime::MIN;
        for ((task, inbox), timers) in pending.tasks.into_iter().zip(pending.inboxes).zip(pending.timers) {
            let seat = Seat {
                shared: shared.clone(),
                inbox,
                timers,
                soonest: None,
                left: std::collections::VecDeque::new(),
                now,
                in_hand: false,
                failed: false,
            };
            self.joins.push(self.tasks.spawn(task(seat)));
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

    /// Stop every package's task, the last registered first, each after the one after it: its wait answers nothing,
    /// and it stops itself.
    pub fn stop(&mut self) {
        let shared = self.spawned();
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

    fn manual(at: &str) -> Arc<dyn Clock> {
        Arc::new(Manual::at(at.parse().unwrap()))
    }

    /// A package of a test: what it asks for, and what it does of each thing that wakes it.
    fn package(
        name: &'static str,
        asks: impl FnOnce(&mut Starting) + 'static,
        mut does: impl FnMut(Woke, &mut Pass<'_>) + Send + 'static,
    ) -> (String, Registers) {
        let registers: Registers = Box::new(move |runtime| {
            let mut starting = runtime.starting(name);
            asks(&mut starting);
            runtime.register(starting, move |mut seat| async move {
                while let Some((woke, mut pass)) = seat.next().await {
                    does(woke, &mut pass);
                    pass.done(Ok(Vec::new()));
                }
            });
            Ok(())
        });
        (name.to_string(), registers)
    }

    /// Holds the agent at its first run and lets go at the second; a task delivers a message soon after it starts.
    #[test]
    fn run_free_an_arrival_from_a_task_wakes_the_package_at_once() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let inbox = Inbox::default();
        let mut runs = 0;
        let waiting = package(
            "waiting",
            move |starting| {
                inbox.wakes(starting.wake());
                starting.every(0.0, 0);
                starting
                    .task(async move {
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
        let mut runtime =
            Runtime::threaded(2, &store, "urn:test:me", manual("2026-11-09T12:00:00Z"), vec![waiting]).unwrap();
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
        let due = package(
            "due",
            |starting| starting.every(0.0, 0),
            |woke, pass| {
                if woke == Woke::Due(0) {
                    pass.hold("due");
                    let at = pass.now.checked_add_day_time_duration(seconds(0.2)).unwrap();
                    pass.wake_at(at);
                }
            },
        );
        let mut runtime = Runtime::new(&store, "urn:test:me", manual("2026-11-11T12:00:00Z"), vec![due]).unwrap();
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
        let wakes = package(
            "wakes",
            |starting| starting.every(0.0, 0),
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
        let mut runtime = Runtime::threaded(2, &store, "urn:test:me", clock, vec![wakes]).unwrap();
        let began = std::time::Instant::now();
        assert_eq!(runtime.run(None, 60.0).unwrap(), MET);
        assert!(began.elapsed() >= Duration::from_millis(150), "it did not wait");
        assert!(began.elapsed() < Duration::from_secs(30), "it waited too long");
        assert_eq!(*runs.lock().unwrap(), 3);
    }

    const STEP: &str = "http://example.org/test#Stepping";

    /// Begins and ends an activity at every pass.
    fn begins() -> (String, Registers) {
        package(
            "begins",
            |starting| starting.every(0.0, 0),
            |woke, pass| {
                if woke == Woke::Due(0) {
                    let activity = pass.begin(STEP, &[]);
                    pass.end(activity);
                }
            },
        )
    }

    #[test]
    fn an_activitys_start_is_heard_by_class_under_the_name_it_was_said_with() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = manual("2026-11-10T12:00:00Z");
        let heard: Arc<Mutex<Vec<Heard>>> = Arc::default();
        let said: Arc<Mutex<Vec<NamedNode>>> = Arc::default();
        let into = heard.clone();
        //  HEARS EVERY START it is told of.
        let hears = package(
            "hears",
            |starting| starting.hears(crate::activity::STARTED, 0),
            move |woke, _| {
                if let Woke::Event(_, event) = woke {
                    into.lock().unwrap().push(event);
                }
            },
        );
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone(), vec![begins(), hears]).unwrap();
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
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone(), vec![begins()]).unwrap();
        runtime.drain(clock.now()).unwrap();
        assert!(
            !runtime.watch.connected(),
            "an emitter that asks whether anybody watches is still told no"
        );
    }

    /// Says an activity's start to whoever hears it, and the hearer writes it down: by passes, the package after it is
    /// ticked only once the start was heard.
    #[test]
    fn by_passes_a_package_is_ticked_after_everything_the_packages_before_it_said_was_heard() {
        let seen: Arc<Mutex<Vec<&'static str>>> = Arc::default();
        let order = |name: &'static str, heard: &'static str| {
            let seen = seen.clone();
            package(
                name,
                |starting| {
                    starting.every(0.0, 0);
                    starting.hears(crate::activity::STARTED, 1);
                },
                move |woke, pass| match woke {
                    Woke::Due(_) => {
                        seen.lock().unwrap().push(name);
                        if name == "first" {
                            let activity = pass.begin(STEP, &[]);
                            pass.end(activity);
                        }
                    }
                    Woke::Event(..) => seen.lock().unwrap().push(heard),
                    _ => {}
                },
            )
        };
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = manual("2026-11-11T12:00:00Z");
        let packages = vec![order("first", "first heard"), order("second", "second heard")];
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone(), packages).unwrap();
        assert_eq!(runtime.parts(), ["first", "second"]);
        runtime.drain(clock.now()).unwrap();
        assert_eq!(
            *seen.lock().unwrap(),
            ["first", "first heard", "second heard", "second"]
        );
    }

    /// A package whose task ended is never waited for.
    #[test]
    fn a_task_that_ended_holds_nothing_busy() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = manual("2026-11-11T12:00:00Z");
        let gone: (String, Registers) = (
            "gone".into(),
            Box::new(|runtime| {
                let mut starting = runtime.starting("gone");
                starting.every(0.0, 0);
                runtime.register(starting, |mut seat| async move {
                    let _ = seat.next().await;
                });
                Ok(())
            }),
        );
        let mut runtime = Runtime::new(&store, "urn:test:me", clock.clone(), vec![gone]).unwrap();
        runtime.drain(clock.now()).unwrap();
        runtime.drain(clock.now()).unwrap();
        runtime.stop();
    }
}
