//! PLANNING, in Rust: the acts a pass runs over the imaginarium, ported from `agent/planning/` one act at a time
//! and held to the same cases. A STAR, NOT A CHAIN, as there: an act calls no other act, and what one needs of
//! another's work it reads off the rows the other wrote.
//!
//! - [`world_at`]: the graphs a rule is answered over in one world, or in the present;
//! - [`next_ground`]: the instant the next ground the search can tell apart begins, where a wait lands;
//! - [`admit`]: every candidate a world admits, one per action per legal filling, written as the edges leaving it;
//! - [`take`]: one candidate taken, the world it reaches forked with the action's effect applied, and its row.

pub mod admit;
pub mod memo;
pub mod next_ground;
pub mod ontology;
pub mod take;
pub mod world_at;

pub use memo::Memo;
