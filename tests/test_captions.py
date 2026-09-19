"""Tests for the caption corrections.

captionFixes exists because captions are transcribed from the generated audio
and inherit whatever the voice sounded like. The tricky part is punctuation:
whisper attaches it to the word, so a fix has to match the bare word and put
the punctuation back on both sides.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from captions import correct


def correct_with(fixes: dict[str, str], word: str) -> str:
    return correct(word, fixes, set())


class TestCorrect:
    def test_leaves_an_unmatched_word_alone(self) -> None:
        assert correct_with({"PAM": "PEM"}, "hello") == "hello"

    def test_replaces_a_bare_word(self) -> None:
        assert correct_with({"PAM": "PEM"}, "PAM") == "PEM"

    def test_keeps_trailing_punctuation(self) -> None:
        assert correct_with({"PAM": "PEM"}, "PAM.") == "PEM."
        assert correct_with({"PAM": "PEM"}, "PAM,") == "PEM,"

    # Regression: the lookup stripped both sides but only restored the trailing
    # one, so a quoted word lost its opening quote.
    def test_keeps_leading_punctuation(self) -> None:
        assert correct_with({"PAM": "PEM"}, '"PAM') == '"PEM'
        assert correct_with({"PAM": "PEM"}, '"PAM"') == '"PEM"'

    def test_matches_inside_parentheses(self) -> None:
        assert correct_with({"PAM": "PEM"}, "(PAM)") == "(PEM)"

    def test_matches_case_insensitively(self) -> None:
        # The lowercased sentence opener whisper produces is the common case.
        assert correct_with({"Chapters": "Chapters"}, "chapters") == "Chapters"

    def test_an_exact_match_is_found(self) -> None:
        assert correct_with({"sans": "SANs"}, "sans,") == "SANs,"

    def test_punctuation_only_is_left_alone(self) -> None:
        assert correct_with({"PAM": "PEM"}, "...") == "..."

    # Regression: the punctuation set was ASCII-only while `lang` defaults to
    # ja, so a Japanese fix silently missed any word whisper ended with 。or 、.
    def test_handles_japanese_punctuation(self) -> None:
        assert correct_with({"ゼロ": "零"}, "ゼロ。") == "零。"
        assert correct_with({"なので": "ので"}, "なので、") == "ので、"
        assert correct_with({"PAM": "PEM"}, "「PAM」") == "「PEM」"

    def test_reports_which_fixes_were_used(self) -> None:
        used: set[str] = set()
        correct("PAM.", {"PAM": "PEM", "sans": "SANs"}, used)
        assert used == {"PAM"}
