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
pub const CATALOGUE: &str = "http://example.org/orexis#CatalogueGraph";
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

/// What the boot reads the world by.
pub const WORLD_GRAPH: &str = "http://example.org/orexis#WorldGraph";
pub const SOCIETY_GRAPH: &str = "http://example.org/orexis#SocietyGraph";
pub const GRAPH: &str = "http://example.org/orexis#Graph";
pub const ROLE: &str = "http://example.org/orexis#Role";

/// The two graphs a writer names: the catalogue, created by genesis alone, and the vocabulary's closure.
pub const CATALOGUE_GRAPH: &str = "http://example.org/orexis/graph/catalogue";
pub const CLOSURE_GRAPH: &str = "http://example.org/orexis/graph/ontology/closure";
