//! Translation over its test viewing, held to `orexis-translation/tests/`: the chats an agent is in, the briefing, what a
//! chat may read and what a person may state, and the part — a person's prose answered or kept as a statement the agent
//! believes as the world's word, held to the words the chat allows, what the agent says to a person rendered and sent
//! back, and in a group an agent answering when named and keeping silent otherwise. The model is a stand-in that answers
//! what the test says, and the conversation runs on the test's own thread.

use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use oxsdatatypes::DateTime;
use serde_json::{Value as Json, json};

use orexis::boot::{Booting, boot};
//  LINKED FOR THE DOCUMENTS THEY BRING: the world's chats are carried by these, and the boot refuses a carrier the
//  binary was built without.
use orexis::clock::{Elapsing, instant};
use orexis::events::as_of;
use orexis::namespaces::Namespaces;
use orexis::ontology::BELIEF;
use orexis::store::{Store, Within, iri, value};
use orexis::task::{Heard, Outside, Package, Running, Turn as Handling, Wake, Woke};
use orexis_speech::events::{Said, Statement};
use orexis_speech::prose::{Carrier, PROSE_GRAPH, PROSE_KEPT, Prose, ProseKept, WRITING_ANNOUNCED, carry, kept};
use orexis_translation::briefing::briefing;
use orexis_translation::chat::chats_of;
use orexis_translation::create::{CONVERSE_SYSTEM, Inline, SAY_SYSTEM, SILENT, TURNS, UNADDRESSED};
use orexis_translation::events::{Conversed, Translated};
use orexis_translation::model::{Answer, Failure, Model, Turn};
use orexis_translation::readable::{QUERY, ROWS, Readable, VOCABULARY};
use orexis_translation::stated::{PROPERTY, Stating, believe, listing, rendered, statement_of, words};
use orexis_transport_email as _;
use orexis_transport_mqtt as _;
use orexis_transport_telegram as _;

const V: &str = "http://example.org/orexis/world/viewing#";
const O: &str = "http://example.org/orexis#";
const STATEMENT: &str = "http://example.org/orexis/speech#StatementGraph";

fn world() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/world")
}

fn now() -> DateTime {
    instant("2026-11-01T09:00:00+00:00").unwrap()
}

fn seeker() -> Store {
    let store = Store::new(Arc::new(Namespaces::linked().unwrap())).unwrap();
    boot(
        &store,
        &Booting {
            world: &world(),
            agent: "seeker",
        },
    )
    .unwrap();
    store
}

fn me() -> String {
    format!("{V}seeker")
}

// --- the chats -----------------------------------------------------------------------------------------------------

#[test]
fn the_agent_reads_its_chats_off_the_world_each_with_its_channel_and_who_is_in_it() {
    let store = seeker();
    let chats: std::collections::BTreeMap<String, _> = chats_of(&store)
        .unwrap()
        .into_iter()
        .map(|c| (c.iri.rsplit('#').next().unwrap().to_string(), c))
        .collect();
    assert_eq!(
        chats.keys().cloned().collect::<Vec<_>>(),
        ["household", "seeker_and_anna", "seeker_and_boris", "seeker_and_clara"]
    );
    let clara = &chats["seeker_and_clara"];
    assert_eq!(clara.channel, format!("{V}clara_telegram"));
    assert_eq!(clara.people, [(format!("{V}clara"), "Clara".to_string())]);
    let household = &chats["household"];
    assert_eq!(
        household.people,
        [
            (format!("{V}anna"), "Anna".to_string()),
            (format!("{V}clara"), "Clara".to_string())
        ]
    );
    assert_eq!(
        household.agents,
        [
            (format!("{V}keeper"), vec!["keeper".to_string(), "Kim".to_string()]),
            (me(), vec!["seeker".to_string()])
        ],
        "an agent answers to its local id, its IRI's local name and the name it goes by"
    );
    assert_eq!(clara.person(None), Some((format!("{V}clara"), "Clara".to_string())));
    assert!(household.person(None).is_none() && household.person(Some(&format!("{V}boris"))).is_none());
    assert_eq!(clara.reads, [format!("{O}BeliefGraph")]);
    assert!(household.reads.is_empty() && chats["seeker_and_anna"].reads.is_empty());
    assert_eq!(clara.allows, [PROPERTY.to_string()]);
    assert_eq!(household.allows, [format!("{V}refused"), format!("{V}viewingAt")]);
    assert!(chats["seeker_and_anna"].allows.is_empty());
}

// --- the briefing --------------------------------------------------------------------------------------------------

#[test]
fn a_briefing_says_who_the_agent_is_what_the_chat_reads_and_what_a_person_may_state() {
    let store = seeker();
    let who = briefing(
        &store,
        &me(),
        &[format!("{O}BeliefGraph")],
        " - speech (93 lines)",
        "A person may state x",
        &[],
    )
    .unwrap();
    assert!(who.starts_with("YOU SPEAK FOR seeker."));
    assert!(
        who.contains("WHAT THIS CHAT LETS YOU READ: every graph of BeliefGraph")
            && who.contains(" - speech (93 lines)")
    );
    assert!(who.ends_with("WHAT A PERSON MAY STATE HERE, with the state tool. A person may state x"));
    let nothing = briefing(&store, &me(), &[], "", "", &[]).unwrap();
    assert!(nothing.contains("lets you read nothing") && nothing.contains("A person states nothing"));
    assert!(!nothing.contains("WHAT THIS CHAT LETS YOU READ") && !nothing.contains("THE ROLES IT PLAYS"));
    let all = briefing(&store, &me(), &[format!("{O}Graph")], "", "", &[]).unwrap();
    assert!(
        all.contains("orexis:Self") || all.contains("Self>"),
        "the self graph is in it where the chat reads it"
    );
    assert!(
        all.contains("THE ROLES IT PLAYS:\n - ")
            && all.contains("\n - Translator: An agent that speaks with people in the chats it is in"),
        "{all}"
    );
    assert_eq!(
        all,
        briefing(&store, &me(), &[format!("{O}Graph")], "", "", &[]).unwrap(),
        "the same text, or nothing caches"
    );
}

