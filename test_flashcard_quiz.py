import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from flashcard_quiz import (
    QuizSession,
    load_cards,
    main,
    make_choices,
    normalise,
    parse_notes,
    pick_cards,
    run_quiz,
    save_cards,
)

CARDS = [
    {"question": "Capital of France?", "answer": "Paris"},
    {"question": "2 + 2?", "answer": "4"},
    {"question": "Python file path class?", "answer": "Path"},
]


class NormaliseTests(unittest.TestCase):
    def test_ignores_case_spaces_and_trailing_punctuation(self):
        self.assertEqual(normalise("  PATH.  "), "path")

    def test_keeps_leading_dot(self):
        self.assertEqual(normalise(".gitignore"), ".gitignore")

    def test_collapses_inner_spaces(self):
        self.assertEqual(normalise("git   push"), "git push")


class ParseNotesTests(unittest.TestCase):
    def test_parses_lines(self):
        cards = parse_notes("Q1 :: A1\nQ2 :: A2\n")
        self.assertEqual(cards, [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}])

    def test_skips_blank_lines_and_comments(self):
        cards = parse_notes("# heading\n\nQ :: A\n")
        self.assertEqual(len(cards), 1)

    def test_answer_may_contain_colons(self):
        cards = parse_notes("Save command? :: :w")
        self.assertEqual(cards[0]["answer"], ":w")

    def test_bad_line_reports_line_number(self):
        with self.assertRaisesRegex(ValueError, "Line 2"):
            parse_notes("Q :: A\nno separator here\n")

    def test_empty_notes_raise(self):
        with self.assertRaises(ValueError):
            parse_notes("# only a comment\n")


class FileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name: str, text: str) -> Path:
        path = self.folder / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_save_then_load_round_trip(self):
        path = self.folder / "cards.json"
        save_cards(CARDS, path)
        self.assertEqual(load_cards(path), CARDS)

    def test_non_list_json_is_rejected(self):
        path = self.write("bad.json", json.dumps({"question": "Q", "answer": "A"}))
        with self.assertRaises(ValueError):
            load_cards(path)

    def test_missing_answer_is_rejected(self):
        path = self.write("bad.json", json.dumps([{"question": "Q"}]))
        with self.assertRaisesRegex(ValueError, "Card 1"):
            load_cards(path)

    def test_broken_json_is_rejected(self):
        path = self.write("bad.json", "[not json")
        with self.assertRaises(ValueError):
            load_cards(path)

    def test_convert_command_writes_json(self):
        notes = self.write("notes.txt", "Q :: A\n")
        out = self.folder / "out.json"
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["convert", str(notes), str(out)])
        self.assertEqual(code, 0)
        self.assertEqual(load_cards(out), [{"question": "Q", "answer": "A"}])

    def test_missing_file_gives_error_code(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code = main(["quiz", str(self.folder / "nope.json")])
        self.assertEqual(code, 1)


class QuizTests(unittest.TestCase):
    def run_with(self, replies):
        answers = iter(replies)
        said = []
        score, missed = run_quiz(CARDS, ask=lambda prompt: next(answers), say=said.append)
        return score, missed, said

    def test_all_correct(self):
        score, missed, _ = self.run_with(["paris", " 4 ", "PATH."])
        self.assertEqual(score, 3)
        self.assertEqual(missed, [])

    def test_wrong_answers_are_collected(self):
        score, missed, said = self.run_with(["London", "4", ""])
        self.assertEqual(score, 1)
        self.assertEqual([card["answer"] for card in missed], ["Paris", "Path"])
        self.assertTrue(any("The answer is: Paris" in line for line in said))


class PickCardsTests(unittest.TestCase):
    def test_limit_cuts_the_list(self):
        self.assertEqual(len(pick_cards(CARDS, limit=2)), 2)

    def test_shuffle_keeps_every_card(self):
        picked = pick_cards(CARDS, shuffle=True)
        self.assertEqual(sorted(c["question"] for c in picked), sorted(c["question"] for c in CARDS))

    def test_no_shuffle_keeps_order(self):
        self.assertEqual(pick_cards(CARDS, shuffle=False), CARDS)

    def test_original_list_is_not_changed(self):
        before = list(CARDS)
        pick_cards(CARDS, limit=1)
        self.assertEqual(CARDS, before)

MORE_CARDS = CARDS + [{"question": "Largest planet?", "answer": "Jupiter"}]


class MakeChoicesTests(unittest.TestCase):
    def test_includes_right_answer_once_with_four_options(self):
        choices = make_choices(MORE_CARDS[0], MORE_CARDS)
        self.assertEqual(len(choices), 4)
        self.assertEqual(choices.count("Paris"), 1)

    def test_options_are_all_different(self):
        choices = make_choices(MORE_CARDS[1], MORE_CARDS)
        self.assertEqual(len(set(choices)), len(choices))

    def test_duplicate_answers_on_other_cards_are_dropped(self):
        cards = [
            {"question": "A?", "answer": "Paris"},
            {"question": "B?", "answer": "paris"},
            {"question": "C?", "answer": "Rome"},
        ]
        choices = make_choices(cards[0], cards)
        self.assertEqual(sorted(choices), ["Paris", "Rome"])

    def test_few_cards_give_fewer_options(self):
        choices = make_choices(CARDS[0], CARDS[:2])
        self.assertEqual(sorted(choices), ["4", "Paris"])


class QuizSessionTests(unittest.TestCase):
    def test_needs_two_different_answers(self):
        same = [{"question": "A?", "answer": "x"}, {"question": "B?", "answer": "X"}]
        with self.assertRaises(ValueError):
            QuizSession(same)

    def test_limit_must_be_positive(self):
        with self.assertRaises(ValueError):
            QuizSession(CARDS, limit=0)

    def test_perfect_run(self):
        session = QuizSession(CARDS, shuffle=False)
        while not session.finished:
            self.assertTrue(session.answer(session.current["answer"]))
            session.next_question()
        self.assertEqual(session.score, 3)
        self.assertEqual(session.missed, [])

    def test_wrong_choice_is_recorded(self):
        session = QuizSession(CARDS, shuffle=False)
        self.assertFalse(session.answer("not the answer"))
        self.assertEqual(session.score, 0)
        self.assertEqual(session.missed, [CARDS[0]])

    def test_options_always_contain_the_right_answer(self):
        session = QuizSession(MORE_CARDS)
        while not session.finished:
            self.assertIn(session.current["answer"], session.choices)
            session.next_question()

    def test_limit_still_offers_four_options(self):
        session = QuizSession(MORE_CARDS, limit=1)
        self.assertEqual(len(session.cards), 1)
        self.assertEqual(len(session.choices), 4)


if __name__ == "__main__":
    unittest.main()


