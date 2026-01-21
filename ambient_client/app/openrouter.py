from .provider_utils import ProviderSettings, get_provider_settings


def get_openrouter_settings() -> ProviderSettings:
    return get_provider_settings(
        name="OpenRouter",
        prefix="OPENROUTER",
        enabled_env="OPENROUTER_ENABLED",
        api_url_env="OPENROUTER_API_URL",
        base_url_env="OPENROUTER_BASE_URL",
        default_url="https://openrouter.ai/api/v1/chat/completions",
        api_key_envs=["OPENROUTER_API", "OPENROUTER_API_KEY"],
        models_env="OPENROUTER_MODELS",
        model_env="OPENROUTER_MODEL",
        default_model="openai/gpt-5.2",
    )
