"""Turns Pydantic models into the JSON Schema dialect each provider accepts.

Providers disagree about which JSON Schema features they support, so each one gets its own
transform. Both start by inlining `$defs`/`$ref`, because neither dialect guarantees reference
support. Whatever comes back is still validated against the full Pydantic model afterwards, so
dropping a constraint here only relaxes what we ask the model for, never what we accept.
"""

from typing import Any

from pydantic import BaseModel

# Keywords Gemini documents as supported for structured output.
_GEMINI_KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "items",
        "prefixItems",
        "minItems",
        "maxItems",
        "enum",
        "format",
        "minimum",
        "maximum",
        "anyOf",
        "title",
        "description",
        "additionalProperties",
    }
)

# OpenAI-style strict mode accepts a smaller set and rejects validation keywords such as minItems.
_STRICT_KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "items",
        "enum",
        "anyOf",
        "description",
        "additionalProperties",
    }
)


def gemini_schema(model: type[BaseModel]) -> dict[str, Any]:
    """`model`'s schema, self-contained and limited to keywords Gemini supports."""
    schema = model.model_json_schema()
    return _convert(schema, schema.get("$defs", {}), _GEMINI_KEYWORDS, strict=False)


def openai_strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """`model`'s schema for OpenAI-compatible `strict: true` structured output.

    Strict mode requires every object to forbid extra properties and to list every property as
    required, so fields the model should leave empty are still sent back as "" or [].
    """
    schema = model.model_json_schema()
    return _convert(schema, schema.get("$defs", {}), _STRICT_KEYWORDS, strict=True)


def _convert(
    node: Any, definitions: dict[str, Any], keywords: frozenset[str], *, strict: bool
) -> Any:
    if isinstance(node, list):
        return [_convert(item, definitions, keywords, strict=strict) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        referenced = definitions[node["$ref"].rsplit("/", 1)[-1]]
        siblings = {key: value for key, value in node.items() if key != "$ref"}
        return _convert({**referenced, **siblings}, definitions, keywords, strict=strict)

    converted: dict[str, Any] = {}
    for key, value in node.items():
        if key == "const":
            converted["enum"] = [value]
        elif key == "oneOf":
            converted["anyOf"] = _convert(value, definitions, keywords, strict=strict)
        elif key == "properties":
            converted[key] = {
                name: _convert(sub, definitions, keywords, strict=strict)
                for name, sub in value.items()
            }
        elif key in keywords:
            converted[key] = _convert(value, definitions, keywords, strict=strict)

    if strict and "properties" in converted:
        converted["additionalProperties"] = False
        converted["required"] = list(converted["properties"])
    return converted
