from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai.deps import get_ai_gateway
from ..ai.gateway import AiGateway
from ..auth.deps import get_current_user
from ..db import get_db
from ..models.search import SearchClick
from ..models.user import User
from ..schemas.search import SearchClickRequest, SearchResponse, SearchResultOut
from ..search.service import search as run_search

router = APIRouter(tags=["search"])


def _get_gateway_or_none() -> AiGateway | None:
    try:
        return get_ai_gateway()
    except Exception:  # noqa: BLE001 — поиск по тексту должен работать даже без настроенного ИИ
        return None


@router.get("/search", response_model=SearchResponse)
async def search_endpoint(
    q: str = Query(default="", max_length=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    gateway = _get_gateway_or_none()
    hits = await run_search(db, gateway, user.id, q)
    return SearchResponse(query=q, results=[SearchResultOut(**hit.__dict__) for hit in hits])


@router.post("/search/click", status_code=204)
async def register_click(
    payload: SearchClickRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    db.add(
        SearchClick(
            user_id=user.id, query=payload.query, result_type=payload.result_type, result_id=payload.result_id
        )
    )
    await db.commit()
