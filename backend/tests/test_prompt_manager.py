from app.models import Intent, ParsedCommand
from app.modules.prompt_manager import PromptManager, normalize_prompt


def test_normalize_prompt_removes_articles_and_spacing():
    assert normalize_prompt(" The   Small, Red Screwdriver ") == "small red screwdriver"


def test_prompt_order_is_specific_to_general():
    manager = PromptManager()
    changed = manager.apply_command(
        ParsedCommand(
            intent=Intent.TRACK_OBJECT,
            object_phrase="small red screwdriver",
            base_object="screwdriver",
        )
    )

    assert changed is True
    assert manager.active_prompts == ["small red screwdriver", "red screwdriver", "screwdriver"]
    assert manager.prompt_version == 1


def test_duplicate_prompt_does_not_reconfigure_model():
    manager = PromptManager()
    command = ParsedCommand(intent=Intent.TRACK_OBJECT, object_phrase="red bottle", base_object="bottle")

    assert manager.apply_command(command) is True
    assert manager.apply_command(command) is False
    assert manager.prompt_version == 1


def test_duplicate_transcript_debouncing():
    manager = PromptManager()

    assert manager.should_ignore_duplicate_transcript("track red bottle") is False
    assert manager.should_ignore_duplicate_transcript("track red bottle") is True
    assert manager.should_ignore_duplicate_transcript("track blue bottle") is False
