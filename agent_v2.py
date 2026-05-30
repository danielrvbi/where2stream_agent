#!/usr/bin/env python
# coding: utf-8
from typing import Any, Dict, List, Optional
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import MessagesState, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

# Local imports
from utils import (
    TMDB_API_KEY, TMDB_BASE, DEFAULT_MODEL, SUBSCRIBED,
    get_ollama_model, get_all_ollama_models, _rq, tmdb_table
)

def get_ollama_model_with_tools(model_name: str, tools: list):
    """Initializes a ChatOllama instance with tools bound."""
    return get_ollama_model(model_name).bind_tools(tools)

@tool
def tmdb_search_movie(
    title: str, year: Optional[int] = None, director: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search TMDB (The Movie Database) for a movie by its title. 
    Can optionally filter by release year or director.
    Returns a list of up to 10 movie candidates containing their 'id', 'title', 'release_year', and 'overview'.
    """
    if not TMDB_API_KEY:
        return [{"error": "TMDB_API_KEY not set"}]

    params = {"api_key": TMDB_API_KEY, "query": title, "include_adult": "false"}
    if year:
        params["year"] = year

    data = _rq(f"{TMDB_BASE}/search/movie", params)
    cands = []

    for r in (data.get("results") or [])[:10]:
        cands.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "original_language": (r.get("original_language") or ""),
                "release_year": (r.get("release_date") or "")[:4],
                "overview": r.get("overview"),
            }
        )
    return cands


@tool
def tmdb_watch_providers(movie_id: int) -> Dict[str, Any]:
    """
    Get TMDB Watch Providers (where to stream, rent, or buy) categorized by country for a specific movie.
    Requires the numeric movie_id (which can be obtained from tmdb_search_movie).
    """
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY not set"}

    data = _rq(f"{TMDB_BASE}/movie/{movie_id}/watch/providers", {"api_key": TMDB_API_KEY})

    results = data.get("results", {})
    if results:
        return tmdb_table(results)

    return {"message": "No watch providers found."}


@tool
def tmdb_search_tv(
    title: str, year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Search TMDB (The Movie Database) for a TV series by its title. 
    Can optionally filter by first air year.
    Returns a list of up to 10 TV series candidates containing their 'id', 'title', 'release_year', and 'overview'.
    """
    if not TMDB_API_KEY:
        return [{"error": "TMDB_API_KEY not set"}]

    params = {"api_key": TMDB_API_KEY, "query": title, "include_adult": "false"}
    if year:
        params["first_air_date_year"] = year

    data = _rq(f"{TMDB_BASE}/search/tv", params)
    cands = []

    for r in (data.get("results") or [])[:10]:
        cands.append(
            {
                "id": r.get("id"),
                "title": r.get("name"),
                "original_language": (r.get("original_language") or ""),
                "release_year": (r.get("first_air_date") or "")[:4],
                "overview": r.get("overview"),
            }
        )
    return cands


@tool
def tmdb_tv_watch_providers(series_id: int) -> Dict[str, Any]:
    """
    Get TMDB Watch Providers (where to stream, rent, or buy) categorized by country for a specific TV series.
    Requires the numeric series_id (which can be obtained from tmdb_search_tv).
    """
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY not set"}

    data = _rq(f"{TMDB_BASE}/tv/{series_id}/watch/providers", {"api_key": TMDB_API_KEY})

    results = data.get("results", {})
    if results:
        return tmdb_table(results)

    return {"message": "No watch providers found."}

# 1. Define the tools array
tools = [
    tmdb_search_movie, 
    tmdb_watch_providers, 
    tmdb_search_tv, 
    tmdb_tv_watch_providers
]

# 2. Define the strict system prompt
system_prompt = SystemMessage(content=f"""
You are a highly specialized entertainment assistant. Your capabilities are strictly limited to:
1. Searching for movies or TV shows to confirm details with the user.
2. Finding streaming platforms where a movie or TV show can be watched.

CRITICAL INSTRUCTION:
- If a user asks about a MOVIE, you MUST execute 'tmdb_search_movie' first to get the ID, then 'tmdb_watch_providers'.
- If a user asks about a TV SHOW or SERIES, you MUST execute 'tmdb_search_tv' first to get the ID, then 'tmdb_tv_watch_providers'.
Under no circumstances should you call the provider tools without first obtaining the exact ID from the respective search tool.

USER CONTEXT & STREAMING PREFERENCES:
1. Primary Location (Netherlands): The user lives in the Netherlands. You must ALWAYS prioritize and present streaming availability in the Netherlands first.
2. VPN Access (Global): The user has a VPN and can access international content. If a title is unavailable in the Netherlands, or if it is available elsewhere on their active subscriptions, you must list the other countries where it can be streamed.
3. Active Subscriptions: Focus on 'flatrate' (subscription) availability for the platforms the user is currently subscribed to:
{SUBSCRIBED}

STYLE GUIDELINE:
- Before calling any tool, briefly state what you are about to do in a natural way (e.g., "I'll look up Shrek for you...", "Now I'll check where it's streaming..."). This helps the user follow your progress.
""")

# 3. Create the node function for the agent
def agent(state: MessagesState, config: RunnableConfig):
    # Ensure the system prompt is always injected at the start of the context window
    messages = [system_prompt] + state["messages"]

    # Dynamic model selection from config
    model_name = config.get("configurable", {}).get("model_name", DEFAULT_MODEL)
    current_llm = get_ollama_model_with_tools(model_name, tools)

    # Invoke the LLM (which is aware of the tools)
    response = current_llm.invoke(messages)

    # Return the response to be appended to the state
    return {"messages": [response]}


# 4. Build the LangGraph Workflow
workflow = StateGraph(MessagesState)

# Add the standard nodes
workflow.add_node("agent", agent)
workflow.add_node("tools", ToolNode(tools))

# Define the flow
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

# 5. Compile the graph into an executable application
memory = MemorySaver()
agent_executor = workflow.compile(checkpointer=memory)

def get_agent():
    return agent_executor
