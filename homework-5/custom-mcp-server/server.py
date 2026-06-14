"""Custom FastMCP server exposing a lorem-ipsum reader.

Provides BOTH primitives the MCP spec distinguishes:

* a **Resource** at the URI template ``lorem://text/{word_count}`` (plus a
  default ``lorem://text`` that yields 30 words) — data a client can READ.
* a **Tool** ``read(word_count=30)`` — an action a client can CALL.

Both return the first ``word_count`` whitespace-separated words of
``lorem-ipsum.md`` that sits next to this file.
"""

from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP("lorem-server")

# Resolve the source file relative to THIS module so the server works no matter
# what the process working directory happens to be.
LOREM_FILE = Path(__file__).resolve().parent / "lorem-ipsum.md"

DEFAULT_WORD_COUNT = 30


def _read_words(word_count: int = DEFAULT_WORD_COUNT) -> str:
    """Return the first ``word_count`` words of the lorem-ipsum source.

    If ``word_count`` exceeds the number of available words, every word is
    returned. A missing source file raises a clear ``FileNotFoundError``.
    """
    if word_count < 0:
        raise ValueError("word_count must be a non-negative integer")

    if not LOREM_FILE.exists():
        raise FileNotFoundError(
            f"Lorem ipsum source file not found: {LOREM_FILE}. "
            "Create lorem-ipsum.md next to server.py."
        )

    words = LOREM_FILE.read_text(encoding="utf-8").split()
    return " ".join(words[:word_count])


@mcp.resource("lorem://text/{word_count}")
def lorem_text(word_count: int = DEFAULT_WORD_COUNT) -> str:
    """Resource: read up to ``word_count`` words via ``lorem://text/{n}``."""
    return _read_words(word_count)


@mcp.resource("lorem://text")
def lorem_text_default() -> str:
    """Resource: the default 30-word reading at ``lorem://text``."""
    return _read_words(DEFAULT_WORD_COUNT)


@mcp.tool
def read(word_count: int = DEFAULT_WORD_COUNT) -> str:
    """Tool: return the first ``word_count`` words of the lorem-ipsum source.

    Args:
        word_count: How many words to return. Defaults to 30. Values larger
            than the source length return the whole file.
    """
    return _read_words(word_count)


if __name__ == "__main__":
    # Default transport is stdio, which is exactly what Claude Code launches.
    mcp.run()
