"""Application entry point for the Music Chatbot Streamlit app."""

# ==== standard imports ====

# ==== external imports ====
import streamlit as st

from src.memory.chat_search import ChatManager
from src.model.chat_model import MusicChatModel
from src.ui_ux.streamlit_ui import render_app


@st.cache_resource
def get_chat_manager() -> ChatManager:
	"""Create and cache the persistence/search manager for this app process."""
	return ChatManager()


@st.cache_resource
def get_chat_model() -> MusicChatModel:
	"""Create and cache the Ollama model facade for this app process."""
	return MusicChatModel()


def main() -> None:
	"""Configure the page and render the Music Chatbot."""
	st.set_page_config(
		page_title="Music Muse",
		page_icon="♫",
		layout="wide",
		initial_sidebar_state="expanded",
	)
	render_app(get_chat_manager(), get_chat_model())


if __name__ == "__main__":
	main()
