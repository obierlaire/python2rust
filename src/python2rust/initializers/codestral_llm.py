"""
This module defines the CodestralLLM class, a custom implementation
of LangChain's LLM for interacting with the Codestral API.
"""

from typing import Any, List, Mapping, Optional
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
import httpx


class CodestralLLM(LLM):
    """
    A custom LLM class for interacting with the Codestral API.

    This class extends the LangChain LLM base class to provide integration
    with the Codestral API for language model tasks. It handles API key
    authentication, request formatting, and response parsing.

    Attributes:
        api_key (str): The API key for authenticating with the Codestral API.
        model (str): The name of the Codestral model to use (default: "codestral-7b").
        temperature (float): The sampling temperature to use (default: 0.1).
        max_tokens (Optional[int]): The maximum number of tokens to generate (default: None).
        base_url (str): The base URL for the Codestral API endpoint.
    """

    api_key: str
    model: str = "codestral-7b"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    base_url: str = "https://codestral.mistral.ai/v1/chat/completions"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "messages": [{"role": "user", "content": prompt}],
            "model": self.model,
            "temperature": self.temperature
        }

        if self.max_tokens:
            data["max_tokens"] = self.max_tokens

        if stop:
            data["stop"] = stop

        try:
            response = httpx.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30.0
            )
            response.raise_for_status()

            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]

        except Exception as e:
            raise ValueError(f"Error calling Codestral API: {str(e)}") from e

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {
            "model_name": f"codestral-{self.model}",
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

    @property
    def _llm_type(self) -> str:
        return "codestral"
