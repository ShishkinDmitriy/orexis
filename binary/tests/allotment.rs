//! The allotment on the binary, held to what its three Python agents did: `world/allotment/tests/test_allotment.py`'s
//! market walks — a dry plot's grower calls for a round, the supplier offers one to both growers, the grower tenders a
//! bid sized from its reading, the supplier clears the round when its window closes and tells the winner its claim,
//! the grower presents the claim and the supplier serves it through the valve over the plot. Three Rust agents in one
//! process on one bus that hands each what another tells it, on one clock every read of which moves it on by a second,
//! as the Python test's does.

use std::cell::RefCell;
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;
use std::rc::Rc;
use std::sync::{Arc, Mutex};

use oxsdatatypes::{DateTime, DayTimeDuration};
use serde_json::Value as Json;

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::{Clock, instant, isoformat};
use orexis::namespaces::Namespaces;
use orexis::ontology::BELIEF;
use orexis::runtime::{Part, Runtime};
use orexis::store::{Store, Within, value};
use orexis_agent::{Seen, Wiring, assemble_seen, booted};
use orexis_mqtt::driver::{Client, Inbox, Mqtt};

const AL: &str = "http://example.org/orexis/world/allotment#";
const MARKET: &str = "http://example.org/orexis/market#";
const NAMES: [&str; 3] = ["supplier", "rose_grower", "fern_grower"];
const READINGS: &str = "sensors/plot_board/reading";

/// One timeline for every agent: a test sets where it stands, and every read moves it on by a second where it ticks.
#[derive(Clone)]
struct Ticking(Arc<Mutex<DateTime>>, bool);

impl Ticking {
    fn at(&self) -> DateTime {
        *self.0.lock().unwrap()
    }

    fn on(&self, seconds: i64) {
        let mut at = self.0.lock().unwrap();
        *at = at.checked_add_day_time_duration(DayTimeDuration::new(seconds)).unwrap();
    }
}

impl Clock for Ticking {
    fn now(&self) -> DateTime {
        if self.1 {
            self.on(1);
        }
        self.at()
    }
}

/// What the bus carried: every publish, and the inboxes it hands one to.
#[derive(Default)]
struct Carried {
    inboxes: BTreeMap<String, Inbox>,
    /// What each agent subscribed to.
    patterns: BTreeMap<String, Vec<String>>,
    published: Vec<(String, Vec<u8>)>,
    /// Every publish with the instant it was made at.
    stamped: Vec<(DateTime, String, Vec<u8>)>,
}

impl Carried {
    fn commands(&self) -> Vec<(String, Json)> {
        self.published
            .iter()
            .filter(|(t, _)| t.starts_with("actuators/"))
            .map(|(t, p)| (t.clone(), serde_json::from_slice(p).unwrap()))
            .collect()
    }

    fn told(&self, agent: &str) -> Vec<String> {
        let topic = format!("agents/{agent}/inbox");
        self.published
            .iter()
            .filter(|(t, _)| *t == topic)
            .map(|(_, p)| String::from_utf8_lossy(p).into_owned())
            .collect()
    }
}

/// One agent's side of the bus: a document to an agent reaches its inbox, and a command is kept.
struct Bus {
    name: &'static str,
    clock: Ticking,
    carried: Rc<RefCell<Carried>>,
}

impl Client for Bus {
    fn subscribe(&mut self, pattern: &str) -> Result<(), Error> {
        let mut carried = self.carried.borrow_mut();
        carried
            .patterns
            .entry(self.name.to_string())
            .or_default()
            .push(pattern.to_string());
        Ok(())
    }

