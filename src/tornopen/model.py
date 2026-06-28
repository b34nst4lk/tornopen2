"""
base_model extends the pydantic.BaseModel feature to
- enable the cleaning of $ref values to point to a specified ref_prefix
- casting of enums to enum values when exporting a model to dict
"""

from enum import Enum as _Enum
try:
    from enum import StrEnum as _StrEnum
except ImportError:  # Python < 3.11
    class _StrEnum(str, _Enum):
        pass
from typing import TypeAlias

from pydantic import BaseModel as _BaseModel
from pydantic.fields import Field


def replace_enums(val):
    if isinstance(val, _Enum):
        return val.value
    if isinstance(val, list):
        return [replace_enums(v) for v in val]
    if isinstance(val, dict):
        return {replace_enums(k): replace_enums(v) for k, v in val.items()}
    return val


def _remove_excluded_schema(schema, model):
    """
    1. Exclusion of keys in schema
    We exclude the key from the schema if the `exclude_schema` is provided

    Example
    ```
    class Example(BaseModel):
        x: int

        class Config:
            fields = {
                "x": {"exclude_schema": True}
            }

    print(Example.schema())
    # Result: {
        'title': 'Example',
        'type': 'object',
        'properties': {},
        'required': [],
    }
    ```
    """
    excluded_keys = {
        key
        for key, value in schema["properties"].items()
        if value.get("exclude_schema")
    }
    schema["properties"] = {
        key: value
        for key, value in schema["properties"].items()
        if key not in excluded_keys
    }
    schema["required"] = [
        key for key in schema.get("required") or [] if key not in excluded_keys
    ]
    schema["key"] = f"{model.__module__}.{model.__name__}"
    schema["name"] = f"{model.__name__}"
    return schema


class BaseModel(_BaseModel):
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        json_schema = handler(core_schema)
        json_schema["key"] = f"{cls.__module__}.{cls.__name__}"
        json_schema = _remove_excluded_schema(json_schema, cls)
        return json_schema

    def get(self, key):
        return self.dict().get(key)

    def __getitem__(self, key):
        val = self.dict()[key]
        return val.value if isinstance(val, _Enum) else val

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def dict(self, *args, **kwargs) -> dict:
        d = super().model_dump(*args, **kwargs)
        return replace_enums(d)


class QueryParams(BaseModel):
    pass


class RequestBody(BaseModel):
    pass


class ResponseBody(BaseModel):
    pass


class ModifySchemaMixin:
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        json_schema = handler(core_schema)
        json_schema["key"] = f"{cls.__module__}.{cls.__name__}"
        return json_schema


# Doc string of Enum is hardcoded to an empty string to prevent the default
# doc string from being displayed on Redoc
class Enum(ModifySchemaMixin, _Enum):
    """"""


class StrEnum(ModifySchemaMixin, _StrEnum):
    """"""


Timestamp: TypeAlias = int


class TimestampedBaseModel(BaseModel):
    created_at: Timestamp = Field(
        description="microsecond integer timestamp when object was first created"
    )
    updated_at: Timestamp = Field(
        description="microsecond integer timestamp when object was last updated"
    )
