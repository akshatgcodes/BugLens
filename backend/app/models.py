from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, JsonColumn


class Report(Base):
    """One analysis: the code as submitted, every issue found, and the suggested fix."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(Text)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JsonColumn, default=list)
    fixed: Mapped[str] = mapped_column(Text, default="")
    # "model" if the LLM's fixed file was used, "rules" if only rule fixes were applied
    fixed_source: Mapped[str] = mapped_column(String(10), default="rules")
    model: Mapped[str] = mapped_column(String(100), default="")
    # complete · partial (the AI step failed or was cut off) · static (no AI configured)
    status: Mapped[str] = mapped_column(String(10), default="complete")
    ai_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
