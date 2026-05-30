#!/usr/bin/env python
# coding: utf-8
# Standard library imports
import argparse
from enum import Enum
import json
import logging
import os
import sys
from textwrap import dedent as ded
from typing import Annotated, Any, Dict, List, NotRequired, Optional, TypedDict
from uuid import UUID
from datetime import datetime
from string import ascii_lowercase, ascii_uppercase

# Third-party imports
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import LLMResult
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import END, MessagesState, START, StateGraph, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import pandas as pd
import pycountry
from pydantic import BaseModel, Field, conlist, constr, model_validator
import requests
from ollama import Client

# Variable assignments
dedent = lambda x: ded(x.strip())
class SimpleJSONTraceHandler(BaseCallbackHandler):
    def __init__(self, filepath: str = "simple_traces.json"):
        self.filepath = filepath
        self.traces = []

        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    self.traces = json.load(f)
            except json.JSONDecodeError:
                pass

    def _save_traces(self) -> None:
        with open(self.filepath, 'w') as f:
            json.dump(self.traces, f, indent=4)

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:

        # Extract just the role and content from the inputs
        simple_inputs = [{"role": msg.type, "content": str(msg.content)} for msg in messages[0]]

        trace_entry = {
            "run_id": str(run_id),
            "model_info": kwargs.get("invocation_params", {}).get("model", "unknown"),
            "start_time": datetime.utcnow().isoformat() + "Z",
            "status": "running",
            "input_messages": simple_inputs
        }

        self.traces.append(trace_entry)
        self._save_traces()

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:

        for trace in self.traces:
            if trace.get("run_id") == str(run_id):
                trace["status"] = "completed"
                trace["end_time"] = datetime.utcnow().isoformat() + "Z"

                # Extract output and token usage (Ollama specific mapping)
                if response.generations and response.generations[0]:
                    gen = response.generations[0][0]
                    trace["output_messages"] = [{"role": "ai", "content": gen.text}]

                    # Grab Ollama token counts from metadata
                    metadata = getattr(gen, 'message', type('obj', (object,), {'response_metadata': {}})).response_metadata
                    trace["token_usage"] = {
                        "prompt_tokens": metadata.get("prompt_eval_count", 0),
                        "completion_tokens": metadata.get("eval_count", 0)
                    }

                    # Update model_info if Ollama provided a more specific one in the response
                    if metadata.get("model"):
                        trace["model_info"] = metadata.get("model")
                break

        self._save_traces()

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:

        for trace in self.traces:
            if trace.get("run_id") == str(run_id):
                trace["status"] = "failed"
                trace["end_time"] = datetime.utcnow().isoformat() + "Z"
                trace["output_messages"] = [{"role": "error", "content": str(error)}]
                break

        self._save_traces()
#llm = ChatOllama(model="llama3.1:8b", temperature=0.0)
#llm = ChatOllama(model="gpt-oss:20b", temperature=0.0, keep_alive=False)
from dotenv import load_dotenv
load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY") or os.getenv("TMDB_key")
TMDB_BASE = "https://api.themoviedb.org/3"
# 1. Initialize the custom JSON handler
json_tracer = SimpleJSONTraceHandler(filepath="agent_traces.json")

def get_all_ollama_models():
    """
    Retrieves a list of all local Ollama models.
    """
    try:
        local_client = Client() # Defaults to http://localhost:11434
        local_response = local_client.list()
        return [model["model"] for model in local_response.get("models", [])]
    except Exception as e:
        print(f"Error fetching local models: {e}")
        return []


def get_ollama_model(model_name: str) -> ChatOllama:
    """
    Initializes a ChatOllama instance for the specified model.
    """
    return ChatOllama(model=model_name, temperature=0, callbacks=[json_tracer])
    

# Default models
#DEFAULT_MODEL = "mistral-small3.2:24b"
DEFAULT_MODEL = "glm-4.6:cloud"
llm = get_ollama_model(DEFAULT_MODEL)
llm_small = get_ollama_model("llama3.1:8b")
SUBSCRIBED = {"NETFLIX", "AMAZON", "HBO", "MAX", "APPLE", "DISNEY", "HULU", "TUBI"}


