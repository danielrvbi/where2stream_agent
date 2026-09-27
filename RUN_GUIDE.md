# Running MovieBot

From the workspace root, start the Chainlit app with the shared UV environment:

```bash
./agents_env.sh run movie_agent chainlit run chainapp.py
```

Open [http://localhost:8000](http://localhost:8000) in a browser and ask:

```text
Where can I stream Planet Terror (2007)?
```

The command uses the shared `.venv` and loads the movie agent configuration from `movie_agent/.env`.
