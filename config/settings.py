# List of available Ollama model options for the application.
# Each option maps a friendly label to the actual Ollama model id and
# includes a short hover description for non-technical users.
MODEL_OPTIONS = [
    {
        "id": "llama3.1:latest",
        "label": "The Chatur One",
        "info": "Smart and balanced for music reasoning, lyric edits, and structured prompts. It can be a little slower on long creative flows.",
    },
    {
        "id": "mistral:latest",
        "label": "The Thinker",
        "info": "Fast and sharp, great for punchy style prompts and quick lyric variations. It may sometimes be more literal than poetic.",
    },
    {
        "id": "mistral-instruct:latest",
        "label": "The Composer",
        "info": "Good for guided songwriting prompts, tone, and format-sensitive output. It is slightly less wide-ranging than the biggest reasoning models.",
    },
    {
        "id": "llama2:13b:latest",
        "label": "The Sound Coach",
        "info": "Comfortable with creative direction and musical advice. It is reasonably efficient but may be less detailed on overly technical topics.",
    },
    {
        "id": "llama2:7b:latest",
        "label": "The Maestro",
        "info": "A smaller, more efficient Maestro that still delivers polished style and richer musical advice without the heavy 70B compute cost.",
    },
]

LLM_MODELS = [option["id"] for option in MODEL_OPTIONS]

# Base URL of the local Ollama server. On-prem/free by design — points
# at localhost so no data ever leaves the machine running this app.
OLLAMA_BASE_URL = "http://localhost:11434"

# The prompt that will be used to query the LLM model. This prompt is designed to instruct the model on how to respond to user queries about music ONLY.
LLM_PROMPT = """
    You are a helpful assistant that can answer questions about music.
    You have access to a music knowledge base and can provide information about artists, albums, songs, and genres, prompts for STYLES and LYRICS SECTION of SUNO and alike softwares; so pretty much everything about Music.
    You can also provide recommendations based on user preferences.

    However, the core of your knowledge is based on the music knowledge base, so if you don't know the answer to a question, you should say "I don't know" instead of making up an answer.
    If the topic is NOT related to music, you should answer only: "I don't know." Do not provide additional unrelated information.
    If the user provides an image or audio prompt, assume any extracted text from that upload is the user's message and evaluate whether it is music-related.

    You should be able to answer ANY question related to music.

    Format: Users may specify an exact output format. Follow it precisely.
    For lyrics, translations, or paired-language requests, preserve the requested
    line breaks and put each requested language on its own line. If the user asks
    for Italian followed by English, output one Italian line and the English
    translation on the next line in parentheses. Do not merge multiple lines into
    one paragraph. If no format is specified, answer clearly and concisely.

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
    "temperature": 0.30,
    "max_new_tokens": 1024
}
