//! PLANNING, in Rust: the acts a pass runs over the imaginarium, ported from `agent/planning/` one act at a time
//! and held to the same cases. A STAR, NOT A CHAIN, as there: an act calls no other act, and what one needs of
//! another's work it reads off the rows the other wrote.
//!
//! - [`world_at`]: the graphs a rule is answered over in one world, or in the present;
//! - [`next_ground`]: the instant the next ground the search can tell apart begins, where a wait lands;
//! - [`admit`]: every candidate a world admits, one per action per legal filling, written as the edges leaving it;
//! - [`take`]: one candidate taken, the world it reaches forked with the action's effect applied, and its row;
//! - [`prepare_ground`]: what crosses from the belief base into the store a search over one scope stands in;
//! - [`lay_ground`]: one ground world per period the agent can see, cut to what the search can change;
//! - [`scope_actions`]: the actions clustered into the scopes their effects join, written as the store's partition;
//! - [`find_scopes`]: every scope each predicate, term and action is in, read back;
//! - [`find_wants`]: the wants a store holds at an instant, narrowed by the criteria a caller names;
//! - [`derive_wants`]: a want minted for every cluster of what a desire's met-test reads unmet, read off the weighings;
//! - [`couplings`]: which instances a holder's constraints can make collide, over what the actions can reach;
//! - [`withdraw`]: every derived want the derivation no longer implies, and every want reached, taken away.

pub mod admit;
pub mod bridge;
pub mod couplings;
pub mod create;
pub mod derive_wants;
pub mod extract_plan;
pub mod find_scopes;
pub mod find_wants;
pub mod footprint;
pub mod lay_ground;
pub mod memo;
pub mod next_ground;
pub mod ontology;
pub mod planner;
pub mod prepare_ground;
pub mod publish_plan;
pub mod refine;
pub mod reroot;
pub mod scope_actions;
pub mod shapes;
pub mod take;
pub mod unweighed;
pub mod violation;
pub mod weigh;
pub mod withdraw;
pub mod world_at;

pub use memo::Memo;
pub use planner::Planner;
