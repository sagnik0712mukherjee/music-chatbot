"""Streamlit presentation layer for the Music Chatbot.

The module keeps Streamlit-specific state and rendering here while leaving
chat persistence, search, and model calls to the modules underneath it.
"""

# ==== standard imports ====
from html import escape
import time

# ==== external imports ====
import streamlit as st

from config.settings import LLM_MODELS
from src.model.feedback import FeedbackManager


def render_app(chat_manager, chat_model) -> None:
	"""Render the complete application for the current Streamlit run.

	Args:
		chat_manager: ChatManager instance used for persistence and search.
		chat_model: MusicChatModel instance used to generate replies.
	"""
	_initialise_state(chat_manager)
	_inject_styles()
	_render_sidebar(chat_manager)

	active_chat = chat_manager.get_chat(st.session_state.active_chat_id)
	if active_chat is None:
		active_chat = chat_manager.create_chat()
		st.session_state.active_chat_id = active_chat.chat_id

	_render_main(chat_manager, chat_model, active_chat)


def _initialise_state(chat_manager) -> None:
	"""Create session-state values and ensure an active chat exists."""
	if "active_chat_id" not in st.session_state:
		chats = chat_manager.list_chats()
		st.session_state.active_chat_id = chats[0].chat_id if chats else None
	st.session_state.setdefault("search_open", False)
	st.session_state.setdefault("search_query", "")
	st.session_state.setdefault("rename_chat_id", None)


def _inject_styles() -> None:
	"""Add compact styling for the music-focused two-column layout."""
	st.markdown(
		"""
		<style>
		:root { --canvas: #110f11; --panel: #191719; --ink: #ffffff; --muted: #d7cbcd; --line: rgba(255,255,255,.18); --accent: #f0444c; --accent-dark: #b8202d; }
		.stApp { background: linear-gradient(120deg, #120f12 0%, #3a1118 42%, #fff7f7 125%) !important; }
		.stApp::before { content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .18; background-image: repeating-linear-gradient(115deg, transparent 0 72px, rgba(255,255,255,.22) 73px, transparent 74px 145px); }
		[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"],
		[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child { background: transparent !important; }
		[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMain"] * { color: var(--ink); }
		[data-testid="stSidebar"] { background: rgba(13, 12, 14, .88) !important; border-right: 1px solid var(--line); }
		[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
		[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] p,
		[data-testid="stCaptionContainer"], label, small { color: var(--ink) !important; }
		[data-testid="stCaptionContainer"] { opacity: .8; }
		[data-baseweb="select"] > div, [data-baseweb="input"] > div,
		[data-testid="stTextArea"] textarea, input { background: #090909 !important; color: #ffffff !important; border: 1px solid rgba(255,255,255,.35) !important; }
		[data-baseweb="select"] svg { fill: #ffffff !important; }
		[data-baseweb="select"] { border-radius: 10px; box-shadow: 0 8px 22px rgba(0,0,0,.22); }
		[data-testid="stSelectbox"] { max-width: 250px; margin: 0 auto; }
		[data-testid="stSelectbox"] label, [data-testid="stSelectbox"] label p { text-align: center !important; width: 100%; }
		[data-testid="stSelectbox"] [data-baseweb="select"] > div { justify-content: center; }
		[data-testid="stSelectbox"] [data-baseweb="select"] input { text-align: center; }
		[data-testid="stTextArea"] textarea::placeholder, input::placeholder { color: #bdb5b7 !important; }
		[data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button { color: #ffffff !important; border-color: var(--accent) !important; background: var(--accent) !important; font-weight: 700; }
		[data-testid="stButton"] button:hover, [data-testid="stFormSubmitButton"] button:hover { background: var(--accent-dark) !important; border-color: #ff7b80 !important; }
		[data-testid="stSlider"] { background: #090909 !important; border: 1px solid rgba(255,255,255,.28); border-radius: 10px; padding: .5rem .75rem .25rem; box-shadow: 0 8px 22px rgba(0,0,0,.22); }
		[data-testid="stSlider"] label, [data-testid="stSlider"] label p { color: #ffffff !important; }
		[data-testid="stSlider"] [role="slider"] { background: var(--accent) !important; border-color: #ffffff !important; }
		[data-testid="stSlider"] [data-baseweb="slider"] > div > div { background: var(--accent) !important; }
		[data-testid="stChatMessage"] { background: rgba(0,0,0,.35); border: 1px solid var(--line); border-radius: 12px; margin: .7rem 0; }
		.pending-message { opacity: .52; filter: saturate(.65); }
		[data-testid="stChatInput"] { width: 100% !important; max-width: none !important; background: rgba(10,10,10,.88); border: 1px solid var(--line); border-radius: 12px; }
		[data-testid="stChatInput"] textarea { background: #090909 !important; color: #ffffff !important; }
		.brand { display: flex; align-items: center; gap: .65rem; margin: .2rem 0 1.4rem; }
		.brand-mark { display: grid; place-items: center; width: 2.1rem; height: 2.1rem; border-radius: 50%; background: var(--accent); color: white; font-size: 1.15rem; box-shadow: 0 0 0 5px rgba(240,68,76,.15), 0 0 22px rgba(240,68,76,.35); }
		.brand-name { color: var(--ink); font-size: 1.1rem; font-weight: 700; letter-spacing: .01em; }
		.welcome { margin: 7vh auto 2rem; max-width: 720px; text-align: center; }
		.welcome-kicker { color: #ff8d91; font-size: .78rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; margin-bottom: .7rem; }
		.welcome h1 { color: var(--ink); font-size: clamp(2rem, 5vw, 3.4rem); margin-bottom: .4rem; text-shadow: 0 3px 22px rgba(240,68,76,.35); }
		.welcome p { color: var(--muted); font-size: 1.05rem; }
		.search-result { border-bottom: 1px solid var(--line); padding: .55rem 0; }
		.search-result-title { color: var(--ink); font-weight: 700; font-size: .9rem; }
		.search-result-snippet { color: var(--muted); font-size: .8rem; line-height: 1.35; }
		.search-result mark { background: #ffe1a8; padding: 0 .12rem; }
		.message-meta { color: var(--muted); font-size: .75rem; margin-bottom: .2rem; }
		</style>
		""",
		unsafe_allow_html=True,
	)


