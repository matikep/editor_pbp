import json
from pathlib import Path

from .normalize import normalize

WORDS_FILE = Path(__file__).resolve().parent.parent / "words.json"


def load_forbidden_words() -> set[str]:
    with open(WORDS_FILE, encoding="utf-8") as f:
        words = json.load(f)
    return {normalize(w) for w in words}
