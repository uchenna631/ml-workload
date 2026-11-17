import asyncio

import httpx
import pytest

from app.main import app


def request(method, path, **kwargs):
    async def send():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_liveness():
    response = request("GET", "/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"prompt": ""},
        {"prompt": "x" * 4001},
    ],
)
def test_generate_rejects_invalid_prompts(payload):
    response = request("POST", "/generate", json=payload)

    assert response.status_code == 422