"""Contract checks for clients of the shared API. No external services are called."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from movie_agent.api import DIST_DIR, app
from movie_agent.agent import tmdb_search_movie, tmdb_watch_providers


class FakeTool:
    def __init__(self, result):
        self.result = result
        self.input = None

    def invoke(self, value):
        self.input = value
        return self.result


class FakeAgent:
    def __init__(self):
        self.thread_id = None

    async def ainvoke(self, value, config):
        self.thread_id = config["configurable"]["thread_id"]
        return {"messages": [AIMessage(content="Streaming answer")]}


class ApiContractTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_built_web_app_is_served_at_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        if DIST_DIR.is_dir():
            self.assertIn("<html", response.text.lower())
        else:
            self.assertEqual(response.json(), {"message": "Where2Stream API is running"})

    def test_movie_search(self):
        tool = FakeTool([{"id": 12, "title": "Example", "poster_path": "/poster.jpg"}])
        with patch("movie_agent.api.tmdb_search_movie", tool):
            response = self.client.post("/api/search-movie", json={"title": "Example"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["poster_path"], "/poster.jpg")
        self.assertEqual(tool.input["title"], "Example")

    def test_real_tools_keep_client_fields_and_provider_shape(self):
        with patch("movie_agent.agent.TMDB_API_KEY", "test"), patch(
            "movie_agent.agent._rq",
            return_value={"results": [{
                "id": 12, "title": "Example", "release_date": "2020-01-01",
                "overview": None, "poster_path": "/poster.jpg",
            }]},
        ):
            search = tmdb_search_movie.invoke({"title": "Example"})
        self.assertEqual(search[0]["poster_path"], "/poster.jpg")
        self.assertEqual(search[0]["overview"], "")

        with patch("movie_agent.agent.TMDB_API_KEY", "test"), patch(
            "movie_agent.agent._rq",
            return_value={"results": {"NL": {"flatrate": [{"provider_name": "Netflix"}]}}},
        ):
            providers = tmdb_watch_providers.invoke({"movie_id": 12})
        self.assertEqual(providers["flatrate"]["NETFLIX"], ["Netherlands"])

    def test_provider_response_and_invalid_id(self):
        tool = FakeTool({"flatrate": {"NETFLIX": ["Netherlands"]}})
        with patch("movie_agent.api.tmdb_watch_providers", tool):
            response = self.client.post("/api/watch-providers", json={"movie_id": 12})
            invalid = self.client.post("/api/watch-providers", json={"movie_id": "bad"})
        self.assertEqual(response.json()["flatrate"], [
            {"Type": "flatrate", "Provider": "NETFLIX", "Country": ["Netherlands"]}
        ])
        self.assertEqual(invalid.status_code, 400)

    def test_chat_returns_reusable_conversation_id(self):
        agent = FakeAgent()
        with patch("movie_agent.api.get_agent", return_value=agent):
            response = self.client.post("/api/agent", json={
                "query": "Where can I watch it?", "conversation_id": "conversation-1"
            })
        self.assertEqual(response.json(), {
            "conversation_id": "conversation-1", "response": "Streaming answer"
        })
        self.assertEqual(agent.thread_id, "conversation-1")


if __name__ == "__main__":
    unittest.main()
