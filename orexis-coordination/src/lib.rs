//! COORDINATION, in Rust, ported from `orexis-coordination/`: two agents that want one resource ask each other what
//! their constraint reads, and a draw decides which goes first
//! (two-agents-that-want-one-resource-ask-each-other-and-draw-lots-for-it).
//!
//! - [`holdings`]: what the agent says of its own future under one constraint, read off its walking intentions;
//! - [`ask`]: the questions it says to the peers it believes in range; [`answer`]: what it says back, under a
//!   constraint it holds too, of what meets;
//! - [`conclude`]: what it concludes of its conflicts, and who won each draw, as the world's outcomes say;
//! - [`lay`]: what it lays of a peer's holdings as forecasts, as the draw says it yields;
//! - [`mint`]: the secret its draws' numbers come from; [`create`]: the package's part.
//!
//! - [`events`]: what it says happened — the holdings asked with, said and foreseen, and the conflicts concluded.
//!
//! It imports no code of planning, execution or speech, and meets them at the store and through whoever links them.
//! - [`coordinator`]: the coordinator the self plays, a struct with a field for each thing its role may state, which reads
//!   itself off the store;

pub mod answer;
pub mod ask;
pub mod conclude;
pub mod coordinator;
pub mod create;
pub mod events;
pub mod holdings;
pub mod lay;
pub mod mint;
pub mod ontology;
pub use coordinator::Coordinator;