// --- what a chat may read ------------------------------------------------------------------------------------------

fn readable() -> Readable {
    Readable::new(&seeker(), &[format!("{O}BeliefGraph")], Some(&me())).unwrap()
}

fn beliefs() -> Vec<String> {
    vec!["orexis:BeliefGraph".to_string()]
}

#[test]
fn each_vocabulary_is_listed_by_its_prefix_and_read_as_a_glossary() {
    let r = readable();
    assert!(
        r.vocabularies.contains_key("orexis") && r.vocabularies.contains_key("speech"),
        "{}",
        r.listing()
    );
    assert_eq!(r.vocabulary("speech"), r.vocabulary("speech:"));
    assert!(
        r.vocabulary("nonesuch")
            .starts_with("no vocabulary 'nonesuch' in this chat; these are:")
    );
    assert!(
        !r.listing().contains("closure"),
        "the subclass closure is derived, and no vocabulary"
    );
    let glossary: Vec<String> = r.vocabulary("speech").lines().map(str::to_string).collect();
    assert!(
        glossary.contains(
            &"speech:Chat (class): Who speaks with whom, through what: a standing thing of the society, with its \
              `speech:participant`s - an agent and a person, or several - and its `speech:channel`, the thing their \
              prose goes through."
                .split_whitespace()
                .collect::<Vec<_>>()
                .join(" ")
        ),
        "{glossary:#?}"
    );
    assert!(
        glossary
            .iter()
            .any(|l| l.starts_with("speech:participant (property, speech:Chat → "))
    );
    assert!(
        glossary
            .iter()
            .any(|l| l.starts_with("speech:allows (property, speech:Chat → rdf:Property): "))
    );
    assert!(
        glossary
            .iter()
            .all(|l| l.rsplit_once(": ").map_or(l.as_str(), |(_, t)| t).chars().count() <= 220)
    );
    assert!(
        regex::Regex::new(r"translation \([0-9]+ terms\)")
            .unwrap()
            .is_match(&r.listing())
    );
    let whole = r.query("SELECT ?c WHERE { speech:Chat rdfs:comment ?c }", &beliefs());
    assert!(whole.contains("the thing their prose goes through") && whole.len() > 150);
}

#[test]
fn a_query_reads_the_chats_graphs_as_one_and_writes_a_name_with_its_prefix() {
    let r = readable();
    assert!(
        r.query(
            "SELECT ?l WHERE { ?l rdfs:label ?n FILTER(CONTAINS(STR(?l), \"flat\")) }",
            &beliefs()
        )
        .contains("flat_12")
    );
    assert_eq!(r.query("ASK { ?c a speech:Chat }", &beliefs()), "true");
    assert_eq!(
        r.query("SELECT ?x WHERE { ?x a <http://example.org/none> }", &beliefs()),
        "(no rows)"
    );
    assert!(
        r.query("SELECT ?c WHERE { ?x a ?c } VALUES ?c { speech:Chat }", &beliefs())
            .contains("c: speech:Chat")
    );
    let named = r.query("SELECT ?c WHERE { ?c a speech:Chat }", &beliefs());
    assert!(
        named.starts_with("c: viewing:") && !named.contains("http://"),
        "{named}"
    );
    assert_eq!(
        r.query(
            "ASK { ?c a speech:Chat ; speech:participant viewing:seeker }",
            &beliefs()
        ),
        "true"
    );
    assert!(
        r.tools()[1]["description"]
            .as_str()
            .unwrap()
            .contains("viewing: naming the agent's own world")
    );
    assert_eq!(
        r.query("SELECT ?x WHERE { ?x ?p \"GRAPH SERVICE FROM\" }", &beliefs()),
        "(no rows)"
    );
}

#[test]
fn a_query_that_could_do_anything_but_read_the_chats_graphs_is_refused_with_why() {
    let r = readable();
    for (text, why) in [
        (
            "SELECT * WHERE { SERVICE <http://elsewhere.example/> { ?s ?p ?o } }",
            "it holds a SERVICE clause",
        ),
        (
            "SELECT * FROM <http://elsewhere.example/> WHERE { ?s ?p ?o }",
            "it holds a FROM",
        ),
        (
            "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
            "only a SELECT or an ASK is run",
        ),
        ("DELETE WHERE { ?s ?p ?o }", "it does not parse"),
    ] {
        let answer = r.query(text, &beliefs());
        assert!(answer.starts_with(&format!("refused: {why}")), "{text}: {answer}");
    }
}

#[test]
fn a_query_reads_the_kinds_it_names_and_the_catalogue_is_never_merged_into_them() {
    let r = readable();
    let found = r.query(
        "SELECT DISTINCT ?g ?how WHERE { GRAPH ?g { ?c a speech:Chat } GRAPH ?cat { ?g orexis:arrivedBy ?how } }",
        &beliefs(),
    );
    assert!(
        found.contains("g: <file://") && found.contains("how: orexis:Asserted"),
        "{found}"
    );
    assert_eq!(
        r.query("ASK { ?g orexis:arrivedBy ?how }", &beliefs()),
        "false",
        "statements about graphs are no data"
    );
    assert_eq!(
        r.query("ASK { ?c a speech:Chat }", &["orexis:OntologyGraph".to_string()]),
        "false"
    );
    assert!(r.listing().contains("orexis:OntologyGraph (") && r.listing().contains("Kinds of graph"));
    assert!(
        r.query("ASK { ?s ?p ?o }", &["planning:WantGraph".to_string()])
            .starts_with("refused: no graph of kind planning:WantGraph in this chat; these are: ")
    );
    assert_eq!(
        r.query("ASK { ?s ?p ?o }", &[]),
        "refused: name the kinds of graph the query reads"
    );
    let answer = r.query("SELECT ?s ?p ?o WHERE { ?s ?p ?o }", &beliefs());
    assert_eq!(answer.matches('\n').count(), ROWS);
    assert!(answer.contains(&format!("(the first {ROWS} of")));
    let names: Vec<String> = r
        .tools()
        .iter()
        .map(|t| t["name"].as_str().unwrap().to_string())
        .collect();
    assert_eq!(names, [VOCABULARY, QUERY]);
    assert_eq!(
        r.call(
            QUERY,
            &json!({"sparql": "ASK { ?c a speech:Chat }", "kinds": beliefs()})
        )
        .as_deref(),
        Some("true")
    );
    assert!(r.call("viewings_offered", &json!({})).is_none());
}

