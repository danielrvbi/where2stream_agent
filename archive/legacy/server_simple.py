#!/usr/bin/env python
"""
Simple FastAPI server to connect the web UI with TMDB API directly
This version doesn't require langchain dependencies
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any, Optional
import os
import sys
import requests
import json

# Load TMDB API key from environment or .env file
TMDB_API_KEY = os.getenv("TMDB_API_KEY") or os.getenv("TMDB_key")
TMDB_BASE = "https://api.themoviedb.org/3"

# Subscribed platforms to filter by
SUBSCRIBED = {"NETFLIX", "AMAZON", "HBO", "MAX", "APPLE", "DISNEY", "HULU", "TUBI"}

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


def _rq(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make a request to TMDB API"""
    params["api_key"] = TMDB_API_KEY
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json()


def filter_subscribed(provider_name: str) -> bool:
    """Filter providers by subscribed platforms"""
    return any(sub in provider_name.upper() for sub in SUBSCRIBED)


def tmdb_table(results: Dict[str, Any]) -> Dict[str, Any]:
    """Format TMDB results into a structured format"""
    if not results:
        return {}
    
    formatted = {}
    for country, providers in results.items():
        for provider_type, provider_list in providers.items():
            if provider_type in ["ads", "flatrate", "free", "rent", "buy"]:
                for provider in provider_list:
                    provider_name = provider.get("provider_name", "").upper().strip()
                    if filter_subscribed(provider_name):
                        if provider_type not in formatted:
                            formatted[provider_type] = []
                        formatted[provider_type].append({
                            "Type": provider_type,
                            "Provider": provider_name,
                            "Country": [country]
                        })
    return formatted


@app.get("/")
async def root():
    return {"message": "Where2Stream API is running", "tmdb_configured": bool(TMDB_API_KEY)}


@app.post("/api/search-movie")
async def search_movie(request: Request):
    """Search for movies by title"""
    try:
        if not TMDB_API_KEY:
            raise HTTPException(status_code=500, detail="TMDB_API_KEY not configured")
            
        # Parse request data
        try:
            data = await request.json()
        except:
            form_data = await request.form()
            data = {k: v for k, v in form_data.items()}
        
        title = data.get("title", "")
        if not title:
            raise HTTPException(status_code=400, detail="Title parameter is required")
        
        # Call TMDB API directly
        params = {
            "api_key": TMDB_API_KEY,
            "query": title,
            "include_adult": "false"
        }
        
        search_data = _rq(f"{TMDB_BASE}/search/movie", params)
        
        results = []
        for r in (search_data.get("results") or [])[:10]:
            results.append({
                "id": r.get("id"),
                "title": r.get("title"),
                "original_language": r.get("original_language") or "",
                "release_year": (r.get("release_date") or "")[:4],
                "overview": r.get("overview"),
                "poster_path": r.get("poster_path"),
            })
        
        return {"results": results}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/watch-providers")
async def get_watch_providers(request: Request):
    """Get watch providers for a specific movie"""
    try:
        if not TMDB_API_KEY:
            raise HTTPException(status_code=500, detail="TMDB_API_KEY not configured")
            
        # Parse request data
        try:
            data = await request.json()
        except:
            form_data = await request.form()
            data = {k: v for k, v in form_data.items()}
        
        movie_id = data.get("movie_id")
        if not movie_id:
            raise HTTPException(status_code=400, detail="movie_id parameter is required")
            
        movie_id = int(movie_id)
        
        # Call TMDB API directly
        data = _rq(f"{TMDB_BASE}/movie/{movie_id}/watch/providers", {"api_key": TMDB_API_KEY})
        
        results = data.get("results", {})
        if results:
            return tmdb_table(results)
        
        return {"message": "No watch providers found."}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tv-search")
async def search_tv(request: Request):
    """Search for TV shows by title"""
    try:
        if not TMDB_API_KEY:
            raise HTTPException(status_code=500, detail="TMDB_API_KEY not configured")
            
        # Parse request data
        try:
            data = await request.json()
        except:
            form_data = await request.form()
            data = {k: v for k, v in form_data.items()}
        
        title = data.get("title", "")
        if not title:
            raise HTTPException(status_code=400, detail="Title parameter is required")
        
        # Call TMDB API directly
        params = {
            "api_key": TMDB_API_KEY,
            "query": title,
            "include_adult": "false"
        }
        
        search_data = _rq(f"{TMDB_BASE}/search/tv", params)
        
        results = []
        for r in (search_data.get("results") or [])[:10]:
            results.append({
                "id": r.get("id"),
                "title": r.get("name"),
                "original_language": r.get("original_language") or "",
                "release_year": (r.get("first_air_date") or "")[:4],
                "overview": r.get("overview"),
                "poster_path": r.get("poster_path"),
            })
        
        return {"results": results}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tv-providers")
async def get_tv_providers(request: Request):
    """Get watch providers for a specific TV series"""
    try:
        if not TMDB_API_KEY:
            raise HTTPException(status_code=500, detail="TMDB_API_KEY not configured")
            
        # Parse request data
        try:
            data = await request.json()
        except:
            form_data = await request.form()
            data = {k: v for k, v in form_data.items()}
        
        series_id = data.get("series_id")
        if not series_id:
            raise HTTPException(status_code=400, detail="series_id parameter is required")
            
        series_id = int(series_id)
        
        # Call TMDB API directly
        data = _rq(f"{TMDB_BASE}/tv/{series_id}/watch/providers", {"api_key": TMDB_API_KEY})
        
        results = data.get("results", {})
        if results:
            return tmdb_table(results)
        
        return {"message": "No watch providers found."}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve static files from the dist directory
if os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("Starting Where2Stream API server...")
    print(f"TMDB_API_KEY configured: {bool(TMDB_API_KEY)}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
