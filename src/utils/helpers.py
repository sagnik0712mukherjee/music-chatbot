"""
Small, stateless helper functions shared across the Music Chatbot app.

Keeping these here (instead of scattering them across modules) means every
other file can stay focused on its own single responsibility, per our
"no over-engineering" rule.
"""

# ==== standard imports ====
import json
import os
import re
import uuid
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def generate_id() -> str:
    """
    Generate a short, unique identifier.

    Used for chat IDs and message IDs. We use uuid4 (random, no
    collisions in practice) and shorten it to keep filenames/URLs tidy.

    Returns:
        str: A 12-character unique hex identifier.
    """
    return uuid.uuid4().hex[:12]


def current_timestamp() -> str:
    """
    Get the current time in IST as an ISO-8601 formatted string.

    Using ISO format keeps timestamps sortable as plain strings and
    easy to serialize into JSON without extra conversion logic. Always
    pinned to IST (Asia/Kolkata) so timestamps are consistent no matter
    where the app/server is hosted.

    Returns:
        str: Current IST timestamp, e.g. "2026-07-28T20:02:05+05:30".
    """
    return datetime.now(IST).isoformat(timespec="seconds")


def save_json(file_path: str, data: dict) -> None:
    """
    Write a dictionary to disk as pretty-printed JSON.

    Creates parent directories if they don't already exist, so callers
    never need to worry about folder setup.

    Args:
        file_path: Destination path for the JSON file.
        data: The dictionary to serialize and save.
    """
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(file_path: str) -> Optional[dict]:
    """
    Read a JSON file from disk into a dictionary.

    Args:
        file_path: Path to the JSON file to read.

    Returns:
        dict: The parsed JSON content, or None if the file doesn't exist.
    """
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_file(file_path: str) -> None:
    """
    Delete a file from disk if it exists.

    Silently does nothing if the file is already absent, so callers
    don't need to guard every delete with an existence check.

    Args:
        file_path: Path to the file to delete.
    """
    if os.path.exists(file_path):
        os.remove(file_path)


def make_chat_title(first_message: str, max_length: int = 40) -> str:
    """
    Derive a short, readable chat title from the first user message.

    Mirrors how Claude/ChatGPT auto-title new chats: take the first
    line, trim whitespace, and truncate with an ellipsis if too long.

    Args:
        first_message: The first user message in the chat.
        max_length: Maximum number of characters before truncating.

    Returns:
        str: A clean, display-ready chat title.
    """
    # Collapse the message to its first line and strip extra whitespace.
    stripped = first_message.strip()
    first_line = stripped.splitlines()[0] if stripped else "New Chat"
    first_line = re.sub(r"\s+", " ", first_line).strip()

    if not first_line:
        return "New Chat"

    if len(first_line) <= max_length:
        return first_line

    return first_line[:max_length].rstrip() + "..."


def innovation_to_temperature(innovation_percent: int) -> float:
    """
    Convert the UI's "Innovation" percentage (0-100) into an LLM
    temperature value used for responses.

    Args:
        innovation_percent: Integer percentage from the UI slider.

    Returns:
        float: Temperature value, clamped to 0.0-0.15 for accuracy.
    """
    # Clamp to defensive bounds in case the UI ever sends a bad value.
    clamped = max(0, min(100, innovation_percent))
    temperature = round(clamped / 100, 2)
    return min(temperature, 0.15)


def list_json_files(directory: str) -> list:
    """
    List all JSON file paths within a directory (non-recursive).

    Args:
        directory: Folder to scan for .json files.

    Returns:
        list: Full paths to each .json file found, empty list if the
            directory doesn't exist yet.
    """
    if not os.path.isdir(directory):
        return []

    return [
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if name.endswith(".json")
    ]