// --- what a person may state ---------------------------------------------------------------------------------------

fn prefixes(store: &Store) -> orexis_translation::readable::Prefixes {
    let mut p = orexis_translation::readable::namespaces(store);
    p.insert("viewing".into(), V.into());
    p
}

#[test]
fn a_chat_allows_the_properties_it_names_or_every_one_a_vocabulary_declares() {
    let store = seeker();
    let named = words(&store, &[format!("{V}viewingAt")]).unwrap();
    assert_eq!(
        named
            .iter()
            .map(|w| (w.iri.clone(), w.domain.clone(), w.range.clone()))
            .collect::<Vec<_>>(),
        [(
            format!("{V}viewingAt"),
            Some(format!("{V}Listing")),
            Some("http://www.w3.org/2001/XMLSchema#dateTime".to_string())
        )]
    );
    let every: Vec<String> = words(&store, &[PROPERTY.to_string()])
        .unwrap()
        .into_iter()
        .map(|w| w.iri)
        .collect();
    for w in [
        format!("{V}viewingAt"),
        format!("{V}refused"),
        format!("{V}viewingAsked"),
        "http://example.org/orexis/speech#allows".into(),
    ] {
        assert!(every.contains(&w), "{w}");
    }
    assert!(words(&store, &[]).unwrap().is_empty());
    let said = listing(
        &store,
        &words(&store, &[format!("{V}refused")]).unwrap(),
        false,
        &prefixes(&store),
        true,
    )
    .unwrap();
    assert_eq!(
        said.lines().collect::<Vec<_>>(),
        [
            "A person may state here, in these words alone:",
            " - viewing:refused (application refused), of a viewing:Listing, a xsd:boolean: Whether the application for the listing was refused.",
            "     viewing:flat_12 (the two-room flat on Kastanienallee)",
            "     viewing:flat_7 (the studio on Rigaer Straße)",
        ]
    );
}

#[test]
fn a_statement_is_one_graph_per_subject_and_word_and_believed_by_nobody_as_the_world_states() {
    let store = seeker();
    let stating = Stating {
        allowed: words(&store, &[PROPERTY.to_string()]).unwrap(),
        every: true,
        prefixes: prefixes(&store),
    };
    let (payload, why) = statement_of(
        &store,
        &stating,
        &json!({"says": "viewing:flat_12 viewing:viewingAt \"2026-11-02T18:00:00+00:00\" ; viewing:refused false ."}),
        &format!("{V}clara"),
        "Tuesday at six, and you are not refused",
        now(),
    )
    .unwrap();
    assert!(why.is_empty(), "{why:?}");
    let payload = payload.unwrap();
    let statements = orexis_speech::heard::heard(&store, &me(), &payload).unwrap();
    assert_eq!(
        statements.len(),
        2,
        "one per subject and word, so each is replaced alone"
    );
    let mut believed = Vec::new();
    for s in &statements {
        believed.extend(believe(&store, s).unwrap());
    }
    let common = store.graphs_of(&[BELIEF], &Within::common()).unwrap();
    assert!(believed.len() == 2 && believed.iter().all(|b| common.contains(b)));
    let found = store
        .rows(
            "PREFIX v: <http://example.org/orexis/world/viewing#>\nSELECT ?at WHERE { v:flat_12 v:viewingAt ?at }",
            &believed.iter().map(String::as_str).collect::<Vec<_>>(),
        )
        .unwrap();
    assert_eq!(
        found.iter().filter_map(|r| value(r, "at")).collect::<Vec<_>>(),
        ["2026-11-02T18:00:00Z"]
    );
}

#[test]
fn a_statement_the_agent_makes_is_read_with_its_words_labels() {
    let store = seeker();
    let doc = orexis::document::Document::of(
        b"<urn:x:a> { <http://example.org/orexis/world/viewing#flat_7> <http://example.org/orexis/world/viewing#refused> true . }\n\
          <urn:x:a> a <http://example.org/orexis/speech#StatementGraph> .\n",
    )
    .unwrap();
    let text = rendered(&store, &doc, &prefixes(&store)).unwrap();
    assert!(text.contains("viewing:flat_7 viewing:refused true"), "{text}");
    assert!(
        text.contains(" - refused: application refused — Whether the application for the listing was refused"),
        "{text}"
    );
    assert!(text.contains(" - flat_7: the studio on Rigaer Straße"), "{text}");
}

// --- the part --------------------------------------------------------------------------------------------------------

/// A carrier standing for every one: what is said to a channel kept, with the message it replies to, and where the
/// agent was shown writing.
#[derive(Default)]
struct Bot {
    said: Vec<(String, String)>,
    replies: Vec<Option<String>>,
    writing: Vec<String>,
}

impl Carrier for Bot {
    fn say_to(&mut self, channel: &str, text: &str, reply: Option<&str>) -> bool {
        self.said.push((channel.to_string(), text.to_string()));
        self.replies.push(reply.map(str::to_string));
        true
    }

    fn writing_in(&mut self, channel: &str) -> bool {
        self.writing.push(channel.to_string());
        true
    }
}

/// The bot as a transport's part: a person's words kept and said kept at the next pass, and what the agent says
/// carried, as a member hears it beneath its trigger.
struct Member {
    store: Store,
    bot: Arc<Mutex<Bot>>,
    kept: Vec<String>,
    /// Documents said, to say said at the next pass, as speech says them.
    said: Vec<Said>,
}

