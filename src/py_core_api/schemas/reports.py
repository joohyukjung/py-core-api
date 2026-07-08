from typing import Literal

from pydantic import BaseModel, Field


class ReportDraftRequest(BaseModel):
    """리포트 초안(텍스트) 생성 요청 스키마."""

    prompt: str = Field(..., min_length=1, description="리포트 생성을 위한 프롬프트")
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Claude 응답 최대 토큰 수. 미지정 시 설정값(anthropic_max_tokens) 사용"
        ),
    )


class ReportDraftResponse(BaseModel):
    """리포트 초안(텍스트) 생성 응답 스키마."""

    content: str = Field(..., description="Claude가 생성한 리포트 본문(텍스트)")
    suggested_title: str = Field(..., description="문서 파일명으로 쓰기 좋은 제안 값")
    input_tokens: int = Field(..., description="입력 토큰 수")
    output_tokens: int = Field(..., description="출력 토큰 수")


class ReportDocumentRequest(BaseModel):
    """승인된 초안을 실제 문서 파일로 변환하는 요청 스키마."""

    title: str = Field(..., min_length=1, description="문서 파일명(확장자 제외)")
    content: str = Field(
        ..., min_length=1, description="문서에 그대로 포함할 리포트 본문(승인된 초안)"
    )
    format: Literal["docx"] = Field(
        default="docx", description="문서 형식. 현재는 docx만 지원"
    )
