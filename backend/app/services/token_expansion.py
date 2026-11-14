import re

# Bounded linear-time regex for hyphen/underscore-delimited identifiers (T-02-02).
TECHNICAL_TOKEN_REGEX = re.compile(r"\b[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)+\b")
_DELIMITER_PATTERN = re.compile(r"[-_]")


def expand_technical_tokens(text: str) -> list[str]:
    """Extract and expand technical error codes, SKUs, and CLI flags into search variants."""
    raw_tokens = TECHNICAL_TOKEN_REGEX.findall(text)
    expanded: set[str] = set()

    for token in raw_tokens:
        concatenated = _DELIMITER_PATTERN.sub("", token)
        expanded.add(token)
        expanded.add(token.replace("_", "-"))
        expanded.add(token.replace("-", "_"))
        expanded.add(_DELIMITER_PATTERN.sub(" ", token))
        expanded.add(concatenated)
        expanded.add(token.lower())
        expanded.add(concatenated.lower())

    return sorted(expanded)


def append_search_index_tokens(body: str) -> str:
    """Append plain-text Search Index Tokens section for PostgreSQL dual-dictionary FTS.

    Never wraps tokens in HTML/XML comments (<!-- -->), which PostgreSQL's ts_parse
    strips during tsvector generation.
    """
    tokens = expand_technical_tokens(body)
    if not tokens:
        return body
    return f"{body}\n\nSearch Index Tokens: {' '.join(tokens)}"
