//! WHAT A TASK HEARS AND SAYS: the events it subscribes to by class and kind of graph, the turn it says what
//! happened in, the arrivals that wake it, and how the run is released.

use std::cell::RefCell;
use std::collections::{BTreeSet, HashMap};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, RwLock};

use oxsdatatypes::DateTime;

use oxigraph::model::{NamedNode, Term};
use tokio::sync::mpsc::{UnboundedReceiver, UnboundedSender, unbounded_channel};
use tokio::sync::{Notify, watch};

use crate::Error;
use crate::activity::{Activity, Ended, Started, Wrote};
use crate::events::{Event, Laps, Mark, Number, Watch};
use crate::store::Store;

pub const MET: &str = "met";
pub const PLANNED: &str = "planned";
pub const UNREACHABLE: &str = "unreachable";
pub const UNFINISHED: &str = "unfinished";

pub const PASS_METRIC: &str = "pass";

/// A pass, or a stretch of the run with something busy, and how long it took: by each part that marked a lap, by
/// the name it marked it under, the kernel naming none.
#[derive(Clone, Debug, PartialEq)]
pub struct Passed {
    pub duration_s: f64,
    pub laps: Vec<(&'static str, f64)>,
    pub quads: Option<i64>,
    pub uptime_s: f64,
}

impl Event for Passed {
    fn metric(&self) -> Option<&'static str> {
        Some(PASS_METRIC)
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        let mut marks = vec![("duration_s", Mark::Value(Some(self.duration_s)))];
        marks.extend(self.laps.iter().map(|(part, s)| (*part, Mark::Value(Some(*s)))));
        marks.push(("quads", Mark::Level(self.quads.map(Number::Int))));
        marks.push(("uptime_s", Mark::Level(Some(Number::Float(self.uptime_s)))));
        marks
    }
}

