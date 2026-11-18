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
//! meter's role's to say (`metrics:windowS`), sixty seconds where it says nothing. Every point is tagged with the world and the
//! agent. The window is written when a pass ends on the first pass by which it has run its length, so a window holds
//! whole passes, and as the part stops, since a stop is an exit.
//!
//! - `window`: the window every reported event is tallied in, and written once it is over;
//! - `meter`: the package's core, the meter the self plays and the window it tallies into;
//! - the start, below the modules, and nothing else: the meter made, its window handed or made, and written as it stops.

use orexis::series::Sink;
use orexis::task::{Handed, Package};

mod meter;
mod window;

pub use meter::Meter;
pub use window::Window;

inventory::submit! { Package { name: "metrics", start } }

/// THE DOCUMENTS THIS PACKAGE BRINGS as it joins, in the order it puts them in.
const DOCUMENTS: orexis::task::Documents = orexis::documents!("ontology.ttl");

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
const ROLE: &str = "http://example.org/orexis/metrics#Meter";

/// THE METRICS' START, which every package this binary holds is given: it joins where the self plays a meter and
/// declines otherwise; joined, its meter is made and its window taken where a test hands one, made where the agent is
/// deployed and the world says where the store its role names answers, and none otherwise; it says it booted;
/// and unless checked, it waits for the agent to stop and writes what the window holds.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE])? {
            return Ok(());
        }
        handed.joins(&DOCUMENTS).await?;
        let mut meter = Meter::new(&handed.store)?;
        let window = match handed.provided.take::<Window>() {
            Some(window) => Some(window),
            None => match handed.provided.read::<orexis::task::Deployed>() {
                Some(deployed) => {
                    match Sink::deployed(&handed.store, orexis::series::METRICS, &orexis::series::environment)? {
                        Some((sink, _)) => {
                            log::info!("{} writes its metrics every {}s", handed.id, meter.window_s);
                            Some(Window::new(
                                sink,
                                meter.window_s,
                                Some(&deployed.world),
                                Some(&handed.id),
                            ))
                        }
                        None => None,
                    }
                }
                None => None,
            },
        };
        let Some(window) = window else {
            handed.booted().await?;
            return Ok(());
        };
        //  WHAT A CHAT READS OF THE METRICS is the series this writes.
        let reader = window.sink.reader();
        handed
            .provided
            .alter(|reads: &mut orexis::series::Reads| reads.metrics = Some(reader));
        meter.tally(window, handed.events.watch());
        if !handed.booted().await? {
            return Ok(());
        }
        handed.stopped().await;
        meter.flush().await;
        Ok(())
    })
}