//  THE MEMBER'S TASK, registered as a package registers itself: it takes the member the test handed outside, hears
//  the agent's words kept and its writing announced, and is rung for what the test queued on it.
inventory::submit! { Package { name: "test/member", documents: &[], start: |handed| {
    let member = handed.outside.take::<Arc<Mutex<Member>>>().expect("a member handed");
    let mut hears = handed.events.hears();
    hears.event(PROSE_KEPT, 1);
    hears.event(WRITING_ANNOUNCED, 1);
    let mut arrived = handed.arrived();
    handed.outside.hand(arrived.wake());
    let handed = handed.clone();
    Ok(Some(Box::pin(async move {
        loop {
            let woke = tokio::select! {
                biased;
                _ = handed.stopped() => break,
                woke = hears.next() => match woke {
                    Some(woke) => Some(woke),
                    None => break,
                },
                _ = arrived.wait() => None,
            };
            let mut turn = handed.turn();
            let mut member = member.lock().unwrap();
            let wrote = match woke {
                Some(Woke::Event(_, event)) => member.heard_event(&event, &mut turn),
                _ => Ok(member.queued(&mut turn)),
            };
            turn.done(wrote)?;
        }
        Ok(())
    })))
} } }

impl Member {
    fn heard_event(&mut self, event: &Heard, pass: &mut Handling<'_>) -> Result<Vec<String>, orexis::Error> {
        carry(&self.store, &mut *self.bot.lock().unwrap(), event, pass, CARRYING)?;
        Ok(Vec::new())
    }

    fn queued(&mut self, pass: &mut Handling<'_>) -> Vec<String> {
        let kept = std::mem::take(&mut self.kept);
        for prose in &kept {
            pass.emit(&ProseKept { prose: prose.clone() });
        }
        for said in std::mem::take(&mut self.said) {
            pass.emit(&said);
        }
        kept
    }
}

const CARRYING: &str = "http://example.org/orexis/telegram#Carrying";

/// What the stand-in was asked: each turn's system blocks, its messages and the names of the tools offered.
type Asked = Arc<Mutex<Vec<(Vec<String>, Vec<Json>, Vec<String>)>>>;

/// A model that answers what the test says: a turn calling each of `calls` in order, while tools are offered and the
/// turn is not the last, then `text`; and `text` to a rendering asked in one call — or a failure, where it fails.
struct StandIn {
    calls: Vec<(String, Json)>,
    text: String,
    asked: Asked,
    fails: Option<Failure>,
}

impl StandIn {
    fn new(calls: Vec<(&str, Json)>, text: &str) -> (Self, Asked) {
        let asked: Asked = Arc::default();
        (
            StandIn {
                calls: calls.into_iter().map(|(n, i)| (n.to_string(), i)).collect(),
                text: text.to_string(),
                asked: asked.clone(),
                fails: None,
            },
            asked,
        )
    }
}

impl Model for StandIn {
    fn converse(&self, system: &[String], messages: &[Json], tools: &[Json], last: bool) -> Result<Turn, Failure> {
        self.asked.lock().unwrap().push((
            system.to_vec(),
            messages.to_vec(),
            tools
                .iter()
                .map(|t| t["name"].as_str().unwrap_or_default().to_string())
                .collect(),
        ));
        if let Some(f) = &self.fails {
            return Err(f.clone());
        }
        let n = messages.iter().filter(|m| m["role"] == "assistant").count();
        if n < self.calls.len() && !tools.is_empty() && !last {
            let (name, inputs) = &self.calls[n];
            let id = format!("call{n}");
            return Ok(Turn {
                calls: vec![(id.clone(), name.clone(), inputs.clone())],
                content: vec![json!({"type": "tool_use", "id": id, "name": name, "input": inputs})],
                ..Turn::default()
            });
        }
        Ok(Turn {
            text: self.text.clone(),
            content: vec![json!({"type": "text", "text": self.text})],
            ..Turn::default()
        })
    }

    fn ask(&self, system: &str, text: &str) -> Result<Answer, Failure> {
        self.asked
            .lock()
            .unwrap()
            .push((vec![system.to_string()], vec![json!(text)], Vec::new()));
        Ok(Answer {
            text: self.text.clone(),
            ..Answer::default()
        })
    }
}

/// What each tool call was answered with, in the order the conversation handed them back.
fn results(messages: &[Json]) -> Vec<String> {
    messages
        .iter()
        .filter(|m| m["role"] == "user" && m["content"].is_array())
        .flat_map(|m| {
            m["content"]
                .as_array()
                .unwrap()
                .iter()
                .map(|b| b["content"].as_str().unwrap_or_default().to_string())
        })
        .collect()
}

/// The seeker's translation, its runtime and its bot: a person's words written on a channel run the pass that hears them.
struct Seeker<'s> {
    store: &'s Store,
    /// The agent's tasks, on a Tokio runtime of the harness's own with its time paused: a test stays sync.
    tasks: tokio::runtime::Runtime,
    running: Option<Running>,
    member: Arc<Mutex<Member>>,
    /// What rings the member for what the test queued on it.
    wake: Wake,
    bot: Arc<Mutex<Bot>>,
    /// The model the translator asks: whichever the test last set.
    model: Arc<Switch>,
    /// Who a test has hear what the agent says, connected at the next pass.
    hearer: Option<Hearer>,
}

/// A model that is whichever the test last set, since the translator is its task's alone.
#[derive(Default)]
struct Switch(Mutex<Option<Arc<dyn Model>>>);

impl Switch {
    fn now(&self) -> Arc<dyn Model> {
        self.0.lock().unwrap().clone().expect("a model set")
    }
}

impl Model for Switch {
    fn name(&self) -> Option<String> {
        self.0.lock().unwrap().as_ref().and_then(|m| m.name())
    }

    fn converse(&self, system: &[String], messages: &[Json], tools: &[Json], last: bool) -> Result<Turn, Failure> {
        self.now().converse(system, messages, tools, last)
    }

    fn ask(&self, system: &str, text: &str) -> Result<Answer, Failure> {
        self.now().ask(system, text)
    }
}

