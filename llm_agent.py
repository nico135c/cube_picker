import requests
import json
import re
from omegaconf import DictConfig

# ============================
# Modular LLM Agent Class
# ============================
class LLM_Agent:
    """
    A modular LLM agent that:
      - accepts a DictConfig describing the LLM
      - sends system + user prompts to the model
      - supports streaming responses
      - parses returned JSON
    """

    def __init__(self, llm_config: DictConfig):
        self.model_name = llm_config.model_name
        self.max_retries = llm_config.max_retries
        self.llm_url = llm_config.url
        self.system_prompt = llm_config.system_prompt

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def process_request(self, user_prompt: str, timeout: float = 15.0):
        """
        Sends user + system prompt to the model, handles streaming,
        parses JSON, and returns the final parsed object.
        """

        request_body = {
            "model": self.model_name,
            "prompt": self.system_prompt + user_prompt,
            "stream": False,
        }

        retries = 0

        while True:
            try:
                response_text = self._stream_response(request_body, timeout)
                cleaned = self._strip_markdown(response_text)
                parsed = self._parse_json(cleaned)
                return parsed

            except requests.Timeout:
                if retries < self.max_retries:
                    retries += 1
                    continue
                raise print("Request timed out.")

            except requests.ConnectionError:
                if retries < self.max_retries:
                    retries += 1
                    continue
                raise print("Connection error.")

            except requests.RequestException as e:
                if retries < self.max_retries:
                    retries += 1
                    continue
                raise print(str(e))

            except json.JSONDecodeError as e:
                if retries < self.max_retries:
                    retries += 1
                    continue
                raise print(f"JSON decode error: {e}")

    # ---------------------------------------------------------
    # Internal networking helpers
    # ---------------------------------------------------------
    def _stream_response(self, message: dict, timeout: float) -> str:
        """
        Streams token chunks from model and returns the final concatenated result.
        """

        collected = ""

        with requests.post(self.llm_url, data=json.dumps(message), stream=True, timeout=timeout) as r:
            for raw_line in r.iter_lines(decode_unicode=True, delimiter=b'\n'):
                if not raw_line:
                    continue

                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                # streaming token chunks
                if "response" in event:
                    collected += event["response"]

                # done
                if event.get("done", False):
                    break

        return collected

    # ---------------------------------------------------------
    # Parsing helpers
    # ---------------------------------------------------------
    def _strip_markdown(self, text: str) -> str:
        """
        Removes ```json ... ``` fences if present.
        """
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def _parse_json(self, text: str):
        """
        Parses the JSON and normalizes to list-of-objects.
        """
        parsed = json.loads(text)

        # Normalize output to always be a list
        if isinstance(parsed, dict):
            return [parsed]
        return parsed
