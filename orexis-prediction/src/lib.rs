//! PREDICTION, in Rust: the agent's foresight, ported from `orexis-prediction/` and held to what its suite asks.
//!
//! - [`foresee`]: the flows integrated from each ground as the planner lays them, every key advancing together, and
//!   a crossing of a range bound answered as the place the next ground is laid;
//! - [`ranges`]: the ranges that apply to what a sensor observes, and which side of one a number lies on;
//! - the start, below the modules: the package's part, which hears nothing and offers the foresight at link.

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::foresight::{Foresees, Foresight, Placed};
use orexis::store::Store;
use orexis::task::{Handed, Package, Task};

use crate::foresee::foresee;

pub mod foresee;
pub mod ontology;
pub mod ranges;

/// Prediction's part: its foresight, offered at link.
#[derive(Default)]
pub struct Prediction;

impl Prediction {
    /// The agent's foresight from `now`, off `beliefs`, for the planner to advance ground by ground; None where no key
    /// is moved by any flow.
    pub fn foresee(
        &self,
        beliefs: &Store,
        now: DateTime,
        placed: Option<&Placed<'_>>,
    ) -> Result<Option<Box<dyn Foresight>>, Error> {
        Ok(foresee(beliefs, now, placed)?.map(|f| Box::new(f) as Box<dyn Foresight>))
    }

    /// The offer the planner takes at link.
    pub fn offered(&self) -> Foresees {
        Box::new(|beliefs, now, placed| Prediction.foresee(beliefs, now, placed))
    }
}

/// THE PREDICTOR THE SELF PLAYS, AS THIS PACKAGE READS IT: a field for each thing `prediction:Predictor` may state,
/// one to one, each what the role says in the agent's self graph and, where it says nothing, the default this
/// package's ontology states.
#[derive(Debug, Clone, PartialEq)]
pub struct Predictor {
    /// How far past an observation the flows are integrated, in the timeline's seconds (`prediction:horizonS`).
    pub horizon_s: f64,
    /// The longest a flow's rate is held before the flows are asked again, in seconds (`prediction:rateHeldS`).
    pub rate_held_s: f64,
}

impl Predictor {
    /// The predictor the self plays, read off the store.
    pub fn new(store: &Store) -> Result<Self, Error> {
        Ok(Predictor {
            horizon_s: ontology::figure_of(store, ontology::HORIZON_TERM)?,
            rate_held_s: ontology::figure_of(store, ontology::RATE_HELD_TERM)?,
        })
    }
}

inventory::submit! { Package { name: "prediction", documents: orexis::documents!("ontology.ttl"), start } }

/// PREDICTION'S START: its foresight offered, for whoever lays the grounds to take, and no task - what it offers is
/// asked for where the grounds are laid, and it waits for nothing.
/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
const ROLE: &str = "http://example.org/orexis/prediction#Predictor";

/// ITS START, which every package this binary holds is given: it joins the agent or declines, by its own reason, and
/// joined, makes its core.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE]).await? {
            return Ok(None);
        }
        make(&handed)
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, Error> {
    handed.outside.hand::<Foresees>(Prediction.offered());
    Ok(None)
}
