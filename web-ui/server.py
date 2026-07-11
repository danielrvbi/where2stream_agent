#!/usr/bin/env python
"""
Simple FastAPI server to connect the web UI with the where2stream agent
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import os
import sys

# Add parent directory to path to import agent modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_v2 import tmdb_search_movie, tmdb_watch_providers
from utils import TMDB_API_KEY, TMDB_BASE, _rq

app = FastAPI(
    title="Where2Stream API",
    description="API for the Where2Stream agent web interface",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Where2Stream API is running"}


@app.post("/api/search-movie")
async def search_movie(title: str, year: int = None, director: str = None):
    """Search for movies by title"""
    try:
        results = tmdb_search_movie(title, year, director)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/watch-providers")
async def get_watch_providers(movie_id: int):
    """Get watch providers for a specific movie"""
    try:
        providers = tmdb_watch_providers(movie_id)
        return providers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tv-search")
async def search_tv(title: str, year: int = None):
    """Search for TV shows by title"""
    try:
        from agent_v2 import tmdb_search_tv
        results = tmdb_search_tv(title, year)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tv-providers")
async def get_tv_providers(series_id: int):
    """Get watch providers for a specific TV series"""
    try:
        from agent_v2 import tmdb_tv_watch_providers
        providers = tmdb_tv_watch_providers(series_id)
        return providers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent")
async def call_agent(query: str):
    """Call the agent with a query - full workflow"""
    try:
        from agent_v2 import get_agent
        from langchain_core.runnables import RunnableConfig
        
        agent_executor = get_agent()
        
        # Run the agent with the query
        result = await agent_executor.ainvoke(
            {"messages": [("user", query)]},
            config=RunnableConfig({"configurable": {"thread_id": "web-ui"}})
        )
        
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve static files from the dist directory
if os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
