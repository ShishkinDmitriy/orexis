//! THE MQTT TRANSPORT'S PART, as `agent/transport/mqtt/create.py` and the family's `Transport.start` make it
//! (a-package-starts-itself): started, it subscribes what the world implies, asks after its sensors' missing readings
//! every `NUDGE_S` of the timeline, and holds the agent running, since what it senses goes on arriving whatever is
//! wanted. Every message a client's thread receives waits in the member's inbox and is handed to the one executing
//! thread as a job that handles it — sensing writing a percept per sensor it is for, whose arrival the runtime tells
//! whoever listens. The executor's commands reach the member through whoever links the parts, sharing it.

use std::cell::RefCell;
use std::collections::VecDeque;
use std::rc::Rc;

use orexis::Error;
use orexis::runtime::{Part, Pass, Starting};

use crate::driver::{Message, Mqtt, NUDGE_S};

const NUDGE: usize = 0;
const HANDLE: usize = 1;

/// Who holds the agent running.
const HOLDER: &str = "transport/mqtt";

/// The member's part: the member, shared with whoever links to it, and the messages handed to the pass.
pub struct Transport<'a> {
    pub member: Rc<RefCell<Mqtt<'a>>>,
    /// Whoever hears a person's prose on a chat's topic: translation, linked — handed it once the member is let go.
    pub prose: Option<orexis::transport::Hears<'a>>,
    pending: VecDeque<Message>,
}

impl<'a> Transport<'a> {
    pub fn new(member: Mqtt<'a>) -> Self {
        Transport {
            member: Rc::new(RefCell::new(member)),
            prose: None,
            pending: VecDeque::new(),
        }
    }
}

impl Part for Transport<'_> {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        self.member.borrow_mut().open()?;
        starting.every(NUDGE_S, NUDGE);
        Ok(())
    }

    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        match job {
            NUDGE => {
                //  A MEMBER KEEPS THE AGENT RUNNING: what it senses goes on arriving whatever is wanted.
                pass.hold(HOLDER);
                self.member.borrow_mut().nudge(pass.now)?;
                Ok(Vec::new())
            }
            HANDLE => {
                let Some(message) = self.pending.pop_front() else {
                    return Ok(Vec::new());
                };
                let (written, heard) = {
                    let mut member = self.member.borrow_mut();
                    let written = member.handle(&message.topic, &message.payload, message.at.unwrap_or(pass.now))?;
                    (written, std::mem::take(&mut member.prose))
                };
                let mut written: Vec<String> = written.into_iter().map(|(_, graph)| graph).collect();
                if let Some(hears) = self.prose.as_mut() {
                    for prose in &heard {
                        written.extend(hears(prose)?);
                    }
                }
                Ok(written)
            }
            _ => Ok(Vec::new()),
        }
    }

    fn submitted(&mut self) -> Vec<usize> {
        let arrived = self.member.borrow().inbox.take();
        let n = arrived.len();
        self.pending.extend(arrived);
        vec![HANDLE; n]
    }

    fn stop(&mut self) {
        self.member.borrow_mut().stop();
    }
}
