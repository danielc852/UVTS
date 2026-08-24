from fastapi import APIRouter

from uvts_api.api.routes import documents, health, sessions, tests

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(sessions.router)
api_router.include_router(tests.router)
api_router.include_router(documents.router)
