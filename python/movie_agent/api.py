"""HTTP API shared by browser clients and a future iPhone client."""

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langchain_core.runnables import RunnableConfig

from .agent import (
    get_agent,
    tmdb_search_movie,
    tmdb_search_tv,
    tmdb_tv_watch_providers,
    tmdb_watch_providers,
)
from .utils import PROJECT_ROOT

app = FastAPI(title="Where2Stream API", version="1.0.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins if origin.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


async def body_data(request: Request) -> dict[str, Any]:
    """Accept JSON from clients and form data from older callers."""
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        return data
    except (ValueError, UnicodeDecodeError):
        return dict(await request.form())


def required(data: dict[str, Any], name: str) -> Any:
    value = data.get(name)
    if value is None or value == "":
        raise HTTPException(status_code=400, detail=f"{name} parameter is required")
    return value


def required_id(data: dict[str, Any], name: str) -> int:
    try:
        return int(required(data, name))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{name} must be an integer") from None


def provider_response(result: dict[str, Any]) -> dict[str, Any]:
    """Keep the existing browser response shape while the agent uses its table."""
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    if "message" in result:
        return {}
    return {
        kind: [
            {"Type": kind, "Provider": provider, "Country": countries}
            for provider, countries in providers.items()
        ]
        for kind, providers in result.items()
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search-movie")
async def search_movie(request: Request) -> dict[str, Any]:
    data = await body_data(request)
    result = tmdb_search_movie.invoke({
        "title": required(data, "title"),
        "year": data.get("year"),
        "director": data.get("director"),
    })
    if result and "error" in result[0]:
        raise HTTPException(status_code=503, detail=result[0]["error"])
    return {"results": result}


@app.post("/api/watch-providers")
async def watch_providers(request: Request) -> dict[str, Any]:
    data = await body_data(request)
    return provider_response(tmdb_watch_providers.invoke({"movie_id": required_id(data, "movie_id")}))


@app.post("/api/tv-search")
async def search_tv(request: Request) -> dict[str, Any]:
    data = await body_data(request)
    result = tmdb_search_tv.invoke({"title": required(data, "title"), "year": data.get("year")})
    if result and "error" in result[0]:
        raise HTTPException(status_code=503, detail=result[0]["error"])
    return {"results": result}


@app.post("/api/tv-providers")
async def tv_providers(request: Request) -> dict[str, Any]:
    data = await body_data(request)
    return provider_response(tmdb_tv_watch_providers.invoke({"series_id": required_id(data, "series_id")}))


@app.post("/api/agent")
async def agent_chat(request: Request) -> dict[str, str]:
    data = await body_data(request)
    query = str(required(data, "query"))
    conversation_id = str(data.get("conversation_id") or uuid4())
    result = await get_agent().ainvoke(
        {"messages": [("user", query)]},
        config=RunnableConfig(configurable={"thread_id": conversation_id}),
    )
    return {
        "conversation_id": conversation_id,
        "response": str(result["messages"][-1].content),
    }


# When built, the React app can be served by the same process as the API.
DIST_DIR = Path(os.getenv("WEB_UI_DIST_DIR", PROJECT_ROOT / "web-ui" / "dist"))
if DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="web-ui")
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Where2Stream API is running"}
