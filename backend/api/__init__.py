from fastapi import APIRouter
from .documents import router as documents_router
from .qa import router as qa_router
from .evaluation import router as evaluation_router

api_router = APIRouter()

api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(qa_router, prefix="/qa", tags=["qa"])
api_router.include_router(evaluation_router, prefix="/evaluation", tags=["evaluation"])

__all__ = ["api_router"]

