import os
import tempfile

# Settings are read at import time, so point everything at throwaway locations first
_tmp = tempfile.mkdtemp()
os.environ.update(
    DATABASE_URL=f"sqlite:///{_tmp}/test.db",
    DATA_DIR=_tmp,
    APP_PASSWORD="test-pass",
    LLM_API_KEY="test-key",
    GROQ_API_KEY="",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.messages import AIMessageChunk  # noqa: E402

from app import review  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


class FakeStreamingChat:
    """Streams a canned reply in small, awkwardly sized pieces, like a real model."""

    def __init__(self, reply: str, size: int = 7, error: Exception | None = None):
        self.reply, self.size, self.error = reply, size, error
        self.calls: list = []

    def stream(self, messages):
        self.calls.append(messages)
        for i in range(0, len(self.reply), self.size):
            yield AIMessageChunk(content=self.reply[i : i + self.size])
        if self.error:
            raise self.error


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def owner(client):
    assert client.post("/api/auth/login", json={"password": "test-pass"}).status_code == 200
    return client


@pytest.fixture
def fake_llm(monkeypatch):
    def install(reply: str, **kw) -> FakeStreamingChat:
        fake = FakeStreamingChat(reply, **kw)
        monkeypatch.setattr(review, "chat_model", lambda: fake)
        return fake

    return install