def _render_sidebar(chat_manager) -> None:
	"""Render new-chat, search, rename, and chat-history controls."""
	with st.sidebar:
		st.markdown(
			'<div class="brand"><div class="brand-mark">♫</div><div class="brand-name">Music Muse</div></div>',
			unsafe_allow_html=True,
		)
		new_col, search_col = st.columns([4, 1])
		with new_col:
			if st.button("＋  New chat", use_container_width=True, type="primary"):
				chat = chat_manager.create_chat()
				st.session_state.active_chat_id = chat.chat_id
				st.session_state.search_open = False
				_rerun()
		with search_col:
			if st.button("⌕", use_container_width=True, help="Search chats"):
				st.session_state.search_open = not st.session_state.search_open
				st.session_state.search_query = ""
				_rerun()

		if st.session_state.search_open:
			_render_search(chat_manager)
			st.divider()

		st.caption("Your conversations")
		visible_chats = [
			chat
			for chat in chat_manager.list_chats()
			if chat.messages or chat.title != "New Chat"
		]
		for chat in visible_chats:
			if st.session_state.rename_chat_id == chat.chat_id:
				_render_rename_form(chat_manager, chat)
				continue

			chat_col, menu_col = st.columns([5, 1])
			with chat_col:
				label = chat.title or "New Chat"
				if st.button(label, key=f"chat-{chat.chat_id}", use_container_width=True):
					st.session_state.active_chat_id = chat.chat_id
					_rerun()
			with menu_col:
				if st.button("⋯", key=f"menu-{chat.chat_id}", help="Rename or delete"):
					st.session_state[f"show_menu_{chat.chat_id}"] = not st.session_state.get(
						f"show_menu_{chat.chat_id}", False
					)
					_rerun()
			if st.session_state.get(f"show_menu_{chat.chat_id}", False):
				rename_col, delete_col = st.columns(2)
				with rename_col:
					if st.button("Rename", key=f"rename-{chat.chat_id}", use_container_width=True):
						st.session_state.rename_chat_id = chat.chat_id
						_rerun()
				with delete_col:
					if st.button("Delete", key=f"delete-{chat.chat_id}", use_container_width=True):
						chat_manager.delete_chat(chat.chat_id)
						remaining = chat_manager.list_chats()
						st.session_state.active_chat_id = remaining[0].chat_id if remaining else None
						_rerun()


def _render_search(chat_manager) -> None:
	"""Render the FTS search box and clickable highlighted results."""
	query = st.text_input("Search chats", key="search_query", label_visibility="collapsed", placeholder="Search chats...")
	if not query.strip():
		return

	results = chat_manager.search(query)
	if not results:
		st.caption("No matching chats")
		return

	for index, result in enumerate(results):
		title = _highlight_to_html(result["title_highlighted"] or "Untitled chat")
		snippet = _highlight_to_html(result["snippet_highlighted"] or "")
		st.markdown(
			f'<div class="search-result"><div class="search-result-title">{title}</div>'
			f'<div class="search-result-snippet">{snippet}</div></div>',
			unsafe_allow_html=True,
		)
		if st.button("Open", key=f"search-open-{index}-{result['chat_id']}", use_container_width=True):
			st.session_state.active_chat_id = result["chat_id"]
			st.session_state.search_open = False
			_rerun()


