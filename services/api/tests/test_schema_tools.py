import json

from app.ai.drafts import LessonDraft
from app.ai.schema_tools import gemini_schema, openai_strict_schema


def _objects(node: object) -> list[dict]:
    """Every object schema (one with `properties`) anywhere in the tree."""
    found: list[dict] = []
    if isinstance(node, dict):
        if "properties" in node:
            found.append(node)
        for value in node.values():
            found.extend(_objects(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_objects(item))
    return found


def test_gemini_schema_is_self_contained_and_uses_supported_keywords() -> None:
    text = json.dumps(gemini_schema(LessonDraft))

    for unsupported in ('"$ref"', '"$defs"', '"default"', '"const"'):
        assert unsupported not in text


def test_strict_schema_forbids_extra_properties_and_requires_every_field() -> None:
    schema = openai_strict_schema(LessonDraft)

    objects = _objects(schema)
    assert objects, "expected at least one object schema"
    for node in objects:
        assert node["additionalProperties"] is False
        assert set(node["required"]) == set(node["properties"])


def _keywords(node: object) -> set[str]:
    """Every key used at a schema position. Property *names* are data, so they are not collected."""
    found: set[str] = set()
    if isinstance(node, dict):
        found.update(node)
        for key, value in node.items():
            if key == "properties":
                for sub in value.values():
                    found.update(_keywords(sub))
            elif key in {"items", "anyOf", "prefixItems"}:
                found.update(_keywords(value))
    elif isinstance(node, list):
        for item in node:
            found.update(_keywords(item))
    return found


def test_strict_schema_drops_keywords_strict_mode_rejects() -> None:
    # Checked structurally, not as a substring: `LessonDraft` has a field *named* `title`, which
    # must survive even though the `title` keyword is dropped.
    keywords = _keywords(openai_strict_schema(LessonDraft))

    assert not keywords & {"$ref", "$defs", "default", "minItems", "maxItems", "title"}


def test_strict_schema_keeps_the_section_types_and_nested_shapes() -> None:
    schema = openai_strict_schema(LessonDraft)

    section = schema["properties"]["sections"]["items"]
    assert "concept_map" in section["properties"]["type"]["enum"]
    assert section["properties"]["steps"]["items"]["properties"]["title"]["type"] == "string"
