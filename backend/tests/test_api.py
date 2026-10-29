import json

from app.config import settings
from tests.conftest import FakeStreamingChat


def events(response) -> list[tuple[str, dict]]:
    out = []
    for frame in response.text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.split("\n"))
        out.append((lines["event"], json.loads(lines["data"])))
    return out


CODE = 'import sqlite3\n\nDB_PASSWORD = "hunter2-prod"\n\n\ndef get(db, uid):\n    row = db.execute(f"SELECT * FROM t WHERE id = {uid}").fetchone()\n    return row[0]\n'

REPLY = "\n".join(
    [
        json.dumps(
            {
                "fix_for": "r2",
                "find": '    row = db.execute(f"SELECT * FROM t WHERE id = {uid}").fetchone()',
                "replace": '    row = db.execute("SELECT * FROM t WHERE id = ?", (uid,)).fetchone()',
            }
        ),
        json.dumps(
            {
                "line": 8,
                "severity": "critical",
                "category": "bug",
                "title": "Crashes when the row is missing",
                "explanation": "fetchone() returns None for an unknown id.",
                "suggestion": "Check for None.",
                "find": "    return row[0]",
                "replace": "    return row[0] if row else None",
            }
        ),
    ]
)


def test_needs_login(client):
    assert client.post("/api/analyze", json={"code": "x"}).status_code == 401
    assert client.get("/api/reports").status_code == 401


def test_full_review_streams_and_is_saved(owner, fake_llm):
    fake = fake_llm(REPLY)
    r = owner.post("/api/analyze", json={"code": CODE, "filename": "repo.py"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ev = events(r)
    assert [k for k, _ in ev] == [
        "meta",
        "static",
        "ai_start",
        "static_fix",
        "issue",
        "fixed",
        "done",
    ]
    meta, static, fixed, done = ev[0][1], ev[1][1], ev[5][1], ev[6][1]
    assert meta["language"] == "python"
    assert [i["rule_id"] for i in static["issues"]] == ["hardcoded-secret", "sql-injection"]
    # Static results already carry the rule-only fix
    assert 'os.environ["DB_PASSWORD"]' in static["fixed"] and static["fixed"].startswith(
        "import os\n"
    )
    # The model reviewed the code with rule fixes applied, and its fixes are in the result
    assert 'os.environ["DB_PASSWORD"]' in fake.calls[0][1].content
    assert fixed["source"] == "model"
    assert fixed["code"].startswith("import os\nimport sqlite3")
    assert "(uid,)" in fixed["code"] and "row[0] if row else None" in fixed["code"]
    assert done["counts"] == {"critical": 3, "warning": 0, "info": 0}

    report = owner.get(f"/api/reports/{done['id']}").json()
    assert report["title"] == "repo.py" and report["status"] == "complete"
    assert [i["id"] for i in report["issues"]] == ["r1", "r2", "a1"]
    assert report["issues"][1]["fixable"] and report["issues"][1]["patch"]["after"].endswith(
        "(uid,)).fetchone()"
    )
    assert report["fixed"] == fixed["code"]
    listed = owner.get("/api/reports").json()
    assert [x["id"] for x in listed] == [done["id"]] and "code" not in listed[0]


def test_without_a_key_static_still_works(owner, monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "")
    ev = events(owner.post("/api/analyze", json={"code": CODE}))
    assert [k for k, _ in ev] == ["meta", "static", "notice", "fixed", "done"]
    assert "LLM_API_KEY" in ev[2][1]["message"]
    assert ev[3][1]["source"] == "rules" and ev[4][1]["status"] == "static"


def test_static_only_on_request(owner, fake_llm):
    fake = fake_llm(REPLY)
    ev = events(owner.post("/api/analyze", json={"code": CODE, "ai": False}))
    assert [k for k, _ in ev] == ["meta", "static", "fixed", "done"] and fake.calls == []


def test_model_failure_keeps_what_arrived(owner, monkeypatch):
    from app import review

    fake = FakeStreamingChat(REPLY + "\n", size=50, error=RuntimeError("connection reset"))
    monkeypatch.setattr(review, "chat_model", lambda: fake)
    ev = events(owner.post("/api/analyze", json={"code": CODE}))
    kinds = [k for k, _ in ev]
    assert kinds == ["meta", "static", "ai_start", "static_fix", "issue", "notice", "fixed", "done"]
    assert "connection reset" in ev[5][1]["message"]
    assert ev[6][1]["source"] == "rules"  # the half-finished model fixes aren't used
    report = owner.get(f"/api/reports/{ev[-1][1]['id']}").json()
    assert report["status"] == "partial" and len(report["issues"]) == 3


def test_a_cut_off_reply_is_reported(owner, fake_llm):
    fake_llm(REPLY[:150], finish="length")
    ev = events(owner.post("/api/analyze", json={"code": CODE}))
    assert [k for k, _ in ev] == ["meta", "static", "ai_start", "notice", "fixed", "done"]
    assert "ran out of output tokens" in ev[3][1]["message"] and ev[-1][1]["status"] == "partial"


def test_language_detection_and_choice(owner, fake_llm):
    fake_llm("")
    ev = events(owner.post("/api/analyze", json={"code": "var a = 1;", "filename": "a.js"}))
    assert ev[0][1]["language"] == "javascript" and ev[1][1]["issues"][0]["rule_id"] == "js-var"
    ev = events(owner.post("/api/analyze", json={"code": "var a = 1;", "language": "go"}))
    assert ev[0][1]["language"] == "go" and ev[1][1]["issues"] == []
    # A clean review: nothing found, the code comes back unchanged
    assert ev[-2][1] == {"code": "var a = 1;", "source": "rules"}


def test_limits(owner, monkeypatch):
    assert owner.post("/api/analyze", json={"code": "   \n"}).status_code == 422
    monkeypatch.setattr(settings, "max_chars", 10)
    r = owner.post("/api/analyze", json={"code": "x = 1\n" * 5})
    assert r.status_code == 413 and "limit is 10" in r.json()["detail"]


def test_delete_report(owner, fake_llm):
    fake_llm("")
    rid = events(owner.post("/api/analyze", json={"code": "x = 1"}))[-1][1]["id"]
    assert owner.delete(f"/api/reports/{rid}").status_code == 204
    assert owner.get(f"/api/reports/{rid}").status_code == 404
    assert owner.delete(f"/api/reports/{rid}").status_code == 404


def test_rules_and_samples(owner):
    body = owner.get("/api/rules").json()
    assert "python" in body["languages"] and len(body["rules"]) > 20
    samples = owner.get("/api/samples").json()
    assert {s["language"] for s in samples} == {"python", "javascript", "typescript", "java", "go"}
