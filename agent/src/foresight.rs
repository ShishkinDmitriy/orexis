//! FORESIGHT, WHERE PLANNING AND PREDICTION MEET: what moves from a ground while nobody acts, carried from ground to
//! ground as the planner lays them (a-flow-is-integrated-where-the-ground-is-laid, #1000). In Python the planner is
//! handed the predictor's `foresee` at link and calls what it returns, neither package importing the other; here the
//! contract is a trait, and the kernel keeps it because it is what the two packages meet at — as it keeps
//! `orexis:FlowGraph`, the kind every agent reads, predictor or not.

use oxigraph::model::Triple;
use oxsdatatypes::DateTime;

use crate::Error;
use crate::store::Store;

/// What a ground the planner stands in reads at an instant: the ground, and every graph holding then beside it.
pub type GraphsAt<'g> = dyn FnMut(DateTime) -> Result<Vec<String>, Error> + 'g;

/// The integration of every key the agent foresees, advanced ground by ground.
pub trait Foresight {
    /// The last instant any key is looked at.
    fn horizon(&self) -> DateTime;

    /// Integrate from `at` towards `until`, reading `graphs_at` — and answer the earliest instant at which a key the
    /// caller lays crosses a bound, with the predicted observation to lay there; or the hour's end, where a key it
    /// lays has moved; or None, every key then standing at `until`.
    fn advance(
        &mut self,
        store: &Store,
        at: DateTime,
        until: DateTime,
        graphs_at: &mut GraphsAt<'_>,
    ) -> Result<Option<(DateTime, Vec<Triple>)>, Error>;

    /// The grounds are laid: take away whatever the integration kept in `store` while it ran.
    fn finish(&mut self, store: &Store) -> Result<(), Error>;
}

/// Whether a crossing of a key — its feature and its property — is the caller's to lay.
pub type Placed<'p> = dyn Fn(&str, &str) -> bool + 'p;

/// The predictor's offer, taken at link: the foresight from `now`, off `beliefs`, None where no key is moved by a flow.
pub type Foresees = Box<dyn Fn(&Store, DateTime, Option<&Placed<'_>>) -> Result<Option<Box<dyn Foresight>>, Error>>;
