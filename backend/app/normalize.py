import re

_ACCENTS = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
_LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"}
_STRIP_RE = re.compile(r"[^a-z0-9]")


def normalize(text: str) -> str:
    """Lowercase, remove accents, apply basic leet-speak mapping and
    strip punctuation, so words can be matched against the forbidden list
    regardless of casing/accents/simple obfuscation."""
    text = text.lower()
    for accented, plain in _ACCENTS.items():
        text = text.replace(accented, plain)
    for leet, plain in _LEET.items():
        text = text.replace(leet, plain)
    return _STRIP_RE.sub("", text)
