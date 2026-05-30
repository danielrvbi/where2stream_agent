import os
import json
import requests
import pandas as pd
import pycountry
import asyncio
import re
import chainlit as cl
from datetime import datetime
from string import ascii_uppercase
from textwrap import dedent as ded
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
from langchain_ollama import ChatOllama
from ollama import Client
from dotenv import load_dotenv

load_dotenv()

# Constants
TMDB_API_KEY = os.getenv("TMDB_API_KEY") or os.getenv("TMDB_key")
TMDB_BASE = "https://api.themoviedb.org/3"
SUBSCRIBED = {"NETFLIX", "AMAZON", "HBO", "MAX", "APPLE", "DISNEY", "HULU", "TUBI"}
DEFAULT_MODEL = "glm-4.6:cloud"

# Utility assignments
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
                if response.generations and response.generations[0]:
                    gen = response.generations[0][0]
                    trace["output_messages"] = [{"role": "ai", "content": gen.text}]
                    metadata = getattr(gen, 'message', type('obj', (object,), {'response_metadata': {}})).response_metadata
                    trace["token_usage"] = {
                        "prompt_tokens": metadata.get("prompt_eval_count", 0),
                        "completion_tokens": metadata.get("eval_count", 0)
                    }
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

# Tracing instance
json_tracer = SimpleJSONTraceHandler(filepath="agent_traces.json")

def get_all_ollama_models():
    """Retrieves a list of all local Ollama models."""
    try:
        local_client = Client()
        local_response = local_client.list()
        return [model["model"] for model in local_response.get("models", [])]
    except Exception as e:
        print(f"Error fetching local models: {e}")
        return []

def get_ollama_model(model_name: str) -> ChatOllama:
    """Initializes a ChatOllama instance for the specified model."""
    return ChatOllama(model=model_name, temperature=0, callbacks=[json_tracer])

# Initialize shared LLMs
llm_small = get_ollama_model("llama3.1:8b")

def _rq(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json()

def update_dict(a, b):
    return {**a, **b}

def rename_country(country):
    name = pycountry.countries.get(alpha_2=country).name
    return name.title()

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

def build_streaming_actions(agent_reply: str, fallback_title: str) -> list[cl.Action]:
    actions: list[cl.Action] = []
    list_matches = re.findall(r"^\d+\.\s+(.*?)$", agent_reply, re.MULTILINE)

    if list_matches:
        for match in list_matches:
            clean_title = match.replace("**", "").strip()
            actions.append(
                cl.Action(
                    name="find_streaming",
                    payload={"movie_title": clean_title},
                    label=f"🍿 Stream {clean_title}",
                    tooltip=f"Check streaming for {clean_title}",
                )
            )
    elif "overview" in agent_reply.lower() or "release" in agent_reply.lower():
        actions = [
            cl.Action(
                name="find_streaming",
                payload={"movie_title": fallback_title},
                label="🍿 Where to Stream?",
                tooltip="Click to find where to watch this",
            )
        ]

    return actions
    
async def summarize_tool_output(step: cl.Step, raw_data: Any):
    "Summarize tool output in the background using first-person narration."
    try:
        # If it's too long, truncate it for the summary LLM
        if isinstance(raw_data, str):
            serialized = raw_data[:2000]
        else:
            serialized = json.dumps(raw_data, default=str)[:2000]

        prompt = (
            "You are an AI assistant narrating your internal actions to a user. "
            "Write a single, very brief sentence explaining what you just did or found based on the data below. "
            "You MUST speak in the first person (e.g., 'I just searched for...', 'I found that...'). "
            "Output ONLY the sentence. Do not use any Markdown formatting, asterisks, or quotes. "
            f"Result data: {serialized}"
        )
        
        summary_response = await llm_small.ainvoke(prompt)
        
        content = summary_response.content
        if isinstance(content, list):
            content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
        
        clean_summary = content.replace('"', '').replace('*', '').strip()
        
        # Update the step output with the summary
        step.input = "" # Hide the raw input block
        step.output = clean_summary
        await step.update()
        
    except Exception as e:
        # Silently fail or provide a generic message to keep the UI clean
        step.output = "I've processed the results."
        await step.update()
