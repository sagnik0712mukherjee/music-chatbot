"""
Defines the ChatMemory class, which represents a single chat conversation:
its messages, title, per-chat model/innovation settings, and per-message
feedback (thumbs up/down). Each ChatMemory persists itself to its own JSON
file on disk, keeping storage simple and human-readable (no database).
"""

# ==== standard imports ====
import os
from typing import Optional

# ==== external imports ====
# (none — this module only depends on the standard library and our own
# helpers module)

from config.settings import LLM_MODELS, default_model_params
from src.utils.helpers import (
    current_timestamp,
    delete_file,
    generate_id,
    load_json,
    make_chat_title,
    save_json,
)

# Folder where every chat's JSON file is stored, one file per chat.
CHATS_DIR = os.path.join("data", "chats")

# Default "Innovation" percentage, derived from the temperature already
# defined in config/settings.py, so we only maintain one source of truth.
DEFAULT_INNOVATION = int(default_model_params["temperature"] * 100)


class ChatMemory:
    """
    Represents a single chat: its messages, title, settings, and feedback.

    This class only knows about ONE chat at a time. Managing the full
    list of chats (create/list/delete) is the job of ChatManager in
    chat_search.py — keeping responsibilities separated.
    """

    def __init__(
        self,
        chat_id: Optional[str] = None,
        title: str = "New Chat",
        model_name: Optional[str] = None,
        innovation: int = DEFAULT_INNOVATION,
    ):
        """
        Create a new, empty chat in memory (not yet saved to disk).

        Args:
            chat_id: Unique chat identifier. Auto-generated if omitted.
            title: Display title, shown in the sidebar. Auto-derived
                from the first message once one is added.
            model_name: Which Ollama model this chat uses. Defaults to
                the first model listed in config/settings.py.
            innovation: Innovation percentage (0-100) driving temperature.
        """
        self.chat_id = chat_id or generate_id()
        self.title = title
        self.model_name = model_name or LLM_MODELS[0]
        self.innovation = innovation
        self.created_at = current_timestamp()
        self.updated_at = self.created_at
        # Each message is a dict: {id, role, content, timestamp, feedback}
        # feedback is one of None, "up", "down".
        self.messages = []

    def add_message(self, role: str, content: str) -> dict:
        """
        Append a new message to the chat and persist it.

        Auto-titles the chat from the first user message, mirroring
        how Claude/ChatGPT name new chats.

        Args:
            role: Either "user" or "assistant".
            content: The message text.

        Returns:
            dict: The newly created message record.
        """
        message = {
            "id": generate_id(),
            "role": role,
            "content": content,
            "timestamp": current_timestamp(),
            "feedback": None,
        }
        self.messages.append(message)

        # Auto-title the chat the first time a user message arrives.
        if role == "user" and self.title == "New Chat":
            self.title = make_chat_title(content)

        self.updated_at = current_timestamp()
        self.save()
        return message

    def set_feedback(self, message_id: str, feedback: Optional[str]) -> bool:
        """
        Attach a thumbs up/down rating to a specific assistant message.

        Args:
            message_id: The id of the message being rated.
            feedback: "up", "down", or None to clear the rating.

        Returns:
            bool: True if the message was found and updated, else False.
        """
        for message in self.messages:
            if message["id"] == message_id:
                message["feedback"] = feedback
                self.updated_at = current_timestamp()
                self.save()
                return True
        return False

    def rename(self, new_title: str) -> None:
        """
        Rename the chat (used by the sidebar's rename action).

        Args:
            new_title: The new display title for this chat.
        """
        cleaned = new_title.strip()
        if cleaned:
            self.title = cleaned
            self.updated_at = current_timestamp()
            self.save()

    def set_model(self, model_name: str) -> None:
        """
        Update which Ollama model this chat uses going forward.

        Args:
            model_name: Must be one of config.settings.LLM_MODELS.
        """
        self.model_name = model_name
        self.updated_at = current_timestamp()
        self.save()

    def set_innovation(self, innovation: int) -> None:
        """
        Update the Innovation percentage (temperature) for this chat.

        Args:
            innovation: Integer 0-100 from the UI slider.
        """
        self.innovation = innovation
        self.updated_at = current_timestamp()
        self.save()

    def get_history_for_prompt(self) -> list:
        """
        Get the conversation so far as plain role/content pairs.

        Strips out feedback/id/timestamp metadata, since the LLM only
        needs to see the conversation itself.

        Returns:
            list: [{"role": "user"/"assistant", "content": str}, ...]
        """
        return [
            {"role": m["role"], "content": m["content"]} for m in self.messages
        ]

    def to_dict(self) -> dict:
        """
        Serialize this chat into a plain dictionary for JSON storage.

        Returns:
            dict: Full chat state, ready for json.dump.
        """
        return {
            "chat_id": self.chat_id,
            "title": self.title,
            "model_name": self.model_name,
            "innovation": self.innovation,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMemory":
        """
        Reconstruct a ChatMemory instance from a dictionary (loaded JSON).

        Args:
            data: Dictionary previously produced by to_dict().

        Returns:
            ChatMemory: The reconstructed chat object.
        """
        chat = cls(
            chat_id=data["chat_id"],
            title=data["title"],
            model_name=data.get("model_name", LLM_MODELS[0]),
            innovation=data.get("innovation", DEFAULT_INNOVATION),
        )
        chat.created_at = data.get("created_at", chat.created_at)
        chat.updated_at = data.get("updated_at", chat.updated_at)
        chat.messages = data.get("messages", [])
        return chat

    def _file_path(self) -> str:
        """
        Build the on-disk JSON file path for this chat.

        Returns:
            str: Path like "data/chats/<chat_id>.json".
        """
        return os.path.join(CHATS_DIR, f"{self.chat_id}.json")

    def save(self) -> None:
        """Persist the current chat state to its JSON file on disk."""
        save_json(self._file_path(), self.to_dict())

    @classmethod
    def load(cls, chat_id: str) -> Optional["ChatMemory"]:
        """
        Load a chat from disk by its id.

        Args:
            chat_id: The chat's unique identifier.

        Returns:
            ChatMemory: The loaded chat, or None if no file exists for it.
        """
        file_path = os.path.join(CHATS_DIR, f"{chat_id}.json")
        data = load_json(file_path)
        if data is None:
            return None
        return cls.from_dict(data)

    def delete(self) -> None:
        """Delete this chat's JSON file from disk."""
        delete_file(self._file_path())