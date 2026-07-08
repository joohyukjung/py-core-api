from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/")
def create_report() -> dict[str, str]:
    # TODO: settings.anthropic_api_key를 사용해 Claude API 호출 로직 구현 예정
    return {"status": "not_implemented"}
