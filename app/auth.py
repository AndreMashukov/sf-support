from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException
from firebase_admin import auth as firebase_auth
from firebase_admin.auth import (
    CertificateFetchError,
    ExpiredIdTokenError,
    InvalidIdTokenError,
    RevokedIdTokenError,
)
from pydantic import BaseModel

from app.firebase_admin_app import init_firebase


class Principal(BaseModel):
    user_id: str
    email: str
    is_staff: bool


def verify_id_token(id_token: str) -> dict[str, Any]:
    init_firebase()
    return firebase_auth.verify_id_token(id_token)


def principal_from_claims(decoded: dict[str, Any]) -> Principal:
    provider = decoded.get("firebase", {}).get("sign_in_provider")
    if provider == "anonymous":
        raise HTTPException(
            status_code=401,
            detail="Anonymous sign-in is not allowed",
        )
    user_id = decoded.get("uid")
    email = decoded.get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=401,
            detail="Signed-in account has no uid or email",
        )
    return Principal(
        user_id=user_id,
        email=email,
        is_staff=decoded.get("role") == "admin",
    )


def get_principal(
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    try:
        decoded = verify_id_token(token)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (
        ExpiredIdTokenError,
        InvalidIdTokenError,
        RevokedIdTokenError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=401, detail="Invalid ID token") from exc
    except CertificateFetchError as exc:
        raise HTTPException(
            status_code=503,
            detail="Firebase certificate fetch failed",
        ) from exc
    return principal_from_claims(decoded)


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def require_staff(principal: PrincipalDep) -> Principal:
    if not principal.is_staff:
        raise HTTPException(status_code=403, detail="Staff only")
    return principal


StaffDep = Annotated[Principal, Depends(require_staff)]
