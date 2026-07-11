#!/usr/bin/env python
"""
Simple FastAPI server to connect the web UI with the where2stream agent
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sys
import json

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


# Pydantic models for request bodies
class MovieSearchRequest(BaseModel):
    title: str
    year: Optional[int] = None
    director: Optional[str] = None


class WatchProvidersRequest(BaseModel):
    movie_id: int


class TVSearchRequest(BaseModel):
    title: str
    year: Optional[int] = None


class TVProvidersRequest(BaseModel):
    series_id: int


class AgentRequest(BaseModel):
    query: str


@app.get("/")
async def root():
    return {"message": "Where2Stream API is running"}


@app.post("/api/search-movie")
async def search_movie(request: Request):
    """Search for movies by title"""
    try:
        # Try to parse as JSON first
        try:
            data = await request.json()
            title = data.get("title", "")
            year = data.get("year")
            director = data.get("director")
        except:
            # Fallback to form data
            form_data = await request.form()
            title = form_data.get("title", "")
            year = form_data.get("year")
            director = form_data.get("director")
            
        if not title:
            raise HTTPException(status_code=400, detail="Title parameter is required")
            
        results = tmdb_search_movie(title, year, director)
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/watch-providers")
async def get_watch_providers(request: Request):
    """Get watch providers for a specific movie"""
    try:
        # Try to parse as JSON first
        try:
            data = await request.json()
            movie_id = data.get("movie_id")
        except:
            # Fallback to form data
            form_data = await request.form()
            movie_id = form_data.get("movie_id")
            
        if not movie_id:
            raise HTTPException(status_code=400, detail="movie_id parameter is required")
            
        movie_id = int(movie_id)
        providers = tmdb_watch_providers(movie_id)
        return providers
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tv-search")
async def search_tv(request: Request):
    """Search for TV shows by title"""
    try:
        from agent_v2 import tmdb_search_tv
        
        # Try to parse as JSON first
        try:
            data = await request.json()
            title = data.get("title", "")
            year = data.get("year")
        except:
            # Fallback to form data
            form_data = await request.form()
            title = form_data.get("title", "")
            year = form_data.get("year")
            
        if not title:
            raise HTTPException(status_code=400, detail="Title parameter is required")
            
        results = tmdb_search_tv(title, year)
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tv-providers")
async def get_tv_providers(request: Request):
    """Get watch providers for a specific TV series"""
    try:
        from agent_v2 import tmdb_tv_watch_providers
        
        # Try to parse as JSON first
        try:
            data = await request.json()
            series_id = data.get("series_id")
        except:
            # Fallback to form data
            form_data = await request.form()
            series_id = form_data.get("series_id")
            
        if not series_id:
            raise HTTPException(status_code=400, detail="series_id parameter is required")
            
        series_id = int(series_id)
        providers = tmdb_tv_watch_providers(series_id)
        return providers
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent")
async def call_agent(request: Request):
    """Call the agent with a query - full workflow"""
    try:
        from agent_v2 import get_agent
        from langchain_core.runnables import RunnableConfig
        
        # Try to parse as JSON first
        try:
            data = await request.json()
            query = data.get("query", "")
        except:
            # Fallback to form data
            form_data = await request.form()
            query = form_data.get("query", "")
            
        if not query:
            raise HTTPException(status_code=400, detail="Query parameter is required")
        
        agent_executor = get_agent()
        
        # Run the agent with the query
        result = await agent_executor.ainvoke(
            {"messages": [("user", query)]},
            config=RunnableConfig({"configurable": {"thread_id": "web-ui"}})
        )
        
        return {"result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve static files from the dist directory
if os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
