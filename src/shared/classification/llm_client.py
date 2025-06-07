"""Light-weight wrapper around an OpenAI-compatible ChatCompletion endpoint.

The wrapper keeps the external dependency isolated so that unit tests can mock
it out easily without requiring network connectivity or valid API keys.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

try:
    import openai  # type: ignore
except ImportError:  # pragma: no cover – allow codebase to run without openai
    openai = None  # type: ignore


class LLMClient:  # noqa: D101 – docstring below
    _DEFAULT_MODEL = "gpt-3.5-turbo-0125"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str | None = None,
        backend: Any | None = None,
    ) -> None:
        """Create a new :class:`LLMClient` instance.

        Parameters
        ----------
        api_key
            API key for the OpenAI backend.  Ignored if *backend* is supplied.
        model
            Model name to use for chat completions.
        backend
            Optional object exposing an ``chat.completions.create`` method that
            mimics :pymod:`openai`.  Supplying *backend* is useful for unit
            testing to avoid real network calls.
        """
        self._model = model or self._DEFAULT_MODEL
        if backend is not None:
            # Testing stub.
            self._backend = backend
        else:
            if openai is None:
                raise ImportError(
                    "openai package not installed and no backend provided. "
                    "Install openai>=1.0 or inject a stub backend."
                )
            self._backend = openai.OpenAI(api_key=api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chat_completion(self, messages: List[dict], temperature: float = 0.0) -> str:  # noqa: D401
        """Synchronously call the chat completion endpoint and return **content**.

        Any exception bubbles up; caller can catch and retry.
        """
        logging.debug("LLMClient.request: %s", messages)
        response = self._backend.chat.completions.create(
            model=self._model, messages=messages, temperature=temperature
        )
        # OpenAI v1 style.
        return response.choices[0].message.content 