    fn publish(&mut self, topic: &str, payload: &[u8], _retain: bool) -> Result<(), Error> {
        let mut carried = self.carried.borrow_mut();
        carried
            .stamped
            .push((self.clock.at(), topic.to_string(), payload.to_vec()));
        carried.published.push((topic.to_string(), payload.to_vec()));
        if let Some(agent) = topic.strip_prefix("agents/").and_then(|t| t.strip_suffix("/inbox"))
            && let Some(inbox) = carried.inboxes.get(agent)
        {
            inbox.deliver(topic, payload, Some(self.clock.at()));
        }
        Ok(())
    }
}

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world() -> std::path::PathBuf {
    tree().parent().unwrap().join("world/allotment")
}

/// What one of the three is believed to hold of `predicate`: each subject's and object's local name or value.
fn facts(store: &Store, predicate: &str) -> BTreeSet<(String, String)> {
    let beliefs = store.graphs_of(&[BELIEF], &Within::default()).unwrap();
    let beliefs: Vec<&str> = beliefs.iter().map(String::as_str).collect();
    let local = |s: String| s.rsplit(['#', '/']).next().unwrap_or_default().to_string();
    store
        .rows(
            &format!("SELECT ?s ?o WHERE {{ ?s <{MARKET}{predicate}> ?o }}"),
            &beliefs,
        )
        .unwrap()
        .iter()
        .map(|r| (local(value(r, "s").unwrap()), value(r, "o").unwrap()))
        .collect()
}

/// The allotment's three agents, booted at noon on the first of January, and driven pass by pass.
fn allotment(walk: impl FnOnce(&mut Market<'_, '_>)) {
    allotment_on(true, walk);
}

/// `allotment`, on a clock that ticks at every read or stands where the walk sets it.
fn allotment_on(ticks: bool, walk: impl FnOnce(&mut Market<'_, '_>)) {
    let namespaces = Arc::new(Namespaces::of_tree(tree()).unwrap());
    let stores: Vec<Store> = NAMES.iter().map(|_| Store::new(namespaces.clone()).unwrap()).collect();
    let clock = Ticking(
        Arc::new(Mutex::new(instant("2026-01-01T12:00:00+00:00").unwrap())),
        ticks,
    );
    let carried = Rc::new(RefCell::new(Carried::default()));
    let world = world();
    let mut assembled = Vec::new();
    for (store, name) in stores.iter().zip(NAMES) {
        let loaded = booted(store, tree(), &world, name, clock.at()).unwrap();
        let bus = Bus {
            name,
            clock: clock.clone(),
            carried: carried.clone(),
        };
        let member = Mqtt::new(store, &format!("{AL}{name}"), vec![(None, Box::new(bus))]);
        carried
            .borrow_mut()
            .inboxes
            .insert(name.to_string(), member.inbox.clone());
        assembled.push(
            assemble_seen(
                store,
                name,
                Arc::new(clock.clone()),
                &loaded,
                None,
                Wiring {
                    mqtt: Some(member),
                    ..Wiring::default()
                },
            )
            .unwrap(),
        );
    }
    let mut seen = Vec::new();
    let mut runtimes: Vec<Runtime<'_>> = Vec::new();
    for ((parts, s), (store, name)) in assembled
        .iter_mut()
        .map(|(p, s)| (p, std::mem::take(s)))
        .zip(stores.iter().zip(NAMES))
    {
        let lent: Vec<(String, &mut dyn Part)> = parts
            .iter_mut()
            .map(|(p, part)| (p.clone(), part.as_mut() as &mut dyn Part))
            .collect();
        runtimes.push(Runtime::new(store, name, &clock, lent).unwrap());
        seen.push(s);
    }
    let mut market = Market {
        stores: &stores,
        runtimes,
        seen,
        clock: clock.clone(),
        carried,
    };
    walk(&mut market);
    for runtime in &mut market.runtimes {
        runtime.stop();
    }
}

struct Market<'a, 'r> {
    stores: &'a [Store],
    runtimes: Vec<Runtime<'r>>,
    seen: Vec<Seen<'a>>,
    clock: Ticking,
    carried: Rc<RefCell<Carried>>,
}

