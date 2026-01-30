from agno.models.openrouter import OpenRouter

from config import get_llm_info


def create_model():
    llm_info = get_llm_info()

    return OpenRouter(
        **llm_info,  # pyright: ignore[reportArgumentType]
        max_tokens=1024,
    )
