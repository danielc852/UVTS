from fastapi import APIRouter

from uvts_api.api.routes import (
    documents,
    evaluations,
    health,
    question_configuration,
    questions,
    reports,
    sessions,
    tests,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(sessions.router)
api_router.include_router(tests.router)
api_router.include_router(documents.router)
api_router.include_router(questions.router)
api_router.include_router(evaluations.router)
api_router.include_router(reports.router)
api_router.include_router(question_configuration.router)
