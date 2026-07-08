from fastapi import APIRouter

from py_core_api.api.v1.endpoints import reports

api_router = APIRouter()
api_router.include_router(reports.router)
