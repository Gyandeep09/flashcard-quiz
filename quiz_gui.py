#!/usr/bin/env python3
"""Flashcard Quiz, window version: a multiple-choice quiz from a JSON file of cards.

Examples:
    python quiz_gui.py cards.json
    python quiz_gui.py cards.json --limit 5
    python quiz_gui.py              (opens a file picker)
"""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from flashcard_quiz import QuizSession, load_cards

BG = "#f4f6fb"
TEXT = "#1f2430"
MUTED = "#5b6275"
CHOICE = "#ffffff"
HOVER = "#e7ecff"
ACCENT = "#3b5bdb"
CORRECT = "#2e9e5b"
WRONG = "#d64545"
FONT = ("Segoe UI", 12)


class QuizApp:
    def __init__(self, root: tk.Tk, cards: list[dict[str, str]], limit: int | None = None) -> None:
        self.root = root
        self.cards = cards
        self.limit = limit
        self.buttons: list[tk.Button] = []
        self.answered = False

        root.title("Flashcard Quiz")
        root.geometry("700x520")
        root.minsize(560, 420)
        root.configure(bg=BG)
        root.bind("<Key>", self.on_key)
        root.bind("<Escape>", lambda event: root.destroy())

        self.container = tk.Frame(root, bg=BG, padx=32, pady=24)
        self.container.pack(fill="both", expand=True)
        self.start()

    # ----- screens -----

    def start(self) -> None:
        self.session = QuizSession(self.cards, limit=self.limit)
        self.show_question()

    def clear(self) -> None:
        for widget in self.container.winfo_children():
            widget.destroy()
        self.buttons = []

    def show_question(self) -> None:
        self.clear()
        self.answered = False
        session = self.session
        total = len(session.cards)

        tk.Label(
            self.container,
            text=f"Question {session.index + 1} of {total}",
            bg=BG, fg=MUTED, font=("Segoe UI", 10),
        ).pack(anchor="w")

        ttk.Progressbar(self.container, maximum=total, value=session.index).pack(fill="x", pady=(4, 20))

        tk.Label(
            self.container,
            text=session.current["question"],
            bg=BG, fg=TEXT, font=("Segoe UI", 16, "bold"),
            wraplength=620, justify="left",
        ).pack(anchor="w", pady=(0, 20))

        for number, choice in enumerate(session.choices, start=1):
            button = tk.Button(
                self.container,
                text=f"{number}.   {choice}",
                anchor="w", font=FONT, bg=CHOICE, fg=TEXT,
                activebackground=HOVER, relief="groove", cursor="hand2",
                padx=14, pady=8,
                command=lambda picked=choice: self.pick(picked),
            )
            button.pack(fill="x", pady=4)
            self.buttons.append(button)

        self.feedback = tk.Label(self.container, text="", bg=BG, font=("Segoe UI", 12, "bold"))
        self.feedback.pack(anchor="w", pady=(14, 0))

        self.next_button = tk.Button(
            self.container, text="Next", font=FONT, bg=ACCENT, fg="white",
            activebackground=ACCENT, activeforeground="white",
            relief="flat", padx=22, pady=6, state="disabled", command=self.go_next,
        )
        self.next_button.pack(side="bottom", anchor="e")

    def show_results(self) -> None:
        self.clear()
        session = self.session
        total = len(session.cards)
        percent = round(session.score / total * 100)

        tk.Label(self.container, text="Quiz complete", bg=BG, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(pady=(10, 0))
        tk.Label(
            self.container,
            text=f"{session.score} / {total}  ({percent}%)",
            bg=BG, fg=ACCENT, font=("Segoe UI", 30, "bold"),
        ).pack(pady=(4, 16))

        if session.missed:
            tk.Label(self.container, text="Review these:", bg=BG, fg=MUTED, font=("Segoe UI", 11, "bold")).pack(anchor="w")
            for card in session.missed:
                tk.Label(
                    self.container,
                    text=f"{card['question']}\n    Answer: {card['answer']}",
                    bg=BG, fg=TEXT, font=("Segoe UI", 11),
                    wraplength=620, justify="left",
                ).pack(anchor="w", pady=3)
        else:
            tk.Label(self.container, text="Perfect score!", bg=BG, fg=CORRECT, font=("Segoe UI", 14, "bold")).pack()

        row = tk.Frame(self.container, bg=BG)
        row.pack(side="bottom", anchor="e")
        tk.Button(row, text="Close", font=FONT, relief="groove", padx=18, pady=6, command=self.root.destroy).pack(side="right", padx=(8, 0))
        tk.Button(
            row, text="Try again", font=FONT, bg=ACCENT, fg="white",
            activebackground=ACCENT, activeforeground="white",
            relief="flat", padx=18, pady=6, command=self.start,
        ).pack(side="right")

    # ----- actions -----

    def pick(self, choice: str) -> None:
        if self.answered:
            return
        self.answered = True

        right = self.session.current["answer"]
        was_correct = self.session.answer(choice)

        for button, text in zip(self.buttons, self.session.choices):
            if text == right:
                color, text_color = CORRECT, "white"
            elif text == choice:
                color, text_color = WRONG, "white"
            else:
                color, text_color = CHOICE, TEXT
            button.config(
                bg=color, fg=text_color,
                activebackground=color, activeforeground=text_color,
                cursor="arrow",
            )

        if was_correct:
            self.feedback.config(text="Correct!", fg=CORRECT)
        else:
            self.feedback.config(text=f"Not quite. The answer is: {right}", fg=WRONG)

        last = self.session.index == len(self.session.cards) - 1
        self.next_button.config(text="See results" if last else "Next", state="normal")

    def go_next(self) -> None:
        self.session.next_question()
        if self.session.finished:
            self.show_results()
        else:
            self.show_question()

    def on_key(self, event: tk.Event) -> None:
        if not self.buttons:
            return
        if event.keysym == "Return" and self.answered:
            self.go_next()
        elif event.char.isdigit() and not self.answered:
            position = int(event.char) - 1
            if 0 <= position < len(self.buttons):
                self.pick(self.session.choices[position])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Multiple-choice flashcard quiz in a window.")
    parser.add_argument("cards", type=Path, nargs="?", help="JSON file of cards (a file picker opens if left out)")
    parser.add_argument("-l", "--limit", type=int, help="ask only this many cards")
    args = parser.parse_args(argv)

    root = tk.Tk()
    path = args.cards

    if path is None:
        root.withdraw()
        chosen = filedialog.askopenfilename(title="Choose a cards file", filetypes=[("JSON files", "*.json")])
        if not chosen:
            return 0
        path = Path(chosen)
        root.deiconify()

    try:
        cards = load_cards(path)
        QuizSession(cards, limit=args.limit)  # check the cards and the limit before opening the window
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        messagebox.showerror("Cannot start the quiz", str(error))
        return 1

    QuizApp(root, cards, limit=args.limit)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

