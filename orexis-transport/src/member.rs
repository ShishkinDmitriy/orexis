//! WHAT A MEMBER OFFERS THE ROWS ABOVE IT: a channel it reaches, and the two acts on one
//! (the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop). TO LISTEN is to be handed every message that
//! arrives on a channel; TO SEND is to send bytes on one, and a REQUEST is a send handed an inbox for its one reply. A
//! member says which channels it reaches by what the world says of them, and adds itself to the agent's `Members` as
//! it makes its core; a row above reads them once every core is made, and names no member.

use std::sync::Arc;

use orexis::Error;

use crate::inbox::Inbox;

/// How a member exchanges bytes on a channel it reaches.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Exchange {
    /// Every message on it arrives of its own accord, once listened to.
    Listened,
    /// It answers what it is sent, once: its bytes are asked for.
    Requested,
}

/// A MEMBER OF THE TRANSPORT FAMILY, as the rows above it see one.
pub trait Member: Send + Sync {
    /// How this member exchanges bytes on `channel`, where it reaches it; None where it does not.
    fn reaches(&self, channel: &str) -> Result<Option<Exchange>, Error>;

    /// Hand every message that arrives on `channel` to `inbox`, from now on.
    fn listen(&self, channel: &str, inbox: Inbox) -> Result<(), Error>;

    /// Send `payload` on `channel`; where `reply` is handed, the one reply is left there, and none where the channel
    /// does not answer — a silence, which the row that asked reasons about.
    fn send(&self, channel: &str, payload: &[u8], reply: Option<Inbox>) -> Result<(), Error>;
}

/// The member that reaches a channel, and how it exchanges bytes on it.
pub type Reached = (Arc<dyn Member>, Exchange);

/// THE MEMBERS THE AGENT HOLDS, each added as it makes its core (`Provided::alter`) and read by a row above once every
/// core is made (`Provided::share`).
#[derive(Clone, Default)]
pub struct Members(Vec<Arc<dyn Member>>);

impl Members {
    /// `member` is one of the agent's.
    pub fn add(&mut self, member: Arc<dyn Member>) {
        self.0.push(member);
    }

    /// The member that reaches `channel`, and how; the first where several would, a world wiring a channel through
    /// one member today.
    pub fn reaching(&self, channel: &str) -> Result<Option<Reached>, Error> {
        for member in &self.0 {
            if let Some(exchange) = member.reaches(channel)? {
                return Ok(Some((member.clone(), exchange)));
            }
        }
        Ok(None)
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Mutex;

    use super::*;

    /// A member reaching the channels it is told of, and answering each request with the channel's name.
    struct Echo(Vec<(&'static str, Exchange)>, Mutex<Vec<String>>);

    impl Member for Echo {
        fn reaches(&self, channel: &str) -> Result<Option<Exchange>, Error> {
            Ok(self.0.iter().find(|(c, _)| *c == channel).map(|(_, e)| *e))
        }

        fn listen(&self, channel: &str, _inbox: Inbox) -> Result<(), Error> {
            self.1.lock().unwrap().push(channel.to_string());
            Ok(())
        }

        fn send(&self, channel: &str, _payload: &[u8], reply: Option<Inbox>) -> Result<(), Error> {
            if let Some(reply) = reply {
                reply.deliver(channel, channel.as_bytes(), None);
            }
            Ok(())
        }
    }

    #[test]
    fn a_channel_is_reached_by_the_member_that_says_so_and_a_request_is_answered_in_the_inbox_handed() {
        let mut members = Members::default();
        members.add(Arc::new(Echo(vec![("urn:a", Exchange::Requested)], Mutex::default())));
        members.add(Arc::new(Echo(vec![("urn:b", Exchange::Listened)], Mutex::default())));
        let (member, exchange) = members.reaching("urn:a").unwrap().expect("reached");
        assert_eq!(exchange, Exchange::Requested);
        assert_eq!(
            members.reaching("urn:b").unwrap().map(|(_, e)| e),
            Some(Exchange::Listened)
        );
        assert!(members.reaching("urn:c").unwrap().is_none());
        let inbox = Inbox::default();
        member.send("urn:a", b"", Some(inbox.clone())).unwrap();
        assert_eq!(inbox.take()[0].payload, b"urn:a");
    }
}
