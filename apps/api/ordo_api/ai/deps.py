from functools import lru_cache

from ..config import get_settings
from .gateway import AiGateway, build_providers
from .routing import load_routing


@lru_cache
def get_ai_gateway() -> AiGateway:
    settings = get_settings()
    providers = build_providers(settings)
    routing = load_routing(settings.AI_ROUTING)
    return AiGateway(providers, routing, data_residency=settings.DATA_RESIDENCY)
