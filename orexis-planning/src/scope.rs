//! A SCOPE AS A PASS WORKS IN IT: the slice of the agent's actions one imaginarium is searched over, handed to the acts
//! that read it — `admit` its actions and what is another scope's, `take` and `lay_ground` what a world is hashed
//! within. The partition itself is the store's (`scope_actions`, read back by `find_scopes`); this is one cell of it.

use std::collections::BTreeSet;

/// One scope: its name, the actions it admits, the terms that are another scope's and what a world in it is hashed
/// within. `Scope::default()` is a store that scoped nothing: no name, every action, nothing elsewhere, hashed whole.
#[derive(Clone, Copy, Debug, Default)]
pub struct Scope<'s> {
    /// The scope's name, for what is said of a search in it; `None` where the store scoped nothing.
    pub name: Option<&'s str>,
    /// The actions it admits; `None` meaning every action the store holds.
    pub actions: Option<&'s BTreeSet<String>>,
    /// The values that are another scope's, which a filling here may not bind.
    pub elsewhere: Option<&'s BTreeSet<String>>,
    /// What a world is identified by; `None` hashing it whole and laying every belief ahead.
    pub within: Option<&'s BTreeSet<String>>,
}
