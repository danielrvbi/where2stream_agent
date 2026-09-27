# Where2Stream

A movie and TV streaming assistant with one Python backend and two web clients. The HTTP API is also the integration point for a future iPhone app.

## Repository layout

```text
python/
  movie_agent/
    agent.py          LangGraph chatbot and TMDB tools
    api.py            FastAPI endpoints used by clients
    utils.py          Shared configuration and data helpers
  pyproject.toml      Python dependencies and installable package
web-ui/
  src/                React and TypeScript client
  chainlit/           Chainlit client, theme, and assets
  start.sh            Local React + API launcher
ios/                  Future native iPhone client
archive/              Previous experiments, server, checkpoints, and traces
Dockerfile            Production React + API image
```

The browser and a future iPhone client can call the same API. Keep TMDB and Mistral keys on the backend; clients only receive search results and chatbot replies.

## Local setup

Use Python 3.12 and Node.js 20 or newer. From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e './python[chainlit]'
cd web-ui && npm ci && cd ..
cp .env.example .env
```

Set `TMDB_API_KEY` and `MISTRAL_API_KEY` in `.env`. The Python package loads that file from the repository root regardless of the current directory.

### React web UI

Run these in separate terminals:

```bash
source .venv/bin/activate
python -m uvicorn movie_agent.api:app --reload --port 8000
```

```bash
cd web-ui
npm run dev
```

Open <http://localhost:3000>. Vite proxies `/api` to the Python server. You can also run `./web-ui/start.sh` after activating the Python environment to start both processes.

### Chainlit UI

```bash
source .venv/bin/activate
cd web-ui/chainlit
chainlit run app.py --port 8001
```

Open <http://localhost:8001>. Running from `web-ui/chainlit` lets Chainlit find its `.chainlit` configuration, welcome page, and `public` assets.

## API for clients

Start the API, then see <http://localhost:8000/docs> for the interactive endpoint list. Requests and responses are JSON.

| Endpoint | Request fields | Response |
| --- | --- | --- |
| `POST /api/search-movie` | `title`, optional `year`, `director` | `{ "results": [...] }` |
| `POST /api/watch-providers` | `movie_id` | Provider groups such as `flatrate`, each containing provider and country entries |
| `POST /api/tv-search` | `title`, optional `year` | `{ "results": [...] }` |
| `POST /api/tv-providers` | `series_id` | Provider groups |
| `POST /api/agent` | `query`, optional `conversation_id` | `response` and `conversation_id` |
| `GET /health` | — | `{ "status": "ok" }` |

For a continuing chatbot conversation, send the returned `conversation_id` with the next query. Conversation memory currently lives in the API process, so it is lost when the process restarts. An iPhone app can use these endpoints without embedding Python or API keys in the app. Deployment, authentication, durable conversation storage, and a native client are future work.

## Production build

```bash
docker build -t where2stream .
docker run --env-file .env -p 8000:8000 where2stream
```

The Docker image builds React and serves it from the FastAPI process. For a local production build, run `cd web-ui && npm run build`, then start the API; it serves `web-ui/dist` when that directory exists.

## Configuration

- Edit subscriptions and default model in `python/movie_agent/utils.py`.
- Set `CORS_ORIGINS` to a comma separated list of allowed browser origins when serving the frontend from another host. Native clients do not use browser CORS.
- Set `VITE_API_BASE` in `web-ui/.env` only if the browser should call an API at a different origin. The default uses the Vite proxy in development and the same host in production.
