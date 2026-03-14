"""FastAPI application — User authentication system with JWT tokens and role-based permissions"""
from __future__ import annotations

from fastapi import FastAPI

from routers.user import router as user_router
from routers.auth import router as auth_router
from routers.token import router as token_router
from routers.role import router as role_router
from routers.permission import router as permission_router

app = FastAPI(title="User authentication system with JWT tokens and role-based permissions", version="0.1.0")


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}

app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(auth_router, prefix="/auths", tags=["auths"])
app.include_router(token_router, prefix="/tokens", tags=["tokens"])
app.include_router(role_router, prefix="/roles", tags=["roles"])
app.include_router(permission_router, prefix="/permissions", tags=["permissions"])
