//! PLANNING'S TERMS that code names, as `agent/planning/ontology.py` names them.

use orexis::ontology::{BELIEF, RECORD};

pub const PLANNING: &str = "http://example.org/orexis/planning#";

pub const DESIRE: &str = "http://example.org/orexis/planning#DesireGraph";
pub const WANT: &str = "http://example.org/orexis/planning#WantGraph";

/// What a planning text is answered over: the kernel's kinds, and the desires and wants.
pub const KNOWN: &[&str] = &[BELIEF, RECORD, DESIRE, WANT];

pub const CANDIDATE: &str = "http://example.org/orexis/planning#Candidate";
pub const WAIT: &str = "http://example.org/orexis/planning#Wait";
pub const FILLS: &str = "http://example.org/orexis/planning#fills";
pub const FROM: &str = "http://example.org/orexis/planning#from";
pub const MINTED: &str = "http://example.org/orexis/planning#minted";
pub const PRECONDITION: &str = "http://example.org/orexis/planning#precondition";

pub const POSSIBLE_GRAPH: &str = "http://example.org/orexis/planning#PossibleGraph";
pub const GROUND_GRAPH: &str = "http://example.org/orexis/planning#GroundGraph";
pub const CHANGEABLE_GRAPH: &str = "http://example.org/orexis/planning#ChangeableGraph";
pub const SPENT: &str = "http://example.org/orexis/planning#spent";
pub const BY: &str = "http://example.org/orexis/planning#by";

/// A step's prediction, two graphs it names: EXECUTION'S words, which the Python planning package imports from
/// `agent/execution/ontology.py` as these two terms alone.
pub const ADDS_GRAPH: &str = "http://example.org/orexis/execution#AddsGraph";
pub const RETRACTS_GRAPH: &str = "http://example.org/orexis/execution#RetractsGraph";
pub const SHAPES: &str = "http://example.org/orexis/planning#ShapesGraph";
pub const CONSTRAINT_GRAPH: &str = "http://example.org/orexis/planning#ConstraintGraph";
pub const DERIVATION_GRAPH: &str = "http://example.org/orexis/planning#DerivationGraph";
pub const SCOPE_GRAPH: &str = "http://example.org/orexis/planning#ScopeGraph";
pub const ANYTHING: &str = "http://example.org/orexis/planning#Anything";
