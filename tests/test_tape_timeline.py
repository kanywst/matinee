"""Tests for the tape walker.

Every defect this module has shipped is represented here. The parser is the
part that decides whether matinee works on a tape nobody wrote it against, so
the real tapes in fixtures/ matter as much as the unit cases.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from tape_timeline import (
    clean_title,
    is_section_comment,
    parse_duration,
    scale_marks,
    split_qualifier,
    timeline,
)

FIXTURES = Path(__file__).parent / "fixtures"


def titles(tape: str) -> list[str]:
    return [m["title"] for m in timeline(tape)[0]]


def elapsed(tape: str) -> float:
    return timeline(tape)[1]


class TestParseDuration:
    @pytest.mark.parametrize(
        "token,expected",
        [
            ("500ms", 500.0),
            ("1.5s", 1500.0),
            ("2s", 2000.0),
            ("1m", 60000.0),
            # VHS takes a bare number as seconds; brtc's tape uses `0.1`.
            ("0.1", 100.0),
            ("3", 3000.0),
            ("nonsense", 0.0),
            ("", 0.0),
        ],
    )
    def test_units(self, token: str, expected: float) -> None:
        assert parse_duration(token) == expected


class TestSplitQualifier:
    def test_strips_at_qualifier(self) -> None:
        assert split_qualifier("Type@100ms") == ("Type", 100.0)
        assert split_qualifier("Enter@50ms") == ("Enter", 50.0)

    def test_leaves_plain_commands_alone(self) -> None:
        assert split_qualifier("Sleep") == ("Sleep", None)


class TestCleanTitle:
    def test_cuts_at_parenthetical(self) -> None:
        assert clean_title("Help (auto-generated from key.Binding)") == "Help"

    def test_cuts_at_comma(self) -> None:
        assert (
            clean_title("Export via huh form, submit and dismiss")
            == "Export via huh form"
        )

    def test_strips_trailing_period(self) -> None:
        assert clean_title("Walk the list.") == "Walk the list"

    # Regression: slicing at a fixed width left "...with a different " with a
    # trailing space, mid-phrase.
    def test_truncates_at_a_word_boundary(self) -> None:
        long = "Step 2: Show a strong password with a different hardware profile"
        result = clean_title(long)
        assert len(result) <= 48
        assert result == result.strip()
        assert not result.endswith(("-", ",", ":"))
        assert long.startswith(result)

    def test_leaves_a_short_title_untouched(self) -> None:
        assert clean_title("Search") == "Search"


class TestSectionComments:
    def test_numbered_comment_is_a_section_however_long(self) -> None:
        lines = ["# 2. " + "x" * 200, 'Type "a"']
        assert is_section_comment(lines, 0) is not None

    def test_lone_comment_is_a_section(self) -> None:
        lines = ['Type "a"', "# Search", 'Type "b"']
        # (title, numbered) -- numbering is what lets a section survive a
        # hidden first step, so it travels with the title.
        assert is_section_comment(lines, 1) == ("Search", False)

    # Regression: requiring no '.' and <40 chars rejected every section comment
    # in prpr's tape and half of brtc's.
    def test_a_lone_comment_with_a_period_is_still_a_section(self) -> None:
        lines = ['Type "a"', "# Walk the list.", 'Type "b"']
        assert is_section_comment(lines, 1) == ("Walk the list", False)

    def test_multi_line_comment_block_is_prose(self) -> None:
        lines = [
            "# This paragraph explains why the next step is written",
            "# the way it is, and must not become a chapter.",
            'Type "a"',
        ]
        assert is_section_comment(lines, 0) is None
        assert is_section_comment(lines, 1) is None

    def test_empty_comment_is_not_a_section(self) -> None:
        assert is_section_comment(["#", 'Type "a"'], 0) is None


class TestTimingModel:
    def test_typing_costs_typing_speed_per_character(self) -> None:
        assert elapsed('Set TypingSpeed 100ms\nType "abcde"\n') == 500.0

    def test_sleep_costs_its_duration(self) -> None:
        assert elapsed("Sleep 1.5s\n") == 1500.0

    def test_a_key_costs_one_typing_speed(self) -> None:
        assert elapsed("Set TypingSpeed 50ms\nEnter\n") == 50.0

    def test_a_repeat_count_multiplies_the_key(self) -> None:
        assert elapsed("Set TypingSpeed 50ms\nEnter 3\n") == 150.0

    # Regression: `Down Sleep 700ms` is valid VHS and prpr's tape uses it seven
    # times; splitting on the first token dropped every one of those sleeps.
    def test_several_statements_on_one_line(self) -> None:
        one_line = "# A\nSet TypingSpeed 50ms\nDown Sleep 700ms\nTab Sleep 1200ms\n"
        separate = "# A\nSet TypingSpeed 50ms\nDown\nSleep 700ms\nTab\nSleep 1200ms\n"
        assert elapsed(one_line) == elapsed(separate) == 2000.0

    # Regression: @-qualified commands fell through every branch, costing 0ms.
    def test_at_qualified_commands_use_their_own_duration(self) -> None:
        assert elapsed('Type@100ms "hello"\n') == 500.0
        assert elapsed("Enter@50ms 3\n") == 150.0

    def test_modifier_keys_cost_time(self) -> None:
        assert elapsed("Set TypingSpeed 50ms\nShift+Tab\nCtrl+L\n") == 100.0

    def test_hidden_blocks_cost_nothing(self) -> None:
        tape = 'Set TypingSpeed 50ms\nHide\nType "setup"\nSleep 30s\nShow\nSleep 1s\n'
        assert elapsed(tape) == 1000.0

    def test_output_and_require_cost_nothing(self) -> None:
        assert elapsed('Output "out/"\nRequire go\nSleep 1s\n') == 1000.0

    def test_wait_costs_nothing(self) -> None:
        assert elapsed("Wait+Screen@300s /READY/\nSleep 1s\n") == 1000.0

    def test_quoted_text_keeps_its_spaces(self) -> None:
        assert elapsed('Set TypingSpeed 100ms\nType "a b c"\n') == 500.0

    def test_backtick_and_single_quotes_are_stripped(self) -> None:
        assert elapsed("Set TypingSpeed 100ms\nType `abc`\n") == 300.0
        assert elapsed("Set TypingSpeed 100ms\nType 'abc'\n") == 300.0


class TestMarkPlacement:
    def test_a_section_is_placed_at_the_command_that_follows_it(self) -> None:
        tape = "Set TypingSpeed 0\nSleep 1s\n# Second\nSleep 1s\n"
        marks, _ = timeline(tape)
        assert marks == [{"title": "Second", "startMs": 1000}]

    def test_a_section_inside_a_hide_block_is_not_placed_there(self) -> None:
        tape = 'Hide\n# Setup\nType "x"\nShow\nSleep 1s\n# Real\nSleep 1s\n'
        assert titles(tape) == ["Real"]


class TestScaleMarks:
    def test_scales_marks_to_the_measured_duration(self) -> None:
        marks = [{"title": "a", "startMs": 0}, {"title": "b", "startMs": 1000}]
        out = scale_marks(marks, 2000.0, 1000)
        assert out[1]["startMs"] == 500

    def test_first_mark_is_pinned_to_zero(self) -> None:
        marks = [{"title": "a", "startMs": 800}]
        assert scale_marks(marks, 1000.0, 10000)[0]["startMs"] == 0

    def test_drops_a_teardown_section_in_the_last_second(self) -> None:
        marks = [
            {"title": "a", "startMs": 0},
            {"title": "Quit", "startMs": 9900},
        ]
        assert [m["title"] for m in scale_marks(marks, 10000.0, 10000)] == ["a"]

    # Regression: the filter could empty the list, and both call sites then
    # indexed marks[0].
    def test_keeps_the_only_section_even_if_it_is_late(self) -> None:
        marks = [{"title": "Quit", "startMs": 9900}]
        out = scale_marks(marks, 10000.0, 10000)
        assert out == [{"title": "Quit", "startMs": 0}]

    def test_no_duration_means_no_scaling(self) -> None:
        marks = [{"title": "a", "startMs": 500}]
        assert scale_marks(marks, 1000.0, None)[0]["startMs"] == 0


class TestRealTapes:
    """The three tapes matinee ships examples for, byte-for-byte.

    They differ in theme, framerate, comment style and statement layout, which
    is the whole reason they are here: the parser was fitted to the first one
    and silently failed on the other two.
    """

    @pytest.mark.parametrize(
        "name,sections,chapters",
        [
            # y509's tape ends with a `# Quit` teardown section, which
            # scale_marks drops as too short to read.
            ("y509.tape", 10, 9),
            ("prpr.tape", 6, 6),
            ("brtc.tape", 2, 2),
        ],
    )
    def test_chapter_counts(self, name: str, sections: int, chapters: int) -> None:
        tape = (FIXTURES / name).read_text(encoding="utf-8")
        marks, estimated = timeline(tape)
        assert len(marks) == sections
        assert len(scale_marks(marks, estimated, round(estimated))) == chapters

    def test_no_tape_yields_a_prose_paragraph_as_a_chapter(self) -> None:
        for name in ("y509.tape", "prpr.tape", "brtc.tape"):
            tape = (FIXTURES / name).read_text(encoding="utf-8")
            for title in titles(tape):
                assert len(title) <= 48
                assert title == title.strip()

    def test_marks_are_monotonic(self) -> None:
        for name in ("y509.tape", "prpr.tape", "brtc.tape"):
            tape = (FIXTURES / name).read_text(encoding="utf-8")
            starts = [m["startMs"] for m in timeline(tape)[0]]
            assert starts == sorted(starts)

    def test_cli_reports_no_sections_rather_than_crashing(self) -> None:
        script = Path(__file__).parent.parent / "scripts" / "tape_timeline.py"
        tape = FIXTURES / "no-sections.tape"
        result = subprocess.run(
            [sys.executable, str(script), str(tape)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "no section comments" in result.stderr

    def test_cli_emits_json(self) -> None:
        script = Path(__file__).parent.parent / "scripts" / "tape_timeline.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                str(FIXTURES / "y509.tape"),
                "--duration-ms",
                "27880",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        marks = json.loads(result.stdout)
        assert len(marks) == 9
        assert marks[0]["startMs"] == 0
        assert all(m["startMs"] < 27880 for m in marks)


class TestTrailingComments:
    """A trailing `# ...` is not a statement.

    VHS accepts `Set Width 1200 # the width`, and walking a comment's words as
    commands let one that merely mentioned a duration inflate the estimate --
    which scale_marks then divides by, moving every chapter mark in the video.
    """

    def test_a_duration_in_a_comment_costs_nothing(self) -> None:
        assert elapsed('Set TypingSpeed 100ms\nType "ab"  # Sleep 10s here\n') == 200.0

    def test_a_comment_after_a_key_costs_nothing(self) -> None:
        assert elapsed("Set TypingSpeed 50ms\nEnter # then Sleep 5s\n") == 50.0

    def test_a_comment_after_a_sleep_costs_nothing(self) -> None:
        assert elapsed("Sleep 2s # then press Enter twice\n") == 2000.0

    def test_a_hash_inside_a_quoted_string_is_not_a_comment(self) -> None:
        assert elapsed('Set TypingSpeed 100ms\nType "#127"\n') == 400.0


class TestWhatCountsAsASection:
    def test_a_header_comment_does_not_become_a_chapter(self) -> None:
        tape = '# y509 demo tape\nSet FontSize 16\n# Launch\nType "a"\nSleep 1s\n'
        assert titles(tape) == ["Launch"]

    def test_a_comment_above_hide_labels_the_setup_not_a_chapter(self) -> None:
        tape = (
            '# Set up the fixtures\nHide\nType "x"\nShow\n'
            'Type "app"\nSleep 3s\n# Search\nSleep 1s\n'
        )
        assert titles(tape) == ["Search"]

    def test_an_enumeration_inside_prose_is_not_a_section(self) -> None:
        tape = (
            '# This tape:\n# 1. builds\n# 2. runs it\n# 3. quits\nType "a"\nSleep 1s\n'
        )
        assert titles(tape) == []

    def test_a_numbered_section_may_run_onto_a_second_line(self) -> None:
        # y509's tape does exactly this, and the continuation must not become
        # a second chapter.
        tape = (
            "# 2. Switch to details pane and browse tabs (last tab is Misc\n"
            "# with the new chain view)\n"
            'Type "a"\nSleep 1s\n'
        )
        assert titles(tape) == ["Switch to details pane and browse tabs"]

    def test_a_configuration_line_does_not_consume_the_mark(self) -> None:
        tape = "Set TypingSpeed 0\nSleep 1s\n# Second\nSet Padding 10\nSleep 1s\n"
        marks, _ = timeline(tape)
        assert marks == [{"title": "Second", "startMs": 1000}]


class TestHiddenSections:
    """A comment on a Hide block is ambiguous, and numbering is the tiebreak.

    Nothing in the shape separates "this documents the setup" from "this names
    a section whose first step happens to be hidden" -- but a number is the
    author saying it is a section.
    """

    def test_a_numbered_section_survives_a_hidden_first_step(self) -> None:
        tape = (
            '# Launch\nType "app"\nSleep 2s\n'
            '# 3. Export\nHide\nType "rm -f out.pem"\nEnter\nShow\n'
            'Type "e"\nSleep 2s\n'
        )
        assert titles(tape) == ["Launch", "Export"]

    def test_an_unnumbered_note_on_a_hide_block_is_dropped(self) -> None:
        tape = (
            '# Set up the fixtures\nHide\nType "x"\nShow\n'
            'Type "app"\nSleep 3s\n# Search\nSleep 1s\n'
        )
        assert titles(tape) == ["Search"]


class TestVHSConstructs:
    """Constructs `vhs validate` accepts that the walker used to price at 0ms."""

    @pytest.mark.parametrize("key", ["Insert", "ScrollUp", "ScrollDown"])
    def test_the_remaining_keys_cost_time(self, key: str) -> None:
        assert elapsed(f"Set TypingSpeed 50ms\n{key}\n") == 50.0

    def test_a_repeat_count_after_a_scroll_key(self) -> None:
        assert elapsed("Set TypingSpeed 50ms\nScrollDown 10\nSleep 2s\n") == 2500.0

    def test_type_accepts_several_strings(self) -> None:
        assert elapsed('Set TypingSpeed 100ms\nType "abc" "de"\n') == 500.0

    def test_an_escaped_quote_stays_inside_one_token(self) -> None:
        # `say "hi"` is eight characters once the escapes are removed.
        assert elapsed('Set TypingSpeed 100ms\nType "say \\"hi\\""\n') == 800.0

    def test_a_hash_inside_a_string_is_not_a_comment(self) -> None:
        assert elapsed('Set TypingSpeed 100ms\nType "#!/bin/sh"\n') == 900.0
