from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.balances import router as balances_router
from app.routers.expenses import router as expenses_router
from app.routers.groups import router as groups_router
from app.routers.settlements import router as settlements_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Split Money Application API",
)


# ==========================================================
# CORS
# ==========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================
# ROUTERS
# ==========================================================

app.include_router(groups_router, prefix="/api")
app.include_router(expenses_router, prefix="/api")
app.include_router(balances_router, prefix="/api")
app.include_router(settlements_router, prefix="/api")


# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():
    return {
        "message": "Split Money API is running",
        "version": settings.APP_VERSION,
    }


# ==========================================================
# HEALTH CHECK
# ==========================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }