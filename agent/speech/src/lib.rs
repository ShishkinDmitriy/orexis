//! SPEECH, in Rust, ported from `agent/speech/`: what a peer says and what the agent says, each kept as what was said
//! — a statement, a kind no reader of the mind is handed — and what the agent believes of it, extracted.
//!
//! - [`heard`]: a peer's document, kept as what was said, or refused whole;
//! - [`said`]: what this agent told a peer, kept as it was said;
//! - [`statements`]: a document as what was said, each graph a statement whatever kind it says;
//! - [`extract`]: what every extraction the agent holds concludes of one statement, one belief derived from it;
//! - [`create`]: the package's part, which extracts from every statement written and says what a step says.
//!
//! - [`events`]: every statement said and heard, history in speech's words.

pub mod create;
pub mod events;
pub mod extract;
pub mod heard;
pub mod ontology;
pub mod said;
pub mod statements;
