//! THE TELEGRAM TRANSPORT'S PART, as `agent/transport/telegram/create.py` and the family's `Transport.start` make it
//! (a-package-starts-itself): started, it polls the bot every `TELEGRAM_POLL_S` and holds the agent running; a message
//! a poll's thread received waits in the member's inbox and is handed to the one executing thread as a job that says
//! it as prose. Whoever links the parts shares the member, so translation sends back through it.

use std::cell::RefCell;
use std::collections::VecDeque;
use std::rc::Rc;

use orexis::Error;
use orexis::runtime::{Part, Pass, Starting};
use orexis::transport::{Hears, Message};

use crate::driver::Telegram;

const POLL: usize = 0;
const HANDLE: usize = 1;
const HOLDER: &str = "transport/telegram";

/// The member's part: the member, shared, and the messages handed to the pass.
pub struct Transport<'a> {
    pub member: Rc<RefCell<Telegram<'a>>>,
    /// Whoever hears the prose a chat's message is: translation, linked — handed it once the member is let go, since
    /// translation carries its answer back through the member.
    pub prose: Option<Hears<'a>>,
    pending: VecDeque<Message>,
}

impl<'a> Transport<'a> {
    pub fn new(member: Telegram<'a>) -> Self {
        Transport {
            member: Rc::new(RefCell::new(member)),
            prose: None,
            pending: VecDeque::new(),
        }
    }
}

impl Part for Transport<'_> {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        self.member.borrow().inbox.wakes(starting.wake());
        starting.every(self.member.borrow().every, POLL);
        Ok(())
    }

    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        pass.hold(HOLDER);
        match job {
            POLL => {
                self.member.borrow().poll();
                Ok(Vec::new())
            }
            _ => {
                let Some(message) = self.pending.pop_front() else {
                    return Ok(Vec::new());
                };
                let prose = self.member.borrow_mut().handle(
                    &message.topic,
                    &message.payload,
                    message.at.unwrap_or(pass.now),
                )?;
                match (prose, self.prose.as_mut()) {
                    (Some(prose), Some(hears)) => hears(&prose),
                    _ => Ok(Vec::new()),
                }
            }
        }
    }

    fn submitted(&mut self) -> Vec<usize> {
        let arrived = self.member.borrow().inbox.take();
        let n = arrived.len();
        self.pending.extend(arrived);
        vec![HANDLE; n]
    }
}
