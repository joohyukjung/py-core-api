from typing import Annotated

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from py_core_api.schemas.reports import (
    ReportDocumentRequest,
    ReportDraftRequest,
    ReportDraftResponse,
)
from py_core_api.services.claude_client import get_anthropic_client
from py_core_api.services.report_service import (
    ReportGenerationError,
    generate_document,
    generate_draft,
)

router = APIRouter(prefix="/reports", tags=["reports"])

_DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


@router.post("/draft", response_model=ReportDraftResponse)
async def create_report_draft(
    request: ReportDraftRequest,
    client: Annotated[AsyncAnthropic, Depends(get_anthropic_client)],
) -> ReportDraftResponse:
    """리포트 본문 초안을 텍스트로 빠르게 생성한다 (파일 생성 없음)."""
    try:
        return await generate_draft(client, request)
    except ReportGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.post("/document")
async def create_report_document(
    request: ReportDocumentRequest,
    client: Annotated[AsyncAnthropic, Depends(get_anthropic_client)],
) -> Response:
    """승인된 초안(content)을 실제 docx 파일로 변환해 반환한다."""
    try:
        report = await generate_document(client, request)
    except ReportGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return Response(
        content=report.content,
        media_type=_DOCX_MIME_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{report.filename}"',
            "X-Input-Tokens": str(report.input_tokens),
            "X-Output-Tokens": str(report.output_tokens),
        },
    )
