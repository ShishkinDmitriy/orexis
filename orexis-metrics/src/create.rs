//! THE PACKAGE'S START: it joins where the self plays a meter, and tallies what the packages say into its window.

use orexis::series::Sink;
use orexis::task::{Handed, Package, Task};

use crate::role::{ROLE, Role};
use crate::window::{Metrics, Window};

inventory::submit! { Package { name: "metrics", documents: orexis::documents!("ontology.ttl"), start } }

/// ITS START, which every package this binary holds is given: it joins where the self plays a meter, and joined,
/// makes its core.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE]).await? {
            return Ok(None);
        }
        make(&handed)
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, orexis::Error> {
    //  HANDED A WINDOW, by a test that reads the points, it tallies into that; deployed and handed none, it makes
    //  its own where the world says where the store its role names answers, its length the role's word or sixty seconds; and
    //  otherwise nothing is tallied.
    let window = match handed.outside.take::<Window>() {
        Some(window) => window,
        None => {
            let Some(deployed) = handed.outside.read::<orexis::task::Deployed>() else {
                return Ok(None);
            };
            let Some((sink, _)) = Sink::deployed(&handed.store, orexis::series::METRICS, &orexis::series::environment)?
            else {
                return Ok(None);
            };
            let interval = Role::read(&handed.store)?.window_s;
            log::info!("{} writes its metrics every {interval}s", handed.id);
            Window::new(sink, interval, Some(&deployed.world), Some(&handed.id))
        }
    };
    let metrics = Metrics::new(window, handed.events.watch());
    let handed = handed.clone();
    Ok(Some(Box::pin(async move {
        handed.stopped().await;
        metrics.window.lock().unwrap().flush();
        Ok(())
    })))
}
