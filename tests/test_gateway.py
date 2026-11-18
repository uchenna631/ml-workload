import asyncio

import httpx
import pytest

from app.main import MODEL, app, get_ollama_client


@pytest.fixture
def mock_ollama():
    def configure(handler):
        async def override_client():
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler),
                base_url="http://ollama",
            ) as client:
                yield client

        app.dependency_overrides[get_ollama_client] = override_client

    yield configure
    app.dependency_overrides.pop(get_ollama_client, None)

@pytest.mark.parametrize("model_available", [True, False])
def test_readiness_checks_model(mock_ollama, model_available):
    def backend(req):
        assert req.method == "GET"
        assert req.url.path == "/api/tags"

        models = [{"name": MODEL}] if model_available else []
        return httpx.Response(200, json={"models": models})

    mock_ollama(backend)

    response = request("GET", "/health/ready")

    if model_available:
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
    else:
        assert response.status_code == 503
        assert response.json()["detail"] == "Model not available"

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