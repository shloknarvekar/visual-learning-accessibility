"""The Pydantic models and packages/contracts/lesson.schema.json must describe the same contract."""

from typing import Any, get_args

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from app.schemas import lesson as lesson_models
from app.schemas.lesson import Lesson, Section


@pytest.fixture(scope="module")
def validator(lesson_schema: dict[str, Any]) -> Draft202012Validator:
    return Draft202012Validator(lesson_schema, format_checker=FormatChecker())


def _schema_errors(validator: Draft202012Validator, instance: Any) -> list[str]:
    return [
        f"/{'/'.join(map(str, error.absolute_path))}: {error.message}"
        for error in validator.iter_errors(instance)
    ]


def _section(lesson_data: dict[str, Any], section_type: str) -> dict[str, Any]:
    return next(s for s in lesson_data["sections"] if s["type"] == section_type)


def test_schema_is_valid_json_schema(lesson_schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(lesson_schema)


def test_example_lesson_matches_json_schema(
    validator: Draft202012Validator, example_lesson_data: dict[str, Any]
) -> None:
    assert _schema_errors(validator, example_lesson_data) == []


def test_example_lesson_matches_pydantic_model(example_lesson_data: dict[str, Any]) -> None:
    Lesson.model_validate(example_lesson_data)


def test_serialised_lesson_matches_json_schema(
    validator: Draft202012Validator, example_lesson: Lesson
) -> None:
    payload = example_lesson.model_dump(mode="json", exclude_none=True)

    assert _schema_errors(validator, payload) == []
    assert Lesson.model_validate(payload) == example_lesson


def test_models_have_the_same_fields_as_the_schema(lesson_schema: dict[str, Any]) -> None:
    assert set(Lesson.model_fields) == set(lesson_schema["properties"])
    for name, definition in lesson_schema["$defs"].items():
        if "properties" in definition:
            model = getattr(lesson_models, name)
            assert set(model.model_fields) == set(definition["properties"]), name


def test_constants_match_the_schema(lesson_schema: dict[str, Any]) -> None:
    defs = lesson_schema["$defs"]
    schema_section_types = {
        defs[ref["$ref"].rsplit("/", 1)[-1]]["properties"]["type"]["const"]
        for ref in defs["Section"]["oneOf"]
    }
    section_models = get_args(get_args(Section)[0])
    model_section_types = {get_args(m.model_fields["type"].annotation)[0] for m in section_models}

    assert model_section_types == schema_section_types
    assert get_args(Lesson.model_fields["schema_version"].annotation) == (
        lesson_schema["properties"]["schema_version"]["const"],
    )
    assert defs["Id"]["pattern"] == lesson_models.ID_PATTERN


def test_rejects_edge_to_unknown_node(example_lesson_data: dict[str, Any]) -> None:
    edges = _section(example_lesson_data, "concept_map")["content"]["edges"]
    edges.append({"from_id": "light", "to_id": "missing-node"})

    with pytest.raises(ValidationError, match="unknown node"):
        Lesson.model_validate(example_lesson_data)


def test_rejects_quiz_answer_that_is_not_an_option(example_lesson_data: dict[str, Any]) -> None:
    example_lesson_data["quiz"][0]["correct_option_id"] = "z"

    with pytest.raises(ValidationError, match="correct_option_id"):
        Lesson.model_validate(example_lesson_data)


def test_rejects_comparison_row_with_wrong_width(example_lesson_data: dict[str, Any]) -> None:
    rows = _section(example_lesson_data, "comparison")["content"]["rows"]
    rows[0]["values"].append("Extra value")

    with pytest.raises(ValidationError, match="values for 2 items"):
        Lesson.model_validate(example_lesson_data)
