//! WHAT A PACKAGE'S TASK IS HANDED, AND WHERE PACKAGES MEET (a-package-is-a-task-that-awaits-its-events). A package
//! is one async function: it makes its core, and loops - it awaits what it hears (`Hears::next`), an arrival
//! (`Arrived::wait`), the clock (`Handed::sleep_until`) or the run's end (`Handed::stopped`), calls its core, and
//! says what happened. The kernel knows no package and no word of what one does: a package REGISTERS ITSELF, its
//! crate submitting its name and its start (`Package`) to a registry the linker collects, and whoever runs an agent
//! starts each one (`Booted::start`), inside the agent's booting: a package decides whether it runs, joins bringing its
//! documents, says it booted, and goes on as its task - THE LIFECYCLE, activities of the kernel's the packages hear on
//! the events as they hear any other (the-lifecycle-is-activities-the-packages-hear).
//!
//! WHAT IT IS HANDED (`Handed`) is plain: the store, the agent's id, the clock, THE EVENTS - where every package says
//! what happened and subscribes to what it hears, the one thing packages share - and what reaches OUTSIDE, the
//! connectors a deployment makes from its environment and a test hands in.
//!
//! A PACKAGE HEARS AN EVENT BY ITS CLASS (`Hears::event`), the class and every class the vocabulary puts beneath it,
//! and A KIND OF GRAPH WRITTEN (`Hears::graph`): every graph a package says it wrote (`Turn::done`) is sent to each
//! task hearing a kind the catalogue says it is. A task hears everything in the order it was said, each under the tag
//! it asked with. WHAT A TASK SAYS WHILE IT HANDLES WHAT WOKE IT IS HEARD WHEN IT NEXT WAITS, its graphs before its
//! events, so a hearer never starts on a sayer's half-written work.
//!
//! THE RUN ENDS WHEN NOTHING HOLDS THE AGENT (`Running::released`), as the last to let go said: `met`, `planned` or
//! `unreachable`; or when it is halted, `unfinished`.

mod hearing;
mod life;
mod provided;

pub use hearing::*;
pub use life::*;
pub use provided::*;

#[cfg(test)]
mod tests {
    use std::sync::atomic::AtomicBool;
    use std::sync::{Arc, Mutex};

    use oxsdatatypes::DateTime;

    use super::*;
    use crate::clock::{Clock, Elapsing, seconds};
    use crate::store::Store;
    use tokio::sync::watch;

    const STEP: &str = "http://example.org/test#Stepping";

    /// What a test's packages write down, provided.
    type Seen = Arc<Mutex<Vec<String>>>;

    fn noon() -> DateTime {
        "2026-11-12T12:00:00Z".parse().unwrap()
    }

    /// An agent over `store` with no world, so no boot is begun: what the kernel's own cases start.
    fn booted(store: &Store, clock: Arc<dyn Clock>, provided: Provided) -> Booted {
        let (stop, stopped) = watch::channel(false);
        Booted {
            handed: handed(store, "urn:test:me", clock, provided, stopped),
            stop,
            first: Vec::new(),
        }
    }

    async fn running(names: &[&str], seen: &Seen) -> Running {
        let store = Store::new().unwrap();
        let provided = Provided::default();
        provided.provide(seen.clone());
        let names: Vec<String> = names.iter().map(|n| n.to_string()).collect();
        booted(&store, Arc::new(Elapsing::from(noon())), provided)
            .first(&names)
            .unwrap()
            .start()
            .await
            .unwrap()
    }

    fn seen_by(handed: &Handed) -> Seen {
        handed
            .provided
            .take::<Seen>()
            .inspect(|s| handed.provided.provide(s.clone()))
            .unwrap()
    }

    //  BEGINS AND ENDS AN ACTIVITY as the run begins, writes down that it did, and then that it waited.
    inventory::submit! { Package { name: "test/begins", start: |handed| named(handed, "test/begins", |handed| {
        let (handed, seen) = (handed.clone(), seen_by(handed));
        Ok(Some(Box::pin(async move {
            let mut turn = handed.turn();
            let activity = turn.begin(STEP, &[]);
            turn.end(activity);
            seen.lock().unwrap().push("begun".into());
            handed.stopped().await;
            Ok(())
        })))
    }) } }

    //  HEARS EVERY START said, and writes each down but the lifecycle's, which the kernel says of every package.
    inventory::submit! { Package { name: "test/hears", start: |handed| named(handed, "test/hears", |handed| {
        let (handed, seen) = (handed.clone(), seen_by(handed));
        let mut hears = handed.events.hears();
        hears.event(crate::activity::STARTED, 7);
        Ok(Some(Box::pin(async move {
            loop {
                let woke = tokio::select! {
                    biased;
                    _ = handed.stopped() => break,
                    woke = hears.next() => woke,
                };
                match woke {
                    Some(Woke::Event(tag, event)) => {
                        let kind = event.activity.map(|(_, k)| k).unwrap_or_default();
                        if !kind.starts_with("http://example.org/orexis#") {
                            seen.lock().unwrap().push(format!("heard {tag} {kind}"));
                        }
                    }
                    _ => break,
                }
            }
            Ok(())
        })))
    }) } }