pub(super) fn started() -> std::time::Instant {
    static STARTED: std::sync::OnceLock<std::time::Instant> = std::sync::OnceLock::new();
    *STARTED.get_or_init(std::time::Instant::now)
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

/// WHAT A TASK DOES EVERY SO MANY SECONDS of the one timeline: due when the run begins, and again that long after
/// each time it fell due.
pub struct Every {
    pub(super) seconds: f64,
    pub(super) at: Option<DateTime>,
}

impl Every {
    pub fn new(seconds: f64) -> Self {
        Every { seconds, at: None }
    }

    /// Whether it is due at `now`; if so, it is next due its seconds on.
    pub fn due(&mut self, now: DateTime) -> bool {
        if self.at.is_some_and(|at| now < at) {
            return false;
        }
        self.at = Some(
            now.checked_add_day_time_duration(crate::clock::seconds(self.seconds))
                .unwrap_or(now),
        );
        true
    }

    /// When it is next due; never by itself where its seconds are nought - it is done after whatever its task
    /// heard, and a wait until now would never be one.
    pub fn at(&self) -> Option<DateTime> {
        if self.seconds > 0.0 { self.at } else { None }
    }
}

/// The sooner of two instants, either of which may be none.
pub fn sooner(a: Option<DateTime>, b: Option<DateTime>) -> Option<DateTime> {
    match (a, b) {
        (Some(a), Some(b)) => Some(if b < a { b } else { a }),
        (a, b) => a.or(b),
    }
}

tokio::task_local! {
    /// WHAT A TASK SAID AND TOOK SINCE IT LAST WAITED: the events it said, told when it next waits, and how many
    /// things it took and is still busy with.
    pub(super) static TURN: RefCell<Local>;
}

#[derive(Default)]
pub(super) struct Local {
    pub(super) said: Vec<Heard>,
    pub(super) in_hand: usize,
    /// The activities open in this task, innermost last: what an event it says is said within.
    pub(super) open: Vec<NamedNode>,
}

/// THE ACTIVITY OPEN IN THE TASK SAYING SOMETHING NOW, innermost: what the watch says an event was said within, so a
/// hearer reads the activity off the event and never off the thread it is heard on. None outside any task.
pub(crate) fn within() -> Option<NamedNode> {
    TURN.try_with(|turn| turn.borrow().open.last().cloned()).ok().flatten()
}

/// `activity` is open in this task from here, or no longer.
pub(super) fn opened(activity: &NamedNode) {
    let _ = TURN.try_with(|turn| turn.borrow_mut().open.push(activity.clone()));
}

pub(super) fn closed(activity: &NamedNode) {
    let _ = TURN.try_with(|turn| turn.borrow_mut().open.retain(|a| a != activity));
}

/// Run `work`, a computation of seconds, so the tasks beside it keep their workers: where the runtime has several,
/// this worker hands its other tasks on and `work` runs in place; on one thread it simply runs.
pub fn long<T>(work: impl FnOnce() -> T) -> T {
    match tokio::runtime::Handle::try_current().map(|h| h.runtime_flavor()) {
        Ok(tokio::runtime::RuntimeFlavor::MultiThread) => tokio::task::block_in_place(work),
        _ => work(),
    }
}

/// HOW MANY THINGS ARE SENT AND NOT YET DONE WITH, across every task: nought is idle.
#[derive(Clone)]
/// When the stretch with something busy began, and how long the last one took, said AS IT ENDED: a task waking before
/// whoever says the stretch looks begins the next, and the length is never read off its beginning.
pub(super) struct Busy(
    pub(super) Arc<watch::Sender<usize>>,
    Arc<Mutex<std::time::Instant>>,
    Arc<Mutex<f64>>,
);

impl Busy {
    pub(super) fn new() -> Self {
        Busy(
            Arc::new(watch::channel(0).0),
            Arc::new(Mutex::new(std::time::Instant::now())),
            Arc::new(Mutex::new(0.0)),
        )
    }

    pub(super) fn up(&self) {
        self.0.send_modify(|n| {
            if *n == 0 {
                *self.1.lock().expect("an instant nobody poisoned") = std::time::Instant::now();
            }
            *n += 1;
        });
    }

    /// When the stretch with something busy began: the last time anything was, after nothing had been.
    pub(super) fn began(&self) -> std::time::Instant {
        *self.1.lock().expect("an instant nobody poisoned")
    }

    pub(super) fn down(&self) {
        self.0.send_modify(|n| {
            *n = n.saturating_sub(1);
            if *n == 0 {
                *self.2.lock().expect("a length nobody poisoned") = self.began().elapsed().as_secs_f64();
            }
        });
    }

    /// How long the stretch took: the last, as it ended, or where something is busy still, so far.
    pub(super) fn took(&self) -> f64 {
        if *self.0.borrow() == 0 {
            *self.2.lock().expect("a length nobody poisoned")
        } else {
            self.began().elapsed().as_secs_f64()
        }
    }
}

/// What a task hears, under the tag it asked with.
#[derive(Clone, Debug, PartialEq)]
pub enum Woke {
    /// An event of a class it hears was said.
    Event(usize, Heard),
    /// Graphs of a kind it hears were written, together: what one turn wrote of that kind.
    Graphs(usize, Vec<String>),
}

pub(super) struct Bus {
    pub(super) beliefs: Store,
    pub(super) watch: Watch,
    /// Who hears what: each task's sender, the classes of event and the kinds of graph it hears, each with its tag.
    pub(super) hearers: RwLock<Vec<Hearer>>,
    /// Every class each class said is beneath, asked once.
    pub(super) closed: Mutex<HashMap<String, Vec<String>>>,
    pub(super) busy: Busy,
    /// Whether the watch is heard: connected when the first task asks to hear an event.
    pub(super) listening: AtomicBool,
    pub(super) held: Mutex<BTreeSet<String>>,
    pub(super) outcome: Mutex<Option<String>>,
    pub(super) laps: Mutex<Option<Laps>>,
    pub(super) error: Mutex<Option<Error>>,
}

pub(super) struct Hearer {
    pub(super) to: UnboundedSender<Woke>,
    /// Each class of event heard, with the class of activity it must start or end where it is an activity's, and
    /// its tag.
    pub(super) events: Vec<(String, Option<String>, usize)>,
    pub(super) graphs: Vec<(String, usize)>,
}

/// THE EVENTS OF ONE AGENT: where its packages say what happened and subscribe to what they hear. A clone is the same
/// events.
#[derive(Clone)]
pub struct Events(pub(super) Arc<Bus>);

impl Events {
    /// The events of an agent over `beliefs`, whose vocabulary says which class is beneath which.
    pub fn new(beliefs: &Store) -> Self {
        let bus = Arc::new(Bus {
            beliefs: beliefs.clone(),
            watch: Watch::default(),
            hearers: RwLock::new(Vec::new()),
            closed: Mutex::new(HashMap::new()),
            busy: Busy::new(),
            listening: AtomicBool::new(false),
            held: Mutex::new(BTreeSet::new()),
            outcome: Mutex::new(None),
            laps: Mutex::new(None),
            error: Mutex::new(None),
        });
        Events(bus)
    }

    /// A turn at `now`, for whoever calls a package's core with no task around it: a unit test.
    pub fn turn<'a>(&'a self, now: DateTime, agent: &'a str) -> Turn<'a> {
        Turn {
            now,
            agent,
            events: self,
            next: None,
            last: None,
        }
    }

    /// THE WATCH EVERY PACKAGE SAYS ITS EVENTS TO, and whoever watches the agent hears them on.
    pub fn watch(&self) -> &Watch {
        &self.0.watch
    }

    /// WORK A TASK SETS GOING OFF ITS OWN TURN, a call it awaits on a task of its own: the agent is busy until what
    /// this answers is dropped, so nobody waiting for it to settle reads it idle while the work is under way.
    pub fn working(&self) -> Working {
        self.0.busy.up();
        Working(self.0.busy.clone())
    }

    /// What a task hears, empty until it says: it asks by `event` and `graph`, and awaits `next`.
    pub fn hears(&self) -> Hears {
        let (to, inbox) = unbounded_channel();
        let index = {
            let mut hearers = self.0.hearers.write().expect("hearers nobody poisoned");
            hearers.push(Hearer {
                to,
                events: Vec::new(),
                graphs: Vec::new(),
            });
            hearers.len() - 1
        };
        Hears {
            events: self.clone(),
            index,
            inbox,
        }
    }

    /// Whether any task hears events of `class`: whoever would say one asks first, where saying it is work.
    pub fn heard(&self, class: &str) -> bool {
        let Ok(classes) = self.closure(class) else {
            return false;
        };
        let hearers = self.0.hearers.read().expect("hearers nobody poisoned");
        hearers
            .iter()
            .any(|h| h.events.iter().any(|(c, _, _)| classes.contains(c)))
    }

    /// Hear the watch, once somebody hears events: what is said on it is told to the tasks that hear its class.
    pub(super) fn listen(&self) {
        if self.0.listening.swap(true, Ordering::SeqCst) {
            return;
        }
        let weak = Arc::downgrade(&self.0);
        self.0.watch.connect_live(move |event, named, _| {
            if let (Some(kind), Some(bus)) = (event.kind(), weak.upgrade()) {
                let heard = Heard {
                    node: named.clone(),
                    kind: kind.to_string(),
                    activity: event.activity().map(|(a, k)| (a.clone(), k.to_string())),
                    about: event.about().into_iter().map(|(p, t)| (p.to_string(), t)).collect(),
                };
                let held = TURN.try_with(|turn| turn.borrow_mut().said.push(heard.clone())).is_ok();
                if !held {
                    Events(bus).tell(heard);
                }
            }
        });
    }

    /// SAY `event` TO WHOEVER WATCHES AND TO EVERY TASK HEARING ITS CLASS, connecting nothing: what the kernel says of
    /// the lifecycle, which every package hears, so the watch is still told no where nothing else watches it. Where the
    /// tasks already hear the watch, it tells them; otherwise it is told them here, held until the sayer next waits.
    pub(super) fn say(&self, event: &dyn Event) {
        let named = self.0.watch.emit(event);
        if self.0.listening.load(Ordering::SeqCst) {
            return;
        }
        let Some(kind) = event.kind() else {
            return;
        };
        let heard = Heard {
            node: named.unwrap_or_else(crate::rdf::mint),
            kind: kind.to_string(),
            activity: event.activity().map(|(a, k)| (a.clone(), k.to_string())),
            about: event.about().into_iter().map(|(p, t)| (p.to_string(), t)).collect(),
        };
        if let Err(heard) = TURN
            .try_with(|turn| turn.borrow_mut().said.push(heard.clone()))
            .map_err(|_| heard)
        {
            self.tell(heard);
        }
    }

    /// Every class `class` is beneath, itself among them.
    pub(super) fn closure(&self, class: &str) -> Result<Vec<String>, Error> {
        let mut closed = self.0.closed.lock().expect("a closure nobody poisoned");
        if let Some(classes) = closed.get(class) {
            return Ok(classes.clone());
        }
        let classes = self.0.beliefs.closed(class)?;
        closed.insert(class.to_string(), classes.clone());
        Ok(classes)
    }

    /// Send `woke` to one task's inbox, counted busy from here; done with at once where the task has ended. Sent
    /// while no inbox is closing, so what a task that ends was sent is in its inbox as it empties it.
    pub(super) fn send(&self, to: &UnboundedSender<Woke>, woke: Woke) {
        let _open = self.0.hearers.read().expect("hearers nobody poisoned");
        self.0.busy.up();
        if to.send(woke).is_err() {
            self.0.busy.down();
        }
    }

    /// Send `event` to every task hearing a class it is beneath.
    pub(super) fn tell(&self, event: Heard) {
        let classes = match self.closure(&event.kind) {
            Ok(classes) => classes,
            Err(e) => return self.failed(e),
        };
        let to: Vec<(UnboundedSender<Woke>, usize)> = {
            let hearers = self.0.hearers.read().expect("hearers nobody poisoned");
            hearers
                .iter()
                .flat_map(|h| {
                    h.events
                        .iter()
                        .filter(|(class, of, _)| {
                            classes.contains(class)
                                && of
                                    .as_ref()
                                    .is_none_or(|of| event.activity.as_ref().is_some_and(|(_, k)| k == of))
                        })
                        .map(|(_, _, tag)| (h.to.clone(), *tag))
                })
                .collect()
        };
        for (to, tag) in to {
            self.send(&to, Woke::Event(tag, event.clone()));
        }
    }

    /// Say that `graphs` were written, to every task hearing a kind the catalogue says any of them is: WHAT ONE
    /// TURN WROTE OF A KIND IS TOLD AS ONE THING, the graphs of it together in the order they were written. One
    /// message of several readings is several percepts, and told one by one each was said and revised apart, so
    /// whoever heard the first revision decided before the rest was believed.
    pub fn wrote(&self, graphs: Vec<String>) -> Result<(), Error> {
        let asked: Vec<(UnboundedSender<Woke>, String, usize)> = {
            let hearers = self.0.hearers.read().expect("hearers nobody poisoned");
            hearers
                .iter()
                .flat_map(|h| h.graphs.iter().map(|(kind, tag)| (h.to.clone(), kind.clone(), *tag)))
                .collect()
        };
        if asked.is_empty() || graphs.is_empty() {
            return Ok(());
        }
        let mut kinds = Vec::new();
        for graph in &graphs {
            kinds.push(self.kinds(graph)?);
        }
        for (to, kind, tag) in asked {
            let of_kind: Vec<String> = graphs
                .iter()
                .zip(&kinds)
                .filter(|(_, kinds)| kinds.contains(&kind))
                .map(|(graph, _)| graph.clone())
                .collect();
            if !of_kind.is_empty() {
                self.send(&to, Woke::Graphs(tag, of_kind));
            }
        }
        Ok(())
    }

    /// Every kind the catalogue says `graph` is.
    pub(super) fn kinds(&self, graph: &str) -> Result<Vec<String>, Error> {
        let Some(cat) = self.0.beliefs.catalogue()? else {
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
            .0
            .beliefs
            .rows(&text, &[])?
            .iter()
            .filter_map(|r| crate::store::iri(r, "k"))
            .collect())
    }

    /// A task failed: the run's error, the first one kept.
    pub fn failed(&self, error: Error) {
        let mut kept = self.0.error.lock().expect("an error nobody poisoned");
        if kept.is_none() {
            *kept = Some(error);
        }
    }

    /// THE TASK WAITS: what it said since it last waited is told, and what it took it is done with.
    pub(super) fn rest(&self) {
        let rested = TURN.try_with(|turn| {
            let mut turn = turn.borrow_mut();
            (std::mem::take(&mut turn.said), std::mem::take(&mut turn.in_hand))
        });
        if let Ok((said, in_hand)) = rested {
            for heard in said {
                self.tell(heard);
            }
            for _ in 0..in_hand {
                self.0.busy.down();
            }
        }
    }

    /// WHAT THE TASK SAID IS TOLD, and it stays busy: what a start waiting on the other starts does, its sayings heard
    /// as when it rests, while it is still counted as starting.
    pub(super) fn spoke(&self) {
        let said = TURN.try_with(|turn| std::mem::take(&mut turn.borrow_mut().said));
        for heard in said.unwrap_or_default() {
            self.tell(heard);
        }
    }

    /// The task took something it was sent, counted busy since it was sent: it is in hand until the task next waits.
    /// Whoever is no task of the agent's is done with it at once.
    pub(super) fn took(&self) {
        if TURN.try_with(|turn| turn.borrow_mut().in_hand += 1).is_err() {
            self.0.busy.down();
        }
    }

    /// The task woke by itself - the clock, or the run began: busy until it next waits.
    pub(super) fn woke(&self) {
        self.0.busy.up();
        self.took();
    }

    /// Mark the end of a part of a stretch with something busy, for the stretch's event, where anybody watches.
    pub fn lap(&self, part: &str) {
        if self.0.watch.connected() {
            let mut laps = self.0.laps.lock().expect("laps nobody poisoned");
            laps.get_or_insert_with(|| Laps::since(self.0.busy.began())).lap(part);
        }
    }
}

/// WHAT A TASK HEARS: the events and graphs it asked for, in the order they were said.
pub struct Hears {
    pub(super) events: Events,
    pub(super) index: usize,
    pub(super) inbox: UnboundedReceiver<Woke>,
}

impl Hears {
    /// Hear every event of `class` said, or of a class the vocabulary puts beneath it, with `tag`.
    pub fn event(&mut self, class: &str, tag: usize) {
        self.events.listen();
        let mut hearers = self.events.0.hearers.write().expect("hearers nobody poisoned");
        hearers[self.index].events.push((class.to_string(), None, tag));
    }

    /// Hear every event of `class` the kernel says (`Events::say`), with `tag`, connecting nothing.
    pub(super) fn said(&mut self, class: &str, tag: usize) {
        let mut hearers = self.events.0.hearers.write().expect("hearers nobody poisoned");
        hearers[self.index].events.push((class.to_string(), None, tag));
    }

    /// Hear every start or end - `phase`, `activity::STARTED` or `activity::ENDED` - of an activity of `kind`, with
    /// `tag`: what a package hears of another's lifecycle, and of the agent's.
    pub fn activity(&mut self, phase: &str, kind: &str, tag: usize) {
        let mut hearers = self.events.0.hearers.write().expect("hearers nobody poisoned");
        hearers[self.index]
            .events
            .push((phase.to_string(), Some(kind.to_string()), tag));
    }

    /// Hear every graph of `kind` written, with `tag`.
    pub fn graph(&mut self, kind: &str, tag: usize) {
        let mut hearers = self.events.0.hearers.write().expect("hearers nobody poisoned");
        hearers[self.index].graphs.push((kind.to_string(), tag));
    }

    /// Whether nothing more waits to be heard.
    pub fn is_empty(&self) -> bool {
        self.inbox.is_empty()
    }

    /// WAIT FOR WHAT IS HEARD NEXT; nothing once nobody can say anything more.
    pub async fn next(&mut self) -> Option<Woke> {
        self.events.rest();
        let woke = self.inbox.recv().await?;
        self.events.took();
        Some(woke)
    }

    /// WAIT FOR WHAT IS HEARD NEXT AND STAY BUSY: what a package booting waits with, what it said told as it waits,
    /// while it is still counted as booting - so no stretch ends, and the run is not over, while a booting waits on
    /// the others.
    pub(super) async fn next_busy(&mut self) -> Option<Woke> {
        self.events.spoke();
        let woke = self.inbox.recv().await?;
        self.events.took();
        Some(woke)
    }
}

impl Drop for Hears {
    /// A task that ended holds nothing busy: nothing it was sent and never took. THE INBOX IS CLOSED AND EMPTIED
    /// WHILE NOTHING IS BEING SENT (`Events::send`): on several threads a task telling an event counts it sent
    /// before it is in the inbox, and an inbox emptied in between would leave the agent busy for ever with what
    /// arrived after.
    fn drop(&mut self) {
        let _sending = self.events.0.hearers.write().expect("hearers nobody poisoned");
        self.inbox.close();
        while self.inbox.try_recv().is_ok() {
            self.events.0.busy.down();
        }
    }
}

pub(super) struct Ring {
    pub(super) notify: Notify,
    /// Whether it rang and the task has not yet woken for it.
    pub(super) rung: AtomicBool,
    /// Whether the task that waits for it is gone.
    pub(super) gone: AtomicBool,
    pub(super) busy: Busy,
}

/// What ends a task's wait when something arrived for it from outside - or the run's, for whoever halts it.
#[derive(Clone, Default)]
pub struct Wake {
    pub(super) ring: Option<Arc<Ring>>,
    pub(super) halt: Option<Arc<Notify>>,
}

impl Wake {
    /// Something arrived.
    pub fn ring(&self) {
        if let Some(ring) = &self.ring
            && !ring.gone.load(Ordering::SeqCst)
            && !ring.rung.swap(true, Ordering::SeqCst)
        {
            ring.busy.up();
            ring.notify.notify_one();
        }
        if let Some(halt) = &self.halt {
            halt.notify_one();
        }
    }
}

/// Work under way off a task's turn: the agent busy while it is held (`Events::working`).
pub struct Working(Busy);

impl Working {
    /// THE WORK IS BACK, in the task that hears what it came to: in hand until that task next waits, as anything it is
    /// sent, so the agent stays busy while the task does what it came to and tells what it said doing it. Dropped
    /// there instead, the agent read idle between the work's end and the telling.
    pub fn back(self) {
        let busy = self.0.clone();
        std::mem::forget(self);
        if TURN.try_with(|turn| turn.borrow_mut().in_hand += 1).is_err() {
            busy.down();
        }
    }
}

impl Drop for Working {
    fn drop(&mut self) {
        self.0.down();
    }
}

/// Where a task waits for what arrives from outside.
pub struct Arrived {
    pub(super) ring: Arc<Ring>,
    pub(super) events: Events,
}

impl Arrived {
    /// What whoever hands the task an arrival rings.
    pub fn wake(&self) -> Wake {
        Wake {
            ring: Some(self.ring.clone()),
            halt: None,
        }
    }

    /// Wait until something arrived.
    pub async fn wait(&mut self) {
        self.events.rest();
        self.ring.notify.notified().await;
        self.ring.rung.store(false, Ordering::SeqCst);
        self.events.took();
    }
}

impl Drop for Arrived {
    fn drop(&mut self) {
        self.ring.gone.store(true, Ordering::SeqCst);
        if self.ring.rung.swap(false, Ordering::SeqCst) {
            self.ring.busy.down();
        }
    }
}

/// WHAT A TASK IS HANDED WITH WHAT WOKE IT: the instant it stands at, where it says what it did, and the agent's
/// life to keep or let go.
pub struct Turn<'a> {
    pub now: DateTime,
    pub agent: &'a str,
    pub(super) events: &'a Events,
    pub(super) next: Option<DateTime>,
    /// The activity this turn ended last: what the graphs it wrote are said of.
    pub(super) last: Option<NamedNode>,
}

