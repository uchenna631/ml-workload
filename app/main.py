
import os
import httpx

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="AI Inference Gateway")

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://ollama.ai-platform.svc.cluster.local:11434"
)

MODEL = os.getenv("MODEL", "qwen2.5:0.5b")


class Prompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(
                f"{OLLAMA_URL}/api/tags"
            )
            response.raise_for_status()

            models = response.json().get("models", [])
            names = {m["name"] for m in models}

            if MODEL not in names:
                raise HTTPException(
                    status_code=503,
                    detail="Model not available"
                )

            return {"status": "ready"}

    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail="Ollama unavailable"
        )


@app.post("/generate")
async def generate(data: Prompt):
    try:
        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": data.prompt,
                    "stream": False
                }
            )

            response.raise_for_status()

            return {
                "answer": response.json()["response"]
            }

    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Inference backend failure"
        )
