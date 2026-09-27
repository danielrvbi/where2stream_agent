# Quick run guide

Install the Python package and frontend dependencies once using the steps in [README.md](README.md).

React plus API:

```bash
source .venv/bin/activate
./web-ui/start.sh
```

Chainlit:

```bash
source .venv/bin/activate
cd web-ui/chainlit
chainlit run app.py --port 8001
```

Set `TMDB_API_KEY` and `MISTRAL_API_KEY` in the repository root `.env` before starting either UI.