impl Turn<'_> {
    /// WHAT THE TASK DID OF WHAT WOKE IT: the graphs it wrote, told to whoever hears their kinds, before the events
    /// it said are.
    pub fn done(&mut self, wrote: Result<Vec<String>, Error>) -> Result<(), Error> {
        let wrote = wrote?;
        self.wrote(&wrote);
        self.events.wrote(wrote)
    }

    /// Say whose `graphs` are, where anybody watches and an activity of this turn wrote them.
    pub(super) fn wrote(&self, graphs: &[String]) {
        if let Some(by) = &self.last
            && !graphs.is_empty()
            && self.events.0.watch.connected()
        {
            self.events.0.watch.emit(&Wrote {
                by: by.clone(),
                graphs: graphs.to_vec(),
            });
        }
    }

    /// One thing done of several in this turn - what a package queued for itself, each in turn: the graphs it wrote
    /// told, then the events it said, before the next is done.
    pub fn told(&mut self, wrote: Vec<String>) -> Result<(), Error> {
        self.wrote(&wrote);
        let told = self.events.wrote(wrote);
        let said = TURN
            .try_with(|turn| std::mem::take(&mut turn.borrow_mut().said))
            .unwrap_or_default();
        for heard in said {
            self.events.tell(heard);
        }
        told
    }

    /// The task is next due at `at`, with nothing heard: it waits no longer than that.
    pub fn wake_at(&mut self, at: DateTime) {
        if self.next.is_none_or(|s| at < s) {
            self.next = Some(at);
        }
    }

    /// When the task said it is next due.
    pub fn next(&self) -> Option<DateTime> {
        self.next
    }

    /// The task's policy decides again at once, with nothing heard: it is due at the next instant, a millisecond on,
    /// since two decisions never stand at one instant - a search cut short is continued from where the clock then
    /// reads, and where a test pauses the clock nothing else would move it.
    pub fn again(&mut self) {
        let next = self
            .now
            .checked_add_day_time_duration(crate::clock::microseconds(0.001));
        self.wake_at(next.unwrap_or(self.now));
    }

    /// Begin an activity of `kind`, triggered by the entities `triggers` names - what the events heard were about -
    /// and say that it started.
    pub fn begin(&mut self, kind: &'static str, triggers: &[NamedNode]) -> Activity {
        let activity = Activity::begin(kind);
        if self.events.0.watch.connected() {
            self.events.0.watch.emit(&Started {
                activity: activity.node.clone(),
                kind,
                triggers: triggers.to_vec(),
                at: self.now,
                lasting: None,
            });
        }
        opened(&activity.node);
        activity
    }

    /// The task STEPS OUT of `activity`, which goes on: what it says from here is said within none of it, until it
    /// steps back in (`step_in`). For an activity whose work is out on a thread while the task hears other events.
    pub fn step_out(&mut self, activity: &Activity) {
        closed(&activity.node);
    }

    /// The task STEPS BACK INTO `activity`, begun in an earlier turn: what it says from here is said within it.
    pub fn step_in(&mut self, activity: &Activity) {
        opened(&activity.node);
    }

    /// Say `event` happened, to whoever watches the agent.
    pub fn emit(&self, event: &dyn Event) {
        self.events.0.watch.emit(event);
    }

    /// End `activity`, and say that it ended.
    pub fn end(&mut self, activity: Activity) {
        self.last = Some(activity.node.clone());
        closed(&activity.node);
        if self.events.0.watch.connected() {
            self.events.0.watch.emit(&Ended {
                activity: activity.node.clone(),
                kind: activity.kind,
                at: self.now,
                duration_s: activity.took(),
                lasting: None,
            });
        }
    }

    /// Mark the end of a part of the stretch, for its event, where anybody watches.
    pub fn lap(&mut self, part: &str) {
        self.events.lap(part);
    }

    /// `who` keeps the agent running.
    pub fn hold(&mut self, who: &str) {
        let mut held = self.events.0.held.lock().expect("holders nobody poisoned");
        held.insert(who.to_string());
    }

    /// `who` no longer keeps the agent running, and says how it ended.
    pub fn release(&mut self, who: &str, outcome: Option<&str>) {
        self.events.0.held.lock().expect("holders nobody poisoned").remove(who);
        if let Some(outcome) = outcome {
            *self.events.0.outcome.lock().expect("an outcome nobody poisoned") = Some(outcome.to_string());
        }
    }
}
