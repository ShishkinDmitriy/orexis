//! EXECUTION'S TERMS that code names, as `agent/execution/ontology.py` names them.

pub const EXECUTION: &str = "http://example.org/orexis/execution#";
/// A walk of the intentions, as the activity it is.
pub const WALKING: &str = "http://example.org/orexis/execution#Walking";

/// A step an intention committed to, as a belief over its landing window, and the window's two lengths.
pub const COMMITTED_STEP_GRAPH: &str = "http://example.org/orexis/execution#CommittedStepGraph";
pub const LANDS_WITHIN_S: &str = "http://example.org/orexis/execution#landsWithinS";
pub const ANSWERED_WITHIN_S: &str = "http://example.org/orexis/execution#answeredWithinS";

/// What a step predicts, as the two graphs it names.
pub const ADDS_GRAPH: &str = "http://example.org/orexis/execution#AddsGraph";
pub const RETRACTS_GRAPH: &str = "http://example.org/orexis/execution#RetractsGraph";

/// How long a commitment is given, the agent's stance.
pub const PATIENCE_S: &str = "http://example.org/orexis/execution#patienceS";

pub const INTENTION: &str = "http://example.org/orexis/execution#Intention";
pub const INTENTION_GRAPH: &str = "http://example.org/orexis/execution#IntentionGraph";
pub const STEP_CLASS: &str = "http://example.org/orexis/execution#Step";

pub const COMMAND: &str = "http://example.org/orexis/execution#Command";
pub const SAYING: &str = "http://example.org/orexis/execution#Saying";
pub const FICTIVE: &str = "http://example.org/orexis/execution#Fictive";

const GRAPH: &str = "http://example.org/orexis/graph/";

/// What this agent is committed to, standing and resolved: its own, and only its own.
pub fn intentions_graph(agent: &str) -> String {
    format!("{GRAPH}intentions/{agent}")
}

/// Where a fictive step puts what it adds and replaces nothing.
pub fn fictive_graph(agent: &str) -> String {
    format!("{GRAPH}fictive/{agent}")
}

/// The graph holding one committed step over its landing window, named for the step for eyes.
pub fn committed_graph(agent: &str, step: &str) -> String {
    let tail = step.trim_end_matches(['#', '/']);
    let local = tail.rsplit(['#', '/']).next().unwrap_or(tail);
    let local: String = local
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '_' { c } else { '_' })
        .collect();
    format!("{GRAPH}committed/{agent}/{local}")
}
