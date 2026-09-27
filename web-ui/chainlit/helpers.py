"""Presentation helpers used only by the Chainlit client."""

import json
import re
from typing import Any

import chainlit as cl

from movie_agent.utils import get_model


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
        actions.append(
            cl.Action(
                name="find_streaming",
                payload={"movie_title": fallback_title},
                label="🍿 Where to Stream?",
                tooltip="Click to find where to watch this",
            )
        )

    return actions


async def summarize_tool_output(step: cl.Step, raw_data: Any) -> None:
    """Summarize a tool result for the Chainlit step display."""
    try:
        serialized = (raw_data if isinstance(raw_data, str) else json.dumps(raw_data, default=str))[:2000]
        prompt = (
            "You are an AI assistant narrating your internal actions to a user. "
            "Write a single, very brief sentence explaining what you just did or found based on the data below. "
            "You MUST speak in the first person. Output ONLY the sentence. "
            f"Result data: {serialized}"
        )
        summary_response = await get_model().ainvoke(prompt)
        content = summary_response.content
        if isinstance(content, list):
            content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
        step.input = ""
        step.output = content.replace('"', "").replace("*", "").strip()
    except Exception:
        step.output = "I've processed the results."
    await step.update()
