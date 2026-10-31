"""The email driver over a stand-in mailbox: every unseen message is delivered by its sender's address, a message is
said as `prose` in the chat whose contact point has that address — whatever case it is written in — one from an
address the world names in no chat is dropped and said once, and what the agent says is sent to the contact point's
address."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.transport.email.driver import Email, _text_of
from agent.transport.transport import Transport

WORLD = Path(__file__).parent / "worlds" / "a_chat_by_email.trig"
TEST = "http://example.org/test#"


class Box:
    def __init__(self, *unseen):
        self.unseen, self.sent = list(unseen), []

    def fetch(self):
        found, self.unseen = self.unseen, []
        return found

    def send(self, to, text):
        self.sent.append((to, text))


@pytest.fixture
def mail(snapshots):
    box = Box()
    driver = Email(TEST + "keeper", box, spawn=lambda work: work())
    heard = []
    driver.prose.connect(lambda prose: heard.append(prose) or [])
    return snapshots.stand_in(WORLD), driver, box, heard


def test_the_driver_answers_the_familys_contract(mail):
    assert isinstance(mail[1], Transport)


def test_a_poll_delivers_every_unseen_message_by_its_senders_address(mail):
    _, driver, box, _ = mail
    delivered = []
    driver.deliver = lambda *message: delivered.append(message[:2])
    box.unseen = [("anna@example.org", "hello"), ("bob@example.org", "hi")]
    assert driver.poll() == [] and driver.poll() == []
    assert delivered == [("anna@example.org", b"hello"), ("bob@example.org", b"hi")]


def test_a_message_is_prose_in_the_chat_whose_contact_point_has_the_address(mail, snapshots, caplog):
    store, driver, _, heard = mail
    assert driver.handle(store, "Anna@Example.org", "is the fern dry?".encode(), snapshots.NOW) == []
    assert [(p.channel, p.sender, p.text) for p in heard] == [(TEST + "anna_mail", None, "is the fern dry?")], \
        "the chat's one person is who wrote, so the channel names no sender"
    for _ in range(2):
        assert driver.handle(store, "bob@example.org", b"hi", snapshots.NOW) == []
    assert len(heard) == 1 and caplog.text.count("mail from bob@example.org") == 1


def test_what_the_agent_says_is_sent_to_the_contact_points_address(mail):
    store, driver, box, _ = mail
    assert driver.say_to(store, TEST + "anna_mail", "the fern is dry") is True
    assert box.sent == [("anna@example.org", "the fern is dry")]
    assert driver.say_to(store, TEST + "keeper_and_anna", "x") is False, "a node with no address is not this member's"


def test_a_messages_text_is_its_plain_part():
    from email.message import EmailMessage
    message = EmailMessage()
    message.set_content(" plain words \n")
    message.add_alternative("<p>html</p>", subtype="html")
    assert _text_of(message) == "plain words"
    html = EmailMessage()
    html.set_content("<p>html</p>", subtype="html")
    assert _text_of(html) is None


def test_connect_refuses_an_agent_with_no_mailbox():
    with pytest.raises(RuntimeError, match="no mailbox in the environment"):
        Email.connect(TEST + "keeper", environ={"MAIL_ADDRESS": "keeper@example.org"})
    driver = Email.connect(TEST + "keeper", environ={"MAIL_ADDRESS": "k@example.org", "MAIL_PASSWORD": "p", "MAIL_IMAP_HOST": "imap",
                                                    "MAIL_SMTP_HOST": "smtp", "MAIL_POLL_S": "60"})
    assert (driver.box.address, driver.box.imap_port, driver.box.smtp_port, driver.every) == ("k@example.org", 993, 465, 60.0)
