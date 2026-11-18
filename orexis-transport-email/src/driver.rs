//! THE EMAIL DRIVER, as `agent/transport/email/driver.py` keeps it: an agent's own mailbox over IMAP and SMTP.
//!
//! **THE MAILBOX IS THE AGENT'S**, named by `MAIL_ADDRESS`, `MAIL_PASSWORD`, `MAIL_IMAP_HOST` and `MAIL_SMTP_HOST`,
//! with `MAIL_IMAP_PORT` and `MAIL_SMTP_PORT` where not 993 and 465, all environment. **IT POLLS** as often as a role says (`email:polledEveryS`), every thirty
//! real seconds by default, awaited as a Tokio task and one poll at a time, every unseen message with a plain text waiting in the inbox, its channel the
//! sender's address; `handle` finds the contact point the world names by that address, whatever case it is written in,
//! and says the prose; an address the world names in no chat is dropped and said once. **IT SENDS** to a contact
//! point's address by `say`, a Tokio task sending each letter in the order it was said, and shows no writing, mail
//! having no way to.

use std::collections::{BTreeSet, VecDeque};
use std::future::Future;
use std::pin::Pin;
use std::sync::{Arc, Mutex};

use futures_util::TryStreamExt;

use oxigraph::model::Literal;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{BELIEF, local_of};
use orexis::store::{Store, Within, iri, value};
use orexis_transport::Inbox;
use orexis_transport::chat::Words;

/// WHAT HOLDS WHERE NO ROLE SAYS HOW OFTEN: the defaults this transport's ontology states (`sh:defaultValue`).
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("the email transport", include_str!("../ontology.ttl")));

/// HOW OFTEN THE MAILBOX IS POLLED, in real seconds: what a role the self plays says in the agent's self graph
/// (`email:polledEveryS`), and the default the transport's ontology states where none says.
pub fn polled_every_s(beliefs: &Store) -> Result<f64, Error> {
    let mut known = beliefs.graphs_of(&[orexis::ontology::SELF_GRAPH], &orexis::store::Within::default())?;
    known.extend(beliefs.graphs_of(&[orexis::ontology::ONTOLOGY], &orexis::store::Within::default())?);
    let known: Vec<&str> = known.iter().map(String::as_str).collect();
    //  ONE QUERY: what a role the self plays says or, where none says, the default the transport's ontology states.
    beliefs
        .rows(
            "PREFIX email: <http://example.org/orexis/email#>
             PREFIX orexis: <http://example.org/orexis#>
             PREFIX sh: <http://www.w3.org/ns/shacl#>
             SELECT (COALESCE(?said, ?own) AS ?every) WHERE { \
             OPTIONAL { ?me a orexis:Self ; orexis:plays ?role . \
                        ?role email:polledEveryS ?said FILTER(?said > 0) } \
             OPTIONAL { ?shape sh:property [ sh:path email:polledEveryS ; \
                        sh:defaultValue ?own ] } } ORDER BY ?every",
            &known,
        )?
        .iter()
        .find_map(|row| orexis::store::value(row, "every")?.parse::<f64>().ok())
        .ok_or_else(|| Error::Document("the email transport's ontology states no default for polledEveryS".into()))
}

/// What a mailbox answers, awaited: the call goes over the wire and holds no thread while it waits.
pub type Pending<'a, T> = Pin<Box<dyn Future<Output = Result<T, String>> + Send + 'a>>;

/// A mailbox: every unseen message as its sender's address and its plain text, each then seen; and one sent.
pub trait Mailbox: Send + Sync {
    fn fetch(&self) -> Pending<'_, Vec<(String, String)>>;
    fn send<'a>(&'a self, to: &'a str, text: &'a str) -> Pending<'a, ()>;
}

/// The mailbox of an agent that is not deployed and was handed none: it reaches nothing.
pub struct Unreachable;

impl Mailbox for Unreachable {
    fn fetch(&self) -> Pending<'_, Vec<(String, String)>> {
        Box::pin(std::future::ready(Err(
            "an agent that is not deployed reaches no mailbox".into(),
        )))
    }
    fn send<'a>(&'a self, _: &'a str, _: &'a str) -> Pending<'a, ()> {
        Box::pin(std::future::ready(Err(
            "an agent that is not deployed reaches no mailbox".into(),
        )))
    }
}

