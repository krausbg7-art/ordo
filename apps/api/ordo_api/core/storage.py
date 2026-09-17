from functools import lru_cache
from typing import Protocol

import boto3

from ..config import Settings, get_settings


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class S3Storage:
    """S3-совместимое хранилище (MinIO локально; в проде — российский
    провайдер). Шифрование — на уровне бакета (SSE), настраивается
    инфраструктурно, а не в коде приложения."""

    def __init__(self, settings: Settings):
        self.bucket = settings.S3_BUCKET
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)


class InMemoryStorage:
    """Storage-заглушка для тестов — без сети и MinIO."""

    def __init__(self):
        self._data: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._data[key] = data

    def get(self, key: str) -> bytes:
        return self._data[key]

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


@lru_cache
def get_storage() -> ObjectStorage:
    return S3Storage(get_settings())


def get_storage_dependency() -> ObjectStorage:
    """Обёртка для FastAPI Depends — переопределяется в тестах на InMemoryStorage."""
    return get_storage()
