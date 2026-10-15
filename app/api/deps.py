import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]
_api_key = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(key: Annotated[str | None, Security(_api_key)]) -> None:
    valid = get_settings().api_keys
    if not key or not any(secrets.compare_digest(key, v) for v in valid):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key")
