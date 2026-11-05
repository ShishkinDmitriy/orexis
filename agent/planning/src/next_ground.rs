//! THE INSTANT THE NEXT GROUND WHOSE IDENTITY DIFFERS BEGINS — where a wait lands (#920), as
//! `agent/planning/next_ground.py` reads it: the first ground later than the one a world stands in whose hash on its
//! row is not the hash of that ground. A read; it writes nothing, and `admit` and `take` ask the one question.

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::store::{Store, value};

use crate::Memo;
use crate::world_at::{catalogue, when};

/// EVERY GROUND, ITS START AND WHAT IT HOLDS BY HASH, earliest first — once a pass.
const GROUNDS_Q: &str = "
SELECT ?at ?hash WHERE { GRAPH $cat { ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?at ; orexis:hash ?hash } }
ORDER BY ?at";

/// The instant the first ground after the one `world` stands in that holds something else, as the search reads
/// it, begins — or None where nothing laid after it does.
pub fn next_ground(store: &Store, world: &str, memo: &mut Memo) -> Result<Option<DateTime>, Error> {
    if let Some(known) = memo.next_ground.get(world) {
        return Ok(*known);
    }
    if memo.grounds.is_none() {
        let cat = catalogue(store, memo)?;
        let text = orexis::bind::bind(GROUNDS_Q, &[("cat", orexis::bind::Value::iri(cat))])?;
        let mut grounds = Vec::new();
        for row in store.rows(&text, &[])? {
            if let (Some(at), Some(hash)) = (value(&row, "at"), value(&row, "hash")) {
                grounds.push((orexis::clock::instant(&at)?, hash));
            }
        }
        memo.grounds = Some(grounds);
    }
    let grounds = memo.grounds.clone().expect("asked above");
    let distinct: std::collections::HashSet<&String> = grounds.iter().map(|(_, h)| h).collect();
    let found = if distinct.len() < 2 {
        None
    } else {
        match when(store, world, memo)? {
            None => None,
            Some((start, _)) => {
                let here = grounds
                    .iter()
                    .filter(|(at, _)| *at <= start)
                    .map(|(_, h)| h)
                    .next_back();
                grounds
                    .iter()
                    .find(|(at, h)| *at > start && Some(h) != here)
                    .map(|(at, _)| *at)
            }
        }
    };
    memo.next_ground.insert(world.to_string(), found);
    Ok(found)
}
