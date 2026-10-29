"""Just enough lexing to tell code from strings and comments.

Rules match against one of three views of the source, all the same length as the
original so offsets and line numbers line up:

- raw:     the source as written
- code:    string contents replaced with MASK, comments blanked
- comment: only comment text kept, everything else blanked

That way `eval(` inside a string or a comment doesn't count as a call, while a TODO only
counts when it's in a comment. It's a scanner, not a parser: regex literals in JS and
heredocs in PHP aren't understood, which is fine for the patterns it feeds.
"""

from dataclasses import dataclass

MASK = "\x00"


@dataclass(frozen=True)
class Syntax:
    line_comments: tuple[str, ...]
    block_comments: tuple[tuple[str, str], ...]
    quotes: tuple[str, ...]  # longest first, so """ wins over "
    multiline: frozenset[str] = frozenset()  # quotes that may span lines
    raw: frozenset[str] = frozenset()  # quotes with no backslash escapes


C_BLOCK = (("/*", "*/"),)

SYNTAX: dict[str, Syntax] = {
    "python": Syntax(("#",), (), ('"""', "'''", '"', "'"), frozenset({'"""', "'''"})),
    "javascript": Syntax(("//",), C_BLOCK, ('"', "'", "`"), frozenset({"`"})),
    "typescript": Syntax(("//",), C_BLOCK, ('"', "'", "`"), frozenset({"`"})),
    "java": Syntax(("//",), C_BLOCK, ('"""', '"', "'"), frozenset({'"""'})),
    "go": Syntax(("//",), C_BLOCK, ('"', "'", "`"), frozenset({"`"}), frozenset({"`"})),
    "php": Syntax(("//", "#"), C_BLOCK, ('"', "'"), frozenset({'"', "'"})),
    "other": Syntax(("#", "//"), C_BLOCK, ('"', "'")),
}


@dataclass(frozen=True)
class Views:
    raw: str
    code: str
    comment: str

    def line_of(self, offset: int) -> int:
        """1-based line number of a character offset."""
        return self.raw.count("\n", 0, offset) + 1


def scan(text: str, language: str) -> Views:
    s = SYNTAX.get(language, SYNTAX["other"])
    starters = {t[0] for t in s.line_comments} | {o[0] for o, _ in s.block_comments}
    starters |= {q[0] for q in s.quotes}
    code = list(text)
    comment = [c if c == "\n" else " " for c in text]
    n = len(text)
    i = 0

    def to_comment(a: int, b: int) -> None:
        for k in range(a, b):
            if text[k] != "\n":
                comment[k] = text[k]
                code[k] = " "

    while i < n:
        if text[i] not in starters:
            i += 1
            continue
        if any(text.startswith(t, i) for t in s.line_comments):
            end = text.find("\n", i)
            end = n if end == -1 else end
            to_comment(i, end)
            i = end
            continue
        block = next(((o, c) for o, c in s.block_comments if text.startswith(o, i)), None)
        if block:
            end = text.find(block[1], i + len(block[0]))
            end = n if end == -1 else end + len(block[1])
            to_comment(i, end)
            i = end
            continue
        quote = next((q for q in s.quotes if text.startswith(q, i)), None)
        if quote:
            j = i + len(quote)
            while j < n:
                if text[j] == "\\" and quote not in s.raw:
                    j += 2
                    continue
                if text.startswith(quote, j):
                    break
                if text[j] == "\n" and quote not in s.multiline:
                    break  # unterminated on this line; don't swallow the rest of the file
                j += 1
            j = min(j, n)
            for k in range(i + len(quote), j):
                if text[k] != "\n":
                    code[k] = MASK
            i = j + (len(quote) if text.startswith(quote, j) else 0)
            continue
        i += 1
    return Views(text, "".join(code), "".join(comment))
