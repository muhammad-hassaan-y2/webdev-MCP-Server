from typing import Literal, Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that serializes to camelCase JSON (to match the JS widget's
    field names) while staying snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TestCase(CamelModel):
    input: list[Any]
    expected: Any


class ParamSpec(CamelModel):
    key: str
    label: str
    min: float
    max: float
    step: float
    default: float
    unit: str | None = None


class CodeMission(CamelModel):
    type: Literal["code"] = "code"
    id: str
    title: str
    concept: str
    description: str
    function_name: str
    starter_code: str
    tests: list[TestCase]
    fallback_hints: list[str]


class SimulationMission(CamelModel):
    type: Literal["simulation"] = "simulation"
    id: str
    title: str
    concept: str
    description: str
    params: list[ParamSpec]
    target_label: str
    fallback_hints: list[str]


Mission = CodeMission | SimulationMission
