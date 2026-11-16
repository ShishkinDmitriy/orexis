//! THE PREDICTOR, the package's core: the role the self plays, read off its self graph, and the foresight it offers.

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::foresight::{Foresees, Foresight, Placed};
use orexis::store::Store;

use crate::foresee::foresee;
use crate::ontology;

/// THE PREDICTOR THE SELF PLAYS, AS THIS PACKAGE READS IT: a field for each thing `prediction:Predictor` may state,
/// one to one, each what the role says in the agent's self graph and, where it says nothing, the default this
/// package's ontology states; and what it offers, the agent's foresight.
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

    /// The agent's foresight from `now`, off `beliefs`, for the planner to advance ground by ground; None where no key
    /// is moved by any flow.
    pub fn foresee(
        &self,
        beliefs: &Store,
        now: DateTime,
        placed: Option<&Placed<'_>>,
    ) -> Result<Option<Box<dyn Foresight>>, Error> {
        Ok(foresee(beliefs, self, now, placed)?.map(|f| Box::new(f) as Box<dyn Foresight>))
    }

    /// The offer the planner takes at link.
    pub fn offered(&self) -> Foresees {
        let predictor = self.clone();
        Box::new(move |beliefs, now, placed| predictor.foresee(beliefs, now, placed))
    }
}