type Hearer = Arc<dyn Fn(&dyn orexis::events::Event, &oxigraph::model::NamedNode) + Send + Sync>;

impl<'s> Seeker<'s> {
    fn new(store: &'s Store) -> Self {
        let bot = Arc::new(Mutex::new(Bot::default()));
        let member = Arc::new(Mutex::new(Member {
            store: store.clone(),
            bot: bot.clone(),
            kept: Vec::new(),
            said: Vec::new(),
        }));
        let model = Arc::new(Switch::default());
        let tasks = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .start_paused(true)
            .build()
            .unwrap();
        let outside = Outside::default();
        outside.hand(member.clone());
        outside.hand(model.clone() as Arc<dyn Model>);
        outside.hand(Inline);
        let names = ["translation".to_string(), "test/member".to_string()];
        let running = {
            let _entered = tasks.enter();
            let clock = Arc::new(Elapsing::from(now()));
            orexis::task::start(store, "seeker", clock, outside.clone(), &names).unwrap()
        };
        let wake = outside.take::<Wake>().expect("the member's wake");
        Seeker {
            store,
            tasks,
            running: Some(running),
            member,
            wake,
            bot,
            model,
            hearer: None,
        }
    }

    fn model(&self, model: StandIn) {
        *self.model.0.lock().unwrap() = Some(Arc::new(model));
    }

    fn write(
        &mut self,
        channel: &str,
        text: &str,
        sender: Option<&str>,
        addressed: Option<bool>,
        message: Option<&str>,
    ) {
        let prose = Prose {
            channel: format!("{V}{channel}"),
            sender: sender.map(|s| format!("{V}{s}")),
            text: text.to_string(),
            at: Some(now()),
            addressed,
            message: message.map(str::to_string),
            reply: None,
        };
        self.member
            .lock()
            .unwrap()
            .kept
            .push(kept(self.store, &me(), &prose).unwrap());
        self.pass();
    }

    /// The agent says `document` to `to`, kept as speech keeps it and said said, as speech says it.
    fn say(&mut self, document: &[u8], to: &str) {
        let doc = orexis::document::Document::of(document).unwrap();
        let graphs = orexis_speech::said::said(self.store, &me(), &doc).unwrap();
        self.member.lock().unwrap().said.push(Said {
            statements: graphs
                .into_iter()
                .map(|graph| Statement {
                    graph,
                    kinds: Vec::new(),
                    said: Vec::new(),
                })
                .collect(),
            to: vec![format!("{V}{to}")],
            at: Some(now()),
        });
        self.pass();
    }

    /// Everything queued on the member and everything it sets off, handled: the member rung, and the agent settled.
    fn pass(&mut self) {
        let running = self.running.as_ref().expect("an agent running");
        if let Some(hearer) = self.hearer.take() {
            running
                .handed
                .events
                .watch()
                .connect(move |event, named| hearer(event, named));
        }
        self.wake.ring();
        self.tasks.block_on(running.settled()).unwrap();
    }

    /// Let `seconds` of the agent's time pass, and what falls due in them be done.
    fn later(&mut self, seconds: f64) {
        self.tasks.block_on(async {
            tokio::time::sleep(std::time::Duration::from_secs_f64(seconds)).await;
            for _ in 0..8 {
                tokio::task::yield_now().await;
            }
        });
        self.pass();
    }

    fn said(&self) -> Vec<(String, String)> {
        self.bot.lock().unwrap().said.clone()
    }

    fn believed(&self) -> Vec<(String, String)> {
        let rows = self
            .store
            .rows(
                "PREFIX : <http://example.org/orexis/world/viewing#>\nSELECT ?flat ?at ?owner WHERE { GRAPH ?g { ?flat :viewingAt ?at } \
                 GRAPH ?c { ?c a orexis:CatalogueGraph . ?g a orexis:BeliefGraph OPTIONAL { ?g orexis:ownedBy ?owner } } }",
                &[],
            )
            .unwrap();
        assert!(
            rows.iter().all(|r| !r.contains_key("owner")),
            "nobody's: the world's word"
        );
        rows.iter()
            .map(|r| (iri(r, "flat").unwrap(), value(r, "at").unwrap()))
            .collect()
    }

    fn statements(&self) -> Vec<String> {
        self.store.graphs_of(&[STATEMENT], &Within::default()).unwrap()
    }
}

/// Every named graph the store holds.
fn graphs(store: &Store) -> std::collections::BTreeSet<String> {
    store
        .engine()
        .named_graphs()
        .flatten()
        .map(|g| g.to_string().trim_matches(['<', '>']).to_string())
        .collect()
}

fn offer() -> Json {
    json!({"says": "viewing:flat_12 viewing:viewingAt \"2026-11-02T18:00:00+00:00\" ."})
}

fn viewings() -> (&'static str, Json) {
    (
        "query",
        json!({"sparql": "PREFIX v: <http://example.org/orexis/world/viewing#>\nSELECT ?flat ?at WHERE { ?flat v:viewingAt ?at }",
               "kinds": ["orexis:BeliefGraph"]}),
    )
}

#[test]
fn a_persons_prose_becomes_a_statement_the_agent_hears_and_believes_as_the_worlds_word() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    let (model, asked) = StandIn::new(vec![("state", offer())], "Thank you, Clara: Tuesday at six.");
    s.model(model);
    s.write(
        "clara_telegram",
        "I can show you Kastanienallee on Tuesday the 2nd at 6pm. Clara",
        None,
        None,
        None,
    );
    let asked = asked.lock().unwrap().clone();
    let (system, messages, offered) = &asked[0];
    assert_eq!(system[0], CONVERSE_SYSTEM);
    assert!(messages[0]["content"].as_str().unwrap().starts_with("From Clara:"));
    for t in ["state", "vocabulary", "query"] {
        assert!(
            offered.contains(&t.to_string()),
            "stating and reading, in one conversation: {offered:?}"
        );
    }
    let statements = s.statements();
    assert_eq!(statements.len(), 1);
    let by = store
        .rows(
            &format!(
                "SELECT ?by WHERE {{ GRAPH <{0}> {{ <{0}> speech:saidBy ?by }} }}",
                statements[0]
            ),
            &[],
        )
        .unwrap();
    assert_eq!(
        by.iter().filter_map(|r| iri(r, "by")).collect::<Vec<_>>(),
        [format!("{V}clara")]
    );
    assert_eq!(
        s.believed(),
        [(format!("{V}flat_12"), "2026-11-02T18:00:00Z".to_string())]
    );
    assert_eq!(results(&asked[1].1), ["kept: the agent believes it now"]);
    assert_eq!(
        s.said(),
        [(
            format!("{V}clara_telegram"),
            "Thank you, Clara: Tuesday at six.".to_string()
        )]
    );
}