    //  HOLDS THE AGENT, and lets it go an hour on by the clock.
    inventory::submit! { Package { name: "test/holds", start: |handed| named(handed, "test/holds", |handed| {
        let (handed, seen) = (handed.clone(), seen_by(handed));
        Ok(Some(Box::pin(async move {
            let mut turn = handed.turn();
            turn.hold("holds");
            let at = turn.now.checked_add_day_time_duration(seconds(3600.0)).unwrap();
            handed.sleep_until(Some(at)).await;
            let mut turn = handed.turn();
            seen.lock().unwrap().push(crate::clock::isoformat(turn.now));
            turn.release("holds", Some(PLANNED));
            handed.stopped().await;
            Ok(())
        })))
    }) } }

    //  WAITS FOR AN ARRIVAL, rung from outside the agent a moment after the run begins, and holds until then.
    inventory::submit! { Package { name: "test/arrives", start: |handed| named(handed, "test/arrives", |handed| {
        let (handed, seen) = (handed.clone(), seen_by(handed));
        let mut arrived = handed.arrived();
        let wake = arrived.wake();
        tokio::spawn(async move {
            tokio::time::sleep(std::time::Duration::from_secs(5)).await;
            wake.ring();
        });
        Ok(Some(Box::pin(async move {
            handed.turn().hold("arrives");
            arrived.wait().await;
            seen.lock().unwrap().push("arrived".into());
            handed.turn().release("arrives", None);
            handed.stopped().await;
            Ok(())
        })))
    }) } }

    #[tokio::test(start_paused = true)]
    async fn an_activitys_start_is_heard_by_class_once_its_sayer_waits() {
        let seen = Seen::default();
        let running = running(&["test/begins", "test/hears"], &seen).await;
        running.settled().await.unwrap();
        assert_eq!(*seen.lock().unwrap(), ["begun", &format!("heard 7 {STEP}")]);
        assert_eq!(running.parts(), ["test/begins", "test/hears"]);
        running.stop().await;
    }

    #[tokio::test(start_paused = true)]
    async fn nobody_hearing_connects_nothing() {
        let seen = Seen::default();
        let running = running(&["test/begins"], &seen).await;
        running.settled().await.unwrap();
        assert!(
            !running.handed.events.watch().connected(),
            "an emitter that asks whether anybody watches is still told no"
        );
        running.stop().await;
    }

    #[tokio::test(start_paused = true)]
    async fn the_run_ends_when_nothing_holds_the_agent_as_the_last_to_let_go_said() {
        let seen = Seen::default();
        let running = running(&["test/holds"], &seen).await;
        let began = std::time::Instant::now();
        assert_eq!(running.released().await.unwrap(), PLANNED);
        assert_eq!(
            *seen.lock().unwrap(),
            ["2026-11-12T13:00:00+00:00"],
            "an hour on, by the clock"
        );
        assert!(
            began.elapsed() < std::time::Duration::from_secs(5),
            "and no hour waited"
        );
        running.stop().await;
    }

    #[tokio::test(start_paused = true)]
    async fn an_arrival_from_outside_ends_the_tasks_wait() {
        let seen = Seen::default();
        let running = running(&["test/arrives"], &seen).await;
        assert_eq!(running.released().await.unwrap(), MET);
        assert_eq!(*seen.lock().unwrap(), ["arrived"]);
        running.stop().await;
    }

    #[tokio::test(start_paused = true)]
    async fn a_halt_ends_the_run_unfinished() {
        let seen = Seen::default();
        let mut running = running(&["test/holds"], &seen).await;
        let halt = Arc::new(AtomicBool::new(true));
        running.halt = Some(halt);
        running.wake().ring();
        assert_eq!(running.released().await.unwrap(), UNFINISHED);
        running.stop().await;
    }

    /// Three graphs written in one turn, two of a kind a task hears and one of another: the task is told the two
    /// together, once, in the order they were written, and nothing of the third.
    #[test]
    fn what_one_turn_wrote_of_a_kind_is_told_as_one_thing() {
        use crate::ontology::{BELIEF, CATALOGUE_GRAPH};
        let store = Store::new().unwrap();
        store
            .update(&format!(
                "PREFIX orexis: <http://example.org/orexis#>
                 INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph }} \
                 GRAPH <urn:test:one> {{ <urn:test:one> a orexis:BeliefGraph }} \
                 GRAPH <urn:test:other> {{ <urn:test:other> a orexis:ActionGraph }} \
                 GRAPH <urn:test:two> {{ <urn:test:two> a orexis:BeliefGraph }} }}"
            ))
            .unwrap();
        let events = Events::new(&store);
        let mut hears = events.hears();
        hears.graph(BELIEF, 3);
        let written = ["urn:test:one", "urn:test:other", "urn:test:two"];
        events.wrote(written.iter().map(|g| g.to_string()).collect()).unwrap();
        assert_eq!(
            hears.inbox.try_recv().ok(),
            Some(Woke::Graphs(
                3,
                vec!["urn:test:one".to_string(), "urn:test:two".to_string()]
            ))
        );
        assert!(hears.inbox.try_recv().is_err(), "told once");
    }

    #[test]
    fn a_package_nobody_registered_is_refused() {
        let store = Store::new().unwrap();
        let clock = Arc::new(crate::clock::Manual::at(noon()));
        let refused = booted(&store, clock, Provided::default()).first(&["test/absent".to_string()]);
        assert!(refused.is_err());
    }
}
