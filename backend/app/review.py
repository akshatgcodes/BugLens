"""The model's half of the review: issues the rules can't see, each with a local fix.

The model answers with one JSON object per line, so issues can be shown while it's still
typing (a single JSON document would only parse at the very end):

    {"line": 12, "severity": "warning", ..., "find": "<exact lines>", "replace": "<fixed>"}

Fixes are search/replace pairs, not a rewritten file. Asked for a whole corrected file,
models also reformat, drop blank lines and add comments, so the diff is mostly noise. A
`find` that doesn't match the code exactly once is not applied, which also catches
fixes for lines the model misread.
"""

import json
import re
from collections.abc import Iterator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.languages import LANGUAGES
from app.rules import CATEGORIES, SEVERITIES

SYSTEM = """You are a senior engineer doing a careful code review.

Answer with one JSON object per line and nothing else: no prose, no code fences.
{"line": 12, "end_line": 14, "severity": "warning", "category": "bug", "title": "...", \
"explanation": "...", "suggestion": "...", "find": "...", "replace": "..."}

- severity: "critical" (exploitable, crashes, data loss, or wrong results in normal use), \
"warning" (a likely bug or risk under some inputs), "info" (maintainability)
- category: "security", "bug", "smell" or "performance"
- line and end_line refer to the numbered listing
- title: under 60 characters. explanation: one or two sentences on what goes wrong and \
when. suggestion: one sentence on how to fix it.
- find: the affected lines copied exactly from the listing (whole lines, without the \
line-number prefix), as few as needed and unique in the file. replace: the same lines \
corrected, keeping the indentation. Use \\n between lines. Leave both out if the fix \
isn't local.
- If a fix needs a new import, put it in that issue's find/replace by extending an \
existing import line.
- Look for what pattern matching can't see: logic errors, unhandled edge cases (empty \
input, None/null, division by zero, off-by-one), missing error handling, race \
conditions, injection and XSS through indirect paths, resource leaks, slow loops.
- Static checks ran first and their findings are listed. Don't report them again. Some \
are already fixed in the listing; for each one marked "needs a fix", if the fix is \
local, output a fix line instead: {"fix_for": "r2", "find": "...", "replace": "..."}
- Most important first. Skip style nitpicks. If the code is fine, output nothing."""


def chat_model() -> BaseChatModel:
    """Tests replace this with a fake that streams a canned reply."""
    from langchain_openai import ChatOpenAI

    base_url, model, key = settings.llm
    return ChatOpenAI(
        base_url=base_url, model=model, api_key=key, temperature=0.1, timeout=120, streaming=True
    )


def prompt(
    code: str, language: str, filename: str | None, static: list[dict], imports: list[str]
) -> str:
    numbered = "\n".join(f"{i:>4} | {line}" for i, line in enumerate(code.split("\n"), 1))
    found = (
        "\n".join(
            f"- {s['id']} line {s['line']}: {s['title']} "
            f"({'fixed' if s['fixable'] else 'needs a fix'})"
            for s in static
        )
        or "- none"
    )
    extra = f"\nThese imports will be added for the fixes: {', '.join(imports)}" if imports else ""
    name = f" ({filename})" if filename else ""
    return (
        f"Language: {LANGUAGES.get(language, language)}{name}\n"
        f"Report at most {settings.max_ai_issues} issues.\n\n"
        f"Static checks already reported:\n{found}{extra}\n\n"
        f"Code:\n{numbered}"
    )


# --- applying a find/replace -----------------------------------------------------------

PREFIX = re.compile(r"^\s*\d+ \| ?")


def _strip_numbers(lines: list[str]) -> list[str]:
    """Models sometimes copy the '  12 | ' prefix from the listing."""
    if lines and all(PREFIX.match(ln) for ln in lines if ln.strip()):
        return [PREFIX.sub("", ln) for ln in lines]
    return lines


def _indent(s: str) -> str:
    return s[: len(s) - len(s.lstrip())]


def apply_patch(text: str, find: str, replace: str) -> tuple[str, dict] | None:
    """Replace the one place `find` occurs. Returns (new text, {before, after}) or None.

    Tried in order: an exact match of whole lines; the same ignoring trailing spaces;
    the same ignoring indentation, re-indenting the replacement to match the file.
    """
    want = _strip_numbers(find.strip("\n").split("\n"))
    new = _strip_numbers(replace.strip("\n").split("\n")) if replace.strip() else []
    if not any(ln.strip() for ln in want):
        return None
    lines = text.split("\n")
    n = len(want)
    for key in (lambda s: s, str.rstrip, str.strip):
        target = [key(ln) for ln in want]
        hits = [
            i for i in range(len(lines) - n + 1) if [key(x) for x in lines[i : i + n]] == target
        ]
        if len(hits) > 1:
            return None  # ambiguous: don't guess which one
        if len(hits) == 1:
            i = hits[0]
            before = lines[i : i + n]
            if key is str.strip and new:
                # Shift the replacement by however much the model's copy was dedented
                have, given = _indent(before[0]), _indent(want[0])
                if have.startswith(given):
                    pad = have[len(given) :]
                    new = [pad + ln if ln.strip() else ln for ln in new]
            if new == before:
                return None
            out = lines[:i] + new + lines[i + n :]
            return "\n".join(out), {"before": "\n".join(before), "after": "\n".join(new)}
    return None


