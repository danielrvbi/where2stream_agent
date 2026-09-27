import json
import logging
import os
import subprocess
import sys
from string import ascii_uppercase
from textwrap import dedent as ded
from typing import Annotated, Any, Dict, List, NotRequired, Optional, TypedDict

import pandas as pd
import pycountry
import requests
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph, add_messages
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field, model_validator
from dotenv import load_dotenv
load_dotenv()

dedent = lambda x: ded(x.strip())



import json
import os
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama

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



logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("streamfind")

TMDB_API_KEY = os.getenv("TMDB_API_KEY") or os.getenv("TMDB_key")
TMDB_BASE = "https://api.themoviedb.org/3"

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


def tmdb_table(results) -> pd.DataFrame:
    """Get a table of the info of providers per country"""
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

        return json.dumps(
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
            .to_dict(),
            indent=4,
        )
    return pd.DataFrame()


def tmdb_search_movie(
    title: str, year: Optional[int] = None, director: Optional[str] = None
) -> Dict[str, Any]:
    """Search TMDB by title (optional year/director). Returns up to 10 candidates."""
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY not set"}
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


def tmdb_watch_providers(movie_id: int) -> Dict[str, Any]:
    """Get TMDB Watch Providers (per country) for a movie_id."""
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY not set"}
    data = _rq(f"{TMDB_BASE}/movie/{movie_id}/watch/providers", {"api_key": TMDB_API_KEY})

    results = data.get("results", {})
    if results:
        return tmdb_table(results)

    return ""


# 1. Initialize the custom JSON handler
json_tracer = SimpleJSONTraceHandler(filepath="agent_traces.json")

# 2. Initialize the Ollama Chat Model with the callback
llm = ChatOllama(
    model="gpt-oss:20b", # Or your preferred local model
    temperature=0,
    callbacks=[json_tracer]
)

def parse_movie_node(state):
    class TMDBSearchMovieInput(BaseModel):
        """Input schema for tmdb_search_movie."""

        title: str = Field(..., description="Movie title to search for")
        year: Optional[int] = Field(None, description="null if not mentioned by the user")
        director: Optional[str] = Field(None, description="null if not mentioned by the user")

        @model_validator(mode="after")
        def enforce_nulls(cls, values):
            if not values.year:
                values.year = None
            if not values.director:
                values.director = None
            return values

    system_prompt = dedent(
        """
    You must extract 'title', 'year', and 'director' from the user query.
    - If year is not explicitly mentioned, return year = null.
    - If director is not explicitly mentioned, return director = null.
    - No extra text, no explanations.
    Example outputs:
      {"title": "Inception", "year": 2010, "director": "Christopher Nolan"}
      {"title": "Titanic", "year": null, "director": null}
    """
    )

    user_input = state["messages"][-1].content if state["messages"] else ""
    thinking_msg = AIMessage(content=f"🔍 **Step 1: Parse Movie Query**\n\nInput: \"{user_input}\"\n\nExtracting title, year, and director...")

    try:
        response = llm.with_structured_output(TMDBSearchMovieInput).invoke(
            [SystemMessage(content=system_prompt), state["messages"][-1]]
        )
        result = response.model_dump()
        output_msg = AIMessage(content=f"✅ **Parsed Result:**\n- Title: {result.get('title')}\n- Year: {result.get('year') or 'Not specified'}\n- Director: {result.get('director') or 'Not specified'}")
    except Exception as e:
        error_msg = AIMessage(content=f"❌ **Parse Error:** {str(e)}")
        return {"next_action": "return", "error": str(e), "messages": [thinking_msg, error_msg]}

    return {"user_movie": result, "messages": [thinking_msg, output_msg]}


