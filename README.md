# Music Muse — Local Music Chatbot

Music Muse is an on-premise music assistant built with Streamlit and Ollama. It helps songwriters, producers, and music fans ask questions about lyrics, genres, composition, production, and music prompts — while keeping conversations local and private.

## Features

- Friendly, Claude-style chat UI with a polished red/black theme.
- Local Ollama backend for on-premise LLM inference.
- Per-chat model selection using friendly labels like "The Chatur One" and "The Maestro".
- Persistent chat history stored as JSON files in `data/chats`.
- Full-text search across conversations.
- Thumbs up / thumbs down feedback on assistant replies.
- Context-aware music guardrails to refuse off-topic queries.
- Adjustable "Innovation" slider for temperature control.

## Project Structure

- `app.py` — Streamlit entrypoint.
- `config/settings.py` — Model registry, Ollama settings, and system prompt.
- `src/ui_ux/streamlit_ui.py` — Chat interface, model picker, layout, and styling.
- `src/model/chat_model.py` — Ollama wrapper, prompt composition, and reply generation.
- `src/model/feedback.py` — Feedback digest builder for adaptive chat behavior.
- `src/model/guardrails.py` — Music-topic guardrail logic.
- `src/memory/chat_memory.py` — Chat persistence and per-chat settings.
- `src/memory/chat_search.py` — SQLite FTS chat search and chat management.
- `src/utils/helpers.py` — Utility helpers for IDs, timestamps, and JSON storage.

## Model Options

The app exposes friendly model names while mapping them to underlying Ollama models:

- `The Chatur One` — `llama3.1:latest`
- `The Thinker` — `mistral:latest`
- `The Composer` — `mistral-instruct:latest`
- `The Sound Coach` — `llama2:13b:latest`
- `The Maestro` — `llama2:7b:latest` (smaller and more efficient than 70B)

> Note: `llama2:70b:latest` was removed as the default Maestro choice in favor of a lighter `llama2:7b:latest` alternative.

## Installation

1. Clone the repo:

```bash
git clone https://github.com/sagnik0712mukherjee/music-chatbot.git
cd music-chatbot
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
streamlit run app.py --server.headless true --server.port 8501
```

## Ollama Setup

Make sure your local Ollama server is running and reachable at `http://localhost:11434`.

Pull the models you want to use:

```bash
ollama pull llama3.1:latest
ollama pull mistral:latest
ollama pull mistral-instruct:latest
ollama pull llama2:13b:latest
ollama pull llama2:7b:latest
```

## Data Storage

- Chat state is stored in `data/chats/` as JSON files.
- Search uses SQLite FTS internally for fast conversation lookup.

## Usage

- Use the sidebar to create, rename, open, or delete chats.
- Ask music questions in the chat composer.
- Choose a model from the friendly selector and hover the `(i)` icon for more details.
- Adjust the `Innovation` slider for more creative, higher-temperature responses.
- Rate assistant messages with 👍 / 👎 to influence later replies.

## Troubleshooting

- If the app cannot connect to Ollama, verify the server is running locally and reachable at `http://localhost:11434`.
- If a model fails to load, run `ollama pull <model-id>` for the chosen option.
- If the UI is slow, try switching to a smaller model like `The Maestro` (`llama2:7b:latest`) instead of larger models.
- Audio input is only supported via the live microphone recorder in the composer. The app no longer supports direct MP3 or audio file uploads.
- Image uploads are supported only for raw image decoding and music translation. The app now encodes uploaded images as Base64 bytes for the model instead of relying on Tesseract OCR.
- If chat history is missing, confirm `data/chats/` exists and is writable by the app.

## Author

Built by [sagnik0712mukherjee](https://github.com/sagnik0712mukherjee)