def _render_rename_form(chat_manager, chat) -> None:
	"""Render the inline chat rename form."""
	with st.form(f"rename-form-{chat.chat_id}"):
		new_title = st.text_input("Chat name", value=chat.title, label_visibility="collapsed")
		save_col, cancel_col = st.columns(2)
		with save_col:
			submitted = st.form_submit_button("Save", use_container_width=True)
		with cancel_col:
			cancelled = st.form_submit_button("Cancel", use_container_width=True)
		if submitted and new_title.strip():
			chat_manager.rename_chat(chat.chat_id, new_title)
			st.session_state.rename_chat_id = None
			_rerun()
		if cancelled:
			st.session_state.rename_chat_id = None
			_rerun()


def _render_main(chat_manager, chat_model, chat) -> None:
	"""Render settings, conversation messages, and the composer."""
	model_col, spacer_col, innovation_col = st.columns([1.15, 1.05, 1.1])
	with model_col:
		selected_model = st.selectbox("Choose your model", LLM_MODELS, index=_model_index(chat.model_name))
		if selected_model != chat.model_name:
			chat.set_model(selected_model)
			chat.model_name = selected_model
	with innovation_col:
		innovation = st.slider("INNOVATION", 0, 100, int(chat.innovation), format="%d%%")
		if innovation != chat.innovation:
			chat.set_innovation(innovation)
			chat.innovation = innovation

	# Native chat_input is anchored below the conversation. Because it is
	# evaluated before the message history, submitted turns render above it.
	prompt = st.chat_input("Curb your musical curiosity...")

	if not chat.messages:
		st.markdown(
			'<div class="welcome"><div class="welcome-kicker">Your next sound starts here</div>'
			'<h1>Make something worth hearing.</h1>'
			'<p>Ask about lyrics, translation, composition, production, or the sound in your head.</p></div>',
			unsafe_allow_html=True,
		)
	else:
		for message in chat.messages:
			_render_message(chat_manager, chat, message)

	if prompt and prompt.strip():
		user_message = chat_manager.add_message(chat.chat_id, "user", prompt.strip())
		refreshed_chat = chat_manager.get_chat(chat.chat_id)
		_render_message(chat_manager, refreshed_chat, user_message, dimmed=True)

		with st.chat_message("assistant"):
			st.markdown('<div class="message-meta">Music Muse</div>', unsafe_allow_html=True)
			with st.spinner("Music Muse is thinking..."):
				reply = chat_model.generate_reply(refreshed_chat, prompt.strip())
			_stream_reply(reply)

		chat_manager.add_message(chat.chat_id, "assistant", reply)
		_rerun()


def _render_message(chat_manager, chat, message: dict, dimmed: bool = False) -> None:
	"""Render one user or assistant message, including assistant feedback."""
	role_label = "You" if message["role"] == "user" else "Music Muse"
	with st.chat_message(message["role"]):
		if dimmed:
			st.markdown(
				f'<div class="pending-message"><div class="message-meta">{role_label}</div>'
				f'<div>{escape(message["content"]).replace(chr(10), "<br>")}</div></div>',
				unsafe_allow_html=True,
			)
		else:
			st.markdown(f'<div class="message-meta">{role_label}</div>', unsafe_allow_html=True)
			st.markdown(message["content"])
		if message["role"] == "assistant":
			up_col, down_col, _ = st.columns([.07, .07, .86])
			with up_col:
				if st.button("👍", key=f"up-{message['id']}", help="Helpful"):
					_save_feedback(chat_manager, chat, message["id"], "up")
			with down_col:
				if st.button("👎", key=f"down-{message['id']}", help="Needs improvement"):
					_save_feedback(chat_manager, chat, message["id"], "down")


def _save_feedback(chat_manager, chat, message_id: str, value: str) -> None:
	"""Persist assistant feedback and refresh the current conversation."""
	FeedbackManager().record_feedback(chat, message_id, value)
	_rerun()


def _stream_reply(reply: str) -> None:
	"""Reveal a completed reply one character at a time in the chat bubble."""
	placeholder = st.empty()
	visible_text = ""
	for character in reply:
		visible_text += character
		placeholder.markdown(visible_text + "▌")
		time.sleep(0.012)
	placeholder.markdown(visible_text)


def _model_index(model_name: str) -> int:
	"""Return the safe selectbox index for a persisted model name."""
	return LLM_MODELS.index(model_name) if model_name in LLM_MODELS else 0


def _highlight_to_html(value: str) -> str:
	"""Convert FTS markdown markers to escaped HTML highlights."""
	pieces = value.split("**")
	rendered = []
	for index, piece in enumerate(pieces):
		escaped = escape(piece)
		rendered.append(f"<mark>{escaped}</mark>" if index % 2 else escaped)
	return "".join(rendered)


def _rerun() -> None:
	"""Request a Streamlit rerun across supported Streamlit versions."""
	if hasattr(st, "rerun"):
		st.rerun()
	else:
		st.experimental_rerun()
