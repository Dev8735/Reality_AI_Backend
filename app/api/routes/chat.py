"""Chat route — POST /chat (AI RAG orchestration + conversation tracking)."""

from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.listing import Listing
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
)
from app.schemas.listing import ListingResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])


# ---------------------------------------------------------------------------
# AI Layer Fallback Helpers
# ---------------------------------------------------------------------------


def _get_polygon_candidates(polygon: list[list[float]] | None) -> list[int] | None:
    """Call Person 1's boundary filter if available."""
    if not polygon:
        return None
    try:
        from ai.rag.boundary_filter import get_candidates  # type: ignore[import-untyped]

        return get_candidates(polygon)
    except ImportError:
        logger.warning(
            "ai.rag.boundary_filter not available — candidate filtering skipped"
        )
        return None
    except Exception as exc:
        logger.error("Error executing boundary candidate filter: %s", exc)
        return None


def _retrieve_listings(
    db: Session, message: str, candidate_ids: list[int] | None
) -> list[Listing]:
    """Call Person 1's RAG retriever if available, else query local DB."""
    try:
        from ai.rag.retriever import search  # type: ignore[import-untyped]

        return search(message, candidate_ids=candidate_ids, top_k=5)
    except ImportError:
        logger.warning("ai.rag.retriever not available — falling back to DB query")
        query = db.query(Listing)
        if candidate_ids is not None:
            query = query.filter(Listing.id.in_(candidate_ids))
        return query.limit(5).all()
    except Exception as exc:
        logger.error("Error executing RAG retriever: %s", exc)
        query = db.query(Listing)
        if candidate_ids is not None:
            query = query.filter(Listing.id.in_(candidate_ids))
        return query.limit(5).all()


def _generate_response(
    message: str, listings: list[Listing], history: list[dict]
) -> str:
    """Generate reply string — uses placeholder text when PLACEHOLDER_MODE is True."""
    if settings.PLACEHOLDER_MODE:
        if not listings:
            return (
                f"[PLACEHOLDER MODE] I reviewed your query '{message}', "
                "but found no matching properties in Surat."
            )
        titles = ", ".join(f"'{l.title}'" for l in listings)
        return (
            f"[PLACEHOLDER MODE] Based on your query '{message}', "
            f"here are relevant properties in Surat: {titles}."
        )

    try:
        from ai.inference import generate_response  # type: ignore[import-untyped]

        return generate_response(message, listings, history)
    except ImportError:
        logger.warning(
            "ai.inference not available — returning fallback response despite PLACEHOLDER_MODE=False"
        )
        titles = ", ".join(f"'{l.title}'" for l in listings) if listings else "none"
        return f"Found relevant listings: {titles}."
    except Exception as exc:
        logger.error("Error invoking AI inference model: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI inference engine failed to process request",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Customer chat message — orchestrates RAG and LLM inference",
)
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChatResponse:
    if not isinstance(current_user, Customer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can initiate or participate in chat sessions",
        )

    # 1. Load or create Conversation
    if body.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == body.conversation_id,
                Conversation.customer_id == current_user.id,
            )
            .first()
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {body.conversation_id} not found",
            )
    else:
        conversation = Conversation(customer_id=current_user.id, messages=[])
        db.add(conversation)
        db.flush()

    messages = conversation.messages or []

    # 2. Append user message
    now_iso = datetime.now(timezone.utc).isoformat()
    user_msg = {"role": "user", "content": body.message, "timestamp": now_iso}
    messages.append(user_msg)

    # 3 & 4. Filter candidates and retrieve listings
    candidate_ids = _get_polygon_candidates(body.polygon)
    listings = _retrieve_listings(db, body.message, candidate_ids)

    # Record leads for retrieved listings (tracks customer inquiry per listing)
    for l in listings:
        existing_lead = (
            db.query(Lead)
            .filter(Lead.listing_id == l.id, Lead.customer_id == current_user.id)
            .first()
        )
        if not existing_lead:
            db.add(Lead(listing_id=l.id, customer_id=current_user.id))

    # 5. Generate assistant reply
    reply_text = _generate_response(body.message, listings, messages)

    # 6. Append assistant message (include listing IDs for history recall)
    assistant_msg = {
        "role": "assistant",
        "content": reply_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "listing_ids": [l.id for l in listings],
    }
    messages.append(assistant_msg)

    conversation.messages = messages
    flag_modified(conversation, "messages")
    db.commit()

    listing_responses = [
        ListingResponse.model_validate(l) for l in listings
    ]

    return ChatResponse(
        conversation_id=conversation.id,
        reply=reply_text,
        listings=listing_responses,
    )


@router.get(
    "/chat/{conversation_id}",
    response_model=ChatHistoryResponse,
    summary="Fetch the full chat history for a conversation",
)
def get_chat_history(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChatHistoryResponse:
    """Return the complete message history for the given conversation.

    Only the owning customer may access their conversation.
    """
    if not isinstance(current_user, Customer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can view chat history",
        )

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.customer_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    raw_messages = conversation.messages or []

    # Collect all listing IDs referenced by assistant messages (handling int or string IDs)
    all_listing_ids: set[int] = set()
    for msg in raw_messages:
        lids = msg.get("listing_ids") or []
        for lid in lids:
            try:
                all_listing_ids.add(int(lid))
            except (ValueError, TypeError):
                pass

    # Batch-load listings from DB in a single query
    listings_map: dict[int, ListingResponse] = {}
    if all_listing_ids:
        db_listings = (
            db.query(Listing).filter(Listing.id.in_(all_listing_ids)).all()
        )
        for l in db_listings:
            listings_map[l.id] = ListingResponse.model_validate(l)

    parsed_messages: list[ChatMessageResponse] = []

    for msg in raw_messages:
        role = msg.get("role", "user")
        sender = role if role in ("user", "assistant") else "user"
        content = msg.get("content", "")
        ts_raw = msg.get("timestamp")

        # Parse timestamp — stored as ISO-8601 string
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw)
            except (ValueError, TypeError):
                ts = datetime.now(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)

        # Attach listings for assistant messages using stored IDs
        msg_lids = []
        for lid in msg.get("listing_ids", []):
            try:
                msg_lids.append(int(lid))
            except (ValueError, TypeError):
                pass

        msg_listings = [
            listings_map[lid]
            for lid in msg_lids
            if lid in listings_map
        ]

        parsed_messages.append(
            ChatMessageResponse(
                sender=sender,
                message=content,
                timestamp=ts,
                listings=msg_listings,
            )
        )

    # Return top-level listings as well so frontend gets all conversation listings
    return ChatHistoryResponse(
        conversation_id=conversation.id,
        user_id=conversation.customer_id,
        messages=parsed_messages,
        listings=list(listings_map.values()),
    )