def choose_movie_node(state):
    user_movie = state.get("user_movie", {})

    if not user_movie:
        error_msg = AIMessage(content="❌ **Step 2: Choose Movie**\n\nError: No movie data from previous step")
        return {"error": "No retrieved movie", "messages": [error_msg]}

    thinking_msg = AIMessage(content=f"🎬 **Step 2: Search & Choose Movie**\n\nSearching TMDB for: {user_movie.get('title')}...")

    movie_candidates = tmdb_search_movie(
        title=user_movie.get("title", ""),
        year=user_movie.get("year", None),
        director=user_movie.get("director", None),
    )

    if isinstance(movie_candidates, dict) and "error" in movie_candidates:
        error_msg = AIMessage(content=f"❌ **TMDB Error:** {movie_candidates['error']}")
        return {"error": movie_candidates["error"], "messages": [thinking_msg, error_msg]}

    if not movie_candidates:
        no_result_msg = AIMessage(content="❌ No movies found matching the query")
        return {"error": "No movies found", "messages": [thinking_msg, no_result_msg]}

    candidates_summary = "\n".join([f"- {c.get('title')} ({c.get('release_year')}) - ID: {c.get('id')}" for c in movie_candidates[:5]])
    candidates_msg = AIMessage(content=f"📋 **Found {len(movie_candidates)} candidates:**\n{candidates_summary}\n\nSelecting best match...")

    class TMDBPickMovie(BaseModel):
        """Pick exactly one candidate by id, or null if no suitable match."""

        movie_id: int = Field(
            ...,
            description="One of the candidate IDs shown below. Use null if none match the user intent.",
        )

    system_prompt = dedent(
        """
        You are selecting exactly ONE movie from the provided candidates.
        Rules:
        - Return a JSON object that matches the schema.
        - 'movie_id' MUST be one of the candidate IDs shown. If no candidate fits, set id = null.
        - No prose beyond fields in the schema.
    """
    )

    user_query = (
        state.get("messages", [HumanMessage(content="")])[-1].content if "messages" in state else ""
    )

    human_content = dedent(
        f"""
    User query: {user_query}

    Candidates (JSON list):
    {movie_candidates}
    """
    )

    try:
        pick: TMDBPickMovie = llm.with_structured_output(TMDBPickMovie).invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_content)]
        )
    except Exception as e:
        error_msg = AIMessage(content=f"❌ **Selection Error:** {str(e)}")
        return {"movie_id": None, "error": f"LLM error: {e}", "messages": [thinking_msg, candidates_msg, error_msg]}

    valid_ids = {c["id"] for c in movie_candidates if c.get("id") is not None}
    chosen_id = pick.movie_id if (pick.movie_id in valid_ids) else None

    if chosen_id is not None:
        retrived_movie = [i for i in movie_candidates if i["id"] == chosen_id][0]
        selected_msg = AIMessage(content=f"✅ **Selected:** {retrived_movie.get('title')} ({retrived_movie.get('release_year')})\n\n🌐 Fetching streaming providers...")
        providers_for_movie = tmdb_watch_providers(movie_id=retrived_movie["id"])

        if isinstance(providers_for_movie, dict) and "error" in providers_for_movie:
            error_msg = AIMessage(content=f"❌ **TMDB Error:** {providers_for_movie['error']}")
            return {
                "retrived_movie": retrived_movie,
                "error": providers_for_movie["error"],
                "messages": [thinking_msg, candidates_msg, selected_msg, error_msg],
            }

        if providers_for_movie is None or providers_for_movie == "":
            no_providers_msg = AIMessage(content="⚠️ No streaming providers found for this movie")
            return {
                "retrived_movie": retrived_movie,
                "messages": [thinking_msg, candidates_msg, selected_msg, no_providers_msg],
            }
        else:
            providers_msg = AIMessage(content="📺 **Providers found!**")
            return {
                "retrived_movie": retrived_movie,
                "providers": providers_for_movie,
                "messages": [thinking_msg, candidates_msg, selected_msg, providers_msg],
            }

    else:
        not_found_msg = AIMessage(content="❌ No matching movie found in candidates")
        return {"error": "Movie not found", "messages": [thinking_msg, candidates_msg, not_found_msg]}


