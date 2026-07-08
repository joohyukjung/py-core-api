from functools import lru_cache

from anthropic import AsyncAnthropic

from py_core_api.core.config import settings


@lru_cache
def get_anthropic_client() -> AsyncAnthropic:
    """AsyncAnthropic 클라이언트 싱글턴.

    FastAPI Depends()로 주입되며, 프로세스 생애주기 동안 하나의 httpx 커넥션 풀을
    재사용한다.
    """
    return AsyncAnthropic(api_key=settings.anthropic_api_key)
