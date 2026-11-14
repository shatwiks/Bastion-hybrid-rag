from app.services.text_splitter import split_markdown_document


def test_small_document_emitted_without_fragmentation() -> None:
    content = "# Overview\n\nThis is a concise guide under the chunk limit."
    chunks = split_markdown_document(title="Cloud Overview", content=content, chunk_size=1000)

    assert len(chunks) == 1
    assert chunks[0]["breadcrumb"] == "[Cloud Overview > Overview]"
    assert chunks[0]["section_header"] == "Overview"
    assert "# Overview" in chunks[0]["body"]
    assert "concise guide" in chunks[0]["body"]


def test_header_hierarchy_tracking_and_breadcrumbs() -> None:
    content = (
        "# Architecture\n\n"
        "Top-level intro.\n\n"
        "## Storage Layer\n\n"
        "Storage details.\n\n"
        "### Replication\n\n"
        "Replication details.\n\n"
        "#### Quorum Rules\n\n"
        "Quorum details."
    )
    chunks = split_markdown_document(title="System Manual", content=content, chunk_size=1000)

    assert len(chunks) == 4
    assert chunks[0]["breadcrumb"] == "[System Manual > Architecture]"
    assert chunks[0]["section_header"] == "Architecture"

    assert chunks[1]["breadcrumb"] == "[System Manual > Architecture > Storage Layer]"
    assert chunks[1]["section_header"] == "Storage Layer"

    assert chunks[2]["breadcrumb"] == "[System Manual > Architecture > Storage Layer > Replication]"
    assert chunks[2]["section_header"] == "Replication"

    assert (
        chunks[3]["breadcrumb"]
        == "[System Manual > Architecture > Storage Layer > Replication > Quorum Rules]"
    )
    assert chunks[3]["section_header"] == "Quorum Rules"


def test_markdown_table_preserved_atomically_when_exceeding_chunk_size() -> None:
    rows = "\n".join(f"| ERR_{400 + i}_CODE | Description for error {i} in service |" for i in range(25))
    table = f"| Code | Description |\n| --- | --- |\n{rows}"
    content = f"# Error Reference\n\nIntro paragraph.\n\n{table}\n\nClosing paragraph."

    assert len(table) > 300
    chunks = split_markdown_document(title="Error Guide", content=content, chunk_size=300)

    table_chunks = [c for c in chunks if "| Code | Description |" in c["body"]]
    assert len(table_chunks) == 1
    table_body = table_chunks[0]["body"]
    assert "| --- | --- |" in table_body
    for i in range(25):
        assert f"| ERR_{400 + i}_CODE |" in table_body


def test_fenced_code_block_preserved_atomically_when_exceeding_chunk_size() -> None:
    code_lines = "\n".join(f"echo 'diagnostic step {i}'" for i in range(25))
    code_block = f"```bash\n{code_lines}\n```"
    content = f"# Runbook\n\nFollow these commands carefully.\n\n{code_block}\n\nVerify output."

    assert len(code_block) > 300
    chunks = split_markdown_document(title="Ops Runbook", content=content, chunk_size=300)

    code_chunks = [c for c in chunks if "```bash" in c["body"]]
    assert len(code_chunks) == 1
    code_body = code_chunks[0]["body"]
    assert code_body.count("```") == 2
    assert "diagnostic step 0" in code_body
    assert "diagnostic step 24" in code_body


def test_large_section_aggregates_blocks_up_to_chunk_size() -> None:
    para_a = "Alpha " * 30
    para_b = "Bravo " * 30
    table = "| Key | Val |\n| --- | --- |\n| A | 1 |\n| B | 2 |"
    content = f"# Large Section\n\n{para_a.strip()}\n\n{table}\n\n{para_b.strip()}"

    chunks = split_markdown_document(title="Doc", content=content, chunk_size=215)

    assert len(chunks) == 3
    for chunk in chunks:
        assert chunk["breadcrumb"] == "[Doc > Large Section]"
        assert chunk["section_header"] == "Large Section"

    combined = "\n\n".join(c["body"] for c in chunks)
    assert "| Key | Val |" in combined
    assert "| B | 2 |" in combined


def test_small_blocks_are_aggregated_into_single_chunk_when_within_budget() -> None:
    content = (
        "# Section\n\n"
        "First short paragraph.\n\n"
        "Second short paragraph.\n\n"
        + ("Long trailing paragraph " * 15).strip()
    )
    chunks = split_markdown_document(title="Doc", content=content, chunk_size=180)

    assert len(chunks) == 2
    assert "First short paragraph." in chunks[0]["body"]
    assert "Second short paragraph." in chunks[0]["body"]
    assert "Long trailing paragraph" in chunks[1]["body"]


def test_empty_and_crlf_content_handled_cleanly() -> None:
    assert split_markdown_document(title="Empty", content="   \n\t  ") == []

    crlf_md = "# Title\r\n\r\n| A | B |\r\n| - | - |\r\n| 1 | 2 |\r\n"
    chunks = split_markdown_document(title="CRLF Doc", content=crlf_md, chunk_size=30)
    assert len(chunks) >= 1
    assert any("| A | B |" in c["body"] and "| 1 | 2 |" in c["body"] for c in chunks)
