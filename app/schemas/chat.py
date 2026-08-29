"""Pydantic schemas for AI chat request and response payloads."""

from pydantic import BaseModel, Field

from app.schemas.listing import ListingResponse


class ChatRequest(BaseModel):
    """Payload for POST /chat."""

    conversation_id: int | None = Field(
        None,
        description="ID of an existing conversation to continue, or null to start a new one",
    )
    message: str = Field(..., min_length=1, description="Customer chat message")
    polygon: list[list[float]] | None = Field(
        None,
        description=(
            "Optional hand-drawn bounding polygon as [[lat, lng], ...] "
            "to restrict RAG search candidates"
        ),
    )


class ChatResponse(BaseModel):
    """Response payload for POST /chat matching AGENTS.md §3 specification."""

    reply: str = Field(..., description="AI assistant conversational response")
    listings: list[ListingResponse] = Field(
        default_factory=list,
        description="Listings retrieved by RAG grounding relevant to the chat context",
    )
