//! EXECUTION'S TERMS that code names, as `agent/execution/ontology.py` names them.

pub const EXECUTION: &str = "http://example.org/orexis/execution#";
/// EXECUTION'S ACTIVITIES, and the trigger of each: an event a higher package's ontology puts beneath a trigger starts
/// that activity, and what it is about is said in the words below.
pub const WALKING: &str = "http://example.org/orexis/execution#Walking";
pub const WALKING_TRIGGER: &str = "http://example.org/orexis/execution#WalkingTrigger";
/// What belief's revision pass names, in belief's words, which execution - above it - reads.
pub const REVISED_SOURCE: &str = "http://example.org/orexis/belief#revised";
pub const CHANGED: &str = "http://example.org/orexis/belief#changed";
pub const ADOPTING: &str = "http://example.org/orexis/execution#Adopting";
pub const ADOPTING_TRIGGER: &str = "http://example.org/orexis/execution#AdoptingTrigger";
pub const SUPERSEDING: &str = "http://example.org/orexis/execution#Superseding";
pub const SUPERSEDING_TRIGGER: &str = "http://example.org/orexis/execution#SupersedingTrigger";
pub const RESOLVING: &str = "http://example.org/orexis/execution#Resolving";
pub const RESOLVING_TRIGGER: &str = "http://example.org/orexis/execution#ResolvingTrigger";
/// What a trigger is about: the plan an intention would adopt, the want it pursues, the step in flight one ends after,
/// and how an intention ends.
pub const ADOPTS: &str = "http://example.org/orexis/execution#adopts";
pub const PURSUES: &str = "http://example.org/orexis/execution#pursues";
pub const ENDS_AFTER: &str = "http://example.org/orexis/execution#endsAfter";
pub const OUTCOME: &str = "http://example.org/orexis/execution#outcome";
/// The desire a want was derived under, PROV's word, for what the executor's events are tagged by.
pub const DERIVED_FROM: &str = "http://www.w3.org/ns/prov#wasDerivedFrom";

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
/// The commands one order of a step sends, kept, and the event that says so.
pub const COMMAND_GRAPH: &str = "http://example.org/orexis/execution#CommandGraph";
pub const ACTUATOR: &str = "http://example.org/orexis/execution#actuator";
pub const PAYLOAD: &str = "http://example.org/orexis/execution#payload";
pub const COMMANDED: &str = "http://example.org/orexis/execution#Commanded";
pub const COMMANDS: &str = "http://example.org/orexis/execution#commands";
/// What a step said, as the event it is said as, in speech's words, which speech hears beneath its trigger.
pub const TOLD: &str = "http://example.org/orexis/execution#Told";
pub const SPEECH_STATEMENT: &str = "http://example.org/orexis/speech#statement";
pub const SPEECH_TO: &str = "http://example.org/orexis/speech#to";
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
