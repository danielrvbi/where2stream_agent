import asyncio
import json
import re
from typing import Any

import chainlit as cl
from langchain_core.runnables import RunnableConfig

from agent_v2 import get_agent, llm_small

BOT_NAME = "MovieBot"


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
    """Summarize tool output in the background using first-person narration."""
    try:
        step.output = "Looking at the results..."
        await step.update()

        serialized = json.dumps(raw_data, default=str)[:1000]

        # UPDATED PROMPT: Force first-person narration and forbid markdown
        prompt = (
            "You are an AI assistant narrating your internal actions to a user. "
            "Write a single, brief sentence explaining what you just did or found based on the data below. "
            "You MUST speak in the first person (e.g., 'I just searched for...', 'I found that...'). "
            "CRITICAL: Output ONLY the sentence. Do not use any Markdown formatting, asterisks, or quotes. "
            f"Result data: {serialized}"
        )
        
        summary_response = await llm_small.ainvoke(prompt)
        
        content = summary_response.content
        if isinstance(content, list):
            content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
        
        # Clean up any rogue quotes or asterisks the LLM might still try to sneak in
        clean_summary = content.replace('"', '').replace('*', '').strip()
        
        # UPDATED UI: Remove markdown styling, just plain text
        step.input = ""  
        step.language = "text"
        step.output = clean_summary
        
        await step.update()
        
    except Exception as e:
        try:
            step.output = f"Raw Data:\n{json.dumps(raw_data, indent=2, default=str)}"
        except TypeError:
            step.output = f"Raw Data:\n{str(raw_data)}"
        await step.update()

async def run_agent_prompt(user_prompt: str, button_fallback_title: str) -> None:
    graph = get_agent()
    config = RunnableConfig(configurable={"thread_id": cl.context.session.id})
    run_steps: dict[str, cl.Step] = {}
    message = cl.Message(content="", author=BOT_NAME)

    async for event in graph.astream_events(
        {"messages": [("user", user_prompt)]},
        version="v2",
        config=config,
    ):
        kind = event.get("event", "")
        name = event.get("name", "")
        run_id = event.get("run_id", "")
        data = event.get("data", {})

        if kind == "on_tool_start":
            step = cl.Step(name=f"🛠️ {name}", type="tool")
            # FIX: Do NOT set step.input here, or the UI draws the dark box. 
            # Give it a loading message instead.
            step.output = "Running..." 
            await step.send()
            run_steps[run_id] = step
        elif kind == "on_tool_end":
            step = run_steps.get(run_id)
            #if step:
                #raw_output = data.get("output")
                #asyncio.create_task(summarize_tool_output(step, raw_output))
        elif kind == "on_chat_model_stream":
            chunk = data.get("chunk")
            if not chunk:
                continue

            chunk_content = getattr(chunk, "content", "")
            if isinstance(chunk_content, list):
                text_parts = []
                for part in chunk_content:
                    if isinstance(part, dict):
                        text_parts.append(part.get("text", ""))
                    else:
                        text_parts.append(str(part))
                chunk_text = "".join(text_parts)
            else:
                chunk_text = str(chunk_content or "")

            if chunk_text and not getattr(chunk, "tool_calls", None):
                await message.stream_token(chunk_text)

    if message.content:
        message.actions = build_streaming_actions(message.content, button_fallback_title)
    await message.send()


@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content="🎬 **Movie Stream Finder Agent (v2)** is ready! Ask me about any movie.",
        author=BOT_NAME,
    ).send()


@cl.on_message
async def on_message(msg: cl.Message):
    await run_agent_prompt(msg.content, msg.content)


@cl.action_callback("find_streaming")
async def on_find_streaming(action: cl.Action):
    payload = action.payload or {}
    movie_title = payload.get("movie_title", "this movie")

    await cl.Message(
        content=f"Checking streaming availability for: {movie_title}...",
        author=BOT_NAME,
    ).send()

    await run_agent_prompt(f"Where can I stream {movie_title}?", movie_title)