/// The plain text of a message, or none where it carries none: its first plain part that is no attachment, and never
/// a page of HTML.
pub fn text_of(raw: &[u8]) -> Option<(String, String)> {
    let message = mail_parser::MessageParser::default().parse(raw)?;
    let sender = message.from()?.first()?.address()?.to_string();
    let text = message.text_body.iter().find_map(|id| match &message.part(*id)?.body {
        mail_parser::PartType::Text(text) => Some(text.trim().to_string()),
        _ => None,
    })?;
    Some((sender, text))
}

/// The mailbox the environment names, over IMAP and SMTP on TLS.
pub struct Remote {
    pub address: String,
    password: String,
    pub imap: (String, u16),
    pub smtp: (String, u16),
}

impl Mailbox for Remote {
    fn fetch(&self) -> Pending<'_, Vec<(String, String)>> {
        Box::pin(async move {
            let e = |e: &dyn std::fmt::Display| e.to_string();
            let _ = rustls::crypto::ring::default_provider().install_default();
            let roots = rustls::RootCertStore {
                roots: webpki_roots::TLS_SERVER_ROOTS.to_vec(),
            };
            let tls = rustls::ClientConfig::builder()
                .with_root_certificates(roots)
                .with_no_client_auth();
            let name = rustls::pki_types::ServerName::try_from(self.imap.0.clone()).map_err(|x| e(&x))?;
            let tcp = tokio::net::TcpStream::connect((self.imap.0.as_str(), self.imap.1))
                .await
                .map_err(|x| e(&x))?;
            let stream = tokio_rustls::TlsConnector::from(Arc::new(tls))
                .connect(name, tcp)
                .await
                .map_err(|x| e(&x))?;
            //  THE SERVER GREETS FIRST, and a client made over a stream of one's own reads it before it speaks.
            let mut client = async_imap::Client::new(stream);
            client.read_response().await.map_err(|x| e(&x))?;
            let mut session = client
                .login(&self.address, &self.password)
                .await
                .map_err(|(x, _)| e(&x))?;
            session.select("INBOX").await.map_err(|x| e(&x))?;
            let mut unseen: Vec<u32> = session.search("UNSEEN").await.map_err(|x| e(&x))?.into_iter().collect();
            unseen.sort_unstable();
            let mut out = Vec::new();
            for number in unseen {
                let fetched: Vec<_> = session
                    .fetch(number.to_string(), "RFC822")
                    .await
                    .map_err(|x| e(&x))?
                    .try_collect()
                    .await
                    .map_err(|x| e(&x))?;
                out.extend(fetched.iter().filter_map(|m| m.body()).filter_map(text_of));
                let _: Vec<_> = session
                    .store(number.to_string(), "+FLAGS (\\Seen)")
                    .await
                    .map_err(|x| e(&x))?
                    .try_collect()
                    .await
                    .map_err(|x| e(&x))?;
            }
            let _ = session.logout().await;
            Ok(out)
        })
    }

    fn send<'a>(&'a self, to: &'a str, text: &'a str) -> Pending<'a, ()> {
        Box::pin(async move {
            use lettre::AsyncTransport as _;
            let _ = rustls::crypto::ring::default_provider().install_default();
            let message = lettre::Message::builder()
                .from(self.address.parse().map_err(|e| format!("{e}"))?)
                .to(to.parse().map_err(|e| format!("{e}"))?)
                .subject("From your agent")
                .body(text.to_string())
                .map_err(|e| e.to_string())?;
            let mail = lettre::AsyncSmtpTransport::<lettre::Tokio1Executor>::relay(&self.smtp.0)
                .map_err(|e| e.to_string())?
                .port(self.smtp.1)
                .credentials(lettre::transport::smtp::authentication::Credentials::new(
                    self.address.clone(),
                    self.password.clone(),
                ))
                .build();
            mail.send(message).await.map(|_| ()).map_err(|e| e.to_string())
        })
    }
}

/// One agent's mailbox: polled for what is written to it, told what the agent says.
pub struct Email {
    beliefs: Store,
    pub me: String,
    pub box_: Arc<dyn Mailbox>,
    pub polled_every_s: f64,
    pub inbox: Inbox,
    polling: Arc<tokio::sync::Mutex<()>>,
    /// What the agent said and the mailbox has yet to send, each an address and its text, oldest first.
    outbox: Arc<Mutex<VecDeque<(String, String)>>>,
    unknown: BTreeSet<String>,
}

