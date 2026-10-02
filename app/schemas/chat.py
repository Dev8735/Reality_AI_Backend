"""Pydantic schemas for AI chat request and response payloads."""

from datetime import datetime

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

    conversation_id: int = Field(..., description="ID of the conversation")
    reply: str = Field(..., description="AI assistant conversational response")
    listings: list[ListingResponse] = Field(
        default_factory=list,
        description="Listings retrieved by RAG grounding relevant to the chat context",
    )


class ChatMessageResponse(BaseModel):
    """A single message in the conversation history."""

    sender: str = Field(..., description="'user' or 'assistant'")
    message: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="UTC timestamp")
    listings: list[ListingResponse] = Field(
        default_factory=list,
        description="Listings associated with this message (populated for assistant messages when available)",
    )


class ChatHistoryResponse(BaseModel):
    """Response payload for GET /chat/{conversation_id}."""

    conversation_id: int
    user_id: int
    messages: list[ChatMessageResponse] = Field(
        default_factory=list,
        description="Ordered list of messages in the conversation",
    )
    listings: list[ListingResponse] = Field(
        default_factory=list,
        description="All listings referenced across assistant messages in this conversation",
    )
