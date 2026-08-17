"""Tool classification: read-only vs. destructive/mutating.

The MCP handshake normalizes a server's tool set but not its trust model — a
tool that reads a page and a tool that submits a form with real consequences
look identical to the permissions layer. This module provides a single source
of truth for classifying a tool as ``read_only`` or ``mutating`` so the
permission layer can enforce read-only vs. destructive distinctions at the
request level (not just in docs).

The classifier is deterministic and dependency-free. Tools whose names start
with a known read-only prefix are classified read_only; everything else is
treated as mutating (conservative default — unknown tools are never assumed
safe).
"""

READ_ONLY_PREFIXES = ("get", "list", "search", "read", "find", "query", "check")

TOOL_CLASS_READ_ONLY = "read_only"
TOOL_CLASS_MUTATING = "mutating"


def classify_tool(tool_name: str) -> str:
    """Classify a tool name as ``read_only`` or ``mutating``.

    A tool is read_only if its name (lowercased) starts with any known
    read-only prefix. Unknown tools default to ``mutating`` — we never
    assume safety.
    """
    name = tool_name.lower()
    if any(name.startswith(p) for p in READ_ONLY_PREFIXES):
        return TOOL_CLASS_READ_ONLY
    return TOOL_CLASS_MUTATING


def is_read_only_tool(tool_name: str) -> bool:
    """Return True if the tool is classified read-only."""
    return classify_tool(tool_name) == TOOL_CLASS_READ_ONLY
