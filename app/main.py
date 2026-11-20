
import os
import httpx
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://ollama.ai-platform.svc.cluster.local:11434"
)

MODEL = os.getenv("MODEL", "qwen2.5:0.5b")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(
        base_url=OLLAMA_URL.rstrip("/"),
        timeout=httpx.Timeout(120.0, connect=3.0, pool=3.0),
        limits=httpx.Limits(
            max_connections=20,
            max_keepalive_connections=10,
        ),
    ) as client:
        app.state.ollama_client = client
        yield


app = FastAPI(
    title="AI Inference Gateway",
    lifespan=lifespan,
)


def get_ollama_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.ollama_client

class Prompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness(
    client: httpx.AsyncClient = Depends(get_ollama_client),
    ):
    try:
        response = await client.get("/api/tags", timeout=3.0)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            raise ValueError("Invalid model listing")
        models = payload["models"]
        if any(
            not isinstance(model, dict)
            or not isinstance(model.get("name"), str)
            for model in models
        ):
            raise ValueError("Invalid model listing")
        names = {model["name"] for model in models}

        if MODEL not in names:
            raise HTTPException(
                status_code=503,
                detail="Model not available",
            )

        return {"status": "ready"}
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail="Ollama unavailable"
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="Invalid inference backend response",
        ) from exc


@app.post("/generate")
async def generate(
    data: Prompt,
    client: httpx.AsyncClient = Depends(get_ollama_client),
):
    try:
        response = await client.post(
            "/api/generate",
            json={
                "model": MODEL,
                "prompt": data.prompt,
                "stream": False,
            },
        )
        response.raise_for_status()

        payload = response.json()
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("response"), str)
        ):
            raise ValueError("Invalid backend response")

        return {"answer": payload["response"]}
    
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Inference backend timed out",
        ) from exc
    
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Inference backend failure"
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="Invalid inference backend response",
        ) from exc
