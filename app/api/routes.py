from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import PrincipalDep, require_staff
from app.models import TicketCategory
from app.rag.graph import run_how_it_works

router = APIRouter(prefix="/api")


class AskBody(BaseModel):
    category: TicketCategory
    query: str = Field(min_length=1)


class TicketCreateBody(BaseModel):
    category: TicketCategory
    query: str = Field(min_length=1)
    url: str | None = None
    rag_run_id: UUID | None = None


class MessageBody(BaseModel):
    body: str = Field(min_length=1)


@router.get("/me")
def me(principal: PrincipalDep) -> dict:
    return principal.model_dump()


@router.post("/ask")
def ask(body: AskBody, principal: PrincipalDep) -> dict:
    if body.category != TicketCategory.how_it_works:
        return {"skip_rag": True, "category": body.category.value}
    return run_how_it_works(query=body.query, user_id=principal.user_id)


@router.post("/tickets")
def create_ticket(_body: TicketCreateBody, _principal: PrincipalDep) -> dict:
    return {"detail": "Ticket create not implemented yet."}


@router.get("/tickets")
def list_tickets(
    principal: PrincipalDep,
    status: Literal["open", "closed"] | None = None,
) -> dict:
    return {
        "items": [],
        "scope": "all" if principal.is_staff else "own",
        "status": status,
    }


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: UUID, _principal: PrincipalDep) -> dict:
    return {"id": str(ticket_id), "detail": "Ticket get not implemented yet."}


@router.post("/tickets/{ticket_id}/messages")
def post_message(
    ticket_id: UUID, _body: MessageBody, _principal: PrincipalDep
) -> dict:
    return {"id": str(ticket_id), "detail": "Message post not implemented yet."}


@router.post("/tickets/{ticket_id}/close")
def close_ticket(
    ticket_id: UUID, principal: PrincipalDep = Depends(require_staff)
) -> dict:
    return {"id": str(ticket_id), "closed_by": principal.user_id}


@router.get("/articles")
def list_articles(_principal: PrincipalDep = Depends(require_staff)) -> dict:
    return {"items": []}
