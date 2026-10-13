"""Configure the SQL agent for Google, OpenAI, OpenRouter, or a local SLM.

Set ``LLM_PROVIDER`` to ``google`` (default), ``openai``, ``openrouter``, or
``slm``. Configure models independently with ``GOOGLE_MODEL_NAME``,
``OPENAI_MODEL_NAME``, ``OPENROUTER_MODEL_NAME``, and ``SLM_MODEL_NAME``.
``MODEL_NAME`` remains a Google-only legacy alias. When Google is selected and
``OPENROUTER_API_KEY`` is set, OpenRouter is used as a fallback. OpenRouter
defaults to ``openrouter/free`` unless ``OPENROUTER_MODEL_NAME`` is set.
``OPENROUTER_MAX_TOKENS`` defaults to 4096 to limit generated output size.
Use ``GEMINI_API_KEY`` (or ``GOOGLE_API_KEY``), ``OPENAI_API_KEY``, or
``OPENROUTER_API_KEY`` for the corresponding hosted provider. Local SLMs must
expose an OpenAI-compatible API; ``SLM_BASE_URL`` defaults to Ollama's
``http://localhost:11434/v1`` and ``SLM_API_KEY`` defaults to ``ollama``.
"""

import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

# Import separated schema and prompt
from src.schemas import SQLQueryResponse
from src.prompts import SYSTEM_PROMPT

# Load variables from .env
load_dotenv()

def _required_api_key(variable_name: str) -> str:
    """Return a configured API key or explain which environment variable is missing."""
    api_key = os.getenv(variable_name)
    if not api_key:
        raise EnvironmentError(
            f"Missing {variable_name} environment variable. "
            "Add it to your .env file or export it in your shell."
        )
    return api_key


def _create_openrouter_model(model_name: str) -> OpenAIChatModel:
    """Build an OpenRouter model with a bounded output-token budget."""
    try:
        max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "4096"))
    except ValueError as err:
        raise ValueError("OPENROUTER_MAX_TOKENS must be a positive integer.") from err
    if max_tokens < 1:
        raise ValueError("OPENROUTER_MAX_TOKENS must be a positive integer.")

    provider = OpenAIProvider(
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=_required_api_key("OPENROUTER_API_KEY"),
    )
    return OpenAIChatModel(
        model_name,
        provider=provider,
        settings={"max_tokens": max_tokens},
    )


def _create_model():
    """Build the selected provider's model from environment configuration."""
    provider_name = os.getenv("LLM_PROVIDER", "google").strip().lower()
    default_models = {
        "google": "gemini-3.6-flash",
        "openai": "gpt-4o-mini",
        "openrouter": "openrouter/free",
        "slm": "llama3.2",
    }
    if provider_name not in default_models:
        options = ", ".join(default_models)
        raise ValueError(f"Unsupported LLM_PROVIDER {provider_name!r}. Choose from: {options}.")

    model_env_names = {
        "google": "GOOGLE_MODEL_NAME",
        "openai": "OPENAI_MODEL_NAME",
        "openrouter": "OPENROUTER_MODEL_NAME",
        "slm": "SLM_MODEL_NAME",
    }
    model_name = os.getenv(model_env_names[provider_name])
    if not model_name and provider_name == "google":
        model_name = os.getenv("MODEL_NAME")
    model_name = (model_name or default_models[provider_name]).strip()

    if provider_name == "google":
        # Accept the old GEMINI_API_KEY name and Google's standard GOOGLE_API_KEY.
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "Missing GEMINI_API_KEY or GOOGLE_API_KEY environment variable. "
                "Add one to your .env file or export it in your shell."
            )
        google_model = GoogleModel(model_name, provider=GoogleProvider(api_key=api_key))
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            return google_model

        openrouter_model_name = (
            os.getenv("OPENROUTER_MODEL_NAME") or default_models["openrouter"]
        ).strip()
        openrouter_model = _create_openrouter_model(openrouter_model_name)
        return FallbackModel(google_model, openrouter_model)

    if provider_name == "openai":
        provider = OpenAIProvider(api_key=_required_api_key("OPENAI_API_KEY"))
        return OpenAIChatModel(model_name, provider=provider)

    if provider_name == "openrouter":
        return _create_openrouter_model(model_name)

    # SLMs such as Ollama can expose an OpenAI-compatible local API.
    provider = OpenAIProvider(
        base_url=os.getenv("SLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("SLM_API_KEY", "ollama"),
    )
    return OpenAIChatModel(model_name, provider=provider)

sql_agent = Agent(
    _create_model(),
    output_type=SQLQueryResponse,
    system_prompt=SYSTEM_PROMPT,
)