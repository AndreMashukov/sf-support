from typing import Annotated

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel


class Principal(BaseModel):
    user_id: str
    email: str
    is_staff: bool


def get_principal(
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    # Scaffold: replace with Firebase Admin verify_id_token.
    raise HTTPException(
        status_code=501,
        detail="Firebase ID token verification is not wired yet.",
    )


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def require_staff(principal: PrincipalDep) -> Principal:
    if not principal.is_staff:
        raise HTTPException(status_code=403, detail="Staff only")
    return principal