impl<'a> Market<'a, '_> {
    fn index(name: &str) -> usize {
        NAMES.iter().position(|n| *n == name).unwrap()
    }

    fn store(&self, name: &str) -> &Store {
        &self.stores[Self::index(name)]
    }

    /// The board's reading, delivered to one grower at the instant the clock stands at.
    fn read(&self, name: &str, payload: &str) {
        let inbox = self.carried.borrow().inboxes[name].clone();
        inbox.deliver(READINGS, payload.as_bytes(), Some(self.clock.at()));
    }

    /// The board's reading, delivered to both growers, each subscribed to the board's topic.
    fn publish(&self, payload: &str) {
        for name in ["rose_grower", "fern_grower"] {
            self.read(name, payload);
        }
    }

    /// Three rounds of one pass each, every agent in turn.
    fn run(&mut self) {
        for _ in 0..3 {
            for runtime in &mut self.runtimes {
                runtime.run(Some(1), 0.0).unwrap();
            }
        }
    }

    /// One pass of one agent alone.
    fn pass(&mut self, name: &str) {
        self.runtimes[Self::index(name)].run(Some(1), 0.0).unwrap();
    }

    fn planner(&self, name: &str) -> std::cell::Ref<'_, orexis_planning::Planner<'a>> {
        self.seen[Self::index(name)].planner.as_ref().unwrap().borrow()
    }

    fn commands(&self) -> Vec<(String, Json)> {
        self.carried.borrow().commands()
    }

    fn walking(&self, name: &str) -> Vec<String> {
        let executor = self.seen[Self::index(name)].executor.as_ref().unwrap();
        executor.borrow().walking().unwrap()
    }
}

fn pair(a: &str, b: &str) -> (String, String) {
    (a.to_string(), b.to_string())
}

fn dose(valve: &str, ml: i64) -> (String, Json) {
    (
        format!("actuators/{valve}/command"),
        serde_json::json!({ "dose_ml": ml }),
    )
}