def _rq(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json()


def update_dict(a, b):
    return {**a, **b}


def rename_country(country):
    name = pycountry.countries.get(alpha_2=country).name
    flag = pycountry.countries.get(alpha_2=country).flag

    return name.title()
    return f"{name} {flag}"


def filter_subscribed(x):
    for i in SUBSCRIBED:
        if i in x:
            return True
    return False


ALL_FLAGS = (
    pd.Series(
        {
            f"{a}{b}": pycountry.countries.get(alpha_2=f"{a}{b}")
            for a in ascii_uppercase
            for b in ascii_uppercase
        }
    )
    .dropna()
    .apply(lambda x: f"{x.name} ({x.flag})".upper())
)
def tmdb_table(results) -> dict:
    "Get a table of the info of providers per country"
    if results:
        sub_df = pd.DataFrame(
            {
                rename_country(country): {
                    k: [i["provider_name"] for i in v]
                    for k, v in results[country].items()
                    if k in ["ads", "flatrate", "free"]
                }
                for country in results.keys()
            }
        )

        if sub_df.empty:
            sub_df = pd.DataFrame(
                {
                    rename_country(country): {
                        k: [i["provider_name"] for i in v]
                        for k, v in results[country].items()
                        if k in ["ads", "rent", "flatrate", "buy", "free"]
                    }
                    for country in results.keys()
                }
            )

        if sub_df.empty:
            return {}

        return (
            sub_df.stack()
            .explode()
            .sort_index()
            .reset_index()
            .set_axis(["Type", "Country", "Provider"], axis=1)
            .assign(Provider=lambda df: df["Provider"].apply(lambda x: str(x).upper().strip()))
            .loc[lambda df: df["Provider"].apply(filter_subscribed)]
            .pivot_table(index=["Type", "Provider"], values="Country", aggfunc=list)
            .groupby(level=0)
            .apply(lambda g: g.droplevel(0).to_dict()["Country"])
            .to_dict()
        )
    return {}
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

# Assuming TMDB_API_KEY, TMDB_BASE, _rq, and tmdb_table are defined elsewhere in your file

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
        # TMDB uses first_air_date_year for TV series filtering
        params["first_air_date_year"] = year

    data = _rq(f"{TMDB_BASE}/search/tv", params)
    cands = []

    for r in (data.get("results") or [])[:10]:
        cands.append(
            {
                "id": r.get("id"),
                "title": r.get("name"),  # TV endpoint uses 'name' instead of 'title'
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
        # We can reuse your existing tmdb_table function since the provider JSON structure is identical
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
    current_llm = get_ollama_model(model_name).bind_tools(tools)

    # Invoke the LLM (which is aware of the tools)
    response = current_llm.invoke(messages)

    # Return the response to be appended to the state
    return {"messages": [response]}
from langgraph.checkpoint.memory import MemorySaver

# 4. Build the LangGraph Workflow
workflow = StateGraph(MessagesState)

# Add the standard nodes
workflow.add_node("agent", agent)
workflow.add_node("tools", ToolNode(tools)) # ToolNode automatically executes the requested tools

# Define the flow
workflow.add_edge(START, "agent")

# tools_condition automatically checks if the LLM returned a tool call. 
# If it did, it routes to "tools". If not, it routes to END.
workflow.add_conditional_edges("agent", tools_condition)

# After tools execute, always return the results back to the agent for the final answer
workflow.add_edge("tools", "agent")

# 5. Compile the graph into an executable application
memory = MemorySaver()
agent_executor = workflow.compile(checkpointer=memory)
def get_agent():
    return agent_executor

if __name__ == "__main__":
    resp = agent_executor.invoke({"messages": HumanMessage("Where to stream shrek 2")})
    [i.pretty_print() for i in resp["messages"]]


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




