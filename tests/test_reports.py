from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from py_core_api.main import app
from py_core_api.services.claude_client import get_anthropic_client

_FAKE_DOCX_BYTES = b"fake docx bytes"


def _fake_draft_message() -> SimpleNamespace:
    raw = (
        '{"suggested_title": "semiconductor_2026_outlook", '
        '"content": "2026년 반도체 시장 전망 리포트 본문..."}'
    )
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=raw)],
        model="claude-sonnet-5",
        usage=SimpleNamespace(input_tokens=15, output_tokens=120),
    )


def _fake_document_message() -> SimpleNamespace:
    bash_result = SimpleNamespace(
        type="bash_code_execution_result",
        content=[SimpleNamespace(file_id="file_abc123")],
    )
    tool_result_block = SimpleNamespace(
        type="bash_code_execution_tool_result",
        content=bash_result,
    )
    return SimpleNamespace(
        content=[tool_result_block],
        model="claude-sonnet-5",
        usage=SimpleNamespace(input_tokens=10, output_tokens=20),
    )


class _FakeFileDownloadResponse:
    async def read(self) -> bytes:
        return _FAKE_DOCX_BYTES


@pytest.fixture
def client() -> Iterator[TestClient]:
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(return_value=_fake_draft_message())),
        beta=SimpleNamespace(
            messages=SimpleNamespace(
                create=AsyncMock(return_value=_fake_document_message())
            ),
            files=SimpleNamespace(
                retrieve_metadata=AsyncMock(
                    return_value=SimpleNamespace(
                        filename="semiconductor_2026_outlook.docx"
                    )
                ),
                download=AsyncMock(return_value=_FakeFileDownloadResponse()),
            ),
        ),
    )
    app.dependency_overrides[get_anthropic_client] = lambda: fake_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_report_draft(client: TestClient) -> None:
    response = client.post(
        "/v1/reports/draft", json={"prompt": "26년 반도체 시장 전망 리포트로 작성해줘"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["suggested_title"] == "semiconductor_2026_outlook"
    assert "반도체" in body["content"]
    assert body["input_tokens"] == 15
    assert body["output_tokens"] == 120


def test_create_report_draft_requires_prompt(client: TestClient) -> None:
    response = client.post("/v1/reports/draft", json={"prompt": ""})

    assert response.status_code == 422


def test_create_report_document(client: TestClient) -> None:
    response = client.post(
        "/v1/reports/document",
        json={
            "title": "semiconductor_2026_outlook",
            "content": "2026년 반도체 시장 전망 리포트 본문...",
        },
    )

    assert response.status_code == 200
    assert response.content == _FAKE_DOCX_BYTES
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert (
        'filename="semiconductor_2026_outlook.docx"'
        in response.headers["content-disposition"]
    )
    assert response.headers["x-input-tokens"] == "10"
    assert response.headers["x-output-tokens"] == "20"


def test_create_report_document_requires_content(client: TestClient) -> None:
    response = client.post(
        "/v1/reports/document", json={"title": "empty", "content": ""}
    )

    assert response.status_code == 422
