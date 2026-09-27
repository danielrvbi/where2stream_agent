import asyncio
import chainlit as cl
from langchain_core.runnables import RunnableConfig

# Local imports
from movie_agent.agent import get_agent
from movie_agent.utils import get_available_models, get_default_model, RETIRED_MODELS
from helpers import build_streaming_actions, summarize_tool_output

BOT_NAME = "MovieBot"

TOOL_DISPLAY_NAMES = {
    "tmdb_search_movie": "🎬 Searching for Movie",
    "tmdb_watch_providers": "🍿 Checking Streaming",
    "tmdb_search_tv": "📺 Searching for TV Show",
    "tmdb_tv_watch_providers": "🍿 Checking TV Streaming",
}

async def run_agent_prompt(user_prompt: str, button_fallback_title: str) -> None:
    graph = get_agent()
    
    # Get the selected model from settings
    settings = cl.user_session.get("settings") or {}
    model_name = settings.get("model") or get_default_model()
    if model_name in RETIRED_MODELS:
        model_name = get_default_model()
    
    config = RunnableConfig(
        configurable={
            "thread_id": cl.context.session.id,
            "model_name": model_name
        }
    )
    run_steps: dict[str, cl.Step] = {}
    message = cl.Message(content="", author=BOT_NAME)
    await cl.Message(content=f"Checking with `{model_name}`...", author=BOT_NAME).send()

    try:
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
                display_name = TOOL_DISPLAY_NAMES.get(name, name)
                step = cl.Step(name=display_name, type="tool")
                
                # Extract a helpful hint from the input
                tool_input = data.get("input", {})
                target = tool_input.get("title") or tool_input.get("movie_title") or tool_input.get("movie_id") or tool_input.get("series_id")
                
                step.output = f"Looking up '{target}'..." if target else "Searching..." 
                await step.send()
                run_steps[run_id] = step
            elif kind == "on_tool_end":
                step = run_steps.get(run_id)
                if step:
                    raw_output = data.get("output")
                    # Summarize in the background to avoid blocking the main stream
                    asyncio.create_task(summarize_tool_output(step, raw_output))
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

                if chunk_text:
                    await message.stream_token(chunk_text)
    except Exception as exc:
        await cl.Message(
            content=(
                f"I couldn't run the agent with `{model_name}`.\n\n"
                f"Error: `{exc}`\n\n"
                "Check that `MISTRAL_API_KEY` is configured in the environment."
            ),
            author=BOT_NAME,
        ).send()
        return

    if message.content:
        message.actions = build_streaming_actions(message.content, button_fallback_title)
    await message.send()


@cl.on_chat_start
async def on_chat_start():
    # Load available models
    models = get_available_models()
    default_model = get_default_model(models)
    
    # Set up settings panel
    await cl.ChatSettings(
        [
            cl.input_widget.Select(
                id="model",
                label="Mistral Model",
                values=models if models else [default_model],
                initial_value=default_model,
                description="Model used by the movie agent.",
            )
        ]
    ).send()
    
    # Initialize settings in session
    cl.user_session.set("settings", {"model": default_model})

    await cl.Message(
        content="🎬 **Movie Stream Finder Agent (v2)** is ready! Ask me about any movie.",
        author=BOT_NAME,
    ).send()


@cl.on_settings_update
async def setup_agent(settings):
    cl.user_session.set("settings", settings)
    await cl.Message(
        content=f"Settings updated! Using model: {settings['model']}",
        author=BOT_NAME
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
