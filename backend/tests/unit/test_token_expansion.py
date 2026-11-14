import pytest

from app.services.token_expansion import (
    TECHNICAL_TOKEN_REGEX,
    append_search_index_tokens,
    expand_technical_tokens,
)


@pytest.mark.parametrize(
    ("token", "expected_variants"),
    [
        (
            "ERR_409_CONFLICT",
            [
                "ERR_409_CONFLICT",
                "ERR-409-CONFLICT",
                "ERR 409 CONFLICT",
                "ERR409CONFLICT",
                "err_409_conflict",
                "err409conflict",
            ],
        ),
        (
            "ERR_503_SERVICE_UNAVAILABLE",
            [
                "ERR_503_SERVICE_UNAVAILABLE",
                "ERR-503-SERVICE-UNAVAILABLE",
                "ERR 503 SERVICE UNAVAILABLE",
                "ERR503SERVICEUNAVAILABLE",
                "err_503_service_unavailable",
                "err503serviceunavailable",
            ],
        ),
        (
            "SKU-9921-A",
            [
                "SKU-9921-A",
                "SKU_9921_A",
                "SKU 9921 A",
                "SKU9921A",
                "sku-9921-a",
                "sku9921a",
            ],
        ),
        (
            "SKU-GLX-500",
            [
                "SKU-GLX-500",
                "SKU_GLX_500",
                "SKU GLX 500",
                "SKUGLX500",
                "sku-glx-500",
                "skuglx500",
            ],
        ),
        (
            "--enable-read-replica",
            [
                "enable-read-replica",
                "enable_read_replica",
                "enable read replica",
                "enablereadreplica",
            ],
        ),
    ],
)
def test_expand_technical_tokens_variants(token: str, expected_variants: list[str]) -> None:
    text = f"Diagnostic log recorded {token} during cluster sync."
    variants = expand_technical_tokens(text)

    for expected in expected_variants:
        assert expected in variants
    assert variants == sorted(set(variants))


def test_expand_technical_tokens_deduplicates_repeated_tokens() -> None:
    text = "Retry after ERR_409_CONFLICT. Duplicate ERR_409_CONFLICT observed."
    variants = expand_technical_tokens(text)
    assert len(variants) == len(set(variants))
    assert "ERR-409-CONFLICT" in variants


def test_technical_token_regex_exported_and_ignores_plain_words() -> None:
    assert TECHNICAL_TOKEN_REGEX.findall("Simple sentence with plain words only.") == []


def test_append_search_index_tokens_formats_plain_text_without_html_comments() -> None:
    body = "Resolution for ERR_409_CONFLICT on appliance SKU-9921-A."
    enriched = append_search_index_tokens(body)

    assert enriched.startswith(f"{body}\n\nSearch Index Tokens: ")
    assert "<!--" not in enriched
    assert "-->" not in enriched
    assert "ERR-409-CONFLICT" in enriched
    assert "err409conflict" in enriched
    assert "SKU_9921_A" in enriched
    assert "sku9921a" in enriched


def test_append_search_index_tokens_noop_for_plain_text() -> None:
    plain_body = "Standard documentation paragraph without technical codes."
    assert append_search_index_tokens(plain_body) == plain_body
