"""OpenAI-compatible HTTP client for tagging. No Django models imported here
so the parsing logic stays unit-testable without a database."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SYSTEM_PROMPT_TEMPLATE = """You tag short personal notes.

Choose tags ONLY from this closed list. Each line is: slug - description

{tag_list}

Also propose a short title for the note: at most 60 characters, plain text,
no trailing full stop, no markdown. It should say what the note is about, not
repeat its first line verbatim. Use the same language as the note.

Hard rules:
- Use only slugs from the list above. Never invent a tag.
- Return between 0 and 5 tags.
- Returning zero tags is valid and expected when nothing fits.
- Prefer fewer, more accurate tags over many weak ones.
- confidence is your own 0-1 estimate; it is informational only.

Respond with JSON only, matching the required schema."""

JSON_SCHEMA = {
    "name": "tagging_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["slug", "confidence"],
                    "additionalProperties": False,
                },
            },
            "none_apply": {"type": "boolean"},
            "title": {"type": "string"},
        },
        "required": ["tags", "none_apply", "title"],
        "additionalProperties": False,
    },
}


class ProviderError(Exception):
    """Raised when the provider call fails in a way worth reporting."""


class ValidationError_(Exception):
    """Raised when model output violates the contract."""


def build_system_prompt(tags) -> str:
    """tags: iterable of objects with .slug and .description."""
    lines = []
    for tag in tags:
        desc = (tag.description or "").strip() or "(no description)"
        lines.append(f"- {tag.slug} - {desc}")
    return SYSTEM_PROMPT_TEMPLATE.format(tag_list="\n".join(lines) or "(no tags defined)")


def truncate_body(body: str, limit: int) -> str:
    if len(body) <= limit:
        return body
    return body[:limit]


def parse_tag_response(
    payload: dict, allowed_slugs: set[str]
) -> tuple[list[dict], bool, str | None]:
    """Validate model output. Returns (valid_tags, none_apply, title).

    Unknown slugs are dropped silently (spec 6). Malformed structure raises
    ValidationError_ so the caller can retry once.
    """
    if not isinstance(payload, dict):
        raise ValidationError_("Response is not a JSON object")

    tags = payload.get("tags")
    none_apply = payload.get("none_apply", False)
    if not isinstance(tags, list):
        raise ValidationError_("`tags` missing or not a list")
    if not isinstance(none_apply, bool):
        raise ValidationError_("`none_apply` missing or not a boolean")
    if len(tags) > 5:
        raise ValidationError_("More than 5 tags returned")

    raw_title = payload.get("title")
    title: str | None = None
    if isinstance(raw_title, str):
        cleaned = " ".join(raw_title.split()).strip().rstrip(".")
        if cleaned:
            title = cleaned[:200]

    valid: list[dict] = []
    seen: set[str] = set()
    for item in tags:
        if not isinstance(item, dict):
            raise ValidationError_("Tag entry is not an object")
        slug = item.get("slug")
        if not isinstance(slug, str):
            raise ValidationError_("Tag entry missing string slug")
        confidence = item.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            confidence = 0.0
        if slug not in allowed_slugs:
            continue
        if slug in seen:
            continue
        seen.add(slug)
        valid.append({"slug": slug, "confidence": float(confidence)})

    return valid, none_apply, title


def _extract_json(content: str):
    """Models sometimes wrap JSON in fences even in json_schema mode."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1] if "```" in content[3:] else content[3:]
        content = content.removeprefix("json").strip()
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValidationError_("No JSON object found in response")
    try:
        return json.loads(content[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValidationError_(f"Invalid JSON: {exc}") from exc


def call_provider(profile, system_prompt: str, user_body: str, timeout: int) -> dict:
    """POST to {base_url}/chat/completions and return the parsed JSON payload."""
    url = profile.base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": profile.model,
        "temperature": 0,
        "response_format": {"type": "json_schema", "json_schema": JSON_SCHEMA},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_body},
        ],
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if profile.api_key_env:
        key = os.environ.get(profile.api_key_env, "")
        if key:
            headers["Authorization"] = f"Bearer {key}"

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise ProviderError(f"HTTP {exc.code} from provider: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError(f"Provider unreachable: {exc}") from exc

    try:
        envelope = json.loads(raw)
        content = envelope["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise ProviderError(f"Unexpected provider envelope: {raw[:300]}") from exc

    return _extract_json(content)
