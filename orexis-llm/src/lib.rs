//! THE LANGUAGE MODEL FAMILY: what every package that asks a language model shares, and nothing else reads — the
//! client a package asks one through, and the words of a model and of asking it (`llm:`, `ontology.ttl`), which a
//! package asking one brings beside its own as it joins (`Handed::joins_with`, `DOCUMENTS`). Which model a package
//! asks, and what it tells it, are the asking role's: a translator names its model (`translation:translatedBy`) and
//! its prompts (knowledge/domain/llm/model.md).
//!
//! - [`model`]: a conversation and one call, the failures a call can end in, and what it spent.

pub mod model;

/// THE WORDS OF A MODEL AND OF ASKING ONE, which a package asking a model brings beside its own as it joins.
pub const DOCUMENTS: orexis::task::Documents = orexis::documents!("ontology.ttl");

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE OF ASKING A MODEL: the defaults this family's ontology
/// states (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("llm", include_str!("../ontology.ttl")));

/// THE FIGURES A ROLE ASKING A MODEL MAY STATE: how long one call may take, and how often a failing one is asked again.
pub const CALLED_WITHIN_S: &str = "http://example.org/orexis/llm#calledWithinS";
pub const RETRIES: &str = "http://example.org/orexis/llm#retries";
