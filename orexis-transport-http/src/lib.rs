//! THE HTTP TRANSPORT, in Rust: how an agent reaches a service over the web, in the words of the W3C Web of Things
//! Thing Description, adopted as it stands — ported from `orexis-transport-http/` and held to what its suite asks.
//!
//! - [`driver`]: which things the member reaches, where each is read, and a request answered by one fetch;
//! - the start, below the modules, and nothing else: the member made and added to the agent's members. It runs no
//!   task: who asks, and how often, is the row above's (the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop).

use std::sync::Arc;

use orexis::task::{Handed, Package};
use orexis_transport::Members;

pub mod driver;
pub mod figures;

inventory::submit! { Package { name: "transport/http", start } }

/// THE DOCUMENTS THIS PACKAGE BRINGS as it joins, in the order it puts them in.
const DOCUMENTS: orexis::task::Documents = orexis::documents!("ontology.ttl");

/// A TRANSPORT IS NO ROLE: this member joins the agent where a role the self plays needs bytes and the world wires
/// them through it - each a role's class with what the world must state of the self, in words declared here.
const WIRED: &[(&str, &str)] = &[(
    "http://example.org/orexis/sensing#Observer",
    "?me orexis:plays/sensing:attends/sensing:sensor ?sensor . ?sensor td:hasForm ?form",
)];
const WORDS: &str = "PREFIX sensing: <http://example.org/orexis/sensing#>
    PREFIX speech: <http://example.org/orexis/speech#>
    PREFIX td: <https://www.w3.org/2019/wot/td#>
    ";

/// ITS START, which every package this binary holds is given: it joins where a role the self plays needs what it
/// reads and the world wires it, and declines otherwise; joined, its member is made and added to the agent's members,
/// and it says it booted. It has no task: a request is a fetch the member awaits as a task of its own.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !orexis_transport::wired(&handed, WORDS, WIRED)? {
            return Ok(());
        }
        handed.joins(&DOCUMENTS).await?;
        let me = orexis::boot::selves(&handed.store)?
            .into_iter()
            .next()
            .unwrap_or_default();
        //  HANDED A MEMBER, by a test that plays the other side, it is that; deployed and handed none, it fetches
        //  over the web; and otherwise, a check or a test that hands none, it is a member that reaches nothing, so
        //  nothing is dialled.
        let member = match handed.provided.take::<crate::driver::Http>() {
            Some(member) => member,
            None if handed.provided.has::<orexis::task::Deployed>() => crate::driver::Http::new(
                &handed.store,
                &me,
                crate::driver::get(crate::figures::figure_of(
                    &handed.store,
                    crate::driver::FETCHED_WITHIN_S,
                )?)?,
            ),
            None => crate::driver::Http::new(
                &handed.store,
                &me,
                crate::driver::answering(|_| Err("an agent that is not deployed reaches no web".to_string())),
            ),
        };
        handed
            .provided
            .alter(|members: &mut Members| members.add(Arc::new(member)));
        handed.booted().await?;
        Ok(())
    })
}
