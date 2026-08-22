"""Streamlit presentation layer for the Music Chatbot.

The module keeps Streamlit-specific state and rendering here while leaving
chat persistence, search, and model calls to the modules underneath it.
"""

# ==== standard imports ====
from html import escape
import time

import streamlit as st

from config.settings import LLM_MODELS, get_model_option_by_id, get_model_option_by_label, model_labels
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
	st.session_state.setdefault("clear_composer_prompt", False)


def _inject_styles() -> None:
	"""Apply the white and gold theme to the Streamlit app."""
	st.markdown(
		"""
		<style>
		:root { --canvas: #ffffff; --panel: #fffaf0; --ink: #000000; --muted: #5f4b1b; --line: rgba(186,134,11,.24); --accent: #cfa55f; --accent-dark: #a37a2a; }
		.stApp { background: linear-gradient(180deg, #ffffff 0%, #fff9eb 45%, #fff2d5 100%) !important; }
		.stApp::before { content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .14; background-image: repeating-linear-gradient(115deg, transparent 0 96px, rgba(223,176,97,.14) 97px, transparent 98px 196px); }
		[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"],
		[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child { background: transparent !important; }
		[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMain"] * { color: var(--ink); }
		[data-testid="stSidebar"] { background: rgba(255,250,240,.98) !important; border-right: 1px solid var(--line); }
		[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
		[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] p,
		[data-testid="stCaptionContainer"], label, small { color: var(--ink) !important; }
		[data-testid="stCaptionContainer"] { opacity: .8; }
		[data-baseweb="select"] > div, [data-baseweb="input"] > div,
		[data-testid="stTextArea"] textarea, input { background: #ffffff !important; color: #000000 !important; border: 1px solid rgba(186,134,11,.24) !important; }
		[data-baseweb="select"] svg { fill: #000000 !important; }
		[data-baseweb="select"] { border-radius: 10px; box-shadow: 0 12px 24px rgba(223,176,97,.18); }
		[data-testid="stSelectbox"] { max-width: 250px; margin: 0 auto; }
		[data-testid="stSelectbox"] label, [data-testid="stSelectbox"] label p { text-align: center !important; width: 100%; }
		[data-testid="stSelectbox"] [data-baseweb="select"] > div { justify-content: center; }
		[data-testid="stSelectbox"] [data-baseweb="select"] input { text-align: center; }
		[data-testid="stTextArea"] textarea::placeholder, input::placeholder { color: #8f7a56 !important; }
		[data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button { color: #000000 !important; border-color: var(--accent) !important; background: var(--accent) !important; font-weight: 700; }
		[data-testid="stButton"] button:hover, [data-testid="stFormSubmitButton"] button:hover { background: var(--accent-dark) !important; border-color: #8a712d !important; }
		[data-testid="stSlider"] { background: #ffffff !important; border: 1px solid rgba(186,134,11,.24); border-radius: 10px; padding: .5rem .75rem .25rem; box-shadow: 0 12px 22px rgba(223,176,97,.14); }
		[data-testid="stSlider"] label, [data-testid="stSlider"] label p { color: #000000 !important; }
		[data-testid="stSlider"] [role="slider"] { background: var(--accent) !important; border-color: #000000 !important; }
		[data-testid="stSlider"] [data-baseweb="slider"] > div > div { background: var(--accent) !important; }
		[data-testid="stChatMessage"] { background: #fffdf4 !important; border: 1px solid rgba(186,134,11,.2) !important; border-radius: 16px; margin: .7rem 0; }
		.pending-message { opacity: .9; }
		[data-testid="stChatInput"] { width: 100% !important; max-width: none !important; background: #ffffff !important; border: 1px solid rgba(186,134,11,.24) !important; border-radius: 14px; }
		[data-testid="stChatInput"] textarea { background: #ffffff !important; color: #000000 !important; }
		[data-testid="stTextArea"] textarea::placeholder, [data-testid="stTextInput"] input::placeholder { color: #8f7a56 !important; opacity: .9; }
		.composer-label { color: #000000 !important; text-align: center; margin-bottom: 1rem; font-size: 1rem; opacity: .95; }
		.composer-box { padding: 1rem 1.1rem 1.1rem; border: 1px solid rgba(186,134,11,.24); border-radius: 28px; background: #ffffff !important; box-shadow: 0 20px 50px rgba(223,176,97,.18); margin-bottom: 1.25rem; }
		.brand { display: flex; align-items: center; gap: .65rem; margin: .2rem 0 1.4rem; }
		.brand-mark { display: grid; place-items: center; width: 2.1rem; height: 2.1rem; border-radius: 50%; background: var(--accent); color: #000000; font-size: 1.15rem; box-shadow: 0 0 0 5px rgba(223,176,97,.24), 0 0 22px rgba(223,176,97,.35); }
		.brand-name { color: var(--ink); font-size: 1.1rem; font-weight: 700; letter-spacing: .01em; }
		.welcome { margin: 7vh auto 2rem; max-width: 720px; text-align: center; }
		.welcome-kicker { color: var(--accent-dark); font-size: .78rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; margin-bottom: .7rem; }
		.welcome h1 { color: var(--ink); font-size: clamp(2rem, 5vw, 3.4rem); margin-bottom: .4rem; }
		.welcome p { color: var(--muted); font-size: 1.05rem; }
		.search-result { border-bottom: 1px solid var(--line); padding: .55rem 0; }
		.search-result-title { color: var(--ink); font-weight: 700; font-size: .9rem; }
		.search-result-snippet { color: var(--muted); font-size: .8rem; line-height: 1.35; }
		.search-result mark { background: #fff0c5; padding: 0 .12rem; }
		.message-meta { color: var(--muted); font-size: .75rem; margin-bottom: .2rem; }
		</style>
		""",
		unsafe_allow_html=True,
	)


