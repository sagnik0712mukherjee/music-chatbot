# List of available Ollama model options for the application.
# Each option maps a friendly label to the actual Ollama model id and
# includes a short hover description for non-technical users.
MODEL_OPTIONS = [
    {
        "id": "qwen3.6:35b-a3b",
        "label": "The Thinker",
        "info": "Large-scale reasoning for precise structure, key theory, and polished music guidance.",
    },
    {
        "id": "deepseek-r1:14b",
        "label": "The Maestro",
        "info": "Creative, accurate music generation with strong style and lyric fidelity.",
    },
]

LLM_MODELS = [option["id"] for option in MODEL_OPTIONS]

# Base URL of the local Ollama server. On-prem/free by design — points
# at localhost so no data ever leaves the machine running this app.
OLLAMA_BASE_URL = "http://localhost:11434"

# The prompt that will be used to query the LLM model. This prompt is designed to instruct the model on how to respond to user queries about music ONLY.
LLM_PROMPT = """
    You are a strict music assistant. Your only job is to answer music-related questions.
    Answer questions about lyrics, composition, songwriting, music theory, genres,
    production, notation, and music prompts. If a user asks anything outside of
    music, respond exactly: "I don't know." Do not add any extra explanation.

    When answering music questions, do not hallucinate. If you do not know the
    answer with confidence, respond exactly: "I don't know." Do not invent facts,
    song lyrics, artist biographies, chord formulas, or key relationships.

    If a user asks you to verify or correct your answer, do not blindly accept the
    correction. Instead say: "I will verify that, but my internal knowledge says..."
    and then provide a strictly supported answer or "I don't know." Do not change
    answers based solely on user assertions.

    If the user provides an image or audio prompt, treat any extracted text as the
    user's message and determine whether it is music-related.

    Format: Follow the user's requested format exactly. For lyrics or translation
    requests, preserve line breaks and place each requested language on its own line.
    If no format is specified, answer clearly and concisely.

    Here is the user's question. Follow all instructions strictly before answering:


"""

def get_model_option(model_id: str) -> dict:
    """Return the model option metadata for a given model id."""
    for option in MODEL_OPTIONS:
        if option["id"] == model_id:
            return option
    return MODEL_OPTIONS[0]


def get_model_option_by_id(model_id: str) -> dict:
    """Alias for get_model_option to support UI lookup by persisted id."""
    return get_model_option(model_id)


def get_model_option_by_label(label: str) -> dict:
    """Return the model option metadata for a given friendly label."""
    for option in MODEL_OPTIONS:
        if option["label"] == label:
            return option
    return MODEL_OPTIONS[0]


def model_labels() -> list:
    """Return the list of friendly model labels for the UI."""
    return [option["label"] for option in MODEL_OPTIONS]

# The parameters for the LLM model. These parameters can be adjusted to change the behavior of the model.
default_model_params = {
    "temperature": 0.08,
    "max_new_tokens": 1024
}
