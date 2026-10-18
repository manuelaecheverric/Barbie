"""Validación de los tokens de Supabase Auth.

Cada request a /api/* debe traer el header `Authorization: Bearer <access_token>`.
El token lo emite Supabase cuando el usuario inicia sesión en el frontend.
"""
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None = None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache
def _jwks_client(supabase_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json", cache_keys=True)


def decode_token(token: str, settings: Settings) -> dict:
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
    except jwt.PyJWTError as exc:
        raise _unauthorized("Token inválido.") from exc

    try:
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise _unauthorized("El servidor no tiene configurado SUPABASE_JWT_SECRET.")
            return jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")

        if not settings.supabase_url:
            raise _unauthorized("El servidor no tiene configurado SUPABASE_URL.")
        signing_key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=["ES256", "RS256"], audience="authenticated")
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Tu sesión expiró. Inicia sesión de nuevo.") from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized("Token inválido.") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Debes iniciar sesión para usar la API.")
    claims = decode_token(credentials.credentials, settings)
    user_id = claims.get("sub")
    if not user_id:
        raise _unauthorized("Token sin usuario.")
    return CurrentUser(id=user_id, email=claims.get("email"))
