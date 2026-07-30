"""
Defines the MusicGuardrail class: a fast, keyword-based pre-filter that
checks whether a user's question is music-related BEFORE it's sent to
the (comparatively slow) LLM.

This is a first line of defense, not the only one — config/settings.py's
LLM_PROMPT already instructs the model itself to decline off-topic
questions. The guardrail exists purely for speed: catching an obviously
off-topic question here means we skip an unnecessary LLM call entirely,
which matters since speed is a stated priority for this app.

Because the LLM has its own on-topic instruction as a backstop, this
guardrail is intentionally lenient — it only blocks a question when NONE
of our music signal words are present. When in doubt, it lets the
question through and trusts the model's own judgment.
"""

# ==== standard imports ====
import re

# ==== external imports ====
# (none — this module is pure standard-library logic)


class MusicGuardrail:
    """
    Lightweight, keyword-based check for whether a message is on-topic
    (i.e. about music) for this chatbot.
    """

    # Broad set of music-related signal words. Deliberately wide-ranging
    # so legitimate music questions are never wrongly blocked — covers
    # genres, roles, production terms, and tools relevant to Sagnik's
    # own workflow (Cubase, DAW, Suno, etc.).
    MUSIC_KEYWORDS = {
        # Core music terms
        "music", "song", "songs", "lyric", "lyrics", "album", "track",
        "melody", "harmony", "chord", "chords", "tempo", "bpm", "rhythm",
        "beat", "genre", "tune", "hook", "verse", "chorus", "bridge",
        "hymn", "anthem", "jingle", "score", "soundtrack", "ost",
        "playlist", "cover", "remix", "acapella", "instrumental",
        # People / roles
        "artist", "singer", "vocalist", "musician", "composer", "compose",
        "composition", "compositions", "lyricist", "band", "orchestra",
        "conductor", "producer", "arranger", "arrangement", "songwriter",
        # Instruments
        "guitar", "piano", "violin", "drum", "drums", "bass", "flute",
        "harmonium", "sitar", "tabla", "synth", "synthesizer", "cello",
        "saxophone", "trumpet", "keyboard", "ukulele",
        # Production / tools
        "recording", "studio", "mixing", "mastering", "daw", "cubase",
        "ableton", "logic pro", "fl studio", "midi", "suno", "udio",
        "kling", "vocal", "vocals", "acoustic",
        # Events / industry
        "concert", "tour", "grammy", "billboard", "gig", "label",
        "spotify", "soundcloud",
        # Genres
        "ghazal", "raga", "qawwali", "pop", "rock", "jazz", "blues",
        "classical", "hiphop", "hip-hop", "rap", "edm", "indie", "folk",
        "reggae", "metal", "country", "opera", "bollywood",
    }

    def is_music_related(self, text: str) -> bool:
        """
        Check whether a message contains at least one music signal word.

        Args:
            text: The user's raw message.

        Returns:
            bool: True if the message looks music-related (or is
                ambiguous/empty and should be let through), False if it
                confidently looks off-topic.
        """
        if not text or not text.strip():
            # Empty input isn't our concern to block — let normal
            # validation elsewhere handle it.
            return True

        # Extract lowercase word tokens so we match whole words only
        # (e.g. "pop" the genre, not "popular" or "popcorn").
        tokens = set(re.findall(r"[a-z]+", text.lower()))

        return not self.MUSIC_KEYWORDS.isdisjoint(tokens)

    def get_refusal_message(self) -> str:
        """
        Canned, on-brand refusal message for off-topic questions.

        Returned instantly without calling the LLM, keeping off-topic
        requests fast and free of unnecessary compute.

        Returns:
            str: A polite message redirecting the user to music topics.
        """
        return (
            "I can only help with music-related questions — things like "
            "lyric writing, translation, composition ideas, genre and "
            "style advice, or Suno-style prompts. Could you rephrase your "
            "question around music?"
        )