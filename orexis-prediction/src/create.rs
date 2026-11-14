//! PREDICTION'S PART, as `agent/prediction/create.py` makes it: the agent's foresight, offered to whoever lays the
//! grounds. It hears nothing and writes nothing: the flows are integrated from each ground as the planner lays them
//! (a-flow-is-integrated-where-the-ground-is-laid, #1000), so what this part offers is `foresee`, which the binary
//! hands the planner at link through the kernel's `Foresight`, neither package importing the other.

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::foresight::{Foresees, Foresight, Placed};
use orexis::store::Store;
use orexis::task::{Handed, Package, Task};

use crate::foresee::foresee;

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

inventory::submit! { Package { name: "prediction", documents: orexis::documents!("ontology.ttl"), start } }

/// PREDICTION'S START: its foresight offered, for whoever lays the grounds to take, and no task - what it offers is
/// asked for where the grounds are laid, and it waits for nothing.
fn start(handed: &Handed) -> Result<Option<Task>, Error> {
    handed.outside.hand::<Foresees>(Prediction.offered());
    Ok(None)
}