impl Email {
    /// The store the member keeps what it carries in.
    pub fn beliefs(&self) -> &Store {
        &self.beliefs
    }

    pub fn new(beliefs: &Store, me: &str, box_: Arc<dyn Mailbox>) -> Self {
        Email {
            beliefs: beliefs.clone(),
            me: me.to_string(),
            box_,
            //  UNTIL IT CONNECTS and reads what a role says, as often as the transport's ontology states.
            polled_every_s: DEFAULTS
                .figure("http://example.org/orexis/email#polledEveryS")
                .expect("the transport's ontology states how often it polls"),
            inbox: Inbox::default(),
            polling: Arc::default(),
            outbox: Arc::default(),
            unknown: BTreeSet::new(),
        }
    }

    /// The mailbox brought up from the environment: refused where it names none.
    pub fn connect(beliefs: &Store, me: &str, env: &dyn Fn(&str) -> Option<String>) -> Result<Self, Error> {
        let needed = ["MAIL_ADDRESS", "MAIL_PASSWORD", "MAIL_IMAP_HOST", "MAIL_SMTP_HOST"];
        let found: Vec<String> = needed.iter().filter_map(|k| env(k).filter(|v| !v.is_empty())).collect();
        let [address, password, imap, smtp] = found.as_slice() else {
            return Err(Error::Evaluation(format!(
                "no mailbox in the environment: {} — write secrets/<agent>/mail.env and regenerate the compose file",
                needed.join(", ")
            )));
        };
        let port = |name: &str, default: u16| env(name).and_then(|p| p.parse().ok()).unwrap_or(default);
        let remote = Remote {
            address: address.clone(),
            password: password.clone(),
            imap: (imap.clone(), port("MAIL_IMAP_PORT", 993)),
            smtp: (smtp.clone(), port("MAIL_SMTP_PORT", 465)),
        };
        let mut email = Email::new(beliefs, me, Arc::new(remote));
        email.polled_every_s = polled_every_s(beliefs)?;
        Ok(email)
    }

    /// Ask for every unseen message, awaited as a Tokio task, one poll at a time.
    pub fn poll(&self) {
        let Ok(one) = self.polling.clone().try_lock_owned() else {
            return;
        };
        let (box_, inbox, me) = (self.box_.clone(), self.inbox.clone(), self.me.clone());
        tokio::spawn(async move {
            let _one = one;
            match box_.fetch().await {
                Ok(found) => {
                    for (sender, text) in found {
                        inbox.deliver(&sender, text.as_bytes(), None);
                    }
                }
                Err(e) => log::warn!("{}: the mailbox would not answer: {e}", local_of(&me)),
            }
        });
    }

    /// `text` sent to `address`, after whatever the agent said before and the mailbox has yet to send: the first left
    /// starts the one task that sends them, oldest first, until none is left, what the mailbox would not send said in
    /// the log.
    fn tell(&self, address: &str, text: &str) {
        let mut outbox = self.outbox.lock().unwrap();
        outbox.push_back((address.to_string(), text.to_string()));
        if outbox.len() > 1 {
            return;
        }
        let (box_, outbox, me) = (self.box_.clone(), self.outbox.clone(), self.me.clone());
        tokio::spawn(async move {
            let mut next = outbox.lock().unwrap().front().cloned();
            while let Some((address, text)) = next {
                if let Err(e) = box_.send(&address, &text).await {
                    log::warn!("{}: the mailbox would not send to {address}: {e}", local_of(&me));
                }
                next = {
                    let mut outbox = outbox.lock().unwrap();
                    outbox.pop_front();
                    outbox.front().cloned()
                };
            }
        });
    }

    fn common(&self) -> Result<Vec<String>, Error> {
        self.beliefs.graphs_of(&[BELIEF], &Within::common())
    }

    /// Whether `channel` is a mailbox this member writes to: a contact point with an address.
    pub fn carries(&self, channel: &str) -> Result<bool, Error> {
        const CARRIES_Q: &str = "PREFIX schema: <https://schema.org/> ASK { $contact schema:email ?address }";
        let common = self.common()?;
        let common: Vec<&str> = common.iter().map(String::as_str).collect();
        self.beliefs
            .ask(&bind(CARRIES_Q, &[("contact", Value::iri(channel))])?, &common)
    }

