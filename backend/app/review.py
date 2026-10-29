"""The model's half of the review: issues the rules can't see, each with a local fix.

The model answers with one JSON object per issue, so issues can be shown while it's still
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
from app.rules import CATEGORIES, NO_SHIFT, SEVERITIES, Shift

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
existing import line. Imports the static fixes need are already in the listing.
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
    extra = (
        {"reasoning_effort": settings.llm_reasoning_effort} if settings.llm_reasoning_effort else {}
    )
    return ChatOpenAI(
        base_url=base_url,
        model=model,
        api_key=key,
        temperature=0.1,
        timeout=120,
        max_tokens=settings.llm_max_tokens,
        streaming=True,
        **extra,
    )


def prompt(code: str, language: str, filename: str | None, static: list[dict], shift: Shift) -> str:
    numbered = "\n".join(f"{i:>4} | {line}" for i, line in enumerate(code.split("\n"), 1))
    found = (
        "\n".join(
            f"- {s['id']} line {shift.to_new(s['line'])}: {s['title']} "
            f"({'fixed' if s['fixable'] else 'needs a fix'})"
            for s in static
        )
        or "- none"
    )
    name = f" ({filename})" if filename else ""
    return (
        f"Language: {LANGUAGES.get(language, language)}{name}\n"
        f"Report at most {settings.max_ai_issues} issues.\n\n"
        f"Static checks already reported:\n{found}\n\n"
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


class ObjectScanner:
    """Pulls complete top-level {...} objects out of streamed text.

    Asked for one object per line, models still sometimes pretty-print them over several
    lines, wrap them in an array or fences, or add a stray brace. Tracking brace depth
    (outside strings) copes with all of that, and still yields each object as soon as
    its closing brace arrives.
    """

    def __init__(self):
        self.buf: list[str] = []
        self.depth = 0
        self.in_string = False
        self.escaped = False

    def feed(self, text: str) -> list[str]:
        out = []
        for ch in text:
            if self.depth == 0:
                if ch == "{":
                    self.depth, self.buf = 1, ["{"]
                continue
            self.buf.append(ch)
            if self.in_string:
                if self.escaped:
                    self.escaped = False
                elif ch == "\\":
                    self.escaped = True
                elif ch == '"':
                    self.in_string = False
            elif ch == '"':
                self.in_string = True
            elif ch == "{":
                self.depth += 1
            elif ch == "}":
                self.depth -= 1
                if self.depth == 0:
                    out.append("".join(self.buf))
        return out

    def pending(self) -> bool:
        return self.depth > 0


class ReviewStream:
    """Turns streamed model text into validated issues, applying each fix as it arrives.

    The model sees the code after rule fixes and their imports; `shift` maps its line
    numbers back to the code the user submitted.
    """

    def __init__(self, code: str, static: list[dict], limit: int, shift: Shift = NO_SHIFT):
        self.code = code
        self.shift = shift
        self.n_lines = len(code.split("\n"))
        self.limit = limit
        self.unfixed = {s["id"] for s in static if not s["fixable"]}
        # (line, category, id), ones that still need a fix first so a repeat lands there
        self.static = sorted(
            ((s["line"], s["category"], s["id"]) for s in static),
            key=lambda t: t[2] not in self.unfixed,
        )
        self.issues: list[dict] = []
        self.skipped = 0
        self.applied = 0
        self.objects = ObjectScanner()

    def feed(self, text: str) -> list[tuple[str, dict]]:
        return [e for obj in self.objects.feed(text) if (e := self._object(obj))]

    def close(self) -> list[tuple[str, dict]]:
        if self.objects.pending():
            self.skipped += 1  # cut off mid-object
        return []

    def _object(self, raw: str) -> tuple[str, dict] | None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.skipped += 1
            return None
        event = self._handle(data) if isinstance(data, dict) else None
        if event is None:
            self.skipped += 1
        return event

    def _patch(self, d: dict) -> dict | None:
        if not isinstance(d.get("find"), str):
            return None
        result = apply_patch(self.code, d["find"], str(d.get("replace") or ""))
        if not result:
            return None
        self.code, patch = result
        self.applied += 1
        return patch

    def _static_fix(self, rid: str, d: dict) -> tuple[str, dict] | None:
        """A fix for a rule finding the rules couldn't fix themselves."""
        if rid not in self.unfixed:
            return None
        patch = self._patch(d)
        if not patch:
            return None
        self.unfixed.discard(rid)
        return "static_fix", {"id": rid, "patch": patch}

    def _handle(self, d: dict) -> tuple[str, dict] | None:
        if "fix_for" in d:
            return self._static_fix(str(d["fix_for"]), d)
        if len(self.issues) >= self.limit:
            return None
        try:
            line = int(d.get("line"))
            end = int(d.get("end_line") or line)
        except (TypeError, ValueError):
            return None
        if not 1 <= line <= self.n_lines:
            return None  # points outside the code: made up
        line, end = self.shift.to_old(line), self.shift.to_old(min(max(end, line), self.n_lines))
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
        end = max(end, line)
        rid = next((i for n, c, i in self.static if c == category and line <= n <= end), None)
        if rid:
            # The rules already said this. Models repeat findings even when told not to,
            # often with the fix the rule couldn't make, so keep the fix and drop the rest.
            return self._static_fix(rid, d)
        if any(i["line"] == line and i["title"].lower() == title.lower() for i in self.issues):
            return None
        patch = self._patch(d)
        issue = {
            "id": f"a{len(self.issues) + 1}",
            "source": "ai",
            "rule_id": None,
            "severity": severity,
            "category": category,
            "line": line,
            "end_line": end,
            "title": title,
            "explanation": _text(d.get("explanation"), 1000),
            "suggestion": _text(d.get("suggestion"), 500),
            "snippet": "",
            "fixable": patch is not None,
            "patch": patch,
        }
        self.issues.append(issue)
        return "issue", issue


class ReviewError(Exception):
    pass


def run(
    code: str, language: str, filename: str | None, static: list[dict], shift: Shift = NO_SHIFT
) -> Iterator[tuple[str, object]]:
    """Reviews `code` (rule fixes and their imports already applied). Yields
    ("issue", dict) and ("static_fix", {id, patch}) as they arrive, ("warning", str) if
    the reply was cut off, then ("fixed", str) with every fix that applied cleanly, or
    ("fixed", None) if none did."""
    stream = ReviewStream(code, static, settings.max_ai_issues, shift)
    messages = [
        SystemMessage(SYSTEM),
        HumanMessage(prompt(code, language, filename, static, shift)),
    ]
    cut_off = False
    try:
        for chunk in chat_model().stream(messages):
            text = chunk.content if isinstance(chunk.content, str) else ""
            yield from stream.feed(text)
            meta = getattr(chunk, "response_metadata", None) or {}
            cut_off = cut_off or meta.get("finish_reason") == "length"
    except Exception as e:
        raise ReviewError(f"The model call failed: {str(e)[:300]}") from e
    yield from stream.close()
    if cut_off:
        yield "warning", "The model ran out of output tokens, so the AI review may be incomplete."
    yield "fixed", stream.code if stream.applied else None
