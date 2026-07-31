"""
Defines the MusicChatModel class: the piece that actually talks to the
local Ollama server (via LangChain) to generate music-focused replies.

This class ties together everything built so far:
- MusicGuardrail: fast pre-filter, skips the LLM call for obviously
  off-topic questions.
- FeedbackManager: injects a digest of this chat's liked/disliked
  answers into the system prompt so the model adapts within the chat.
- ChatMemory: supplies conversation history, the chosen Ollama model,
  and the Innovation (temperature) setting for this chat.
"""

# ==== standard imports ====
# (none beyond what's re-exported below)

# ==== external imports ====
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from config.settings import LLM_PROMPT, OLLAMA_BASE_URL, default_model_params
from src.model.feedback import FeedbackManager
from src.model.guardrails import MusicGuardrail
from src.utils.helpers import innovation_to_temperature


class MusicChatModel:
    """
    Generates music-focused chat replies using a local Ollama model,
    respecting each chat's chosen model, Innovation setting, and
    accumulated feedback.
    """

    def __init__(self):
        """Set up the guardrail and feedback helpers this model relies on."""
        self.guardrail = MusicGuardrail()
        self.feedback_manager = FeedbackManager()

    def generate_reply(self, chat, user_message: str) -> str:
        """
        Generate the assistant's reply to a new user message.

        Does NOT persist anything to disk — the caller (ChatManager) is
        responsible for saving both the user message and this reply.

        Args:
            chat: The ChatMemory for the current conversation (supplies
                history, model_name, and innovation).
            user_message: The new message the user just sent, not yet
                part of chat.messages.

        Returns:
            str: The assistant's reply text (or a guardrail/error message).
        """
        # Fast pre-filter: skip the LLM entirely for obviously off-topic asks.
        if not self.guardrail.is_music_related(user_message) and not self._has_music_context(chat):
            return self.guardrail.get_refusal_message()

        system_prompt = self._build_system_prompt(chat)
        messages = self._build_messages(system_prompt, chat, user_message)
        llm = self._build_llm(chat)

        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as error:
            # Ollama not running, model not pulled, network issue, etc.
            # Fail gracefully with an actionable message instead of
            # crashing the Streamlit app.
            return self._build_error_message(chat, error)

    def _has_music_context(self, chat) -> bool:
        """Allow short follow-ups when the existing conversation is musical.

        A follow-up such as "give me the style prompt" may contain no music
        keyword on its own, but it is unambiguous when the prior turns discuss
        lyrics, genres, songs, or production.
        """
        recent_messages = chat.get_history_for_prompt()[-6:]
        return any(
            entry["role"] == "user" and self.guardrail.is_music_related(entry["content"])
            for entry in recent_messages
        )

    def _build_system_prompt(self, chat) -> str:
        """
        Assemble the full system prompt: the base music-assistant
        instructions plus this chat's feedback digest, if any.

        Args:
            chat: The ChatMemory for the current conversation.

        Returns:
            str: The complete system prompt to send to the model.
        """
        digest = self.feedback_manager.build_feedback_digest(chat)
        if not digest:
            return LLM_PROMPT

        return (
            f"{LLM_PROMPT}\n\n"
            "Additional guidance based on feedback earlier in this "
            f"conversation:\n{digest}"
        )

    def _build_messages(self, system_prompt: str, chat, user_message: str) -> list:
        """
        Convert the system prompt, prior chat history, and the new user
        message into LangChain message objects ready for ChatOllama.

        Args:
            system_prompt: Output of _build_system_prompt().
            chat: The ChatMemory for the current conversation.
            user_message: The new message the user just sent.

        Returns:
            list: SystemMessage, followed by alternating HumanMessage /
                AIMessage for history, ending with the new HumanMessage.
        """
        messages = [SystemMessage(content=system_prompt)]

        history = chat.get_history_for_prompt()
        for entry in history:
            if entry["role"] == "user":
                messages.append(HumanMessage(content=entry["content"]))
            else:
                messages.append(AIMessage(content=entry["content"]))

        # The UI persists the user turn before generation so it can remain
        # visible while Ollama is thinking. Do not send that turn twice.
        if not history or history[-1] != {"role": "user", "content": user_message}:
            messages.append(HumanMessage(content=user_message))
        return messages

    def _build_llm(self, chat) -> ChatOllama:
        """
        Construct a ChatOllama client configured for this chat's chosen
        model and Innovation (temperature) setting.

        Args:
            chat: The ChatMemory for the current conversation.

        Returns:
            ChatOllama: Ready to call .invoke() on.
        """
        return ChatOllama(
            model=chat.model_name,
            temperature=innovation_to_temperature(chat.innovation),
            num_predict=default_model_params["max_new_tokens"],
            base_url=OLLAMA_BASE_URL,
        )

    def _build_error_message(self, chat, error: Exception) -> str:
        """
        Turn a low-level connection/model error into a clear, actionable
        message for the user, rather than surfacing a raw stack trace.

        Args:
            chat: The ChatMemory for the current conversation (used to
                name the model that failed).
            error: The exception raised by the Ollama client.

        Returns:
            str: A friendly explanation with next steps.
        """
        return (
            f"I couldn't reach the '{chat.model_name}' model on Ollama. "
            "Please make sure the Ollama server is running locally and "
            f"that this model has been pulled (`ollama pull {chat.model_name}`).\n\n"
            f"Technical detail: {error}"
        )