    /// A message from an address: the chat whose contact point has that address, and its words — its one person being
    /// who wrote, the channel names no sender; none where the world names the address in no chat.
    pub fn handle(&mut self, channel: &str, payload: &[u8], _at: DateTime) -> Result<Option<(String, Words)>, Error> {
        const CONTACT_Q: &str = "PREFIX schema: <https://schema.org/>
            SELECT ?contact WHERE { ?contact schema:email ?address FILTER (LCASE(STR(?address)) = LCASE($address)) }";
        let common = self.common()?;
        let common: Vec<&str> = common.iter().map(String::as_str).collect();
        let address = Value::Term(Literal::new_simple_literal(channel).into());
        let found = self.beliefs.rows(&bind(CONTACT_Q, &[("address", address)])?, &common)?;
        let Some(contact) = found.first().and_then(|r| iri(r, "contact")) else {
            if self.unknown.insert(channel.to_string()) {
                log::warn!(
                    "{}: mail from {channel}, whom the world names in no chat: dropped",
                    local_of(&self.me)
                );
            }
            return Ok(None);
        };
        Ok(Some((contact, Words::said(&String::from_utf8_lossy(payload)))))
    }
}

impl Email {
    /// `words` sent to the address of the contact point `channel`; a mailbox shows no writing, so words saying only
    /// that send nothing. Whether the channel is a contact point with an address, the letter then on its way.
    pub fn say(&mut self, channel: &str, words: &Words) -> bool {
        if words.writing {
            return false;
        }
        let text = words.text.as_str();
        const ADDRESS_Q: &str =
            "PREFIX schema: <https://schema.org/> SELECT ?address WHERE { $contact schema:email ?address }";
        let Ok(common) = self.common() else { return false };
        let common: Vec<&str> = common.iter().map(String::as_str).collect();
        let Ok(query) = bind(ADDRESS_Q, &[("contact", Value::iri(channel))]) else {
            return false;
        };
        let Some(address) = self
            .beliefs
            .rows(&query, &common)
            .ok()
            .and_then(|r| r.first().and_then(|r| value(r, "address")))
        else {
            return false;
        };
        self.tell(&address, text);
        true
    }
}

#[cfg(test)]
mod tests {
    //! The driver over a stand-in mailbox, held to `agent/transport/email/tests/test_driver.py`.

    use std::path::Path;

    use super::*;
    use orexis::snapshots::{now, stand_in};

    const TEST: &str = "http://example.org/test#";

    #[derive(Default)]
    struct Box_ {
        unseen: Mutex<Vec<(String, String)>>,
        sent: Mutex<Vec<(String, String)>>,
    }

