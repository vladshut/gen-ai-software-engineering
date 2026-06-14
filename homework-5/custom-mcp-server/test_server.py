"""In-process verification of the custom FastMCP server.

Uses FastMCP's in-memory ``Client`` (no subprocess, no network) to call the
``read`` tool and assert the returned word counts are EXACTLY what we asked for.
Run it with the venv python:  ``python test_server.py``
"""

import asyncio

from fastmcp import Client

from server import mcp


def _extract_text(result) -> str:
    """Pull the plain string out of a FastMCP call_tool result across versions."""
    # FastMCP >=2 exposes structured `.data`; fall back to the content blocks.
    data = getattr(result, "data", None)
    if isinstance(data, str):
        return data
    content = getattr(result, "content", None)
    if content:
        return content[0].text
    return str(result)


async def main() -> None:
    async with Client(mcp) as client:
        # 1) explicit word_count=5 -> exactly 5 words
        res5 = await client.call_tool("read", {"word_count": 5})
        text5 = _extract_text(res5)
        count5 = len(text5.split())

        # 2) default (no args) -> exactly 30 words
        res30 = await client.call_tool("read", {})
        text30 = _extract_text(res30)
        count30 = len(text30.split())

        # 3) read the resource template too, proving the Resource primitive works
        res_resource = await client.read_resource("lorem://text/7")
        resource_text = res_resource[0].text
        count_resource = len(resource_text.split())

    print(f"read(word_count=5)  -> {count5} words: {text5!r}")
    print(f"read()              -> {count30} words: {text30!r}")
    print(f"lorem://text/7      -> {count_resource} words: {resource_text!r}")

    assert count5 == 5, f"expected 5 words, got {count5}"
    assert count30 == 30, f"expected 30 words, got {count30}"
    assert count_resource == 7, f"expected 7 words, got {count_resource}"
    print("\nAll assertions passed ✅  (5 == 5, 30 == 30, 7 == 7)")


if __name__ == "__main__":
    asyncio.run(main())
