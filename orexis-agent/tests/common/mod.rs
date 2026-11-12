//! What every world's test does of a running agent: its clock on Tokio's paused time, which runs ahead whenever every
//! task is idle, and the three waits a scenario is made of - until everything said was handled, until a stretch of
//! the agent's time has passed, and until nothing holds the agent.
#![allow(dead_code)]

use std::sync::Arc;
use std::time::Duration;

use oxsdatatypes::DateTime;

use orexis::clock::Elapsing;
use orexis::task::{Running, UNFINISHED};

/// The agent's clock from `at`, on Tokio's time.
pub fn clock(at: DateTime) -> Arc<Elapsing> {
    Arc::new(Elapsing::from(at))
}

/// Until everything said so far was heard and done with.
pub async fn settled(running: &Running) {
    running.settled().await.unwrap();
}

/// Let `seconds` of the agent's time pass, the agent doing whatever falls due in them.
pub async fn pass(running: &Running, seconds: f64) {
    tokio::time::sleep(Duration::from_secs_f64(seconds)).await;
    //  WHAT FALLS DUE AT THE VERY INSTANT THE STRETCH ENDS is the agent's to do before the test looks: its tasks'
    //  sleeps ended with this one, and each is let run.
    for _ in 0..8 {
        tokio::task::yield_now().await;
    }
    running.settled().await.unwrap();
}

/// Until every agent of a society has settled: what one tells another wakes it, so they are waited for in turn until
/// a round finds them all at rest.
pub async fn settled_all(society: &[Running]) {
    loop {
        let mut busy = false;
        for running in society {
            busy |= !running.idle();
            running.settled().await.unwrap();
        }
        if !busy {
            break;
        }
    }
}

/// Let `seconds` of the society's one time pass, each agent doing whatever falls due in them.
pub async fn pass_all(society: &[Running], seconds: f64) {
    tokio::time::sleep(Duration::from_secs_f64(seconds)).await;
    for _ in 0..8 {
        tokio::task::yield_now().await;
    }
    settled_all(society).await;
}

/// How the run ends within `seconds` of the agent's time: as the last to let go said, or `unfinished` where something
/// still holds it then.
pub async fn outcome(running: &Running, seconds: u64) -> String {
    match tokio::time::timeout(Duration::from_secs(seconds), running.released()).await {
        Ok(outcome) => outcome.unwrap(),
        Err(_) => UNFINISHED.to_string(),
    }
}

struct Stderr;

impl log::Log for Stderr {
    fn enabled(&self, _: &log::Metadata) -> bool {
        true
    }
    fn log(&self, record: &log::Record) {
        eprintln!("LOG {} {}", record.level(), record.args());
    }
    fn flush(&self) {}
}

/// Say what the agent logs on stderr, for a test being looked into.
pub fn logged() {
    static LOGGER: Stderr = Stderr;
    let _ = log::set_logger(&LOGGER);
    log::set_max_level(log::LevelFilter::Debug);
}
