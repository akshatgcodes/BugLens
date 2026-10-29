"""Which language a snippet is in: from the file name if there is one, else a guess."""

import re

LANGUAGES = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "go": "Go",
    "php": "PHP",
    "other": "Other",
}

EXTENSIONS = {
    "py": "python",
    "pyw": "python",
    "js": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "mts": "typescript",
    "java": "java",
    "go": "go",
    "php": "php",
}

# (language, pattern, weight). Weights only matter relative to each other.
SIGNALS: list[tuple[str, re.Pattern, int]] = [
    (lang, re.compile(p, re.M), w)
    for lang, p, w in [
        ("php", r"<\?php", 10),
        ("php", r"\$\w+\s*=", 2),
        ("go", r"^package \w+", 6),
        ("go", r"^func (\(\w+ \*?\w+\) )?\w+\(", 4),
        ("go", r":= ", 2),
        ("java", r"\b(public|private|protected) (static )?(final )?(class|void|[A-Z]\w*) ", 4),
        ("java", r"System\.out\.print", 4),
        ("python", r"^\s*def \w+\(.*\)\s*(->.*)?:\s*$", 4),
        ("python", r"^(from [\w.]+ )?import \w+", 2),
        ("python", r"^\s*(if|for|while|elif|else|try|except|with)\b.*:\s*$", 1),
        ("python", r"\bself\.", 2),
        ("typescript", r"^\s*(export )?(interface|type) \w+", 4),
        ("typescript", r"\w\s*:\s*(string|number|boolean|any|unknown)\b", 3),
        ("javascript", r"\b(const|let) \w+\s*=", 2),
        ("javascript", r"=>", 1),
        ("javascript", r"\brequire\(|\bmodule\.exports\b|\bconsole\.log\(", 2),
        ("javascript", r"^\s*function \w+\(", 2),
    ]
]


def from_filename(name: str | None) -> str | None:
    if not name or "." not in name:
        return None
    return EXTENSIONS.get(name.rsplit(".", 1)[1].lower())


def guess(code: str) -> str:
    scores: dict[str, int] = {}
    for lang, pattern, weight in SIGNALS:
        hits = len(pattern.findall(code))
        if hits:
            scores[lang] = scores.get(lang, 0) + weight * min(hits, 5)
    if not scores:
        return "other"
    # TypeScript is JavaScript plus types: only call it TS if there are type signals
    if "typescript" in scores:
        scores["typescript"] += scores.pop("javascript", 0)
    return max(scores, key=lambda k: scores[k])


def detect(code: str, filename: str | None = None, chosen: str | None = None) -> str:
    if chosen and chosen in LANGUAGES:
        return chosen
    return from_filename(filename) or guess(code)
