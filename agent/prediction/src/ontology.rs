//! THE WORDS THE PREDICTION PACKAGE READS AND WRITES, as `agent/prediction/ontology.py` names them: its own, the
//! flow and what it says, SOSA's on the observation it reads and the one it predicts, and ONE of sensing's, the kind
//! an observation is kept in — prediction sits above sensing and imports none of its code (#944).

use orexis::ontology::OREXIS;

pub const PREDICTION: &str = "http://example.org/orexis/prediction#";
pub const SOSA: &str = "http://www.w3.org/ns/sosa/";

/// THIS PACKAGE'S OWN: one thing that moves a value while nobody acts, the property it moves, the select answering
/// how fast.
pub const FLOW: &str = "http://example.org/orexis/prediction#Flow";
pub const MOVES: &str = "http://example.org/orexis/prediction#moves";
pub const RATE: &str = "http://example.org/orexis/prediction#rate";

/// HOW FAR PAST AN OBSERVATION THE AGENT LOOKS: a stance it states of itself in its self graph.
pub const HORIZON_TERM: &str = "http://example.org/orexis/prediction#horizonS";

/// SOSA'S, on an observation — the key a flow's answer is matched by, and the number.
pub const FEATURE: &str = "http://www.w3.org/ns/sosa/hasFeatureOfInterest";
pub const PROPERTY: &str = "http://www.w3.org/ns/sosa/observedProperty";
pub const RESULT: &str = "http://www.w3.org/ns/sosa/hasSimpleResult";

/// SENSING'S, the package beneath: the kind an observation and what the rules concluded of it are kept in.
pub const OBSERVATION_GRAPH: &str = "http://example.org/orexis/sensing#ObservationGraph";

/// The local name of a term, safe to paste into an IRI.
pub fn slug(iri: &str) -> String {
    let trimmed = iri.trim_end_matches(['#', '/']);
    let local = trimmed.rsplit(['#', '/']).next().unwrap_or(trimmed);
    local
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '_' { c } else { '_' })
        .collect()
}

/// The node every prediction of one key says the reading of its stretch is — ONE per key, as a fluent is (#988),
/// and never the percept's it was made from (#944). A reader matches the key, never the name.
pub fn predicted_of(feature: &str, property: &str) -> String {
    format!("{OREXIS}predicted_{}_{}", slug(feature), slug(property))
}
