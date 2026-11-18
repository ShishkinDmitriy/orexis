//! THE MEMBER'S PART: a chat carrier (`orexis_transport::chat`) over its bot, polled as often as a role says — the member's own words here,
//! and the core the family's.

use orexis::Error;
use orexis_transport::Inbox;
use orexis_transport::chat::{ChatMember, ChatTransport, Words};
use oxsdatatypes::DateTime;

use crate::driver::Telegram;

/// The member's part: the member, shared as a chat carrier with the rows above, and the messages handed to the pass.
pub type Transport = ChatTransport<Telegram>;

impl ChatMember for Telegram {
    const HOLDER: &'static str = "transport/telegram";

    fn inbox(&self) -> &Inbox {
        &self.inbox
    }

    fn poll(&self) {
        Telegram::poll(self)
    }

    fn carries(&self, channel: &str) -> Result<bool, Error> {
        Telegram::carries(self, channel)
    }

    fn handle(&mut self, topic: &str, payload: &[u8], at: DateTime) -> Result<Option<(String, Words)>, Error> {
        Telegram::handle(self, topic, payload, at)
    }

    fn say(&mut self, channel: &str, words: &Words) -> bool {
        Telegram::say(self, channel, words)
    }
}
