//! THE KERNEL'S TERMS that code names, as `agent/ontology.py` names them: T-Box terms and the one convention a
//! writer names graphs by, never an instance (rule 1).

pub const OREXIS: &str = "http://example.org/orexis#";
pub const GRAPH_PREFIX: &str = "http://example.org/orexis/graph/";

/// How a graph's content got there.
pub const ASSERTED: &str = "http://example.org/orexis#Asserted";
pub const DERIVED: &str = "http://example.org/orexis#Derived";
pub const RECEIVED: &str = "http://example.org/orexis#Received";
pub const RECORDED: &str = "http://example.org/orexis#Recorded";

/// The graph kinds the kernel declares.
pub const ONTOLOGY: &str = "http://example.org/orexis#OntologyGraph";
pub const BELIEF: &str = "http://example.org/orexis#BeliefGraph";
pub const FORECAST: &str = "http://example.org/orexis#ForecastGraph";
pub const PLAN: &str = "http://example.org/orexis#PlanGraph";
pub const RECORD: &str = "http://example.org/orexis#RecordGraph";
pub const ACTION: &str = "http://example.org/orexis#ActionGraph";
pub const FLOW_GRAPH: &str = "http://example.org/orexis#FlowGraph";
pub const SELF_GRAPH: &str = "http://example.org/orexis#SelfGraph";

pub const HASH: &str = "http://example.org/orexis#hash";
pub const SELF: &str = "http://example.org/orexis#Self";

/// Where a period begins and ends.
pub const START: &str = "http://example.org/orexis#start";
pub const END: &str = "http://example.org/orexis#end";

/// When a graph was expected to end, kept once an event ended it at another instant.
pub const EXPECTED_INVALIDATION: &str = "http://example.org/orexis#expectedInvalidation";

/// What the boot reads the world by.
pub const WORLD_GRAPH: &str = "http://example.org/orexis#WorldGraph";
pub const SOCIETY_GRAPH: &str = "http://example.org/orexis#SocietyGraph";
pub const GRAPH: &str = "http://example.org/orexis#Graph";
/// The stretch a graph holds over, as its metadata says it.
pub const PERIOD: &str = "http://purl.org/dc/terms/PeriodOfTime";

/// What the world is connected to, as its agents read it: no belief, asked by a package as it starts.
pub const DEPLOYMENT: &str = "http://example.org/orexis#DeploymentGraph";
pub const ROLE: &str = "http://example.org/orexis#Role";

/// What says what a graph is, and the graph it says it of.
pub const METADATA_GRAPH: &str = "http://example.org/orexis#MetadataGraph";
pub const METADATA_OF: &str = "http://example.org/orexis#metadataOf";

/// The one graph a writer names: the vocabulary's closure.
pub const CLOSURE_GRAPH: &str = "http://example.org/orexis/graph/ontology/closure";

/// An IRI's local part, the name a parameter answers to as a variable, a token and a column.
pub fn local_of(iri: &str) -> String {
    let tail = iri.rsplit('#').next().unwrap_or(iri);
    tail.rsplit('/').next().unwrap_or(tail).to_string()
}