def response_wrap_node(state):
    messages = state.get("messages", [])
    retrived_movie = state.get("retrived_movie", {})
    movie_title = retrived_movie.get("title", "the movie")

    thinking_msg = AIMessage(content=f"📝 **Step 3: Generate Final Response**\n\nCompiling streaming information for '{movie_title}'...")

    system_prompt = dedent(
        """
    You produce the final user-facing answer for an AI system that searches in which services and which countries to stream the movie asked.
    ## Context
    - The given data is already filtering the subscription the user has
    - The user location is the Netherlands, so that is the only Non-VPN option that exists

    ## Constraints:
    - It doesn't matter what is the user's country. They will use a VPN
    - Mention ALL countries where the movie is available
    - Mention all available options to see the movie (only if info is available)
    - If nothing is available anywhere, say so.
    - Do not invent providers or countries not in the input.

    """
    )

    response = llm.invoke(messages + [SystemMessage(content=system_prompt)])
    return {"messages": [thinking_msg, response]}


class MovieState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]
    user_movie: Dict[str, Optional[Any]]
    retrived_movie: Dict[str, Any]
    providers: Dict[str, Any]
    next_action: NotRequired[str]
    error: NotRequired[str]
    country: NotRequired[str]
    subscriptions: NotRequired[List[str]]
    vpn_countries: NotRequired[List[str]]


def build_app(model_name: str = "gpt-oss:20b"):
    def route_after_parse(state: MovieState):
        return END if state.get("error") else "choose_movie_node"

    def route_after_choose(state: MovieState):
        return END if state.get("error") else "response_wrap_node"

    graph = StateGraph(MovieState)
    graph.add_node("parse_movie_node", parse_movie_node)
    graph.add_node("choose_movie_node", choose_movie_node)
    graph.add_node("response_wrap_node", response_wrap_node)

    graph.set_entry_point("parse_movie_node")
    graph.add_conditional_edges("parse_movie_node", route_after_parse)
    graph.add_conditional_edges("choose_movie_node", route_after_choose)
    graph.add_edge("response_wrap_node", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


_AGENT = None


def get_agent():
    global _AGENT
    if _AGENT is None:
        _AGENT = build_app()
    return _AGENT


def run_agent_with_state(user_message: str) -> Dict[str, Any]:
    resp = get_agent().invoke({"messages": [HumanMessage(content=user_message.strip())]})
    final_content = ""
    if resp.get("messages"):
        last_msg = resp["messages"][-1]
        if isinstance(last_msg, AIMessage):
            final_content = last_msg.content
        else:
            final_content = str(getattr(last_msg, "content", last_msg))
    return {"response": final_content, "state": resp}


def run_agent(user_message: str) -> str:
    return run_agent_with_state(user_message)["response"]


def run_agent_stream(user_message: str):
    """Stream agent execution step by step.
    
    Yields dicts with keys:
    - "type": "step" | "final"
    - "node": node name (e.g., "parse_movie_node") for steps
    - "messages": list of new AIMessages for this step
    - "state": current state snapshot
    - "response": final response string (only for "final" type)
    """
    initial_state = {"messages": [HumanMessage(content=user_message.strip())]}
    
    final_state = None
    for chunk in get_agent().stream(initial_state, stream_mode="updates"):
        # chunk is a dict like {node_name: output} or the full state
        if isinstance(chunk, dict):
            # Get the node name and output from the chunk
            if len(chunk) == 1:
                node_name = list(chunk.keys())[0]
                output = chunk[node_name]
            else:
                # Might be the full state
                node_name = "unknown"
                output = chunk
            
            final_state = output
            
            # Extract thinking messages (AIMessages with emoji prefixes)
            messages = output.get("messages", []) if isinstance(output, dict) else []
            thinking_msgs = [
                m for m in messages 
                if isinstance(m, AIMessage) and 
                any(m.content.startswith(prefix) for prefix in ["🔍", "🎬", "📝", "✅", "📋", "❌", "⚠️", "🌐", "📺"])
            ]
            
            yield {
                "type": "step",
                "node": node_name,
                "messages": thinking_msgs,
                "state": output
            }
    
    # Yield final result from the last state
    if final_state is None:
        final_state = {}
    final_content = ""
    if final_state.get("messages"):
        last_msg = final_state["messages"][-1]
        if isinstance(last_msg, AIMessage):
            final_content = last_msg.content
    
    yield {
        "type": "final",
        "response": final_content,
        "state": final_state
    }


def restart_ollama_daemon():
    subprocess.run(["pkill", "-9", "ollama"])
    subprocess.run(["ollama", "serve"])

