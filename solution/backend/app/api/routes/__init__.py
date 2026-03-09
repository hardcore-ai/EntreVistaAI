from .auth import router as auth_router
from .campaigns import router as campaigns_router
from .candidates import router as candidates_router
from .evaluations import router as evaluations_router

__all__ = ["auth_router", "campaigns_router", "candidates_router", "evaluations_router"]
