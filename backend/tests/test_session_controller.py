import pytest

from app.models import SessionState
from app.modules.session_controller import TrackingSessionController


def test_valid_state_machine_path_is_logged():
    controller = TrackingSessionController()

    controller.transition_to(SessionState.LISTENING, "push to talk")
    controller.transition_to(SessionState.PARSING_COMMAND, "audio final")
    controller.transition_to(SessionState.SEARCHING, "object parsed")
    controller.transition_to(SessionState.LOCKED, "single candidate")
    controller.transition_to(SessionState.TRACKING, "tracker started")

    assert controller.state == SessionState.TRACKING
    assert len(controller.transitions) == 5
    assert controller.latest_transition()[0] == "LOCKED -> TRACKING"


def test_invalid_transition_raises():
    controller = TrackingSessionController()

    with pytest.raises(ValueError):
        controller.transition_to(SessionState.TRACKING, "skip required states")


def test_new_command_recovers_from_error_state():
    controller = TrackingSessionController()

    controller.transition_to(SessionState.ERROR, "detector failed")
    controller.transition_to(SessionState.PARSING_COMMAND, "fresh trainer command")
    controller.transition_to(SessionState.SEARCHING, "object parsed")

    assert controller.state == SessionState.SEARCHING
    assert controller.latest_transition()[0] == "PARSING_COMMAND -> SEARCHING"


def test_new_command_can_refine_while_searching():
    controller = TrackingSessionController()

    controller.transition_to(SessionState.PARSING_COMMAND, "first command")
    controller.transition_to(SessionState.SEARCHING, "first object not found yet")
    controller.transition_to(SessionState.PARSING_COMMAND, "refined trainer command")
    controller.transition_to(SessionState.SEARCHING, "refined object parsed")

    assert controller.state == SessionState.SEARCHING


def test_valid_tracking_update_recovers_from_error_state():
    controller = TrackingSessionController()

    controller.transition_to(SessionState.ERROR, "transient websocket race")
    controller.transition_to(SessionState.TRACKING, "valid target update arrived")

    assert controller.state == SessionState.TRACKING
    assert controller.latest_transition()[0] == "ERROR -> TRACKING"
