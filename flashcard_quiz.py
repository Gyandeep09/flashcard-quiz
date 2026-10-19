#!/usr/bin/env python3
"""Flashcard Quiz: turn your notes into an interactive quiz in the terminal.

Examples:
    python flashcard_quiz.py convert notes.txt cards.json
    python flashcard_quiz.py quiz cards.json
    python flashcard_quiz.py quiz cards.json --limit 5
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Callable

Card = dict[str, str]


def normalise(text: str) -> str:
    """Make two answers comparable.

    Ignores case, extra spaces and trailing punctuation, so "Path." and
    "  path " both match "Path".
    """
    return " ".join(text.casefold().split()).rstrip(".!? ")


def load_cards(path: Path) -> list[Card]:
    """Read cards from a JSON file.

    The file must hold a list of objects, each with a "question" and an
    "answer" that are non-empty strings. Raises ValueError if it does not.
    """
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list) or not data:
        raise ValueError("The JSON file must contain a non-empty list of cards.")

    cards: list[Card] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Card {index}: expected an object with question and answer.")
        question = item.get("question")
        answer = item.get("answer")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"Card {index}: missing or empty 'question'.")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"Card {index}: missing or empty 'answer'.")
        cards.append({"question": question.strip(), "answer": answer.strip()})
    return cards


def save_cards(cards: list[Card], path: Path) -> None:
    """Write cards to a JSON file."""
    path.write_text(json.dumps(cards, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_notes(text: str) -> list[Card]:
    """Turn plain notes into cards.

    One card per line, written as: question :: answer
    Blank lines and lines starting with # are ignored.
    """
    cards: list[Card] = []
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        question, separator, answer = line.partition("::")
        question, answer = question.strip(), answer.strip()
        if not separator or not question or not answer:
            raise ValueError(f"Line {number}: expected 'question :: answer'.")
        cards.append({"question": question, "answer": answer})
    if not cards:
        raise ValueError("No cards found in the notes.")
    return cards


def pick_cards(cards: list[Card], limit: int | None = None, shuffle: bool = True) -> list[Card]:
    """Return the cards to ask, optionally shuffled and cut to `limit`."""
    chosen = list(cards)
    if shuffle:
        random.shuffle(chosen)
    if limit is not None:
        chosen = chosen[:limit]
    return chosen

def make_choices(
    card: Card,
    cards: list[Card],
    count: int = 4,
    rng: random.Random | None = None,
) -> list[str]:
    """Return multiple-choice options for `card`, in random order.

    The options are the right answer plus wrong answers borrowed from the
    other cards. Duplicates are removed, so the right answer never appears
    twice. With fewer than `count - 1` other answers you get fewer options.
    """
    rng = rng or random.Random()
    right = card["answer"]

    seen = {normalise(right)}
    pool: list[str] = []
    for other in cards:
        key = normalise(other["answer"])
        if key not in seen:
            seen.add(key)
            pool.append(other["answer"])

    choices = rng.sample(pool, min(count - 1, len(pool))) + [right]
    rng.shuffle(choices)
    return choices


class QuizSession:
    """The state of one multiple-choice quiz, with no screen code in it.

    The window in quiz_gui.py draws it, and the tests drive it directly.
    """

    def __init__(
        self,
        cards: list[Card],
        limit: int | None = None,
        shuffle: bool = True,
        choice_count: int = 4,
    ) -> None:
        if len({normalise(card["answer"]) for card in cards}) < 2:
            raise ValueError("A multiple-choice quiz needs at least 2 different answers.")
        if limit is not None and limit < 1:
            raise ValueError("The limit must be 1 or more.")

        self.all_cards = cards
        self.cards = pick_cards(cards, limit, shuffle)
        self.choice_count = choice_count
        self.index = 0
        self.score = 0
        self.missed: list[Card] = []
        self.choices = make_choices(self.cards[0], cards, choice_count)

    @property
    def finished(self) -> bool:
        return self.index >= len(self.cards)

    @property
    def current(self) -> Card:
        return self.cards[self.index]

    def answer(self, choice: str) -> bool:
        """Record the player's choice for the current card. True if correct."""
        correct = normalise(choice) == normalise(self.current["answer"])
        if correct:
            self.score += 1
        else:
            self.missed.append(self.current)
        return correct

    def next_question(self) -> None:
        """Move on to the next card and build its options."""
        self.index += 1
        if not self.finished:
            self.choices = make_choices(self.current, self.all_cards, self.choice_count)


def run_quiz(
    cards: list[Card],
    ask: Callable[[str], str] = input,
    say: Callable[[str], None] = print,
) -> tuple[int, list[Card]]:
    """Ask every card in turn. Returns (score, cards answered wrongly).

    `ask` and `say` are parameters so the tests can feed in answers
    without a keyboard.
    """
    score = 0
    missed: list[Card] = []

    for number, card in enumerate(cards, start=1):
        say(f"\nQuestion {number}/{len(cards)}: {card['question']}")
        reply = ask("Your answer: ")
        if normalise(reply) == normalise(card["answer"]):
            say("Correct!")
            score += 1
        else:
            say(f"Not quite. The answer is: {card['answer']}")
            missed.append(card)

    return score, missed


def show_summary(score: int, total: int, missed: list[Card], say: Callable[[str], None] = print) -> None:
    percent = round(score / total * 100) if total else 0
    say(f"\nScore: {score}/{total} ({percent}%)")
    if missed:
        say("\nReview these:")
        for card in missed:
            say(f"  - {card['question']} -> {card['answer']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Turn your notes into an interactive quiz.")
    commands = parser.add_subparsers(dest="command", required=True)

    quiz = commands.add_parser("quiz", help="take a quiz from a JSON file of cards")
    quiz.add_argument("cards", type=Path, help="JSON file of cards")
    quiz.add_argument("-l", "--limit", type=int, help="ask only this many cards")
    quiz.add_argument("--no-shuffle", action="store_true", help="keep the cards in file order")

    convert = commands.add_parser("convert", help="convert a notes file into a JSON file of cards")
    convert.add_argument("notes", type=Path, help="text file with lines like: question :: answer")
    convert.add_argument("output", type=Path, help="JSON file to write")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "convert":
            cards = parse_notes(args.notes.read_text(encoding="utf-8"))
            save_cards(cards, args.output)
            print(f"Wrote {len(cards)} card(s) to {args.output}")
            return 0

        if args.limit is not None and args.limit < 1:
            print("--limit must be 1 or more.", file=sys.stderr)
            return 1

        cards = pick_cards(load_cards(args.cards), args.limit, shuffle=not args.no_shuffle)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    try:
        score, missed = run_quiz(cards)
    except (KeyboardInterrupt, EOFError):
        print("\nQuiz stopped.")
        return 1

    show_summary(score, len(cards), missed)
    return 0


if __name__ == "__main__":
    sys.exit(main()) 


