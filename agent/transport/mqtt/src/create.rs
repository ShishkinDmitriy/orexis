//! THE MQTT TRANSPORT'S PART, as `agent/transport/mqtt/create.py` and the family's `Transport.start` make it
//! (a-package-starts-itself): started, it subscribes what the world implies, asks after its sensors' missing readings
//! every `NUDGE_S` of the timeline, and holds the agent running, since what it senses goes on arriving whatever is
//! wanted. Every message a session's task receives waits in the member's inbox and is handed to the one executing
//! thread as a job that handles it — sensing writing a percept per sensor it is for, whose arrival the runtime tells
//! whoever listens. The executor's commands reach the member through whoever links the parts, sharing it.

use std::cell::RefCell;
use std::collections::VecDeque;
use std::rc::Rc;

use orexis::Error;
use orexis::runtime::{Heard, Part, Pass, Starting};
use orexis::transport::{ProseKept, carry, kept};

use crate::driver::{Message, Mqtt, NUDGE_S};

const NUDGE: usize = 0;
const HANDLE: usize = 1;
const CARRY: usize = 2;

/// What the member does as an activity, and what starts it.
const CARRYING: &str = "http://example.org/orexis/mqtt#Carrying";
const CARRYING_TRIGGER: &str = "http://example.org/orexis/mqtt#CarryingTrigger";

/// Who holds the agent running.
const HOLDER: &str = "transport/mqtt";

/// The member's part: the member, shared with whoever links to it, and the messages handed to the pass.
pub struct Transport<'a> {
    pub member: Rc<RefCell<Mqtt<'a>>>,
    pending: VecDeque<Message>,
}

impl<'a> Transport<'a> {
    pub fn new(member: Mqtt<'a>) -> Self {
        Transport {
            member: Rc::new(RefCell::new(member)),
            pending: VecDeque::new(),
        }
    }
}

impl Part for Transport<'_> {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        //  THE SESSIONS LISTEN BEFORE THE MEMBER SUBSCRIBES: a subscription waits in a queue only they empty.
        let listening = {
            let mut member = self.member.borrow_mut();
            member.inbox.wakes(starting.wake());
            std::mem::take(&mut member.listening)
        };
        for session in listening {
            starting.task(session)?;
        }
        self.member.borrow_mut().open()?;
        starting.every(NUDGE_S, NUDGE);
        starting.hears(CARRYING_TRIGGER, CARRY);
        Ok(())
    }

    /// What the member's policy does of its trigger: the agent's own words carried where they are on a channel it
    /// carries.
    fn heard_event(&mut self, _job: usize, event: &Heard, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        let store = self.member.borrow().beliefs().clone();
        carry(&store, &mut *self.member.borrow_mut(), event, pass, CARRYING)?;
        Ok(Vec::new())
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
                let (written, heard, store, me) = {
                    let mut member = self.member.borrow_mut();
                    let written = member.handle(&message.topic, &message.payload, message.at.unwrap_or(pass.now))?;
                    let (store, me) = (member.beliefs().clone(), member.me.clone());
                    (written, std::mem::take(&mut member.prose), store, me)
                };
                let mut written: Vec<String> = written.into_iter().map(|(_, graph)| graph).collect();
                //  A PERSON'S WORDS ON A CHAT'S TOPIC are kept, and said kept, for whoever translates.
                for prose in &heard {
                    let graph = kept(&store, &me, prose)?;
                    pass.emit(&ProseKept { prose: graph.clone() });
                    written.push(graph);
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
