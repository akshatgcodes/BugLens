import json

import pytest

from app.review import ReviewStream, apply_patch

CODE = "def f(x):\n    if x:\n        return 1 / x\n    return 0\n"


def issue(**kw) -> str:
    base = {"line": 3, "severity": "warning", "category": "bug", "title": "Divides by x"}
    return json.dumps(base | kw)


def run(reply: str, size: int, static=(), code=CODE) -> tuple[ReviewStream, list]:
    s = ReviewStream(code, list(static), limit=15)
    events = []
    for i in range(0, len(reply), size):
        events += s.feed(reply[i : i + size])
    return s, events + s.close()


@pytest.mark.parametrize("size", [1, 2, 5, 13, 1000])
def test_issues_come_out_whatever_the_chunking(size):
    reply = (
        "```json\n"
        + issue()
        + "\n"
        + issue(line=1, title="No type hints", severity="low", category="style")
        + "\n```"
    )
    s, events = run(reply, size)
    assert [(k, e["line"], e["severity"], e["category"]) for k, e in events] == [
        ("issue", 3, "warning", "bug"),
        ("issue", 1, "info", "smell"),
    ]
    assert s.skipped == 0


def test_bad_lines_are_skipped_not_fatal():
    reply = "\n".join(
        [
            "Here is my review:",
            issue(line=99),  # outside the code
            issue(line="x"),
            issue(title=""),
            "[1, 2]",
            issue(severity="extreme", category="vibes"),
            issue(severity="extreme", category="vibes"),  # duplicate
        ]
    )
    s, events = run(reply, 9)
    assert [(e["severity"], e["category"]) for _, e in events] == [("warning", "bug")]
    assert s.skipped == 6


def test_findings_the_rules_already_made_are_dropped():
    static = [{"id": "r1", "line": 3, "category": "bug", "fixable": True}]
    _, events = run(issue() + "\n" + issue(category="performance", title="Slow"), 4, static)
    assert [e["title"] for _, e in events] == ["Slow"]


def test_limit():
    s = ReviewStream(CODE, [], limit=2)
    events = s.feed("\n".join(issue(title=f"t{i}") for i in range(5)) + "\n")
    assert len(events) == 2


def test_fixes_apply_as_issues_arrive():
    fix = {"find": "        return 1 / x", "replace": "        return 1 / x if x else 0"}
    s, events = run(issue(**fix) + "\n", 6)
    ((_, e),) = events
    assert e["fixable"] and e["patch"] == {"before": fix["find"], "after": fix["replace"]}
    assert "1 / x if x else 0" in s.code and s.applied == 1


def test_fix_for_a_static_finding():
    static = [
        {"id": "r1", "line": 2, "category": "security", "fixable": False},
        {"id": "r2", "line": 4, "category": "bug", "fixable": True},
    ]
    reply = "\n".join(
        [
            json.dumps({"fix_for": "r1", "find": "    if x:", "replace": "    if x is not None:"}),
            json.dumps(
                {"fix_for": "r2", "find": "    return 0", "replace": "    return -1"}
            ),  # already fixed
            json.dumps(
                {"fix_for": "r9", "find": "    return 0", "replace": "    return -1"}
            ),  # unknown
        ]
    )
    s, events = run(reply, 11, static)
    assert events == [
        (
            "static_fix",
            {"id": "r1", "patch": {"before": "    if x:", "after": "    if x is not None:"}},
        )
    ]
    assert s.skipped == 2


TEXT = "a = 1\nif a:\n    b = 2   \n    c = 3\nb = 2\n"


@pytest.mark.parametrize(
    "find,replace,result",
    [
        # exact
        ("if a:\n", "if a > 0:", "a = 1\nif a > 0:\n    b = 2   \n    c = 3\nb = 2\n"),
        # trailing spaces don't matter
        (
            "    b = 2\n    c = 3",
            "    b = 4\n    c = 5",
            "a = 1\nif a:\n    b = 4\n    c = 5\nb = 2\n",
        ),
        # copied without indentation: the replacement is re-indented
        ("b = 2   \nc = 3", "b = 4\nc = 5", "a = 1\nif a:\n    b = 4\n    c = 5\nb = 2\n"),
        # copied with the listing's line numbers
        ("   2 | if a:", "   2 | if a > 0:", "a = 1\nif a > 0:\n    b = 2   \n    c = 3\nb = 2\n"),
        # empty replace deletes
        ("    c = 3", "", "a = 1\nif a:\n    b = 2   \nb = 2\n"),
    ],
)
def test_apply_patch(find, replace, result):
    out = apply_patch(TEXT, find, replace)
    assert out and out[0] == result


@pytest.mark.parametrize(
    "find,replace",
    [
        (" b = 2", "b = 3"),  # matches two places once indentation is ignored: ambiguous
        ("z = 9", "z = 0"),  # not in the file
        ("if a:", "if a:"),  # changes nothing
        ("", "x"),
    ],
)
def test_apply_patch_refuses(find, replace):
    assert apply_patch(TEXT, find, replace) is None
