import os
import json
import requests
import pandas as pd
import pycountry
from pathlib import Path
from datetime import datetime
from string import ascii_uppercase
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv

PROJECT_ROOT = Path(os.getenv("MOVIE_AGENT_ROOT", Path(__file__).resolve().parents[2]))
load_dotenv(PROJECT_ROOT / ".env")

# Constants
TMDB_API_KEY = os.getenv("TMDB_API_KEY") or os.getenv("TMDB_key")
TMDB_BASE = "https://api.themoviedb.org/3"
SUBSCRIBED = {"NETFLIX", "AMAZON", "HBO", "MAX", "APPLE", "DISNEY", "HULU", "TUBI"}
RETIRED_MODELS = {"glm-4.6:cloud"}
DEFAULT_MODEL = "mistral-small-latest"

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
json_tracer = SimpleJSONTraceHandler(
    filepath=str(Path(os.getenv("MOVIE_AGENT_TRACE_FILE", Path.cwd() / "agent_traces.json")))
)

def get_available_models():
    """Return the configured remote model for the movie agent."""
    return [DEFAULT_MODEL]

def get_default_model(models: Optional[List[str]] = None) -> str:
    """Return the configured Mistral model."""
    return DEFAULT_MODEL

def get_model(model_name: str = DEFAULT_MODEL) -> ChatMistralAI:
    """Initialize the configured Mistral chat model."""
    return ChatMistralAI(
        model=DEFAULT_MODEL,
        temperature=0,
        callbacks=[json_tracer],
    )

def _rq(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json()

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