#[test]
fn said_again_of_a_subject_a_word_replaces_what_was_said_and_unsaid_it_is_believed_no_more() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    s.model(StandIn::new(vec![("state", offer())], "ok").0);
    s.write("clara_telegram", "Tuesday at six", None, None, None);
    s.model(
        StandIn::new(
            vec![(
                "state",
                json!({"says": "viewing:flat_12 viewing:viewingAt \"2026-11-03T10:00:00+00:00\" ."}),
            )],
            "ok",
        )
        .0,
    );
    s.write("clara_telegram", "no, Wednesday at ten", None, None, None);
    assert_eq!(
        s.believed(),
        [(format!("{V}flat_12"), "2026-11-03T10:00:00Z".to_string())],
        "one statement per subject and word"
    );
    s.model(
        StandIn::new(
            vec![("state", json!({"unsays": ["viewing:flat_12 viewing:viewingAt"]}))],
            "ok",
        )
        .0,
    );
    s.write("clara_telegram", "the viewing is off", None, None, None);
    assert!(
        s.believed().is_empty() && s.statements().len() == 1,
        "unsaid: a statement of nothing"
    );
}

#[test]
fn what_a_person_states_is_held_to_the_words_the_chat_allows_and_to_their_domain_and_range() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    for (says, why) in [
        (
            "viewing:flat_12 viewing:viewingAsked \"evenings\" .",
            "viewingAsked is no word a person may state here",
        ),
        (
            "viewing:seeker viewing:viewingAt \"2026-11-02T18:00:00+00:00\" .",
            "seeker is no Listing, which viewingAt is said of",
        ),
        (
            "viewing:flat_12 viewing:viewingAt \"Tuesday\" .",
            "'Tuesday', is no dateTime",
        ),
        ("viewing:flat_12 viewing:viewingAt viewing:flat_7 .", "is no dateTime"),
        (
            "[] viewing:refused true .",
            "refused is said of no thing the world names",
        ),
        ("viewing:flat_12 viewing:refused", "not Turtle"),
    ] {
        let (model, asked) = StandIn::new(vec![("state", json!({ "says": says }))], "ok");
        s.model(model);
        s.write(
            "household_telegram",
            &format!("seeker, {says}"),
            Some("anna"),
            None,
            None,
        );
        let last = asked.lock().unwrap().last().unwrap().1.clone();
        let answers = results(&last);
        assert!(
            answers.len() == 1 && answers[0].starts_with("not kept: ") && answers[0].contains(why),
            "{says}: {answers:?}"
        );
    }
    assert!(s.statements().is_empty(), "nothing kept");
    let (model, asked) = StandIn::new(
        vec![("state", json!({"says": "viewing:flat_7 viewing:refused true ."}))],
        "ok",
    );
    s.model(model);
    s.write(
        "household_telegram",
        "seeker, the studio is gone",
        Some("anna"),
        None,
        None,
    );
    assert_eq!(
        results(&asked.lock().unwrap().last().unwrap().1),
        ["kept: the agent believes it now"]
    );
}

#[test]
fn the_model_is_briefed_with_who_the_agent_is_what_the_chat_reads_and_what_a_person_may_state() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    let (model, asked) = StandIn::new(vec![], "I am the seeker; I look for a flat.");
    s.model(model);
    s.write("clara_telegram", "who are you?", None, None, None);
    let asked = asked.lock().unwrap().clone();
    let (system, _, offered) = &asked[0];
    assert_eq!(system[0], CONVERSE_SYSTEM);
    assert!(system[1].starts_with("YOU SPEAK FOR seeker."));
    assert!(system[2].starts_with("IT IS NOW 2026-11-01T09:00"), "{}", system[2]);
    assert!(system[1].contains("WHAT THIS CHAT LETS YOU READ") && system[1].contains(" - speech ("));
    assert!(
        system[1].contains("WHAT A PERSON MAY STATE HERE")
            && system[1].contains("anything in a word a vocabulary declares")
    );
    for t in ["vocabulary", "query", "state"] {
        assert!(offered.contains(&t.to_string()));
    }
    assert_eq!(
        s.said(),
        [(
            format!("{V}clara_telegram"),
            "I am the seeker; I look for a flat.".to_string()
        )]
    );
}

#[test]
fn the_model_loads_a_vocabulary_and_queries_what_the_chat_reads() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    let (model, asked) = StandIn::new(
        vec![
            ("vocabulary", json!({"name": "speech"})),
            (
                "query",
                json!({"sparql": "SELECT ?c WHERE { ?c a speech:Chat }", "kinds": ["orexis:BeliefGraph"]}),
            ),
            (
                "query",
                json!({"sparql": "SELECT * WHERE { SERVICE <http://elsewhere.example/> { ?s ?p ?o } }", "kinds": ["orexis:BeliefGraph"]}),
            ),
        ],
        "We speak here, and in three other chats.",
    );
    s.model(model);
    s.write("clara_telegram", "in which chats are you?", None, None, None);
    let answers = results(&asked.lock().unwrap().last().unwrap().1);
    assert!(answers[0].contains("speech:Chat"));
    assert!(answers[1].contains("seeker_and_clara") && answers[1].contains("household"));
    assert!(answers[2].starts_with("refused: it holds a SERVICE clause"));
    assert_eq!(
        s.said(),
        [(
            format!("{V}clara_telegram"),
            "We speak here, and in three other chats.".to_string()
        )]
    );
}

