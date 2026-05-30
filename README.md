# Movie Stream Finder Agent (v2)

A sophisticated AI agent built with **LangGraph**, **LangChain**, and **Ollama** that helps you find where to stream movies and TV shows. It integrates with The Movie Database (TMDB) API to provide real-time availability across various streaming platforms, tailored to your subscriptions and location.

## 🚀 Features

- **Intelligent Search**: Uses TMDB to find accurate movie and series IDs before checking streaming availability.
- **VPN-Aware**: Prioritizes availability in the Netherlands but also lists international options for VPN users.
- **Subscription Filtering**: Automatically filters results to show platforms you actually subscribe to (e.g., Netflix, Disney+, Max, etc.).
- **Interactive UI**: Powered by **Chainlit**, featuring:
    - Real-time streaming tokens for agent "thoughts".
    - Interactive buttons to quickly check streaming for mentioned titles.
    - Background summarization of tool outputs for a cleaner chat experience.
- **Local LLM Support**: Designed to run with **Ollama** for privacy and local execution.
- **Persistent Memory**: Remembers your conversation history using LangGraph's `MemorySaver`.

## 🛠️ Technology Stack

- **Framework**: LangGraph, LangChain
- **LLM Engine**: Ollama (local models)
- **UI**: Chainlit
- **Data Source**: TMDB API
- **Data Processing**: Pandas, Pycountry

## 📋 Prerequisites

1.  **Ollama**: Ensure you have [Ollama](https://ollama.com/) installed and running locally.
    - Recommended models: `glm-4.6:cloud` (or similar large model) for the main agent and `llama3.1:8b` for summarization.
2.  **TMDB API Key**: Obtain an API key from [The Movie Database](https://www.themoviedb.org/documentation/api).

## ⚙️ Setup

1.  **Clone the repository** (if applicable).
2.  **Install dependencies**:
    ```bash
    pip install langchain langchain-ollama langgraph pandas pycountry requests pydantic python-dotenv chainlit ollama
    ```
3.  **Configure Environment Variables**:
    Create a `.env` file in the root directory and add your TMDB API key:
    ```env
    TMDB_API_KEY=your_api_key_here
    ```

## 🏃 How to Run

Start the Chainlit application:

```bash
chainlit run chainapp.py
```

The application will be available at `http://localhost:8000`.

## 🔧 Configuration

### Subscribed Providers
You can modify the list of active subscriptions in `agent_v2.py`:
```python
SUBSCRIBED = {"NETFLIX", "AMAZON", "HBO", "MAX", "APPLE", "DISNEY", "HULU", "TUBI"}
```

### Model Selection
You can change the default models in `agent_v2.py` or select your preferred Ollama model directly in the Chainlit settings panel in the UI.

## 📁 Project Structure

- `agent_v2.py`: Contains the LangGraph workflow, tools, and agent logic.
- `chainapp.py`: The Chainlit interface and UI logic.
- `agent_traces.json`: (Generated) Logs tool calls and LLM interactions for debugging.
