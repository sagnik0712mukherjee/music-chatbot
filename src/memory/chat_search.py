"""
Defines two related classes for working with the full set of chats:

- ChatSearchIndex: a SQLite FTS5-backed full-text search index over every
  message in every chat. Gives us fast, ranked search with highlighted
  snippets, without adding any external dependency (sqlite3 + fts5 both
  ship with Python).
- ChatManager: the "front door" for everything chat-list related —
  create, list, rename, delete — which also keeps ChatSearchIndex in
  sync so search results never go stale.
"""

# ==== standard imports ====
import os
import re
import sqlite3
from typing import Optional

# ==== external imports ====
# (none — sqlite3 is part of the Python standard library)

from src.memory.chat_memory import CHATS_DIR, ChatMemory
from src.utils.helpers import list_json_files

# Where the search index database file lives on disk.
SEARCH_DB_PATH = os.path.join("data", "search_index.db")

# Marker strings used to wrap matched search terms, so the UI can render
# them as bold text via st.markdown() without needing raw HTML.
HIGHLIGHT_START = "**"
HIGHLIGHT_END = "**"


class ChatSearchIndex:
    """
    Full-text search index over all chat messages, backed by SQLite FTS5.

    Each row in the index mirrors one message: which chat it belongs to,
    that chat's current title, and the message content. This is kept in
    sync by ChatManager whenever a chat is created, messaged, renamed,
    or deleted.
    """

    def __init__(self, db_path: str = SEARCH_DB_PATH):
        """
        Open (or create) the FTS5 search index database.

        Args:
            db_path: File path for the SQLite database.
        """
        parent_dir = os.path.dirname(db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # check_same_thread=False because Streamlit can call in from
        # different internal threads across reruns.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self) -> None:
        """Create the FTS5 virtual table if it doesn't already exist."""
        self.conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                chat_id UNINDEXED,
                chat_title,
                message_id UNINDEXED,
                role UNINDEXED,
                content
            )
            """
        )
        self.conn.commit()

    def index_message(
        self, chat_id: str, chat_title: str, message_id: str, role: str, content: str
    ) -> None:
        """
        Add one message to the search index.

        Args:
            chat_id: The chat this message belongs to.
            chat_title: The chat's current title (duplicated per row so
                title search and content search can share one query).
            message_id: Unique id of the message.
            role: "user" or "assistant".
            content: The message text to make searchable.
        """
        self.conn.execute(
            """
            INSERT INTO messages_fts (chat_id, chat_title, message_id, role, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, chat_title, message_id, role, content),
        )
        self.conn.commit()

    def update_chat_title(self, chat_id: str, new_title: str) -> None:
        """
        Update the stored title for every indexed message in a chat.

        Called after a rename, so title search always reflects the
        current name shown in the sidebar.

        Args:
            chat_id: The chat that was renamed.
            new_title: Its new title.
        """
        self.conn.execute(
            "UPDATE messages_fts SET chat_title = ? WHERE chat_id = ?",
            (new_title, chat_id),
        )
        self.conn.commit()

    def remove_chat(self, chat_id: str) -> None:
        """
        Remove every indexed message belonging to a deleted chat.

        Args:
            chat_id: The chat that was deleted.
        """
        self.conn.execute("DELETE FROM messages_fts WHERE chat_id = ?", (chat_id,))
        self.conn.commit()

    def clear(self) -> None:
        """Wipe the entire index. Used before a full rebuild."""
        self.conn.execute("DELETE FROM messages_fts")
        self.conn.commit()

    @staticmethod
    def _tokenize(query: str) -> list:
        """
        Break a raw search string into safe, alphanumeric search tokens.

        Strips FTS5 special characters (quotes, hyphens, etc.) so a
        user's search text can never accidentally break the MATCH
        query syntax.

        Args:
            query: Raw text typed into the search box.

        Returns:
            list: Lowercase word tokens.
        """
        return re.findall(r"\w+", query.lower())

    def search(self, query: str, limit: int = 10) -> list:
        """
        Search across all chats and return one best-matching result per
        chat, ranked by relevance, with matched terms highlighted.

        Args:
            query: The user's search text.
            limit: Maximum number of distinct chats to return.

        Returns:
            list: Dicts of the form:
                {
                    "chat_id": str,
                    "title_highlighted": str,  # chat title, ** around matches
                    "snippet_highlighted": str,  # message excerpt, matches marked
                    "role": str,  # role of the matched message
                }
                Ordered by relevance, most relevant first.
        """
        tokens = self._tokenize(query)
        if not tokens:
            return []

        # Prefix-match every token (word*) and OR them together, so
        # partial/typo-tolerant, "search-as-you-type" style results
        # come back — closer to how Claude's search box behaves.
        match_expr = " OR ".join(f"{token}*" for token in tokens)

        cursor = self.conn.execute(
            """
            SELECT
                chat_id,
                snippet(messages_fts, 1, ?, ?, '...', 6) AS title_snippet,
                snippet(messages_fts, 4, ?, ?, '...', 10) AS content_snippet,
                role,
                bm25(messages_fts) AS rank
            FROM messages_fts
            WHERE messages_fts MATCH ?
            ORDER BY rank
            LIMIT 100
            """,
            (
                HIGHLIGHT_START,
                HIGHLIGHT_END,
                HIGHLIGHT_START,
                HIGHLIGHT_END,
                match_expr,
            ),
        )

        # Keep only the single best (first, since already rank-ordered)
        # match per chat, so a chat doesn't show up multiple times.
        results = []
        seen_chat_ids = set()
        for chat_id, title_snippet, content_snippet, role, _rank in cursor.fetchall():
            if chat_id in seen_chat_ids:
                continue
            seen_chat_ids.add(chat_id)
            results.append(
                {
                    "chat_id": chat_id,
                    "title_highlighted": title_snippet,
                    "snippet_highlighted": content_snippet,
                    "role": role,
                }
            )
            if len(results) >= limit:
                break

        return results