#[test]
fn a_chat_reading_nothing_offers_no_query_and_names_the_things_a_person_may_state_something_of() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    let (model, asked) = StandIn::new(vec![], "I am looking at two flats.");
    s.model(model);
    s.write(
        "household_telegram",
        "seeker, how is the search going?",
        Some("anna"),
        None,
        None,
    );
    let (system, _, offered) = asked.lock().unwrap()[0].clone();
    assert_eq!(offered, ["state"]);
    let who = &system[1];
    assert!(who.contains("lets you read nothing of the agent's store"));
    assert!(
        who.contains("viewing:viewingAt (viewing offered at), of a viewing:Listing, a xsd:dateTime"),
        "{who}"
    );
    assert!(who.contains("viewing:flat_12 (the two-room flat on Kastanienallee)"));
    assert!(!who.contains("viewingAsked"));
    let (model, asked) = StandIn::new(vec![], "hello");
    s.model(model);
    s.write("anna_mail", "a viewing on Tuesday?", None, None, None);
    let (system, _, offered) = asked.lock().unwrap()[0].clone();
    assert!(
        offered.is_empty() && system[1].contains("A person states nothing here"),
        "a chat allowing nothing hears questions alone"
    );
}

#[test]
fn a_question_is_answered_by_as_many_queries_as_it_needs_and_writes_nothing() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    s.model(StandIn::new(vec![("state", offer())], "").0);
    s.write(
        "clara_telegram",
        "I can show you Kastanienallee on Tuesday the 2nd at 6pm.",
        None,
        None,
        None,
    );
    let before = graphs(&store);
    let (model, asked) = StandIn::new(
        vec![viewings()],
        "Kastanienallee on Tuesday at 18:00; nothing yet for the studio.",
    );
    s.model(model);
    s.write(
        "clara_telegram",
        "when can I see Kastanienallee, and the studio?",
        None,
        None,
        None,
    );
    assert_eq!(
        results(&asked.lock().unwrap().last().unwrap().1),
        ["flat: viewing:flat_12, at: 2026-11-02T18:00:00Z"]
    );
    assert_eq!(
        s.said().last().unwrap(),
        &(
            format!("{V}clara_telegram"),
            "Kastanienallee on Tuesday at 18:00; nothing yet for the studio.".to_string()
        )
    );
    let prose: std::collections::BTreeSet<String> = store
        .graphs_of(&[PROSE_GRAPH], &Within::default())
        .unwrap()
        .into_iter()
        .collect();
    let new: std::collections::BTreeSet<String> = graphs(&store).difference(&before).cloned().collect();
    assert_eq!(
        (new.len(), new.is_subset(&prose)),
        (2, true),
        "a question writes nothing but the words kept, the person's and the agent's"
    );
}

#[test]
fn a_conversation_says_what_it_spent_and_what_was_written_called_and_answered_where_it_is_heard() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    let spent: Arc<Mutex<Vec<Translated>>> = Arc::default();
    let conversed: Arc<Mutex<Vec<Conversed>>> = Arc::default();
    let (a, b) = (spent.clone(), conversed.clone());
    s.hearer = Some(Arc::new(move |e, _| {
        if let Some(t) = as_of::<Translated>(e) {
            a.lock().unwrap().push(t.clone());
        }
        if let Some(c) = as_of::<Conversed>(e) {
            b.lock().unwrap().push(c.clone());
        }
    }));
    s.model(StandIn::new(vec![viewings()], "Nothing yet.").0);
    s.write("clara_telegram", "anything for the studio?", None, None, None);
    let spent = spent.lock().unwrap();
    assert_eq!(spent.len(), 1);
    assert_eq!(
        (spent[0].act.as_deref(), spent[0].outcome.as_deref(), spent[0].requests),
        (Some("answer"), Some("said"), Some(2.0))
    );
    assert_eq!(
        spent[0].input_tokens,
        Some(0.0),
        "a stand-in spends nothing, and says so"
    );
    let conversed = conversed.lock().unwrap();
    assert_eq!(conversed.len(), 1);
    assert_eq!(
        (
            conversed[0].wrote.as_str(),
            conversed[0].answer.as_deref(),
            conversed[0].outcome.as_deref()
        ),
        ("anything for the studio?", Some("Nothing yet."), Some("said"))
    );
    assert_eq!(conversed[0].calls.len(), 1);
    assert_eq!(
        (conversed[0].calls[0].0.as_str(), &conversed[0].calls[0].1),
        ("query", &viewings().1)
    );
}

#[test]
fn a_conversation_ends_in_words_by_its_last_turn_and_a_model_writing_none_has_failed() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    let (model, asked) = StandIn::new(vec![viewings(); 10], "I could not find out.");
    s.model(model);
    s.write("clara_telegram", "ask until you know", None, None, None);
    assert_eq!(asked.lock().unwrap().len(), TURNS);
    assert_eq!(
        s.said(),
        [(format!("{V}clara_telegram"), "I could not find out.".to_string())]
    );
    s.bot.lock().unwrap().said.clear();
    s.model(StandIn::new(vec![], "").0);
    s.write("clara_telegram", "what is the forecast?", None, None, None);
    assert_eq!(
        s.said(),
        [(
            format!("{V}clara_telegram"),
            "seeker could not answer: its model wrote no words (no reason given).".to_string()
        )]
    );
}

