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
    /// It is told what it is sent, and answers nothing: a device's command.
    Sent,
}

/// A MEMBER OF THE TRANSPORT FAMILY, as the rows above it see one.
pub trait Member: Send + Sync {
    /// Whether this member reaches `channel` by `exchange`: a row asks for the way it means to use the channel, since
    /// one channel may be reached two ways, a chat's listened to and sent on.
    fn reaches(&self, channel: &str, exchange: Exchange) -> Result<bool, Error>;

    /// Hand every message that arrives on `channel` to `inbox`, from now on.
    fn listen(&self, channel: &str, inbox: Inbox) -> Result<(), Error>;

    /// Send `payload` on `channel`; where `reply` is handed, the one reply is left there, and none where the channel
    /// does not answer — a silence, which the row that asked reasons about.
    fn send(&self, channel: &str, payload: &[u8], reply: Option<Inbox>) -> Result<(), Error>;
}

/// THE MEMBERS THE AGENT HOLDS, each added as it makes its core (`Provided::alter`) and read by a row above once every
/// core is made (`Provided::share`).
#[derive(Clone, Default)]
pub struct Members(Vec<Arc<dyn Member>>);

impl Members {
    /// `member` is one of the agent's.
    pub fn add(&mut self, member: Arc<dyn Member>) {
        self.0.push(member);
    }

    /// The member that reaches `channel` by `exchange`; the first where several would, a world wiring a channel
    /// through one member today.
    pub fn reaching(&self, channel: &str, exchange: Exchange) -> Result<Option<Arc<dyn Member>>, Error> {
        for member in &self.0 {
            if member.reaches(channel, exchange)? {
                return Ok(Some(member.clone()));
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
        fn reaches(&self, channel: &str, exchange: Exchange) -> Result<bool, Error> {
            Ok(self.0.iter().any(|(c, e)| *c == channel && *e == exchange))
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
        let member = members
            .reaching("urn:a", Exchange::Requested)
            .unwrap()
            .expect("reached");
        assert!(
            members.reaching("urn:a", Exchange::Listened).unwrap().is_none(),
            "asked another way"
        );
        assert!(members.reaching("urn:b", Exchange::Listened).unwrap().is_some());
        assert!(members.reaching("urn:c", Exchange::Requested).unwrap().is_none());
        let inbox = Inbox::default();
        member.send("urn:a", b"", Some(inbox.clone())).unwrap();
        assert_eq!(inbox.take()[0].payload, b"urn:a");
    }
}
