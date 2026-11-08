"""The spec's required coverage: tag output validation."""

from app.tagging.client import OutputError, build_system_prompt, parse_tag_response

ALLOWED = {"trading", "economics", "cooking"}


def test_unknown_slugs_are_dropped_silently():
    tags, none_apply, title = parse_tag_response(
        {"tags": [{"slug": "trading", "confidence": 0.9}, {"slug": "invented", "confidence": 0.5}],
         "none_apply": False, "title": "Markets"},
        ALLOWED,
    )
    assert [t["slug"] for t in tags] == ["trading"]
    assert none_apply is False
    assert title == "Markets"


def test_malformed_json_structure_raises():
    for payload in ({}, {"tags": "nope"}, {"tags": [], "none_apply": "yes"}):
        try:
            parse_tag_response(payload, ALLOWED)
        except OutputError:
            continue
        raise AssertionError(f"expected OutputError for {payload}")


def test_empty_tag_list_is_valid():
    tags, none_apply, _ = parse_tag_response({"tags": [], "none_apply": True, "title": ""}, ALLOWED)
    assert tags == []
    assert none_apply is True


def test_more_than_five_tags_rejected():
    payload = {
        "tags": [{"slug": "trading", "confidence": 0.1} for _ in range(6)],
        "none_apply": False,
        "title": "x",
    }
    try:
        parse_tag_response(payload, ALLOWED)
    except OutputError:
        return
    raise AssertionError("expected OutputError")


def test_title_is_trimmed_and_stripped_of_trailing_period():
    _, _, title = parse_tag_response(
        {"tags": [], "none_apply": True, "title": "  Sourdough   Starter.  "}, ALLOWED
    )
    assert title == "Sourdough Starter"


def test_prompt_lists_slugs_and_descriptions():
    class T:
        def __init__(self, slug, description):
            self.slug, self.description = slug, description

    prompt = build_system_prompt([T("trading", "markets"), T("cooking", "")])
    assert "trading - markets" in prompt
    assert "cooking - (no description)" in prompt
