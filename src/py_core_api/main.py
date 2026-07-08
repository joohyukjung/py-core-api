from fastapi import FastAPI

from py_core_api.api import health
from py_core_api.api.v1 import api_router
from py_core_api.core.logging import setup_logging
from py_core_api.core.middleware import log_requests

setup_logging()

app = FastAPI(title="py-core-api")

app.middleware("http")(log_requests)

app.include_router(health.router)
app.include_router(api_router, prefix="/v1")


def main() -> None:
    import uvicorn

    uvicorn.run("py_core_api.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
