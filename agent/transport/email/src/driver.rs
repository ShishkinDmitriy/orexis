//! THE EMAIL DRIVER, as `agent/transport/email/driver.py` keeps it: an agent's own mailbox over IMAP and SMTP.
//!
//! **THE MAILBOX IS THE AGENT'S**, named by `MAIL_ADDRESS`, `MAIL_PASSWORD`, `MAIL_IMAP_HOST` and `MAIL_SMTP_HOST`,
//! with `MAIL_IMAP_PORT` and `MAIL_SMTP_PORT` where not 993 and 465, all environment. **IT POLLS** every `MAIL_POLL_S`
//! real seconds on a thread of its own, every unseen message with a plain text waiting in the inbox, its channel the
//! sender's address; `handle` finds the contact point the world names by that address, whatever case it is written in,
//! and says the prose; an address the world names in no chat is dropped and said once. **IT SENDS** to a contact
//! point's address by `say_to`, and shows no writing, mail having no way to.

use std::collections::BTreeSet;
use std::sync::{Arc, Mutex};

use oxigraph::model::Literal;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{BELIEF, local_of};
use orexis::store::{Store, Within, iri, value};
use orexis::transport::Inbox;
use orexis_speech::prose::{Carrier, Prose};

pub const POLL_S: f64 = 30.0;

const CONTACT_Q: &str =
    "SELECT ?contact WHERE { ?contact schema:email ?address FILTER (LCASE(STR(?address)) = LCASE($address)) }";
const ADDRESS_Q: &str = "SELECT ?address WHERE { $contact schema:email ?address }";

/// A mailbox: every unseen message as its sender's address and its plain text, each then seen; and one sent.
pub trait Mailbox: Send + Sync {
    fn fetch(&self) -> Result<Vec<(String, String)>, String>;
    fn send(&self, to: &str, text: &str) -> Result<(), String>;
}

/// What runs a poll: on a thread of its own, or at once in a test.
pub type Spawn = Box<dyn Fn(Box<dyn FnOnce() + Send>) + Send + Sync>;

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
    fn fetch(&self) -> Result<Vec<(String, String)>, String> {
        let _ = rustls::crypto::ring::default_provider().install_default();
        let client = imap::ClientBuilder::new(self.imap.0.as_str(), self.imap.1)
            .mode(imap::ConnectionMode::Tls)
            .tls_kind(imap::TlsKind::Rust)
            .connect()
            .map_err(|e| e.to_string())?;
        let mut session = client
            .login(&self.address, &self.password)
            .map_err(|(e, _)| e.to_string())?;
        session.select("INBOX").map_err(|e| e.to_string())?;
        let mut unseen: Vec<u32> = session
            .search("UNSEEN")
            .map_err(|e| e.to_string())?
            .into_iter()
            .collect();
        unseen.sort_unstable();
        let mut out = Vec::new();
        for number in unseen {
            let fetched = session.fetch(number.to_string(), "RFC822").map_err(|e| e.to_string())?;
            out.extend(fetched.iter().filter_map(|m| m.body()).filter_map(text_of));
            session
                .store(number.to_string(), "+FLAGS (\\Seen)")
                .map_err(|e| e.to_string())?;
        }
        let _ = session.logout();
        Ok(out)
    }

    fn send(&self, to: &str, text: &str) -> Result<(), String> {
        use lettre::Transport as _;
        let message = lettre::Message::builder()
            .from(self.address.parse().map_err(|e| format!("{e}"))?)
            .to(to.parse().map_err(|e| format!("{e}"))?)
            .subject("From your agent")
            .body(text.to_string())
            .map_err(|e| e.to_string())?;
        let mail = lettre::SmtpTransport::relay(&self.smtp.0)
            .map_err(|e| e.to_string())?
            .port(self.smtp.1)
            .credentials(lettre::transport::smtp::authentication::Credentials::new(
                self.address.clone(),
                self.password.clone(),
            ))
            .build();
        mail.send(&message).map(|_| ()).map_err(|e| e.to_string())
    }
}