#[test]
fn a_dry_plot_is_watered_by_a_claim_bought_on_the_supplier_s_venue() {
    allotment(|m| {
        m.read("rose_grower", r#"{"rose_moisture": 0.2}"#);
        m.read("fern_grower", r#"{"fern_moisture": 0.45}"#);
        m.run();
        let told = m.carried.borrow().told("supplier");
        assert!(!told.is_empty(), "the dry grower called for a round");
        assert!(
            facts(m.store("rose_grower"), "open").contains(&pair("water", "true")),
            "the supplier offered a round, and the grower believes it"
        );
        assert!(
            facts(m.store("fern_grower"), "open").contains(&pair("water", "true")),
            "offered to every bidder on the venue"
        );
        assert!(told.iter().any(|p| p.contains("Bid")), "the dry grower tendered");
        assert!(m.commands().is_empty(), "nothing is served before the round clears");

        m.clock.on(31);
        m.run();
        let held = facts(m.store("rose_grower"), "heldBy");
        assert_eq!(held.len(), 1, "one claim: {held:?}");
        let (claim, holder) = held.into_iter().next().unwrap();
        assert_eq!(
            holder,
            format!("{AL}rose_grower"),
            "the round cleared, and the rose won the lot"
        );
        let amounts: Vec<String> = facts(m.store("rose_grower"), "amountL")
            .into_iter()
            .filter(|(c, _)| *c == claim)
            .map(|(_, a)| a)
            .collect();
        assert_eq!(
            amounts.iter().map(|a| a.parse::<f64>().unwrap()).collect::<Vec<_>>(),
            [0.5],
            "0.2 against a middle of 0.45 at two litres a fraction asks half a litre, all the lot"
        );
        assert!(
            facts(m.store("rose_grower"), "pricePerL")
                .iter()
                .any(|(c, p)| *c == claim && p.parse::<f64>().unwrap() == 3.0),
            "pay-as-bid: the claim costs what the rose bid"
        );
        assert_eq!(
            facts(m.store("supplier"), "presented"),
            BTreeSet::from([pair(&claim, "true")]),
            "the rose presented it"
        );
        assert_eq!(m.commands(), [dose("rose_valve", 500)], "and the supplier served it");
        assert_eq!(
            facts(m.store("rose_grower"), "discharged"),
            BTreeSet::from([pair(&claim, "true")]),
            "and told the rose it was discharged"
        );
        assert!(
            facts(m.store("rose_grower"), "holdsClaimOn").is_empty(),
            "so the rose holds it no longer"
        );

        m.clock.on(300);
        m.read("rose_grower", r#"{"rose_moisture": 0.45}"#);
        m.run();
        assert!(
            m.walking("rose_grower").is_empty(),
            "the reading answered the presentation"
        );
        assert_eq!(
            m.commands().len(),
            1,
            "one dose, and nothing more once the plot is watered"
        );
    });
}

#[test]
fn one_lot_goes_to_the_dearer_bid_and_the_other_grower_calls_again() {
    allotment(|m| {
        m.read("rose_grower", r#"{"rose_moisture": 0.2}"#);
        m.read("fern_grower", r#"{"fern_moisture": 0.25}"#);
        m.run();
        m.clock.on(31);
        m.run();
        assert_eq!(m.commands(), [dose("rose_valve", 500)], "the rose won the first lot");
        let fern: BTreeSet<_> = facts(m.store("fern_grower"), "heldBy");
        let rose: BTreeSet<_> = facts(m.store("rose_grower"), "heldBy");
        assert!(
            fern.difference(&rose).next().is_none(),
            "the fern won nothing, and knows only of the rose's claim"
        );
        m.read("rose_grower", r#"{"rose_moisture": 0.45}"#);

        m.clock.on(120);
        m.run();
        //  THE SECOND ROUND CLEARS WHEN ITS PERIOD ENDS, and where that falls on this clock depends on how many times
        //  the agents read it — every read is a second — so the walk waits for the round, a round's length at a time.
        for _ in 0..3 {
            m.clock.on(31);
            m.run();
            if m.commands().len() > 1 {
                break;
            }
        }
        assert_eq!(
            m.commands(),
            [dose("rose_valve", 500), dose("fern_valve", 400)],
            "the fern called again, won the second round alone, and was served four tenths of a litre"
        );
    });
}

const KINDS: [&str; 5] = [
    "market#Call",
    "market#Round",
    "market#Bid",
    "market#Claim",
    "market#Presentation",
];

/// `test_simulation.py`'s walk — the rose's plot dried below its floor three days on, its grower buying water on the
/// supplier's venue and the supplier serving the claim, the simulator's next reading answering the grower — replayed
/// from what the Python simulator published, on a clock that stands where the walk sets it, and held to the doses and
/// the documents the Python agents sent at each instant.
#[test]
fn a_plot_that_dries_below_its_floor_is_watered_with_bought_water() {
    let text =
        std::fs::read_to_string(Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/allotment.tsv")).unwrap();
    let (mut steps, mut commands, mut told) = (Vec::<(DateTime, Vec<String>)>::new(), Vec::new(), Vec::new());
    for line in text.lines().filter(|l| !l.starts_with('#') && !l.trim().is_empty()) {
        let (kind, rest) = line.split_once('\t').unwrap();
        match kind {
            "step" => {
                let mut fields = rest.splitn(3, '\t');
                let at = instant(fields.next().unwrap()).unwrap();
                steps.push((at, fields.nth(1).map(str::to_string).into_iter().collect()));
            }
            "command" => commands.push(rest.to_string()),
            "told" => told.push(rest.to_string()),
            other => panic!("{other}: no such line"),
        }
    }
    allotment_on(false, |m| {
        for (at, published) in &steps {
            *m.clock.0.lock().unwrap() = *at;
            for payload in published {
                m.publish(payload);
            }
            m.run();
        }
        assert!(
            m.walking("rose_grower").is_empty(),
            "the simulator's reading answered the presentation"
        );
        let carried = m.carried.borrow();
        let said = |(at, topic, payload): &(DateTime, String, Vec<u8>)| {
            let text = String::from_utf8_lossy(payload);
            if topic.starts_with("actuators/") {
                let json: Json = serde_json::from_slice(payload).unwrap();
                format!("command\t{}\t{topic}\t{json}", isoformat(*at))
            } else {
                let kinds: Vec<&str> = KINDS.iter().copied().filter(|k| text.contains(k)).collect();
                format!("told\t{}\t{topic}\t{}", isoformat(*at), kinds.join(","))
            }
        };
        let sent: Vec<String> = carried.stamped.iter().map(said).collect();
        let (doses, documents): (Vec<String>, Vec<String>) = sent.into_iter().partition(|l| l.starts_with("command"));
        let strip = |l: &String| l.split_once('\t').unwrap().1.to_string();
        assert_eq!(
            doses.iter().map(strip).collect::<Vec<_>>(),
            commands,
            "the doses, against the Python agents'"
        );
        assert_eq!(
            documents.iter().map(strip).collect::<Vec<_>>(),
            told,
            "the documents told, against the Python agents'"
        );
    });
}

/// Every scope `store` holds, each as the set of its members' local names.
fn scopes(store: &Store) -> Vec<BTreeSet<String>> {
    let mut held: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let text = "SELECT ?m ?s WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:ScopeGraph } \
                GRAPH ?g { ?m planning:inScope ?s } }";
    for r in store.rows(text, &[]).unwrap() {
        let member = value(&r, "m").unwrap();
        let member = member.rsplit(['#', '/']).next().unwrap_or_default().to_string();
        held.entry(value(&r, "s").unwrap()).or_default().insert(member);
    }
    held.into_values().collect()
}

/// The allotment imports the climate domain and holds no heater, so a row leaving the heater unbound is no filling
/// (#913): two scopes, the market plumbing with the dosing, and `Serving` alone on `discharged`, the wait in both.
#[test]
fn the_allotment_is_two_scopes_and_the_heating_it_imports_is_in_neither() {
    allotment(|m| {
        for name in NAMES {
            let scopes = scopes(m.store(name));
            assert_eq!(
                scopes.len(),
                2,
                "{name}: two scopes, not one per plot for a heating nothing can take: {scopes:?}"
            );
            assert!(
                !scopes.iter().any(|s| s.contains("Heating")),
                "{name}: the heating is in no scope: {scopes:?}"
            );
            let least = scopes.iter().min_by_key(|s| s.len()).unwrap();
            let most = scopes.iter().max_by_key(|s| s.len()).unwrap();
            assert!(
                ["Serving", "discharged"].iter().all(|w| least.contains(*w)),
                "{name}: Serving stands alone: {scopes:?}"
            );
            assert!(
                ["Dosing", "Calling", "Tendering", "Presenting", "Offering", "Clearing"]
                    .iter()
                    .all(|w| most.contains(*w)),
                "{name}: the market plumbing and the dosing are one scope: {scopes:?}"
            );
            assert!(
                scopes.iter().all(|s| s.contains("Wait")),
                "{name}: the wait is in every scope: {scopes:?}"
            );
        }
    });
}

/// The market's `Calling` and `Tendering` read anything until #908 — a predicate list under `NOT EXISTS` with a `NOT
/// EXISTS` nested in it — so a grower's every world hashed whole and a reading inside its band at a new instant was a
/// surprise every pass. Read, the same number ten minutes on is the old present.
#[test]
fn a_grower_s_world_is_hashed_within_what_the_market_s_texts_read() {
    allotment(|m| {
        m.read("rose_grower", r#"{"rose_moisture": 0.45}"#);
        m.pass("rose_grower");
        {
            let planner = m.planner("rose_grower");
            let read = planner
                .read()
                .expect("the growers' read set is readable: no text of the allotment reads anything");
            for p in ["bidsIn", "calledBy", "calledOn", "answered", "clearedAt"] {
                assert!(read.contains(&format!("{MARKET}{p}")), "{p} is read: {read:?}");
            }
            assert!(
                planner.rerooted.iter().all(|p| *p == "first") && !planner.rerooted.is_empty(),
                "{:?}",
                planner.rerooted
            );
        }
        m.clock.on(600);
        m.read("rose_grower", r#"{"rose_moisture": 0.45}"#);
        m.pass("rose_grower");
        let planner = m.planner("rose_grower");
        assert!(
            !planner.rerooted.is_empty() && planner.rerooted.iter().all(|p| *p == "ground"),
            "the same reading at a new instant is the present the last pass stood in, not a surprise: {:?}",
            planner.rerooted
        );
    });
}

/// The holder's own IRI is never part of a trouble's key (#908): the present's trouble and the foreseen one are one
/// want over one open stretch, placed from the present, though the grower is no member of `Serving`'s scope.
#[test]
fn the_present_reading_and_its_foreseen_prediction_are_one_way_of_failing() {
    allotment(|m| {
        let noon = instant("2026-01-01T12:00:00+00:00").unwrap();
        let scopes = scopes(m.store("rose_grower"));
        assert!(
            scopes.len() > 1 && scopes.iter().any(|s| !s.contains("rose_grower")),
            "the premise: a scope the grower is no member of: {scopes:?}"
        );
        m.read("rose_grower", r#"{"rose_moisture": 0.2}"#);
        m.pass("rose_grower");
        let text = "SELECT ?g ?s ?e WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . \
                    ?g a planning:WantGraph ; dcterms:temporal ?p . ?p orexis:start ?s OPTIONAL { ?p orexis:end ?e } } }";
        let planner = m.planner("rose_grower");
        let wants: Vec<_> = planner
            .imaginaria
            .values()
            .flat_map(|store| store.rows(text, &[]).unwrap())
            .collect();
        assert!(
            wants.len() == 1 && !wants[0].contains_key("e"),
            "one want graph over one open stretch: {wants:?}"
        );
        let within = |s: &str, minutes: i64| {
            instant(s).unwrap()
                < noon
                    .checked_add_day_time_duration(DayTimeDuration::new(minutes * 60))
                    .unwrap()
        };
        assert!(
            within(&value(&wants[0], "s").unwrap(), 1),
            "in trouble from the present: {wants:?}"
        );
        let committed = m
            .store("rose_grower")
            .rows(
                "SELECT ?s WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . \
                 ?g a execution:CommittedStepGraph ; dcterms:temporal/orexis:start ?s } }",
                &[],
            )
            .unwrap();
        assert!(!committed.is_empty(), "a step is committed");
        assert!(
            committed.iter().all(|r| within(&value(r, "s").unwrap(), 2)),
            "the plan is placed from the present, not from the foreseen ground twenty minutes on: {committed:?}"
        );
    });
}

#[test]
fn each_agent_listens_on_its_own_topic_and_the_growers_on_their_probes() {
    allotment(|m| {
        let mut patterns = m.carried.borrow().patterns.clone();
        patterns.values_mut().for_each(|p| p.sort());
        let expected: BTreeMap<String, Vec<String>> = [
            ("supplier", vec!["agents/supplier/inbox"]),
            ("rose_grower", vec!["agents/rose_grower/inbox", READINGS]),
            ("fern_grower", vec!["agents/fern_grower/inbox", READINGS]),
        ]
        .into_iter()
        .map(|(n, p)| (n.to_string(), p.into_iter().map(str::to_string).collect()))
        .collect();
        assert_eq!(
            patterns, expected,
            "the board's one topic, named for it, and each grower reads its own probe's value of the document"
        );
    });
}
