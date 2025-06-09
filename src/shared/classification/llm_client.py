"""Light-weight wrapper around an OpenAI-compatible ChatCompletion endpoint.

The wrapper keeps the external dependency isolated so that unit tests can mock
it out easily without requiring network connectivity or valid API keys.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional
import os

# --- Optional back-ends -----------------------------------------------------
# We defer-import these so the project can run even when a given SDK is
# absent – for example, unit tests or environments that only need Gemini.

try:  # noqa: WPS229 – ignore cyclomatic complexity for import fallbacks
    import openai  # type: ignore
except ImportError:  # pragma: no cover – allow codebase to run without openai
    openai = None  # type: ignore

try:
    # Google Generative AI Python SDK (Gemini)
    import google.generativeai as genai  # type: ignore
except ImportError:  # pragma: no cover – optional dependency
    genai = None  # type: ignore


class LLMClient:  # noqa: D101 – docstring below
    # Default models per provider
    _DEFAULT_OPENAI_MODEL = "gpt-3.5-turbo-0125"
    _DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"

    _PROVIDER_OPENAI = "openai"
    _PROVIDER_GEMINI = "gemini"

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
        # ------------------------------------------------------------------
        # Select backend provider (priority order):
        #   1) Explicit *backend* injection (tests)
        #   2) If the google-generativeai SDK is available **and** a Gemini
        #      API key is present (param or env var) → use Gemini.
        #   3) Otherwise fall back to OpenAI.
        # ------------------------------------------------------------------

        if backend is not None:
            self._provider = "stub"
            self._backend = backend
            self._model = model or "test-stub"
            return

        # Auto-detect Gemini first – preferred provider for this project.
        gemini_key = api_key or os.getenv("GEMINI_API_KEY")
        if genai is not None and gemini_key:
            genai.configure(api_key=gemini_key)
            self._provider = self._PROVIDER_GEMINI
            self._model = model or self._DEFAULT_GEMINI_MODEL
            self._backend = genai.GenerativeModel(self._model)
            return

        # Fallback: OpenAI
        if openai is None:
            raise ImportError(
                "Neither google-generativeai (Gemini) nor openai SDK is "
                "available, and no backend stub provided."
            )

        openai_key = api_key or os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError(
                "OPENAI_API_KEY must be set when using the OpenAI backend."
            )

        self._provider = self._PROVIDER_OPENAI
        self._model = model or self._DEFAULT_OPENAI_MODEL
        self._backend = openai.OpenAI(api_key=openai_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chat_completion(self, messages: List[dict], temperature: float = 0.0) -> str:  # noqa: D401
        """Synchronously call the chat completion endpoint and return **content**.

        Any exception bubbles up; caller can catch and retry.
        """
        logging.debug("LLMClient.request: %s", messages)

        if self._provider == self._PROVIDER_OPENAI:
            response = self._backend.chat.completions.create(
                model=self._model, messages=messages, temperature=temperature
            )
            return response.choices[0].message.content

        if self._provider == self._PROVIDER_GEMINI:
            # Convert list-of-role dicts → single prompt string. For Gemini we
            # concatenate user/assistant turns; this is good enough for our
            # simple prompt usage (single user message).
            prompt_parts = []
            for m in messages:
                role = m.get("role", "user")
                prompt_parts.append(f"## {role}\n{m['content']}")
            prompt = "\n\n".join(prompt_parts)
            
            # Gemini uses generation_config for temperature
            generation_config = genai.types.GenerationConfig(
                temperature=temperature
            )
            response = self._backend.generate_content(
                prompt, 
                generation_config=generation_config
            )
            return response.text  # type: ignore[attr-defined]

        # Stub backend – assume it returns string directly.
        return self._backend(messages)  # type: ignore[misc] 