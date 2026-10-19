# Flashcard Quiz

A tool that turns your study notes into an interactive quiz. You write one question and answer per line in a text file and convert it to JSON. Then you take the quiz either in a window with multiple-choice buttons or in the terminal by typing your answers. It uses only the Python standard library.

## Requirements

- Python 3.9 or newer
- No third-party packages
- `tkinter` for the window verison. It comes with the Python installer from python.org on Windows. On Linux, install the `python3-tk` package.

## Quick start

1. Write your notes, one card per line, as `question :: answer`:

```text
   # Lines starting with # are ignored.
   What keyword defines a function in Python? :: def
   Which pathlib class represents a file path? :: Path
```

2. Convert the notes to a JSON file of cards:

```bash
   python flashcard_quiz.py convert notes.txt cards.json
```

3. Take the quiz, in a window or in the terminal:

```bash
   python quiz_gui.py cards.json
   python flashcard_quiz.py quiz cards.json
```

## Window version (multiple choice)

```bash
python quiz_gui.py cards.json
```

The window shows one question at a time with four answer buttons. After you choose, your pick turns red if it was wrong, the right answer turns green, and a progress bar tracks how far you are. The last screen shows your score and the cards to review, with a "Try again" button.

- Keys: `1` to `4` choose an answer, `Enter` moves on, `Esc` closes the window.
- `python quiz_gui.py cards.json --limit 5` asks only 5 cards.
- `python quiz_gui.py` with no file opens a file picker.

The wrong options are borrowed from the answers on your other cards, so the cards file needs at least 2 different answers. Answers that match after ignoring case and punctuation are never offered as wrong options.

## Terminal version (typed answers)

```bash
python flashcard_quiz.py quiz cards.json
```

Example session:

```text
Question 1/3: What keyword defines a function in Python?
Your answer: def
Correct!

Question 2/3: Which built-in returns the number of items in a list?
Your answer: length
Not quite. The answer is: len

Question 3/3: Which pathlib class represents a file path?
Your answer: path
Correct!

Score: 2/3 (67%)

Review these:
  - Which built-in returns the number of items in a list? -> len
```

## Options

| Command | What it does |
| --- | --- |
| `convert NOTES OUTPUT` | Reads a notes file and writes a JSON file of cards. |
| `quiz CARDS` | Asks every card in random order. |
| `quiz CARDS --limit N` | Asks only N cards. |
| `quiz CARDS --no-shuffle` | Asks the cards in file order. |

Press Ctrl+C during a quiz to stop it.

## How answers are checked

An answer is correct if it matches the stored answer after ignoring upper and lower case, extra spaces, and trailing punctuation (`.`, `!`, `?`). So `PATH.` and `path` both match `Path`. Spelling differences still count as wrong, and a blank answer counts as wrong.

## The JSON format

`cards.json` is a list of objects, each with a `question` and an `answer`. You can write it by hand instead of using `convert`:

```json
[
  { "question": "Which pathlib class represents a file path?", "answer": "Path" }
]
```

Both versions report a clear error if the file is not valid JSON, is not a list, or has a card with a missing or empty field. The error names the card number.

## Run the tests

```bash
python -m unittest -v
```

## Project layout

```text
flashcard_quiz.py        card loading, notes converter, quiz logic, terminal quiz
quiz_gui.py              the multiple-choice window
test_flashcard_quiz.py   unit tests
notes.txt                sample notes
cards.json               sample cards, made from notes.txt
README.md
.gitignore
```

## Ideas for extending it

- Save missed cards to a file and offer a retry round.
- Track scores over time in a JSON file.
- Let each card list its own wrong options, for harder multiple-choice questions.
- Accept several correct answers per card in the terminal version.
- Add a flip-the-card mode where you grade yourself.

