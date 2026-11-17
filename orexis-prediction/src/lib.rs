//! PREDICTION, in Rust: the agent's foresight, ported from `orexis-prediction/` and held to what its suite asks.
//!
//! - [`foresee`]: the flows integrated from each ground as the planner lays them, every key advancing together, and
//!   a crossing of a range bound answered as the place the next ground is laid;
//! - [`ranges`]: the ranges that apply to what a sensor observes, and which side of one a number lies on;
//! - `predictor`: the package's core, the predictor the self plays and the foresight it offers;
//! - the start, below the modules, and nothing else: the predictor made, and its foresight offered at link.

use orexis::foresight::Foresees;
use orexis::task::{Handed, Package};

pub mod foresee;
pub mod ontology;
mod predictor;
pub mod ranges;

pub use predictor::Predictor;

inventory::submit! { Package { name: "prediction", start } }

/// THE DOCUMENTS THIS PACKAGE BRINGS as it joins, in the order it puts them in.
const DOCUMENTS: orexis::task::Documents = orexis::documents!("ontology.ttl");

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
const ROLE: &str = "http://example.org/orexis/prediction#Predictor";

/// PREDICTION'S START, which every package this binary holds is given: it joins where the self plays a predictor and
/// declines otherwise; joined, its predictor is made and its foresight offered, for whoever lays the grounds to take,
/// and it says it booted - and has no task, what it offers being asked for where the grounds are laid.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE])? {
            return Ok(());
        }
        handed.joins(&DOCUMENTS).await?;
        let predictor = Predictor::new(&handed.store)?;
        handed.provided.provide::<Foresees>(predictor.offered());
        handed.booted().await?;
        Ok(())
    })
}