    impl Mailbox for Box_ {
        fn fetch(&self) -> Pending<'_, Vec<(String, String)>> {
            Box::pin(std::future::ready(Ok(std::mem::take(
                &mut *self.unseen.lock().unwrap(),
            ))))
        }
        fn send<'a>(&'a self, to: &'a str, text: &'a str) -> Pending<'a, ()> {
            self.sent.lock().unwrap().push((to.into(), text.into()));
            Box::pin(std::future::ready(Ok(())))
        }
    }

    /// Every task spawned so far run as far as it goes.
    async fn settled() {
        for _ in 0..8 {
            tokio::task::yield_now().await;
        }
    }

    fn world() -> Store {
        stand_in(&Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/worlds/a_chat_by_email.trig"))
    }

    fn mail(store: &Store) -> (Email, Arc<Box_>) {
        let box_ = Arc::new(Box_::default());
        let mail = Email::new(store, &format!("{TEST}keeper"), box_.clone());
        (mail, box_)
    }

    #[tokio::test]
    async fn a_poll_delivers_every_unseen_message_by_its_senders_address() {
        let store = world();
        let (mail, box_) = mail(&store);
        *box_.unseen.lock().unwrap() = vec![
            ("anna@example.org".into(), "hello".into()),
            ("bob@example.org".into(), "hi".into()),
        ];
        mail.poll();
        settled().await;
        mail.poll();
        settled().await;
        let delivered: Vec<(String, Vec<u8>)> = mail.inbox.take().into_iter().map(|m| (m.topic, m.payload)).collect();
        assert_eq!(
            delivered,
            [
                ("anna@example.org".to_string(), b"hello".to_vec()),
                ("bob@example.org".to_string(), b"hi".to_vec())
            ]
        );
    }

    #[test]
    fn a_message_is_words_on_the_chat_whose_contact_point_has_the_address() {
        let store = world();
        let (mut mail, _) = mail(&store);
        let (channel, words) = mail
            .handle("Anna@Example.org", "is the fern dry?".as_bytes(), now())
            .unwrap()
            .unwrap();
        assert!(mail.carries(&channel).unwrap());
        assert_eq!(
            (channel.as_str(), words.from, words.text.as_str()),
            (format!("{TEST}anna_mail").as_str(), None, "is the fern dry?"),
            "the chat's one person is who wrote, so the channel names no sender"
        );
        for _ in 0..2 {
            assert!(
                mail.handle("bob@example.org", b"hi", now()).unwrap().is_none(),
                "dropped"
            );
        }
    }

    #[tokio::test]
    async fn what_the_agent_says_is_sent_to_the_contact_points_address_in_the_order_said() {
        let store = world();
        let (mut mail, box_) = mail(&store);
        assert!(mail.say(&format!("{TEST}anna_mail"), &Words::said("the fern is dry")));
        assert!(mail.say(&format!("{TEST}anna_mail"), &Words::said("and now watered")));
        settled().await;
        assert_eq!(
            *box_.sent.lock().unwrap(),
            [
                ("anna@example.org".to_string(), "the fern is dry".to_string()),
                ("anna@example.org".to_string(), "and now watered".to_string())
            ]
        );
        assert!(mail.outbox.lock().unwrap().is_empty(), "and none left to send");
        assert!(
            !mail.say(&format!("{TEST}keeper_and_anna"), &Words::said("x")),
            "a node with no address is not this member's"
        );
        let writing = Words {
            writing: true,
            ..Words::default()
        };
        assert!(
            !mail.say(&format!("{TEST}anna_mail"), &writing),
            "a mailbox shows no writing"
        );
    }

    #[test]
    fn a_messages_text_is_its_plain_part() {
        let both = "From: Anna <anna@example.org>\r\nTo: keeper@example.org\r\nMIME-Version: 1.0\r\n\
                    Content-Type: multipart/alternative; boundary=\"b\"\r\n\r\n--b\r\n\
                    Content-Type: text/plain; charset=utf-8\r\n\r\n plain words \r\n--b\r\n\
                    Content-Type: text/html; charset=utf-8\r\n\r\n<p>html</p>\r\n--b--\r\n";
        assert_eq!(
            text_of(both.as_bytes()),
            Some(("anna@example.org".to_string(), "plain words".to_string()))
        );
        let html = "From: anna@example.org\r\nContent-Type: text/html\r\n\r\n<p>html</p>\r\n";
        assert_eq!(text_of(html.as_bytes()), None);
    }

    #[test]
    fn connect_refuses_an_agent_with_no_mailbox() {
        let store = world();
        //  THE TRANSPORT'S ONTOLOGY STATES HOW OFTEN WHERE NO ROLE DOES, as the package brings it.
        store
            .update(
                "PREFIX : <http://example.org/test#>
                 PREFIX email: <http://example.org/orexis/email#>
                 PREFIX sh: <http://www.w3.org/ns/shacl#>
                 INSERT DATA { GRAPH :ontology { [] sh:property \
                 [ sh:path email:polledEveryS ; sh:defaultValue 30 ] } }",
            )
            .unwrap();
        let me = format!("{TEST}keeper");
        let partial = |k: &str| (k == "MAIL_ADDRESS").then(|| "keeper@example.org".to_string());
        assert!(Email::connect(&store, &me, &partial).is_err());
        let env = |k: &str| {
            match k {
                "MAIL_ADDRESS" => Some("k@example.org"),
                "MAIL_PASSWORD" => Some("p"),
                "MAIL_IMAP_HOST" => Some("imap"),
                "MAIL_SMTP_HOST" => Some("smtp"),
                _ => None,
            }
            .map(str::to_string)
        };
        let mail = Email::connect(&store, &me, &env).unwrap();
        assert_eq!(
            mail.polled_every_s, 30.0,
            "no role of this world says how often, so the default the transport's ontology states"
        );
    }
}
