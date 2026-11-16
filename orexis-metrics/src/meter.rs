//! THE METER, the package's core: the role the self plays, read off its self graph and the world's deployment, and the
//! window it tallies every reported event in.

use std::sync::{Arc, Mutex};

use orexis::events::Watch;
use orexis::task::PASS_METRIC;

use crate::ROLE;
use crate::window::Window;

/// THE METER THE SELF PLAYS, IN ONE QUERY: where the series store it names answers, and how long a window is, the
/// role's word or, where it says none, the default the metrics' ontology states on the meter's shape
/// (`sh:defaultValue`).
const METER_Q: &str = "SELECT ?role ?kind ?store (COALESCE(?windowSaid, ?windowOwn) AS ?window) WHERE { \
?me a orexis:Self ; orexis:plays ?role . ?role a ?kind . \
OPTIONAL { ?role <http://example.org/orexis/metrics#windowS> ?windowSaid FILTER(?windowSaid > 0) } \
OPTIONAL { ?shape sh:targetClass <{ROLE}> ; sh:property [ sh:path <http://example.org/orexis/metrics#windowS> ; sh:defaultValue ?windowOwn ] } \
OPTIONAL { ?role <http://example.org/orexis/metrics#writtenTo> ?named . ?named <https://schema.org/url> ?store } }";

/// THE METER THE SELF PLAYS, the package's core: a field for each thing `metrics:Meter` may say, and the window it
/// tallies every reported event in.
pub struct Meter {
    /// Where the series store the role names answers (`metrics:writtenTo`), as the world's deployment states it:
    /// None where the role names none or the world says nothing of the one named.
    pub written_to: Option<String>,
    /// How long a window is, in real seconds (`metrics:windowS`), and the default the ontology states where the role states none.
    pub window_s: f64,
    /// The window every reported event is tallied in, once it is handed one or makes its own.
    pub window: Option<Arc<Mutex<Window>>>,
}

impl Meter {
    /// The meter the self plays, read off its self graph and the world's deployment graph by this package's own
    /// query. An agent plays one meter: two are refused, and where the self plays none nothing is said.
    pub fn new(store: &orexis::store::Store) -> Result<Self, orexis::Error> {
        use orexis::ontology::{DEPLOYMENT, ONTOLOGY, SELF_GRAPH};
        use orexis::store::{Within, value};
        let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(store.graphs_of(&[DEPLOYMENT], &Within::common())?);
        known.extend(store.graphs_of(&[ONTOLOGY], &Within::default())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let mut rows = Vec::new();
        for row in store.rows(&METER_Q.replace("{ROLE}", ROLE), &known)? {
            let kind = value(&row, "kind").unwrap_or_default();
            if kind == ROLE || store.closed(&kind)?.iter().any(|class| class == ROLE) {
                rows.push(row);
            }
        }
        //  ONE IS PLAYED: what the role says is said to this package once for the agent, and two are never picked
        //  between, which onboarding refuses before a boot does.
        let played: std::collections::BTreeSet<String> = rows.iter().filter_map(|row| value(row, "role")).collect();
        if played.len() > 1 {
            return Err(orexis::Error::Document(format!(
                "the self plays {} meters, and an agent plays one",
                played.len()
            )));
        }
        if rows.is_empty() {
            return Err(orexis::Error::Document(format!(
                "the self plays no {}",
                orexis::ontology::local_of(ROLE)
            )));
        }
        let said = |what: &str| {
            rows.iter()
                .find_map(|row| value(row, what))
                .filter(|said| !said.is_empty())
        };
        //  A FIGURE NEITHER THE ROLE NOR THE SHAPE STATES is a package shipped broken.
        let figure = |what: &str| {
            said(what)
                .and_then(|figure| figure.parse::<f64>().ok())
                .ok_or_else(|| orexis::Error::Document(format!("the metrics' ontology states no default for {what}")))
        };
        Ok(Meter {
            written_to: said("store"),
            window_s: figure("window")?,
            window: None,
        })
    }

    /// Tally into `window` every event `watch` is said, writing it after the pass that ends it.
    pub fn tally(&mut self, window: Window, watch: &Watch) {
        let window = Arc::new(Mutex::new(window));
        let heard = window.clone();
        watch.connect(move |event, _| {
            let mut window = heard.lock().unwrap();
            window.tally(event);
            if event.metric() == Some(PASS_METRIC) && window.due() {
                window.flush();
            }
        });
        self.window = Some(window);
    }

    /// Write what the window holds, as the meter stops.
    pub fn flush(&self) {
        if let Some(window) = &self.window {
            window.lock().unwrap().flush();
        }
    }
}