class ChatManager:
    """
    The single entry point for managing the full collection of chats.

    Wraps ChatMemory (one chat) and ChatSearchIndex (search across all
    chats) so the UI layer only ever needs to talk to ChatManager.
    """

    def __init__(self):
        """Set up the chats folder and open the search index."""
        os.makedirs(CHATS_DIR, exist_ok=True)
        self.search_index = ChatSearchIndex()

        # If the index is empty but chats already exist on disk (e.g.
        # first run after pulling new code, or the index db was
        # deleted), rebuild it so search isn't silently broken.
        if not list_json_files(CHATS_DIR):
            return
        cursor = self.search_index.conn.execute("SELECT COUNT(*) FROM messages_fts")
        (indexed_count,) = cursor.fetchone()
        if indexed_count == 0:
            self.rebuild_index()

    def create_chat(
        self, model_name: Optional[str] = None, innovation: Optional[int] = None
    ) -> ChatMemory:
        """
        Create and persist a brand-new, empty chat.

        Args:
            model_name: Ollama model to use for this chat.
            innovation: Innovation percentage (0-100) for this chat.

        Returns:
            ChatMemory: The newly created chat.
        """
        kwargs = {}
        if model_name is not None:
            kwargs["model_name"] = model_name
        if innovation is not None:
            kwargs["innovation"] = innovation

        chat = ChatMemory(**kwargs)
        chat.save()
        return chat

    def get_chat(self, chat_id: str) -> Optional[ChatMemory]:
        """
        Load a single chat by id.

        Args:
            chat_id: The chat's unique identifier.

        Returns:
            ChatMemory: The chat, or None if it doesn't exist.
        """
        return ChatMemory.load(chat_id)

    def list_chats(self) -> list:
        """
        List every saved chat, most recently updated first.

        Returns:
            list: ChatMemory instances, sorted newest-first, ready for
                display in the sidebar.
        """
        chats = []
        for file_path in list_json_files(CHATS_DIR):
            chat_id = os.path.splitext(os.path.basename(file_path))[0]
            chat = ChatMemory.load(chat_id)
            if chat is not None:
                chats.append(chat)

        chats.sort(key=lambda c: c.updated_at, reverse=True)
        return chats

    def add_message(self, chat_id: str, role: str, content: str) -> Optional[dict]:
        """
        Add a message to a chat and keep the search index up to date.

        Args:
            chat_id: The chat to add the message to.
            role: "user" or "assistant".
            content: The message text.

        Returns:
            dict: The created message record, or None if the chat
                doesn't exist.
        """
        chat = self.get_chat(chat_id)
        if chat is None:
            return None

        message = chat.add_message(role, content)
        self.search_index.index_message(
            chat_id=chat.chat_id,
            chat_title=chat.title,
            message_id=message["id"],
            role=message["role"],
            content=message["content"],
        )
        return message

    def rename_chat(self, chat_id: str, new_title: str) -> bool:
        """
        Rename a chat and refresh its title everywhere it's indexed.

        Args:
            chat_id: The chat to rename.
            new_title: The new display title.

        Returns:
            bool: True if the chat was found and renamed, else False.
        """
        chat = self.get_chat(chat_id)
        if chat is None:
            return False

        chat.rename(new_title)
        self.search_index.update_chat_title(chat_id, chat.title)
        return True

    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat and remove it from the search index.

        Args:
            chat_id: The chat to delete.

        Returns:
            bool: True if the chat was found and deleted, else False.
        """
        chat = self.get_chat(chat_id)
        if chat is None:
            return False

        chat.delete()
        self.search_index.remove_chat(chat_id)
        return True

    def search(self, query: str, limit: int = 10) -> list:
        """
        Search across every chat's messages and titles.

        Args:
            query: The user's search text.
            limit: Maximum number of distinct chat results to return.

        Returns:
            list: Ranked search results, see ChatSearchIndex.search().
        """
        return self.search_index.search(query, limit=limit)

    def rebuild_index(self) -> None:
        """
        Rebuild the search index from scratch by reading every chat's
        JSON file off disk. Useful for recovery if the index database
        is ever deleted or gets out of sync.
        """
        self.search_index.clear()
        for chat in self.list_chats():
            for message in chat.messages:
                self.search_index.index_message(
                    chat_id=chat.chat_id,
                    chat_title=chat.title,
                    message_id=message["id"],
                    role=message["role"],
                    content=message["content"],
                )