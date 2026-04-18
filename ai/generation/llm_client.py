import requests
import json
from typing import Iterator


OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "mistral:7b-instruct-q4_0"


class LLMClient:
    """
    Sends prompts to Ollama and returns responses.
    Supports both full responses and streaming (token by token).
    """

    def __init__(self, model: str = DEFAULT_MODEL, ollama_url: str = OLLAMA_URL):
        self.model = model
        self.url = ollama_url

    def generate(self, messages: list[dict]) -> str:
        """Blocking call — waits for full response then returns it."""
        response = requests.post(self.url, json={
            "model": self.model,
            "messages": messages,
            "stream": False,
        }, timeout=120)
        response.raise_for_status()
        return response.json()["message"]["content"]

    def stream(self, messages: list[dict]) -> Iterator[str]:
        """
        Streaming call — yields tokens as they arrive.
        Use this for the FastAPI SSE endpoint so the UI
        shows text appearing word by word.

        Usage:
            for token in client.stream(messages):
                print(token, end="", flush=True)
        """
        response = requests.post(self.url, json={
            "model": self.model,
            "messages": messages,
            "stream": True,
        }, stream=True, timeout=120)
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            token = data.get("message", {}).get("content", "")
            if token:
                yield token
            if data.get("done"):
                break

    def is_available(self) -> bool:
        try:
            r = requests.get(
                self.url.replace("/api/chat", "/api/tags"), timeout=5
            )
            return r.status_code == 200
        except requests.exceptions.ConnectionError:
            return False