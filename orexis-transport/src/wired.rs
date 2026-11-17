//! WHETHER A MEMBER JOINS: the world wires the self through it.

use orexis::Error;
use orexis::ontology::{BELIEF, SELF_GRAPH};
use orexis::store::Within;
use orexis::task::Handed;

/// WHETHER THE WORLD WIRES THE SELF THROUGH A TRANSPORT: one of `wired` holds, each a role's class the self plays
/// with a pattern about `?me` the common beliefs and the self graph answer, in the `words` the transport declares.
/// What a member asks as its start begins: the family names no member and no pattern.
pub fn wired(handed: &Handed, words: &str, wired: &[(&str, &str)]) -> Result<bool, Error> {
    let store = &handed.store;
    let mut known = store.graphs_of(&[BELIEF], &Within::common())?;
    known.extend(store.graphs_of(&[SELF_GRAPH], &Within::default())?);
    let known: Vec<&str> = known.iter().map(String::as_str).collect();
    for (role, pattern) in wired {
        if handed.plays(&[role])?
            && store.ask(
                &format!("PREFIX orexis: <http://example.org/orexis#> {words}ASK {{ ?me a orexis:Self . {pattern} }}"),
                &known,
            )?
        {
            return Ok(true);
        }
    }
    Ok(false)
}
