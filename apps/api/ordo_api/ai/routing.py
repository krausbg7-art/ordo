from pathlib import Path

import yaml
from pydantic import BaseModel


class RouteConfig(BaseModel):
    provider: str
    fallback: str | None = None
    max_completion_tokens: int = 1500
    long_input_threshold_chars: int | None = None


class RoutingTable(BaseModel):
    routes: dict[str, RouteConfig]

    def resolve(self, task_type: str) -> RouteConfig:
        if task_type not in self.routes:
            raise KeyError(f"Неизвестный тип задачи ИИ: {task_type}")
        return self.routes[task_type]


def _find_routing_file(configured: str) -> Path:
    direct = Path(configured)
    if direct.exists():
        return direct

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / configured
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"Файл маршрутизации ИИ не найден: {configured} (переменная AI_ROUTING)"
    )


def load_routing(configured_path: str) -> RoutingTable:
    path = _find_routing_file(configured_path)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return RoutingTable.model_validate(data)
