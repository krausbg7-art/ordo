# Ordo — дела в порядке

ИИ-секретарь руководителя: приложение и веб-версия. Загружайте файлы,
подключайте почту и календари — Ordo ищет по всему с первых букв,
извлекает задачи из материалов и ведёт их на канбан-доске со статусами,
как в CRM. ИИ — модели Kimi (Moonshot AI) и Qwen (Alibaba) через единый шлюз.

См. [`PLAN.md`](./PLAN.md) — архитектура, модели данных, порядок реализации.

## Стек

- `apps/api` — FastAPI (Python 3.12), SQLAlchemy 2, Alembic, Pydantic v2.
- `apps/worker` — фоновые задачи на arq + Redis (извлечение текста, ИИ,
  синхронизация календарей).
- `apps/web` — Next.js, TypeScript, Tailwind, dnd-kit.
- PostgreSQL 16 (`pgvector`, `pg_trgm`), Redis, MinIO (S3-совместимое хранилище).

## Быстрый старт

```bash
cp .env.example .env
# при необходимости отредактируйте .env (ключи ИИ, DATA_RESIDENCY и т.д.)
docker compose up --build
```

После старта:

- API: http://localhost:8000 (`/healthz`, `/docs`)
- Веб: http://localhost:3000
- MinIO консоль: http://localhost:9001

Миграции применяются автоматически сервисом `migrate` перед стартом `api`.

## Переменные окружения

Все переменные описаны в [`.env.example`](./.env.example). Ключевые:

- `DATA_RESIDENCY=ru` — запросы с пользовательскими данными идут только на
  `selfhost` (собственный vLLM-сервер); `DATA_RESIDENCY=dev` разрешает
  облачные `kimi`/`qwen`.
- `MOONSHOT_*`, `DASHSCOPE_*`, `SELFHOST_*` — ключи и модели провайдеров ИИ.
- `AI_ROUTING` — путь к `config/ai_routing.yaml`, где задан выбор провайдера
  по типу задачи.

## Смена модели / провайдера ИИ

1. Отредактируйте `KIMI_MODEL`, `QWEN_MODEL`, `QWEN_VL_MODEL` или
   `SELFHOST_MODEL` в `.env`.
2. Проверьте, что модель ещё существует у провайдера:
   ```bash
   cd apps/api && python -m ordo_api.ai.check_models
   ```
3. При необходимости измените маршрутизацию по типам задач в
   `config/ai_routing.yaml` — код менять не нужно.

## Подключение собственного vLLM-сервера

`SELFHOST_BASE_URL` и `SELFHOST_MODEL` указывают на любой OpenAI-совместимый
эндпоинт (например, vLLM с `--served-model-name`). При `DATA_RESIDENCY=ru`
это единственный провайдер, к которому уходят запросы с содержимым
пользовательских данных.

## Разработка

```bash
# API
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest

# Worker
cd apps/worker
pip install -e ".[dev]"
pytest

# Веб
cd apps/web
npm install
npm run dev
```

`make eval` — прогоняет фикстуры из `tests/fixtures/` через реальную модель
(если заданы ключи ИИ) и печатает точность извлечения задач.

## Безопасность

- Пароли — argon2, сессии — JWT в httpOnly cookie.
- Все данные изолированы по `user_id`.
- Ключи ИИ никогда не попадают на фронтенд.
- Логи структурированные, без содержимого пользовательских данных.
- Удаление аккаунта удаляет файлы, фрагменты и логи ИИ-вызовов.
