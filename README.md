# Movie Stream Finder Agent (v2)

A sophisticated AI agent built with **LangGraph**, **LangChain**, and **Ollama** that helps you find where to stream movies and TV shows. It integrates with The Movie Database (TMDB) API to provide real-time availability across various streaming platforms, tailored to your subscriptions and location.

This project includes:
- A **backend agent** for intelligent streaming search and filtering.
- A **modern web UI** (`web-ui/`) for visual, interactive movie discovery.

## 🚀 Features

### Backend Agent
- **Intelligent Search**: Uses TMDB to find accurate movie and series IDs before checking streaming availability.
- **VPN-Aware**: Prioritizes availability in the Netherlands but also lists international options for VPN users.
- **Subscription Filtering**: Automatically filters results to show platforms you actually subscribe to (e.g., Netflix, Disney+, Max, etc.).
- **Local LLM Support**: Designed to run with **Ollama** for privacy and local execution.
- **Persistent Memory**: Remembers your conversation history using LangGraph's `MemorySaver`.

### Web UI (`web-ui/`)
- **Interactive Search**: Real-time movie search with autocomplete suggestions.
- **Visual Movie Cards**: Beautiful card layout with movie posters and details.
- **Streaming Information**: Clear display of where movies are available to stream.
- **Progress Tracking**: Visual progress indicator showing the workflow steps.
- **Responsive Design**: Works on desktop, tablet, and mobile devices.
- **Chat Interface**: Conversation-style interaction with the agent.

## 🛠️ Technology Stack

### Backend Agent
- **Framework**: LangGraph, LangChain
- **LLM Engine**: Ollama (local models)
- **Data Source**: TMDB API
- **Data Processing**: Pandas, Pycountry

### Web UI (`web-ui/`)
- **Frontend**: React 18 + TypeScript + Vite
- **Styling**: Custom CSS with modern design patterns
- **Backend**: FastAPI (Python) to connect with the agent

## 📋 Prerequisites

### Backend Agent
1.  **Ollama**: Ensure you have [Ollama](https://ollama.com/) installed and running locally.
      - Recommended local models for this setup: `gemma4:26b-mlx` for the main agent and `mistral-small3.2:latest` for summarization.
2.  **TMDB API Key**: Obtain an API key from [The Movie Database](https://www.themoviedb.org/documentation/api).

### Web UI (`web-ui/`)
1. **Node.js 18+**
2. **Python 3.8+** (for the FastAPI backend)

## ⚙️ Setup

### Backend Agent
1.  **Clone the repository** (if applicable).
2.  **Install dependencies** (from the workspace root, using the shared `uv` environment):
    ```bash
    uv sync
    ```
3.  **Configure Environment Variables**:
    Create a `.env` file in the root directory and add your TMDB API key:
    ```env
    TMDB_API_KEY=your_api_key_here
    ```

### Web UI (`web-ui/`)
1. **Install frontend dependencies**:
    ```bash
    cd web-ui
    npm install
    ```
2. **Set up environment variables**:
    Create a `.env` file in the `web-ui` directory:
    ```env
    VITE_API_BASE=http://localhost:8000
    ```
3. **Install Python dependencies** (for the FastAPI backend):
    ```bash
    pip install fastapi uvicorn python-multipart
    ```

## 🏃 How to Run

### Backend Agent
Start the Chainlit application from the workspace root:

```bash
./agents_env.sh run movie_agent chainlit run chainapp.py
```

The application will be available at `http://localhost:8000`.

### Web UI (`web-ui/`)
1. **Start the API server**:
    ```bash
    cd web-ui
    python server.py
    ```
2. **Start the Vite dev server**:
    ```bash
    npm run dev
    ```
3. Open your browser to `http://localhost:3000`.

## 🔧 Configuration

### Backend Agent
#### Subscribed Providers
You can modify the list of active subscriptions in `agent_v2.py`:
```python
SUBSCRIBED = {"NETFLIX", "AMAZON", "HBO", "MAX", "APPLE", "DISNEY", "HULU", "TUBI"}
```

#### Model Selection
You can change the default models in `agent_v2.py` or select your preferred Ollama model directly in the Chainlit settings panel in the UI.

### Web UI (`web-ui/`)
#### Changing Colors
Edit the CSS variables in `web-ui/src/App.css`:
```css
:root {
  --primary-color: #6366f1;
  --secondary-color: #8b5cf6;
  --background-color: #0f172a;
  /* ... other colors */
}
```

#### API Endpoints
The web UI connects to the following endpoints (defined in `web-ui/server.py`):
- `POST /api/search-movie` - Search for movies by title
- `POST /api/watch-providers` - Get streaming providers for a movie
- `POST /api/tv-search` - Search for TV shows
- `POST /api/tv-providers` - Get streaming providers for TV shows
- `POST /api/agent` - Full agent workflow

## 📁 Project Structure

### Backend Agent
- `agent_v2.py`: Contains the LangGraph workflow, tools, and agent logic.
- `chainapp.py`: The Chainlit interface and UI logic.
- `agent_traces.json`: (Generated) Logs tool calls and LLM interactions for debugging.

### Web UI (`web-ui/`)
```
web-ui/
├── src/
│   ├── components/          # React components (MovieCard, SearchBar, etc.)
│   ├── types.ts             # TypeScript interfaces
│   ├── api.ts               # API client functions
│   ├── App.tsx              # Main application component
│   └── main.tsx             # Entry point
├── server.py               # FastAPI backend
├── package.json
├── tsconfig.json
└── vite.config.ts
```
