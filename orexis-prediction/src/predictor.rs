//! THE PREDICTOR, the package's core: the role the self plays, read off its self graph, and the foresight it offers.

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::foresight::{Foresees, Foresight, Placed};
use orexis::store::Store;

use orexis::ontology::{ONTOLOGY, SELF_GRAPH};
use orexis::store::{Within, value};

use crate::foresee::foresee;

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
    /// The predictor the self plays, read off the store in one query: what its role says and, where it says
    /// nothing, the default prediction's ontology states. THE SELF GRAPH WAS HELD TO ITS REQUIREMENTS AT ONBOARDING,
    /// so each figure is stated once at most; nothing is picked between here.
    pub fn new(store: &Store) -> Result<Self, Error> {
        /// THE PREDICTOR THE SELF PLAYS, IN ONE QUERY: each figure its role says or, where it says none, the default
        /// prediction's ontology states on its shape of the role (`sh:defaultValue`).
        const PREDICTOR_Q: &str = "PREFIX orexis: <http://example.org/orexis#> PREFIX sh: <http://www.w3.org/ns/shacl#> SELECT DISTINCT (COALESCE(?horizonSaid, ?horizonOwn) AS ?horizon) \
        (COALESCE(?heldSaid, ?heldOwn) AS ?held) WHERE { \
        ?shape sh:targetClass <http://example.org/orexis/prediction#Predictor> ; \
          sh:property [ sh:path <http://example.org/orexis/prediction#horizonS> ; sh:defaultValue ?horizonOwn ] , \
                      [ sh:path <http://example.org/orexis/prediction#rateHeldS> ; sh:defaultValue ?heldOwn ] . \
        OPTIONAL { ?me a orexis:Self ; orexis:plays ?r1 . ?r1 <http://example.org/orexis/prediction#horizonS> ?horizonSaid } \
        OPTIONAL { ?me a orexis:Self ; orexis:plays ?r2 . ?r2 <http://example.org/orexis/prediction#rateHeldS> ?heldSaid } }";
        let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(store.graphs_of(&[ONTOLOGY], &Within::default())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(PREDICTOR_Q, &known)?;
        let row = rows
            .first()
            .ok_or_else(|| Error::Document("the store states no predictor's figures, and no default".into()))?;
        let number = |name: &str| {
            value(row, name)
                .and_then(|said| said.parse::<f64>().ok())
                .ok_or_else(|| Error::Document(format!("a predictor's {name} is no number of seconds")))
        };
        Ok(Predictor {
            horizon_s: number("horizon")?,
            rate_held_s: number("held")?,
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
