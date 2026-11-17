//! THE MEMBER'S PART: a chat carrier (`orexis_transport::chat`) over its bot, polled as often as a role says — the member's own words here,
//! and the core the family's.

use orexis::Error;
use orexis::store::Store;
use orexis_speech::prose::Prose;
use orexis_transport::Inbox;
use orexis_transport::chat::{ChatMember, ChatTransport};
use oxsdatatypes::DateTime;

use crate::driver::Telegram;

/// What starts the member's carrying.
pub(crate) const CARRYING_TRIGGER: &str = "http://example.org/orexis/telegram#CarryingTrigger";

/// The member's part: the member, and the messages handed to the pass.
pub type Transport = ChatTransport<Telegram>;

impl ChatMember for Telegram {
    const CARRYING: &'static str = "http://example.org/orexis/telegram#Carrying";
    const HOLDER: &'static str = "transport/telegram";

    fn me(&self) -> &str {
        &self.me
    }

    fn inbox(&self) -> &Inbox {
        &self.inbox
    }

    fn beliefs(&self) -> &Store {
        Telegram::beliefs(self)
    }

    fn poll(&self) {
        Telegram::poll(self)
    }

    fn handle(&mut self, channel: &str, payload: &[u8], at: DateTime) -> Result<Option<Prose>, Error> {
        Telegram::handle(self, channel, payload, at)
    }
}
