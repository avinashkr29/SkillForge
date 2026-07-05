from app.config import Settings
from app.models import Intent
from app.modules.command_parser import ObjectCommandParser


def parser() -> ObjectCommandParser:
    return ObjectCommandParser(Settings(OPENAI_API_KEY=None))


def test_extracts_object_phrase_from_action_sentence():
    parsed = parser().parse_deterministic("I am picking up the red screwdriver.")

    assert parsed.intent == Intent.TRACK_OBJECT
    assert parsed.object_phrase == "red screwdriver"
    assert parsed.base_object == "screwdriver"
    assert parsed.attributes.color == "red"
    assert parsed.action_context == "pick_up"
    assert parsed.requires_confirmation is False


def test_simple_track_command():
    parsed = parser().parse_deterministic("track red bottle")

    assert parsed.intent == Intent.TRACK_OBJECT
    assert parsed.object_phrase == "red bottle"
    assert parsed.base_object == "bottle"


def test_unresolved_pronoun_requires_confirmation():
    parsed = parser().parse_deterministic("track this")

    assert parsed.intent == Intent.UNCLEAR
    assert parsed.requires_confirmation is True


def test_stop_tracking_command():
    parsed = parser().parse_deterministic("please stop tracking")

    assert parsed.intent == Intent.STOP_TRACKING
