import re
from typing import Any

from langchain_text_splitters import MarkdownHeaderTextSplitter

HEADERS_TO_SPLIT: list[tuple[str, str]] = [
    ("#", "H1"),
    ("##", "H2"),
    ("###", "H3"),
    ("####", "H4"),
]

# Matches complete fenced code blocks OR complete Markdown tables OR standard paragraphs.
# Tables and fenced code blocks are matched as indivisible atomic units (T-02-01).
BLOCK_PATTERN = re.compile(
    r"(```[\s\S]*?```"
    r"|(?:^\|.+?\|[ \t]*$\n?)+"
    r"|(?:[^\n]+(?:\n(?!#|\||```|\n)[^\n]+)*))",
    re.MULTILINE,
)


def _build_breadcrumb(title: str, metadata: dict[str, Any]) -> tuple[str, str]:
    """Build hierarchical breadcrumb '[Title > H1 > H2 > ...]' and leaf header."""
    headers = [title]
    for h_key in ("H1", "H2", "H3", "H4"):
        if h_val := metadata.get(h_key):
            headers.append(str(h_val).strip())
    return f"[{' > '.join(headers)}]", headers[-1]


def split_markdown_document(
    title: str,
    content: str,
    chunk_size: int = 1000,
) -> list[dict[str, Any]]:
    """Split Markdown into structure-aware chunks with hierarchical breadcrumbs.

    Preserves Markdown tables and fenced code blocks intact without mid-block slicing.
    """
    normalized = content.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT,
        strip_headers=False,
    )
    raw_sections = header_splitter.split_text(normalized)

    chunks: list[dict[str, Any]] = []
    for section in raw_sections:
        # MarkdownHeaderTextSplitter joins separated blocks with "  \n"; restore
        # paragraph breaks so BLOCK_PATTERN detects individual paragraphs cleanly.
        section_text = section.page_content.replace("  \n", "\n\n").strip()
        if not section_text:
            continue

        breadcrumb, leaf_header = _build_breadcrumb(title, section.metadata)

        if len(section_text) <= chunk_size:
            chunks.append(
                {
                    "breadcrumb": breadcrumb,
                    "section_header": leaf_header,
                    "body": section_text,
                }
            )
            continue

        blocks = [
            match.group(0).strip()
            for match in BLOCK_PATTERN.finditer(section_text)
            if match.group(0).strip()
        ]
        current_chunk: list[str] = []
        current_len = 0

        for block in blocks:
            block_len = len(block)
            separator_len = 2 if current_chunk else 0
            if current_chunk and (current_len + separator_len + block_len > chunk_size):
                chunks.append(
                    {
                        "breadcrumb": breadcrumb,
                        "section_header": leaf_header,
                        "body": "\n\n".join(current_chunk),
                    }
                )
                current_chunk = [block]
                current_len = block_len
            else:
                current_chunk.append(block)
                current_len += separator_len + block_len

        if current_chunk:
            chunks.append(
                {
                    "breadcrumb": breadcrumb,
                    "section_header": leaf_header,
                    "body": "\n\n".join(current_chunk),
                }
            )

    return chunks
