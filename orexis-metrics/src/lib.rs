//! METRICS, as `orexis-metrics/` keeps them: every reported event tallied in memory, and written once a window with
//! every level as it last stood — reading an event only through its marks (`orexis::events`), so nothing here names a
//! package's word. Created only where a metrics sink is loaded.
//!
//! AN EVENT IS NOT A POINT. A counted event is added to the window's TALLY for its measurement and its tags: how many
//! (`count`), for each VALUE its sum, mean and max, all floats so a field never changes type between windows, and for
//! each FLAG how many raised it, nought where none did. A LEVEL is kept as it last stood, in the type it was said in.
//! At the end of the window the tallies and the levels are written, every point stamped at the flush's own instant,
//! and the next opens.
//!
//! REAL TIME, NEVER THE AGENT'S: the window is kept by a monotonic real clock and a flush is stamped by the wall, so
//! nothing here reads the agent's timeline, which may run fast or tick per read. The window's length is the
//! environment's, `METRICS_INTERVAL_S`, sixty seconds where nothing says. Every point is tagged with the world and the
//! agent. The window is written when a pass ends on the first pass by which it has run its length, so a window holds
//! whole passes, and as the part stops, since a stop is an exit.

use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};
use std::time::Instant;

use oxsdatatypes::DateTime;

use orexis::events::{Event, Field, Mark, Number, Point, Watch, counted, round6};
use orexis::runtime::{PASS_METRIC, Runtime};
use orexis::series::Sink;

/// The window's length where the environment says none, and the key it is said under.
pub const INTERVAL_S: f64 = 60.0;
pub const INTERVAL_KEY: &str = "METRICS_INTERVAL_S";

/// The window's length as the environment says it, or sixty seconds where it says none or no positive number.
pub fn load(env: &dyn Fn(&str) -> Option<String>) -> f64 {
    match env(INTERVAL_KEY) {
        None => INTERVAL_S,
        Some(told) => match told.parse::<f64>() {
            Ok(s) if s > 0.0 => s,
            _ => {
                log::warn!("{INTERVAL_KEY}={told:?} is no positive number of seconds — the window is {INTERVAL_S}s");
                INTERVAL_S
            }
        },
    }
}

#[derive(Default)]
struct Tally {
    count: i64,
    flags: Vec<(String, i64)>,
    values: Vec<(String, (i64, f64, f64))>,
}

