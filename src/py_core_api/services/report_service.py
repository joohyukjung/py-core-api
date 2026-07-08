import json
import logging
from dataclasses import dataclass

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
)
from anthropic.types.beta import BetaCodeExecutionTool20250825Param

from py_core_api.core.config import settings
from py_core_api.schemas.reports import (
    ReportDocumentRequest,
    ReportDraftRequest,
    ReportDraftResponse,
)

logger = logging.getLogger("py_core_api.services.report")

_FILES_API_BETA = "files-api-2025-04-14"
_CODE_EXECUTION_TOOL: BetaCodeExecutionTool20250825Param = {
    "type": "code_execution_20250825",
    "name": "code_execution",
}
_DEFAULT_TITLE = "report"


class ReportGenerationError(Exception):
    """Claude API 호출 실패 시 발생하는 예외."""


class ReportFileNotFoundError(ReportGenerationError):
    """Claude 응답 안에서 생성된 .docx 파일을 찾지 못한 경우."""


@dataclass
class GeneratedReport:
    """생성된 리포트 파일과 부가 정보."""

    content: bytes
    filename: str
    input_tokens: int
    output_tokens: int


def _build_draft_prompt(request: ReportDraftRequest) -> str:
    return (
        "아래 요청에 맞는 리포트 본문을 작성해줘. 응답은 반드시 아래 형식의 JSON "
        "하나만 출력하고, 코드블록 표시나 다른 설명 없이 순수 JSON으로만 답해줘.\n"
        '{"suggested_title": "영문 소문자와 언더스코어(_)로 된 파일명 슬러그 '
        '(확장자 제외, 공백/한글 금지)", "content": "리포트 본문 전체"}\n\n'
        f"요청 내용: {request.prompt}"
    )


def _parse_draft_json(raw_text: str) -> tuple[str, str]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
        return (
            str(data.get("suggested_title") or _DEFAULT_TITLE),
            str(data.get("content") or raw_text),
        )
    except (json.JSONDecodeError, AttributeError):
        logger.warning("draft_json_parse_failed")
        return _DEFAULT_TITLE, raw_text


async def generate_draft(
    client: AsyncAnthropic, request: ReportDraftRequest
) -> ReportDraftResponse:
    """리포트 본문(텍스트) 초안을 빠르게 생성한다. code execution은 사용하지 않는다."""
    try:
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=request.max_tokens or settings.anthropic_max_tokens,
            messages=[{"role": "user", "content": _build_draft_prompt(request)}],
        )
    except APITimeoutError as exc:
        logger.exception("claude_api_timeout")
        raise ReportGenerationError("Claude API 요청이 시간 초과되었습니다.") from exc
    except APIConnectionError as exc:
        logger.exception("claude_api_connection_error")
        raise ReportGenerationError("Claude API에 연결할 수 없습니다.") from exc
    except APIStatusError as exc:
        logger.exception(
            "claude_api_status_error", extra={"status_code": exc.status_code}
        )
        raise ReportGenerationError(
            f"Claude API가 오류를 반환했습니다 (status={exc.status_code})."
        ) from exc

    raw_text = "".join(block.text for block in message.content if block.type == "text")
    suggested_title, content = _parse_draft_json(raw_text)

    return ReportDraftResponse(
        content=content,
        suggested_title=suggested_title,
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
    )


def _build_document_prompt(request: ReportDocumentRequest) -> str:
    return (
        "code execution 도구(bash)를 사용해서 python-docx로 아래 내용을 그대로 "
        f"Word 문서로 만들어줘. 파일명은 반드시 '{request.title}.docx'로 워크스페이스 "
        "루트에 저장하고, 적절한 제목/문단 스타일을 적용해줘. 텍스트로만 답하지 말고 "
        "실제 .docx 파일을 만들어야 해. 본문 내용을 요약하거나 바꾸지 말고 그대로 "
        "문서에 담아줘.\n\n"
        f"문서에 들어갈 내용:\n{request.content}"
    )


async def _find_docx_file(client: AsyncAnthropic, message) -> tuple[str, str]:
    """응답에서 생성된 파일 중 .docx 확장자 파일의 (file_id, filename)을 찾는다."""
    candidate_ids: list[str] = []
    for block in message.content:
        if block.type != "bash_code_execution_tool_result":
            continue
        result = block.content
        if result.type != "bash_code_execution_result":
            continue
        candidate_ids.extend(output.file_id for output in result.content)

    for file_id in candidate_ids:
        metadata = await client.beta.files.retrieve_metadata(file_id)
        if metadata.filename.endswith(".docx"):
            return file_id, metadata.filename

    raise ReportFileNotFoundError("생성된 .docx 파일을 찾을 수 없습니다.")


async def generate_document(
    client: AsyncAnthropic, request: ReportDocumentRequest
) -> GeneratedReport:
    """승인된 초안(content)을 code execution + Files API로 실제 docx 파일로 만든다."""
    try:
        message = await client.beta.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            betas=[_FILES_API_BETA],
            messages=[{"role": "user", "content": _build_document_prompt(request)}],
            tools=[_CODE_EXECUTION_TOOL],
        )
    except APITimeoutError as exc:
        logger.exception("claude_api_timeout")
        raise ReportGenerationError("Claude API 요청이 시간 초과되었습니다.") from exc
    except APIConnectionError as exc:
        logger.exception("claude_api_connection_error")
        raise ReportGenerationError("Claude API에 연결할 수 없습니다.") from exc
    except APIStatusError as exc:
        logger.exception(
            "claude_api_status_error", extra={"status_code": exc.status_code}
        )
        raise ReportGenerationError(
            f"Claude API가 오류를 반환했습니다 (status={exc.status_code})."
        ) from exc

    file_id, filename = await _find_docx_file(client, message)

    file_response = await client.beta.files.download(file_id)
    content = await file_response.read()

    return GeneratedReport(
        content=content,
        filename=filename,
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
    )