def _ensure_composer_state() -> None:
	"""Ensure the prompt composer state exists in Streamlit session state."""
	if st.session_state.get("clear_composer_prompt", False):
		st.session_state["composer_prompt"] = ""
		st.session_state["clear_composer_prompt"] = False
	st.session_state.setdefault("composer_prompt", "")


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
		selected_label = st.selectbox(
			"Choose your model",
			model_labels(),
			index=_model_label_index(chat.model_name),
		)
		selected_option = get_model_option_by_label(selected_label)
		if selected_option["id"] != chat.model_name:
			chat.set_model(selected_option["id"])
			chat.model_name = selected_option["id"]
		st.caption(selected_option["info"])
	with innovation_col:
		innovation = st.slider("INNOVATION", 0, 100, int(chat.innovation), format="%d%%")
		if innovation != chat.innovation:
			chat.set_innovation(innovation)
			chat.innovation = innovation

	_ensure_composer_state()

	st.markdown(
		'<div class="composer-label">Ask your music question in plain text. This assistant prefers accurate music answers and will reply with "I don\'t know" rather than invent.</div>',
		unsafe_allow_html=True,
	)
	st.markdown('<div class="composer-box">', unsafe_allow_html=True)
	with st.form("composer_form"):
		prompt = st.text_area(
			"",
			value=st.session_state.get("composer_prompt", ""),
			placeholder="Curb your musical curiosity...",
			key="composer_prompt",
			label_visibility="collapsed",
			height=150,
		)
		send = st.form_submit_button("Send")
	st.markdown('</div>', unsafe_allow_html=True)

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

	if send and prompt and prompt.strip():
		user_message_text = prompt.strip()
		model_input = user_message_text
		dimmed_message = {
			"id": "pending",
			"role": "user",
			"content": user_message_text,
		}
		_render_message(chat_manager, chat, dimmed_message, dimmed=True)

		with st.chat_message("assistant"):
			st.markdown('<div class="message-meta">Music Muse</div>', unsafe_allow_html=True)
			with st.spinner("Music Muse is thinking..."):
				reply = chat_model.generate_reply(chat, model_input)
				_stream_reply(reply)

		chat_manager.add_message(chat.chat_id, "user", user_message_text)
		chat_manager.add_message(chat.chat_id, "assistant", reply)
		st.session_state["clear_composer_prompt"] = True
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


def _model_label_index(model_name: str) -> int:
	"""Return the friendly selectbox index for a persisted model name."""
	labels = model_labels()
	option = get_model_option_by_id(model_name)
	return labels.index(option["label"]) if option and option["label"] in labels else 0


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
