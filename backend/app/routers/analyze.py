import json
import secrets
import time
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import review, rules
from app.auth import require_owner
from app.config import settings
from app.db import SessionLocal, get_db
from app.languages import LANGUAGES, detect
from app.models import Report
from app.samples import SAMPLES

router = APIRouter(prefix="/api", tags=["analyze"], dependencies=[Depends(require_owner)])


class AnalyzeIn(BaseModel):
    code: str
    language: str | None = None  # None or "auto": detect from filename, then content
    filename: str | None = Field(default=None, max_length=255)
    ai: bool = True


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def counts(issues: list[dict]) -> dict:
    c = Counter(i["severity"] for i in issues)
    return {s: c.get(s, 0) for s in rules.SEVERITIES}


def title_for(filename: str | None, language: str, code: str) -> str:
    if filename:
        return filename[:255]
    n = code.count("\n") + (0 if code.endswith("\n") else 1)
    return f"{LANGUAGES.get(language, language)} snippet, {n} line{'s' if n != 1 else ''}"


@router.post("/analyze")
def analyze(body: AnalyzeIn) -> StreamingResponse:
    code = body.code.replace("\r\n", "\n")
    if not code.strip():
        raise HTTPException(422, "Paste some code first")
    if len(code) > settings.max_chars:
        raise HTTPException(
            413, f"That's {len(code):,} characters; the limit is {settings.max_chars:,}"
        )
    language = detect(code, body.filename, None if body.language == "auto" else body.language)
    _, model, key = settings.llm

    def events():
        started = time.perf_counter()
        report_id = secrets.token_hex(6)
        state = {"status": "complete", "error": "", "fixed_source": "rules"}
        found = rules.find(code, language)
        static = [f.to_dict(i, code) for i, f in enumerate(found, 1)]
        rule_fixed, imports = rules.apply_fixes(code, found, language)
        fixed = rules.insert_imports(rule_fixed, imports, language)
        ai_issues: list[dict] = []
        finished = False
        try:
            yield sse("meta", {"id": report_id, "language": language, "model": model})
            yield sse(
                "static",
                {
                    "issues": static,
                    "fixed": fixed,
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            if not body.ai:
                state["status"] = "static"
            elif not key:
                state["status"] = "static"
                state["error"] = "AI review is off: no LLM_API_KEY is set on the server."
                yield sse("notice", {"message": state["error"]})
            else:
                yield sse("ai_start", {})
                try:
                    for kind, data in review.run(
                        rule_fixed, language, body.filename, static, imports
                    ):
                        if kind == "issue":
                            ai_issues.append(data)
                            yield sse("issue", data)
                        elif kind == "static_fix":
                            for item in static:
                                if item["id"] == data["id"]:
                                    item["fixable"], item["patch"] = True, data["patch"]
                            yield sse("static_fix", data)
                        elif data is not None:
                            fixed = rules.insert_imports(data, imports, language)
                            state["fixed_source"] = "model"
                except review.ReviewError as e:
                    state["status"], state["error"] = "partial", str(e)
                    yield sse("notice", {"message": str(e)})
            yield sse("fixed", {"code": fixed, "source": state["fixed_source"]})
            finished = True
        finally:
            # Also runs when the browser goes away mid-stream, so what we have is kept
            with SessionLocal() as db:
                db.add(
                    Report(
                        id=report_id,
                        title=title_for(body.filename, language, code),
                        language=language,
                        code=code,
                        issues=static + ai_issues,
                        fixed=fixed,
                        fixed_source=state["fixed_source"],
                        model=model if state["status"] != "static" else "",
                        status=state["status"] if finished else "partial",
                        ai_error=state["error"] if finished else "Stopped before the end.",
                    )
                )
                db.commit()
        yield sse(
            "done",
            {
                "id": report_id,
                "status": state["status"],
                "counts": counts(static + ai_issues),
                "ms": round((time.perf_counter() - started) * 1000),
            },
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _out(r: Report, full: bool) -> dict:
    out = {
        "id": r.id,
        "title": r.title,
        "language": r.language,
        "status": r.status,
        "counts": counts(r.issues),
        "created_at": r.created_at.isoformat() + "Z",
    }
    if full:
        out |= {
            "code": r.code,
            "issues": r.issues,
            "fixed": r.fixed,
            "fixed_source": r.fixed_source,
            "model": r.model,
            "ai_error": r.ai_error,
        }
    return out


@router.get("/reports")
def list_reports(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Report).order_by(Report.created_at.desc()).limit(100))
    return [_out(r, full=False) for r in rows]


@router.get("/reports/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)) -> dict:
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    return _out(r, full=True)


@router.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: str, db: Session = Depends(get_db)) -> None:
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    db.delete(r)
    db.commit()


@router.get("/rules")
def list_rules() -> dict:
    return {"languages": LANGUAGES, "rules": rules.catalogue()}


@router.get("/samples")
def list_samples() -> list[dict]:
    return SAMPLES
