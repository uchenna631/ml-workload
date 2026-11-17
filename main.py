import os
import httpx

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

class Prompt(BaseModel):
    prompt: str

@app.post("/generate")
async def generate(request: Prompt):
    try:
        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "qwen2.5:0.5b",
                    "prompt": request.prompt,
                    "stream": False
                }
            )

            response.raise_for_status()
            result = response.json()

            return {"answer": result["response"]}

    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Inference backend unavailable"
        )