#[test]
fn in_a_group_an_agent_answers_when_named_keeps_silent_when_another_is_and_says_nothing_it_does_not_know() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    let (model, asked) = StandIn::new(vec![], "I am looking at two flats.");
    s.model(model);
    s.write(
        "household_telegram",
        "keeper, is the door locked?",
        Some("anna"),
        None,
        None,
    );
    assert!(
        asked.lock().unwrap().is_empty() && s.said().is_empty(),
        "words to another agent of the chat"
    );
    s.write(
        "household_telegram",
        "seeker, how is the search going?",
        Some("anna"),
        None,
        None,
    );
    let (system, _, offered) = asked.lock().unwrap()[0].clone();
    assert!(system[0] == CONVERSE_SYSTEM && offered == ["state"]);
    assert_eq!(
        s.said(),
        [(
            format!("{V}household_telegram"),
            "I am looking at two flats.".to_string()
        )]
    );
    s.bot.lock().unwrap().said.clear();
    let (model, asked) = StandIn::new(vec![], SILENT);
    s.model(model);
    s.write(
        "household_telegram",
        "is anyone watching the plants?",
        Some("clara"),
        None,
        None,
    );
    let (system, _, offered) = asked.lock().unwrap()[0].clone();
    assert!(
        system[0] == format!("{CONVERSE_SYSTEM}{UNADDRESSED}") && offered.is_empty(),
        "unnamed in a group: nothing stated"
    );
    assert!(
        s.said().is_empty(),
        "what it holds does not answer it, so it keeps silent"
    );
    s.write("household_telegram", "hello?", Some("nobody"), None, None);
    assert_eq!(
        asked.lock().unwrap().len(),
        1,
        "someone the chat names not is not heard"
    );
}

#[test]
fn in_a_group_words_that_tag_or_reply_to_the_agent_are_its_own_and_its_answer_replies_to_them() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    let (model, asked) = StandIn::new(vec![], "I am looking at two flats.");
    s.model(model);
    s.write(
        "household_telegram",
        "how is the search going?",
        Some("anna"),
        Some(false),
        Some("41"),
    );
    assert!(asked.lock().unwrap().is_empty() && s.said().is_empty());
    s.write(
        "household_telegram",
        "how is the search going?",
        Some("anna"),
        Some(true),
        Some("42"),
    );
    let (system, _, offered) = asked.lock().unwrap()[0].clone();
    assert!(system[0] == CONVERSE_SYSTEM && offered == ["state"]);
    assert_eq!(s.bot.lock().unwrap().replies, [Some("42".to_string())]);
    s.write(
        "household_telegram",
        "seeker, and you?",
        Some("anna"),
        Some(false),
        Some("43"),
    );
    assert_eq!(asked.lock().unwrap().len(), 2);
    assert_eq!(
        s.bot.lock().unwrap().replies,
        [Some("42".to_string()), Some("43".to_string())]
    );
}

#[test]
fn what_the_agent_says_to_a_person_is_rendered_and_sent_through_their_chat() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    let words = "Dear Clara, could I view the studio on Rigaer Straße? Weekday evenings suit me. — seeker";
    let (model, asked) = StandIn::new(vec![], words);
    s.model(model);
    let statement = b"@prefix : <http://example.org/orexis/world/viewing#> .\n\
<urn:x:asked> { :flat_7 :viewingAsked \"weekday evenings\" . }\n\
<urn:x:asked> a <http://example.org/orexis/speech#StatementGraph> .\n";
    s.say(statement, "clara");
    let (system, text, _) = asked.lock().unwrap()[0].clone();
    let text = text[0].as_str().unwrap().to_string();
    assert_eq!(system, [SAY_SYSTEM]);
    assert!(
        text.contains("To: Clara") && text.contains("\"weekday evenings\""),
        "{text}"
    );
    assert!(
        text.contains("viewingAsked: viewing asked for — The hours the seeker can come to view the listing"),
        "{text}"
    );
    assert_eq!(
        s.said(),
        [(format!("{V}clara_telegram"), words.to_string())],
        "her own chat, not the household's group"
    );
    s.say(statement, "keeper");
    assert_eq!(
        asked.lock().unwrap().len(),
        1,
        "a document to an agent is the bus's, not translation's"
    );
}

#[test]
fn the_person_sees_the_agent_writing_from_the_words_heard_to_the_answer_said() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    s.model(StandIn::new(vec![viewings()], "The seeker has nothing to say yet.").0);
    s.write("clara_telegram", "what are you doing?", None, None, None);
    assert_eq!(
        s.bot.lock().unwrap().writing,
        [format!("{V}clara_telegram")],
        "shown before the model is asked"
    );
    s.later(3.0 * orexis_translation::create::WRITING_S);
    assert_eq!(
        s.bot.lock().unwrap().writing.len(),
        1,
        "and shown no more once the answer is said"
    );
    s.model(StandIn::new(vec![], SILENT).0);
    s.write(
        "household_telegram",
        "is anyone watching the plants?",
        Some("clara"),
        None,
        None,
    );
    assert_eq!(
        s.bot.lock().unwrap().writing,
        [format!("{V}clara_telegram")],
        "unaddressed in a group it shows nothing"
    );
}

#[test]
fn a_model_that_fails_says_so_in_the_chat_where_the_agent_was_addressed() {
    let store = seeker();
    let mut s = Seeker::new(&store);
    let (mut model, _) = StandIn::new(vec![], "");
    model.fails = Some(Failure::Other("HTTP Error 401: Unauthorized".into()));
    s.model(model);
    s.write("clara_telegram", "what are you doing?", None, None, None);
    assert_eq!(
        s.said(),
        [(
            format!("{V}clara_telegram"),
            "seeker could not answer: its model would not answer (HTTP Error 401: Unauthorized).".to_string()
        )]
    );
    let shown = s.bot.lock().unwrap().writing.len();
    s.later(3.0 * orexis_translation::create::WRITING_S);
    assert_eq!(
        s.bot.lock().unwrap().writing.len(),
        shown,
        "shown no more once it has answered"
    );
    s.bot.lock().unwrap().said.clear();
    let (mut model, _) = StandIn::new(vec![], "");
    model.fails = Some(Failure::Refused("401".into()));
    s.model(model);
    s.write(
        "household_telegram",
        "is anyone watching the plants?",
        Some("clara"),
        None,
        None,
    );
    assert!(
        s.said().is_empty(),
        "unaddressed in a group, a failure is the log's alone"
    );
}
