"""Streamlit presentation layer for the Music Chatbot.

The module keeps Streamlit-specific state and rendering here while leaving
chat persistence, search, and model calls to the modules underneath it.
"""

# ==== standard imports ====
from html import escape
from io import BytesIO
import tempfile
import time
import base64

# ==== external imports ====
from PIL import Image as PILImage
import streamlit as st

try:
	import audiorecorder
	if hasattr(audiorecorder, "audiorecorder"):
		streamlit_audiorecorder = audiorecorder.audiorecorder
	else:
		from audiorecorder import audiorecorder as streamlit_audiorecorder
	AUDIO_RECORDER_AVAILABLE = True
	AUDIO_RECORDER_ERROR = ""
except Exception as exc:
	streamlit_audiorecorder = None
	AUDIO_RECORDER_AVAILABLE = False
	AUDIO_RECORDER_ERROR = str(exc)

from config.settings import LLM_MODELS, MODEL_OPTIONS, get_model_option_by_id, get_model_option_by_label, model_labels
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
+		[data-testid="stTextArea"] textarea::placeholder, [data-testid="stTextInput"] input::placeholder { color: #ffffff !important; opacity: .95; }
+		.composer-label { color: #ffffff !important; text-align: center; margin-bottom: 0.75rem; font-size: 0.96rem; opacity: .92; }
+		.composer-box { padding: 1rem 1.1rem 0.8rem; border: 1px solid rgba(255,255,255,.12); border-radius: 28px; background: rgba(10,10,10,.92); box-shadow: 0 22px 60px rgba(0,0,0,.24); margin-bottom: 1rem; }
+		.composer-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
+		.icon-button { display: inline-flex; align-items: center; justify-content: center; width: 2.8rem; height: 2.8rem; border-radius: 50%; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.16); color: #ffffff !important; font-size: 1.2rem; }
+		.upload-label { color: var(--muted); font-size: 0.88rem; }
+		.uploader-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin-bottom: 1rem; }
+		.upload-slot { min-height: 3rem; }
+		.stFileUploader > label { display: none !important; }
+		.stFileUploader div[role="button"] { min-height: 3rem; justify-content: center; }
+		.stFileUploader div[role="button"] span { color: #ffffff !important; }
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


def _transcribe_audio_path(file_path: str) -> tuple[str, str | None]:
	"""Transcribe a local audio file path with Whisper."""
	try:
		import whisper
	except ImportError:
		return "", "Install the 'whisper' package to enable audio transcription."

	try:
		model = whisper.load_model("tiny")
		result = model.transcribe(file_path, fp16=False)
		return result.get("text", "").strip(), None
	except Exception as exc:
		return "", f"Audio transcription failed: {exc}"


def _transcribe_audio(uploaded_file) -> tuple[str, str | None]:
	"""Convert an uploaded audio file into a text prompt using Whisper."""
	if hasattr(uploaded_file, "read"):
		with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
			tmp.write(uploaded_file.read())
			file_path = tmp.name
		return _transcribe_audio_path(file_path)

	if hasattr(uploaded_file, "export"):
		with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
			uploaded_file.export(tmp.name, format="wav")
			file_path = tmp.name
		return _transcribe_audio_path(file_path)

	return "", "Unsupported audio input format."


def _handle_live_audio(recorded_audio) -> None:
	"""Process a live recorder AudioSegment and populate the composer prompt."""
	if not recorded_audio or len(recorded_audio) == 0:
		return
	if st.session_state.get("audio_upload_name") == "live-recorded":
		return

	transcript, error = _transcribe_audio(recorded_audio)
	st.session_state["pending_audio_text"] = transcript
	st.session_state["audio_error"] = error or ""
	st.session_state["audio_upload_name"] = "live-recorded"
	if transcript and not st.session_state.get("composer_prompt"):
		st.session_state["composer_prompt"] = transcript


def _prepare_image_payload(uploaded_file) -> tuple[str, str | None]:
	"""Prepare an uploaded image as Base64 bytes for the model to decode."""
	try:
		image = PILImage.open(uploaded_file).convert("RGB")
	except Exception as exc:
		return "", f"Image processing failed: {exc}"

	try:
		buffer = BytesIO()
		image.save(buffer, format="PNG")
		encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
		payload = (
			"Please decode this uploaded image and extract any lyrics, titles, "
			"or music-related text. The image is encoded as Base64 below. "
			"If you cannot decode it, respond with \"I don't know.\""
			"\n\n[IMAGE_BASE64_START]\n"
			f"{encoded}\n"
			"[IMAGE_BASE64_END]"
		)
		return payload, None
	except Exception as exc:
		return "", f"Image encoding failed: {exc}"


def _ensure_composer_state() -> None:
	"""Ensure the prompt composer state exists in Streamlit session state."""
	st.session_state.setdefault("composer_prompt", "")
	st.session_state.setdefault("pending_audio_text", "")
	st.session_state.setdefault("pending_image_text", "")
	st.session_state.setdefault("pending_image_payload", "")
	st.session_state.setdefault("audio_error", "")
	st.session_state.setdefault("image_error", "")
	st.session_state.setdefault("audio_upload_name", "")
	st.session_state.setdefault("image_upload_name", "")


def _handle_audio_upload(uploaded_file) -> None:
	"""Process an uploaded audio file and populate the composer prompt."""
	if not uploaded_file:
		return
	name = getattr(uploaded_file, "name", "")
	if name == st.session_state.get("audio_upload_name"):
		return

	transcript, error = _transcribe_audio(uploaded_file)
	st.session_state["pending_audio_text"] = transcript
	st.session_state["audio_error"] = error or ""
	st.session_state["audio_upload_name"] = name
	if transcript and not st.session_state.get("composer_prompt"):
		st.session_state["composer_prompt"] = transcript


def _handle_image_upload(uploaded_file) -> None:
	"""Process an uploaded image and prepare it for model inference."""
	if not uploaded_file:
		return
	name = getattr(uploaded_file, "name", "")
	if name == st.session_state.get("image_upload_name"):
		return

	payload, error = _prepare_image_payload(uploaded_file)
	st.session_state["pending_image_payload"] = payload
	st.session_state["pending_image_text"] = (
		"Image uploaded and encoded for model inference."
		if payload
		else ""
	)
	st.session_state["image_error"] = error or ""
	st.session_state["image_upload_name"] = name
	if payload and not st.session_state.get("composer_prompt"):
		st.session_state["composer_prompt"] = (
			"Decode the uploaded image and extract any lyrics or music-related text."
		)


def _clear_composer_uploads() -> None:
	"""Clear any pending audio/image upload state after the prompt is sent."""
	for key in [
		"pending_audio_text",
		"pending_image_text",
		"pending_image_payload",
		"audio_error",
		"image_error",
		"audio_upload_name",
		"image_upload_name",
	]:
		st.session_state.pop(key, None)


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
	with innovation_col:
		innovation = st.slider("INNOVATION", 0, 100, int(chat.innovation), format="%d%%")
		if innovation != chat.innovation:
			chat.set_innovation(innovation)
			chat.innovation = innovation

	_ensure_composer_state()

	st.markdown('<div class="composer-label">Use the live microphone for audio input; upload images for raw byte decoding and music translation.</div>', unsafe_allow_html=True)
	with st.container():
		with st.container():
			st.markdown('<div class="composer-box">', unsafe_allow_html=True)
			st.markdown('<div class="composer-toolbar"><div><span class="icon-button">🎤</span> <span class="upload-label">Live mic</span></div><div><span class="icon-button">＋</span> <span class="upload-label">Image upload</span></div></div>', unsafe_allow_html=True)
			col1, col2 = st.columns([1, 1])
			with col1:
				st.markdown('<div class="recorder-slot">', unsafe_allow_html=True)
				if AUDIO_RECORDER_AVAILABLE:
					recorded_audio = streamlit_audiorecorder(
						start_prompt="Record",
						stop_prompt="Stop",
						pause_prompt="",
						key="live_audio_recorder",
					)
					if recorded_audio and len(recorded_audio) > 0:
						_handle_live_audio(recorded_audio)
				else:
					st.info("Install the 'audiorecorder' package to enable live mic recording.")
					if AUDIO_RECORDER_ERROR:
						st.caption(f"Recorder error: {AUDIO_RECORDER_ERROR}")
				st.markdown('</div>', unsafe_allow_html=True)
			with col2:
				image_file = st.file_uploader(
					"",
					type=["png", "jpg", "jpeg", "bmp", "gif", "webp", "tiff"],
					key="image_upload",
					label_visibility="collapsed",
					help="Upload an image with lyrics or music notation for raw Base64 decoding and music translation.",
				)
			st.markdown('</div>', unsafe_allow_html=True)

	if image_file:
		_handle_image_upload(image_file)

	if st.session_state.get("audio_error"):
		st.warning(st.session_state["audio_error"])
	if st.session_state.get("image_error"):
		st.warning(st.session_state["image_error"])

	if st.session_state.get("pending_audio_text"):
		st.markdown("**Audio transcription preview:**")
		st.text_area("", st.session_state["pending_audio_text"], disabled=True, height=90, label_visibility="collapsed")
	if st.session_state.get("pending_image_text"):
		st.markdown("**Image upload attached to the next message:**")
		st.text_area("", st.session_state["pending_image_text"], disabled=True, height=90, label_visibility="collapsed")

	with st.form("composer_form"):
		prompt = st.text_area(
			"",
			value=st.session_state.get("composer_prompt", ""),
			placeholder="Curb your musical curiosity...",
			key="composer_prompt",
			label_visibility="collapsed",
			height=130,
		)
		send = st.form_submit_button("Send")

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
		image_payload = st.session_state.get("pending_image_payload")
		if image_payload:
			model_input += "\n\n" + image_payload

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
		_clear_composer_uploads()
		st.session_state["composer_prompt"] = ""
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