/// One agent's mailbox: polled for what is written to it, told what the agent says.
pub struct Email {
    beliefs: Store,
    pub me: String,
    pub box_: Arc<dyn Mailbox>,
    pub every: f64,
    pub spawn: Spawn,
    pub inbox: Inbox,
    polling: Arc<Mutex<()>>,
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
            every: POLL_S,
            spawn: Box::new(|work| {
                std::thread::spawn(work);
            }),
            inbox: Inbox::default(),
            polling: Arc::default(),
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
        if let Some(every) = env("MAIL_POLL_S").and_then(|s| s.parse().ok()) {
            email.every = every;
        }
        Ok(email)
    }

    /// Ask for every unseen message, on a thread of its own, one poll at a time.
    pub fn poll(&self) {
        let (box_, inbox, me, polling) = (
            self.box_.clone(),
            self.inbox.clone(),
            self.me.clone(),
            self.polling.clone(),
        );
        (self.spawn)(Box::new(move || {
            let Ok(_one) = polling.try_lock() else { return };
            match box_.fetch() {
                Ok(found) => {
                    for (sender, text) in found {
                        inbox.deliver(&sender, text.as_bytes(), None);
                    }
                }
                Err(e) => log::warn!("{}: the mailbox would not answer: {e}", local_of(&me)),
            }
        }));
    }

    fn common(&self) -> Result<Vec<String>, Error> {
        self.beliefs.graphs_of(&[BELIEF], &Within::common())
    }

    /// A message from an address: the prose it is, in the chat whose contact point has that address — its one person
    /// being who wrote, the channel names no sender; none where the world names the address in no chat.
    pub fn handle(&mut self, channel: &str, payload: &[u8], at: DateTime) -> Result<Option<Prose>, Error> {
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
        Ok(Some(Prose {
            channel: contact,
            sender: None,
            text: String::from_utf8_lossy(payload).into_owned(),
            at: Some(at),
            addressed: None,
            message: None,
            reply: None,
        }))
    }
}

impl Carrier for Email {
    fn say_to(&mut self, channel: &str, text: &str, _reply: Option<&str>) -> bool {
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
        match self.box_.send(&address, text) {
            Ok(()) => true,
            Err(e) => {
                log::warn!("{}: the mailbox would not send to {address}: {e}", local_of(&self.me));
                false
            }
        }
    }

    fn writing_in(&mut self, _channel: &str) -> bool {
        false
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
        fn fetch(&self) -> Result<Vec<(String, String)>, String> {
            Ok(std::mem::take(&mut *self.unseen.lock().unwrap()))
        }
        fn send(&self, to: &str, text: &str) -> Result<(), String> {
            self.sent.lock().unwrap().push((to.into(), text.into()));
            Ok(())
        }
    }

    fn world() -> Store {
        stand_in(&Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/worlds/a_chat_by_email.trig"))
    }

    fn mail(store: &Store) -> (Email, Arc<Box_>) {
        let box_ = Arc::new(Box_::default());
        let mut mail = Email::new(store, &format!("{TEST}keeper"), box_.clone());
        mail.spawn = Box::new(|work| work());
        (mail, box_)
    }

    #[test]
    fn a_poll_delivers_every_unseen_message_by_its_senders_address() {
        let store = world();
        let (mail, box_) = mail(&store);
        *box_.unseen.lock().unwrap() = vec![
            ("anna@example.org".into(), "hello".into()),
            ("bob@example.org".into(), "hi".into()),
        ];
        mail.poll();
        mail.poll();
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
    fn a_message_is_prose_in_the_chat_whose_contact_point_has_the_address() {
        let store = world();
        let (mut mail, _) = mail(&store);
        let prose = mail
            .handle("Anna@Example.org", "is the fern dry?".as_bytes(), now())
            .unwrap()
            .unwrap();
        assert_eq!(
            (prose.channel.as_str(), prose.sender, prose.text.as_str()),
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

    #[test]
    fn what_the_agent_says_is_sent_to_the_contact_points_address() {
        let store = world();
        let (mut mail, box_) = mail(&store);
        assert!(mail.say_to(&format!("{TEST}anna_mail"), "the fern is dry", None));
        assert_eq!(
            *box_.sent.lock().unwrap(),
            [("anna@example.org".to_string(), "the fern is dry".to_string())]
        );
        assert!(
            !mail.say_to(&format!("{TEST}keeper_and_anna"), "x", None),
            "a node with no address is not this member's"
        );
        assert!(!mail.writing_in(&format!("{TEST}anna_mail")));
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
        let me = format!("{TEST}keeper");
        let partial = |k: &str| (k == "MAIL_ADDRESS").then(|| "keeper@example.org".to_string());
        assert!(Email::connect(&store, &me, &partial).is_err());
        let env = |k: &str| {
            match k {
                "MAIL_ADDRESS" => Some("k@example.org"),
                "MAIL_PASSWORD" => Some("p"),
                "MAIL_IMAP_HOST" => Some("imap"),
                "MAIL_SMTP_HOST" => Some("smtp"),
                "MAIL_POLL_S" => Some("60"),
                _ => None,
            }
            .map(str::to_string)
        };
        let mail = Email::connect(&store, &me, &env).unwrap();
        assert_eq!(mail.every, 60.0);
    }
}
