# PLAN — Ordo, MVP сервера и веб-версии

## Открытые вопросы и решения по умолчанию

1. **Формат JWT** — используем `httpOnly` cookie `ordo_session` с JWT (HS256, `SECRET_KEY` из `.env`), refresh не делаем в MVP (просто увеличенный TTL + `/auth/refresh` эндпоинт-заглушка на будущее).
2. **arq vs Celery** — берём **arq** (проще, async, один Redis, хватает для MVP).
3. **pgvector размерность эмбеддингов** — 1536 (совместимо с большинством OpenAI-совместимых embedding-моделей); в `mock`-провайдере — тоже 1536, детерминированный хэш-вектор.
4. **HEIC** — конвертация через `pillow-heif`, если библиотека недоступна в окружении — файл помечается «не поддерживается» вместо падения.
5. **CalDAV** — используем `caldav` (python) с basic auth (пароль приложения), без реального OAuth Google (только фиче-флаг `GOOGLE_CALENDAR_ENABLED=false` и заглушка роута).
6. **Поиск** — Postgres `pg_trgm` + `tsvector` (`russian` конфиг) для префиксного/полнотекстового, `pgvector` cosine для смыслового при запросе >3 слов. Ранжирование — простая взвешенная сумма (совпадение, клики, давность, час дня), без ML.
7. **Шифрование файлов** — SSE на уровне MinIO/S3 (`ServerSideEncryption`), а не шифрование на уровне приложения (проще и надёжнее для MVP).
8. **Rate limit** — `slowapi` (in-memory/redis) на `/upload` и `/ai/*`.
9. **Мультитенантность** — одна организация = один `user_id`-владелец; `Board` привязана к `user_id` (без команд в MVP, это не в задаче).
10. **Дедупликация предложений** — в MVP по схожести названия (`difflib`), без отдельного эмбеддинг-индекса задач; поле для эмбеддингов уже заложено в `FileChunk`, при необходимости дедуп по эмбеддингам добавляется туда же позже.
11. **MSG-вложения** — через `extract-msg`; если библиотека не смогла разобрать файл, он помечается «не поддерживается» вместо падения воркера.

Там, где задача не уточняет — выбираем разумный вариант и не останавливаемся.

## Структура репозитория

```
ordo/
  apps/
    api/            # FastAPI
      ordo_api/
        main.py
        config.py
        db.py
        models/
        schemas/
        routers/
        auth/
        ai/
        search/
        core/
      alembic/
      tests/
      pyproject.toml
    worker/         # arq worker
      ordo_worker/
        main.py
        tasks/
          extract_text.py
          extract_tasks.py
          calendar_sync.py
      tests/
      pyproject.toml
    web/            # Next.js + TS + Tailwind + dnd-kit
      app/
      components/
      lib/
      tests/
  packages/
    shared/         # общие Pydantic-схемы/типы, если понадобится
  config/
    ai_routing.yaml
  tests/
    fixtures/
  .github/workflows/ci.yml
  docker-compose.yml
  .env.example
  Makefile
  README.md
```

## Модели данных (SQLAlchemy 2, общие для api/worker через shared package `ordo_api.models`)

- `User(id, email, password_hash, created_at)`
- `Board(id, user_id, name, created_at)`
- `Status(id, board_id, name, order, color)`
- `Task(id, board_id, status_id, title, description, priority, due_date, person, source_type, source_ref, position, created_by, created_at, updated_at)`
- `File(id, user_id, filename, content_type, size, s3_key, status, error, created_at)`
- `FileChunk(id, file_id, text, embedding vector(1536), chunk_index)`
- `TaskSuggestion(id, user_id, file_id, title, due_date, priority, person, quote, status, dedup_of_task_id, created_at)`
- `CalendarAccount(id, user_id, kind[ics|caldav|google], url, username, secret_ref, enabled, last_synced_at)`
- `CalendarEvent(id, calendar_account_id, uid, title, start_at, end_at, description, location, raw)`
- `AiCallLog(id, user_id, provider, model, task_type, input_tokens, output_tokens, duration_ms, status, created_at)`
- `SearchClick(id, user_id, query, result_type, result_id, created_at)`

## API (основные роуты)

- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- `GET/POST /boards`, `GET/PATCH /boards/{id}/statuses`, `POST /boards/{id}/statuses/reorder`
- `GET/POST /tasks`, `PATCH /tasks/{id}`, `POST /tasks/{id}/move`, `DELETE /tasks/{id}`
- `GET /today`
- `POST /files` (upload), `GET /files`, `GET /files/{id}`
- `GET /suggestions`, `POST /suggestions/{id}/accept`, `POST /suggestions/{id}/reject`
- `GET/POST /calendars`, `POST /calendars/{id}/sync`, `GET /calendars/{id}/events`, `POST /calendar-events/{id}/to-task`
- `GET /search?q=`
- `GET /healthz`

## Порядок реализации (шаги = коммиты)

1. Скелет монорепо, docker-compose, `.env.example`, конфиг, healthcheck, модели, auth (argon2 + JWT cookie), Alembic-миграция. Тесты auth.
2. Канбан: статусы по умолчанию, CRUD задач, перемещение с транзакцией, фильтры, `/today`. Веб: доска на dnd-kit, модалка задачи, экран «Сегодня».
3. ИИ-шлюз: `LLMProvider`, `OpenAICompatibleProvider`, `mock`, роутинг по `ai_routing.yaml`, резидентность, `AiCallLog`, `check_models`.
4. Приём файлов: загрузка в MinIO, extract-пайплайн в worker по типам, чанки+эмбеддинги, извлечение задач с `quote`-проверкой, дедуп, `TaskSuggestion` UI.
5. Календари: ICS-импорт, CalDAV-синхронизация, экран «Календари», dedup по UID.
6. Поиск: `pg_trgm`+`tsvector`+`pgvector`, эндпоинт, веб-строка поиска.
7. Качество: фикстуры, pytest, Playwright сценарий, `make eval`, CI (GitHub Actions), README.

После каждого шага — коммит с зелёными тестами (где применимо).