# --- validating streamed issues --------------------------------------------------------

SEVERITY_ALIASES = {
    "high": "critical",
    "error": "critical",
    "blocker": "critical",
    "medium": "warning",
    "moderate": "warning",
    "low": "info",
    "minor": "info",
    "note": "info",
}
CATEGORY_ALIASES = {
    "style": "smell",
    "maintainability": "smell",
    "readability": "smell",
    "correctness": "bug",
    "logic": "bug",
    "reliability": "bug",
    "perf": "performance",
}
# Non-breaking and figure hyphens, narrow spaces: models emit them, they look odd in a UI
TYPOGRAPHY = str.maketrans({"‐": "-", "‑": "-", "‒": "-", " ": " ", " ": " "})


def _text(value, limit: int) -> str:
    return str(value or "").translate(TYPOGRAPHY).strip()[:limit]


class ReviewStream:
    """Turns streamed model text into validated issues, applying each fix as it arrives."""

    def __init__(self, code: str, static: list[dict], limit: int):
        self.code = code
        self.n_lines = len(code.split("\n"))
        self.limit = limit
        self.static = {(s["line"], s["category"]) for s in static}
        self.unfixed = {s["id"] for s in static if not s["fixable"]}
        self.issues: list[dict] = []
        self.skipped = 0
        self.applied = 0
        self.buf = ""

    def feed(self, text: str) -> list[tuple[str, dict]]:
        self.buf += text
        out = []
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            out += self._line(line)
        return out

    def close(self) -> list[tuple[str, dict]]:
        rest, self.buf = self.buf, ""
        return self._line(rest)

    def _line(self, raw: str) -> list[tuple[str, dict]]:
        s = raw.strip()
        if not s or s.startswith("```"):
            return []
        try:
            data = json.loads(s)
        except json.JSONDecodeError:
            self.skipped += 1
            return []
        if isinstance(data, dict) and "fix_for" in data:
            fix = self._static_fix(data)
            return [("static_fix", fix)] if fix else []
        issue = self._validate(data) if isinstance(data, dict) else None
        if issue is None:
            self.skipped += 1
            return []
        self.issues.append(issue)
        return [("issue", issue)]

    def _static_fix(self, d: dict) -> dict | None:
        """A fix for a rule finding the rules couldn't fix themselves."""
        rid = d.get("fix_for")
        if rid not in self.unfixed or not isinstance(d.get("find"), str):
            self.skipped += 1
            return None
        result = apply_patch(self.code, d["find"], str(d.get("replace") or ""))
        if not result:
            self.skipped += 1
            return None
        self.code, patch = result
        self.unfixed.discard(rid)
        self.applied += 1
        return {"id": rid, "patch": patch}

    def _validate(self, d: dict) -> dict | None:
        if len(self.issues) >= self.limit:
            return None
        try:
            line = int(d.get("line"))
            end = int(d.get("end_line") or line)
        except (TypeError, ValueError):
            return None
        if not 1 <= line <= self.n_lines:
            return None  # points outside the code: made up
        title = _text(d.get("title"), 120)
        if not title:
            return None
        severity = str(d.get("severity", "")).lower()
        severity = SEVERITY_ALIASES.get(severity, severity)
        category = str(d.get("category", "")).lower()
        category = CATEGORY_ALIASES.get(category, category)
        if category not in CATEGORIES:
            category = "bug"
        if severity not in SEVERITIES:
            severity = "warning"
        if (line, category) in self.static:
            return None  # the rules already said this
        if any(i["line"] == line and i["title"].lower() == title.lower() for i in self.issues):
            return None
        patch = None
        if isinstance(d.get("find"), str) and isinstance(d.get("replace"), str):
            result = apply_patch(self.code, d["find"], d["replace"])
            if result:
                self.code, patch = result
                self.applied += 1
        return {
            "id": f"a{len(self.issues) + 1}",
            "source": "ai",
            "rule_id": None,
            "severity": severity,
            "category": category,
            "line": line,
            "end_line": min(max(end, line), self.n_lines),
            "title": title,
            "explanation": _text(d.get("explanation"), 1000),
            "suggestion": _text(d.get("suggestion"), 500),
            "snippet": "",
            "fixable": patch is not None,
            "patch": patch,
        }


class ReviewError(Exception):
    pass


def run(
    code: str, language: str, filename: str | None, static: list[dict], imports: list[str]
) -> Iterator[tuple[str, object]]:
    """Reviews `code` (rule fixes already applied). Yields ("issue", dict) and
    ("static_fix", {id, patch}) as they arrive, then ("fixed", str) with every fix that
    applied cleanly, or None if none did."""
    stream = ReviewStream(code, static, settings.max_ai_issues)
    messages = [
        SystemMessage(SYSTEM),
        HumanMessage(prompt(code, language, filename, static, imports)),
    ]
    try:
        for chunk in chat_model().stream(messages):
            text = chunk.content if isinstance(chunk.content, str) else ""
            yield from stream.feed(text)
    except Exception as e:
        raise ReviewError(f"The model call failed: {str(e)[:300]}") from e
    yield from stream.close()
    yield "fixed", stream.code if stream.applied else None
