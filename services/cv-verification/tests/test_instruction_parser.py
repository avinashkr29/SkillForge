from pathlib import Path

import pytest

from lego_ar.instruction_parser import load_instructions, parse_instruction_line


def test_parse_instruction_line():
    step = parse_instruction_line(
        "step one: take red block put on top of white block",
        1,
    )
    assert step is not None
    assert step.number == 1
    assert step.source_color == "red"
    assert step.target_color == "white"


def test_load_instructions_file(tmp_path: Path):
    instructions = tmp_path / "steps.txt"
    instructions.write_text(
        "step one: take red block put on top of white block\n"
        "step two: take yellow block put on top of red block\n",
        encoding="utf-8",
    )
    steps = load_instructions(instructions)
    assert len(steps) == 2
    assert steps[1].source_color == "yellow"
    assert steps[1].target_color == "red"


def test_load_instructions_missing_file():
    with pytest.raises(FileNotFoundError):
        load_instructions("missing.txt")