impl Tally {
    fn add(&mut self, marks: &[(&'static str, Mark)]) {
        self.count += 1;
        for (name, mark) in marks {
            match mark {
                Mark::Flag(raised) => match self.flags.iter_mut().find(|(n, _)| n == name) {
                    Some((_, c)) => *c += i64::from(*raised),
                    None => self.flags.push((name.to_string(), i64::from(*raised))),
                },
                Mark::Value(Some(v)) => match self.values.iter_mut().find(|(n, _)| n == name) {
                    Some((_, (n, total, most))) => {
                        *n += 1;
                        *total += v;
                        *most = most.max(*v);
                    }
                    None => self.values.push((name.to_string(), (1, *v, *v))),
                },
                _ => {}
            }
        }
    }

    fn fields(&self) -> BTreeMap<String, Field> {
        let mut out = BTreeMap::from([("count".to_string(), Field::Int(self.count))]);
        for (name, c) in &self.flags {
            out.insert(name.clone(), Field::Int(*c));
        }
        for (name, (n, total, most)) in &self.values {
            out.insert(format!("{name}_sum"), Field::Float(round6(*total)));
            out.insert(format!("{name}_mean"), Field::Float(round6(total / *n as f64)));
            out.insert(format!("{name}_max"), Field::Float(round6(*most)));
        }
        out
    }
}

type Key = (String, Vec<(String, String)>);

/// One agent's window over its metrics sink.
pub struct Window {
    pub sink: Sink,
    pub interval_s: f64,
    who: Vec<(String, String)>,
    tallies: BTreeMap<Key, Tally>,
    levels: BTreeMap<Key, BTreeMap<String, Field>>,
    opened: f64,
    /// The real monotonic clock in seconds, and the wall a flush is stamped by — a test's own, so it never sleeps.
    pub monotonic: Box<dyn Fn() -> f64 + Send + Sync>,
    pub wall: Box<dyn Fn() -> DateTime + Send + Sync>,
}

impl Window {
    /// A window over `sink`, its points tagged with `world` and `agent`.
    pub fn new(sink: Sink, interval_s: f64, world: Option<&str>, agent: Option<&str>) -> Self {
        let started = Instant::now();
        let monotonic: Box<dyn Fn() -> f64 + Send + Sync> = Box::new(move || started.elapsed().as_secs_f64());
        let who = [("world", world), ("agent", agent)]
            .iter()
            .filter_map(|(k, v)| v.map(|v| (k.to_string(), v.to_string())))
            .collect();
        Window {
            sink,
            interval_s,
            who,
            tallies: BTreeMap::new(),
            levels: BTreeMap::new(),
            opened: monotonic(),
            monotonic,
            wall: Box::new(DateTime::now),
        }
    }

    /// Open the window afresh on the clock it is now kept by.
    pub fn reopen(&mut self) {
        self.opened = (self.monotonic)();
    }

    /// Add `event` to the window where it reports: counted, its values and flags aggregated, its levels kept as they
    /// last stood — under its measurement and the tags it carries.
    pub fn tally(&mut self, event: &dyn Event) {
        let Some(name) = event.metric() else { return };
        let marks = event.marks();
        if marks.is_empty() {
            return;
        }
        let mut tags: Vec<(String, String)> = marks
            .iter()
            .filter_map(|(n, m)| match m {
                Mark::Tag(Some(v)) => Some((n.to_string(), v.clone())),
                _ => None,
            })
            .collect();
        tags.sort();
        let key = (name.to_string(), tags);
        if counted(&marks) {
            self.tallies.entry(key.clone()).or_default().add(&marks);
        }
        let levels: Vec<(String, Field)> = marks
            .iter()
            .filter_map(|(n, m)| match m {
                Mark::Level(Some(Number::Int(i))) => Some((n.to_string(), Field::Int(*i))),
                Mark::Level(Some(Number::Float(f))) => Some((n.to_string(), Field::Float(round6(*f)))),
                _ => None,
            })
            .collect();
        if !levels.is_empty() {
            self.levels.entry(key).or_default().extend(levels);
        }
    }

    /// Whether the window is over, on the real monotonic clock.
    pub fn due(&self) -> bool {
        (self.monotonic)() - self.opened >= self.interval_s
    }

    /// Write the window: every tally and every level as it last stood, a point per measurement and tag set, each at
    /// the flush's instant, and open the next. The points written.
    pub fn flush(&mut self) -> Vec<Point> {
        let mut held: BTreeMap<Key, BTreeMap<String, Field>> = std::mem::take(&mut self.tallies)
            .into_iter()
            .map(|(k, t)| (k, t.fields()))
            .collect();
        for (key, levels) in std::mem::take(&mut self.levels) {
            held.entry(key).or_default().extend(levels);
        }
        self.opened = (self.monotonic)();
        let at = (self.wall)();
        let points: Vec<Point> = held
            .into_iter()
            .map(|((measurement, tags), fields)| Point {
                measurement,
                tags: self.who.iter().cloned().chain(tags).collect(),
                fields,
                time: Some(at),
            })
            .collect();
        if !points.is_empty() {
            self.sink.write(&points);
        }
        points
    }
}

/// The metrics part: every reported event tallied, the window written after the pass that ends it and as it stops.
pub struct Metrics {
    pub window: Arc<Mutex<Window>>,
}

impl Metrics {
    /// The part, hearing every event `watch` is said.
    pub fn new(window: Window, watch: &Watch) -> Self {
        let window = Arc::new(Mutex::new(window));
        let heard = window.clone();
        watch.connect(move |event, _| {
            let mut window = heard.lock().unwrap();
            window.tally(event);
            if event.metric() == Some(PASS_METRIC) && window.due() {
                window.flush();
            }
        });
        Metrics { window }
    }
}

impl Metrics {
    /// METRICS STARTING ITSELF on a runtime: a task that waits for the run's end, and writes the last window as it
    /// stops; what it tallies it hears on the watch.
    pub fn start(self, runtime: &mut Runtime) {
        let wait = runtime.wait("metrics");
        runtime.spawn(wait, move |mut wait| async move {
            while wait.next().await.is_some() {}
            self.window.lock().unwrap().flush();
        });
    }
}

#[cfg(test)]
mod tests {
    //! The window, held to what `agent/metrics/tests/test_window.py` holds the Python one to.

    use super::*;

    struct Tried {
        outcome: Option<&'static str>,
        duration_s: Option<f64>,
        weighed: Option<f64>,
        gave_up: bool,
    }

    impl Event for Tried {
        fn metric(&self) -> Option<&'static str> {
            Some("tried")
        }
        fn marks(&self) -> Vec<(&'static str, Mark)> {
            vec![
                ("outcome", Mark::Tag(self.outcome.map(str::to_string))),
                ("duration_s", Mark::Value(self.duration_s)),
                ("weighed", Mark::Value(self.weighed)),
                ("gave_up", Mark::Flag(self.gave_up)),
            ]
        }
    }

    struct Held(&'static str, Number);

    impl Event for Held {
        fn metric(&self) -> Option<&'static str> {
            Some("held")
        }
        fn marks(&self) -> Vec<(&'static str, Mark)> {
            vec![
                ("scope", Mark::Tag(Some(self.0.into()))),
                ("worlds", Mark::Level(Some(self.1))),
            ]
        }
    }

    fn tried(outcome: &'static str, duration_s: Option<f64>, weighed: f64, gave_up: bool) -> Tried {
        Tried {
            outcome: Some(outcome),
            duration_s,
            weighed: Some(weighed),
            gave_up,
        }
    }

    fn window(written: Arc<Mutex<Vec<Point>>>) -> (Window, Arc<Mutex<f64>>) {
        let real = Arc::new(Mutex::new(1000.0));
        let at = real.clone();
        let sink = Sink::new(
            "METRICS",
            "m",
            Box::new(move |_, points| {
                written.lock().unwrap().extend(points.iter().cloned());
                Ok(())
            }),
        );
        let mut w = Window::new(sink, 60.0, Some("hanoi"), Some("mover"));
        w.monotonic = Box::new(move || *at.lock().unwrap());
        w.wall = Box::new(|| orexis::clock::instant("2030-06-01T08:00:00+00:00").unwrap());
        w.reopen();
        (w, real)
    }

    #[test]
    fn an_event_is_tallied_and_written_once_a_window() {
        let written = Arc::new(Mutex::new(Vec::new()));
        let (mut w, real) = window(written.clone());
        w.tally(&tried("Exhausted", Some(0.5), 20.0, true));
        w.tally(&tried("Exhausted", Some(1.5), 20.0, false));
        w.tally(&tried("Satisfied", Some(0.25), 7.0, false));
        *real.lock().unwrap() = 1059.0;
        assert!(
            !w.due() && written.lock().unwrap().is_empty(),
            "a window is sixty seconds"
        );
        *real.lock().unwrap() = 1060.0;
        assert!(w.due());
        let points: BTreeMap<String, Point> = w.flush().into_iter().map(|p| (p.tags["outcome"].clone(), p)).collect();
        let f = |x: f64| Field::Float(x);
        assert_eq!(
            points["Exhausted"].fields,
            BTreeMap::from([
                ("count".to_string(), Field::Int(2)),
                ("gave_up".to_string(), Field::Int(1)),
                ("duration_s_sum".to_string(), f(2.0)),
                ("duration_s_mean".to_string(), f(1.0)),
                ("duration_s_max".to_string(), f(1.5)),
                ("weighed_sum".to_string(), f(40.0)),
                ("weighed_mean".to_string(), f(20.0)),
                ("weighed_max".to_string(), f(20.0)),
            ])
        );
        assert_eq!(points["Satisfied"].fields["gave_up"], Field::Int(0));
        for (o, p) in &points {
            assert_eq!(p.measurement, "tried");
            assert_eq!(
                p.tags,
                BTreeMap::from([
                    ("world".into(), "hanoi".into()),
                    ("agent".into(), "mover".into()),
                    ("outcome".into(), o.clone())
                ])
            );
        }
        assert_eq!(written.lock().unwrap().len(), 2);
        assert!(!w.due() && w.flush().is_empty(), "the next window opened empty");
    }

    #[test]
    fn a_level_is_written_as_it_last_stood_in_its_type_and_only_in_a_window_that_said_it() {
        let (mut w, _) = window(Arc::new(Mutex::new(Vec::new())));
        w.tally(&Held("hanoi", Number::Int(20)));
        w.tally(&Held("hanoi", Number::Int(7)));
        w.tally(&Held("courier", Number::Float(2.5)));
        let points: BTreeMap<String, Field> = w
            .flush()
            .into_iter()
            .map(|p| (p.tags["scope"].clone(), p.fields["worlds"].clone()))
            .collect();
        assert_eq!(
            points,
            BTreeMap::from([("hanoi".into(), Field::Int(7)), ("courier".into(), Field::Float(2.5))])
        );
        assert!(w.flush().is_empty());
    }

    #[test]
    fn the_window_is_the_environments_or_sixty_seconds() {
        assert_eq!(load(&|_| None), 60.0);
        assert_eq!(load(&|_| Some("15".into())), 15.0);
        assert_eq!(load(&|_| Some("never".into())), 60.0);
        assert_eq!(load(&|_| Some("0".into())), 60.0);
    }
}
