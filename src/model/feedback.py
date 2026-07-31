"""
Defines the FeedbackManager class: turns the thumbs up/down ratings
already stored on a ChatMemory's messages into a short "feedback digest"
that gets injected into the system prompt for future replies.

This is how the chatbot "learns" within a conversation without any
actual model fine-tuning (not practical for local Ollama models): we
show it a handful of recent liked/disliked examples so it can match the
style of what worked and avoid repeating what didn't.
"""

# ==== standard imports ====
from typing import Optional

# ==== external imports ====
# (none — this module only reads data already stored on a ChatMemory)


class FeedbackManager:
    """
    Builds a compact, prompt-ready summary of a chat's thumbs up/down
    feedback so the model can adapt its future answers accordingly.
    """

    # Only the most recent N examples per category are included, so the
    # digest stays short and doesn't eat into the model's context window
    # or slow down generation.
    MAX_EXAMPLES_PER_CATEGORY = 3

    # Each Q/A snippet is capped to this many characters, again to keep
    # the digest lightweight.
    MAX_SNIPPET_LENGTH = 150

    VALID_FEEDBACK_VALUES = {"up", "down", None}

    def record_feedback(self, chat, message_id: str, feedback: Optional[str]) -> bool:
        """
        Validate and store a thumbs up/down rating on a chat message.

        Args:
            chat: The ChatMemory instance the message belongs to.
            message_id: The id of the assistant message being rated.
            feedback: "up", "down", or None to clear a rating.

        Returns:
            bool: True if the rating was valid and applied, else False.
        """
        if feedback not in self.VALID_FEEDBACK_VALUES:
            return False
        return chat.set_feedback(message_id, feedback)

    def build_feedback_digest(self, chat) -> str:
        """
        Build a short digest of liked/disliked examples from this chat.

        Args:
            chat: The ChatMemory instance to read feedback from.

        Returns:
            str: A prompt-ready digest, or "" if no feedback has been
                given yet (so callers can skip adding an empty section).
        """
        liked_examples = self._collect_examples(chat, "up")
        disliked_examples = self._collect_examples(chat, "down")

        if not liked_examples and not disliked_examples:
            return ""

        sections = []
        if liked_examples:
            sections.append(
                "Responses the user marked GOOD (match this style and approach):\n"
                + "\n".join(liked_examples)
            )
        if disliked_examples:
            sections.append(
                "Responses the user marked BAD (do not repeat these mistakes):\n"
                + "\n".join(disliked_examples)
            )

        return "\n\n".join(sections)

    def _collect_examples(self, chat, feedback_value: str) -> list:
        """
        Gather the most recent question/answer pairs rated with a given
        feedback value.

        Args:
            chat: The ChatMemory instance to scan.
            feedback_value: Either "up" or "down".

        Returns:
            list: Formatted "- Q: ... -> A: ..." strings, most recent
                last, capped at MAX_EXAMPLES_PER_CATEGORY.
        """
        examples = []
        for index, message in enumerate(chat.messages):
            if message["role"] != "assistant" or message.get("feedback") != feedback_value:
                continue

            answer = self._truncate(message["content"])
            question = self._find_preceding_user_message(chat.messages, index)

            if question:
                examples.append(f'- Q: "{self._truncate(question)}" -> A: "{answer}"')
            else:
                examples.append(f'- A: "{answer}"')

        # Keep only the most recent examples (list is chronological, so
        # the most recent ones are at the end).
        return examples[-self.MAX_EXAMPLES_PER_CATEGORY :]

    def _find_preceding_user_message(self, messages: list, assistant_index: int) -> Optional[str]:
        """
        Walk backwards from an assistant message to find the user
        question that prompted it.

        Args:
            messages: The full list of message dicts for a chat.
            assistant_index: Index of the assistant message to trace back from.

        Returns:
            str: The preceding user message content, or None if not found.
        """
        for i in range(assistant_index - 1, -1, -1):
            if messages[i]["role"] == "user":
                return messages[i]["content"]
        return None

    def _truncate(self, text: str) -> str:
        """
        Collapse whitespace and cap a string's length for use in the digest.

        Args:
            text: Raw message content.

        Returns:
            str: A single-line, length-capped version of the text.
        """
        cleaned = " ".join(text.strip().split())
        if len(cleaned) <= self.MAX_SNIPPET_LENGTH:
            return cleaned
        return cleaned[: self.MAX_SNIPPET_LENGTH].rstrip() + "..."