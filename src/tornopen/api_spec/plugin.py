import re
from inspect import Parameter, isclass
from typing import Any, Dict, Type, Union, get_args, get_origin

from apispec import BasePlugin
from apispec.core import Components
from apispec.utils import trim_docstring
from pydantic import create_model

import logging

from ..http_error import HTTPError
from ..model import BaseModel
from .exception_finder import get_exceptions


# Utils
def _is_required(parameter_type: Union[type, Parameter]):
    if isinstance(parameter_type, type):
        return False
    return get_origin(parameter_type) == Union and type(None) in get_args(
        parameter_type
    )


def _is_implemented(method, handler):
    if isinstance(method, str):
        method = getattr(handler, method)

    return method is not handler._unimplemented_method


def get_implemented_http_methods(handler):
    return [
        method.lower()
        for method in handler.SUPPORTED_METHODS
        if _is_implemented(method.lower(), handler)
    ]


def _clear_none_from_dict(dictionary: Dict[Any, Any]):
    new_dict = {}
    for k, v in dictionary.items():
        if isinstance(v, dict):
            v = _clear_none_from_dict(v)
        if v not in [None, {}, []]:
            new_dict[k] = v
    return new_dict


# /Utils


SCHEMA_REF_TEMPLATE = "#/components/schemas/{model}"


class TornOpenPlugin(BasePlugin):
    """APISpec plugin for Tornado"""

    def init_spec(self, spec):
        self.spec = spec

    def path_helper(self, *, handler_class, **_):
        return handler_class.handler_class_params.path

    def operation_helper(self, *, operations, url_spec, **_):
        try:
            processed_operations = Operations(self.spec, url_spec, self.spec.components)
            operations.update(**processed_operations)
        except Exception as e:
            logging.error(
                f"Error in creating documentation for {url_spec.regex.pattern} {url_spec.handler_class.__qualname__}"
            )
            logging.exception(e)


def schema_has_been_registered(
    referenced_schema_id: str,
    referenced_schema: dict,
    components: Components,
) -> bool:
    if referenced_schema_id not in components.schemas:
        return False
    if referenced_schema.get("key") in components.schemas:
        return True
    return referenced_schema["key"] == components.schemas[referenced_schema_id]["key"]


def get_duplicated_schema(
    referenced_schema_id: str,
    referenced_schema: dict,
    components: Components,
):
    if referenced_schema_id not in components.schemas:
        return None

    duplicated_schema = components.schemas[referenced_schema_id]
    if referenced_schema.get("key") == duplicated_schema.get("key"):
        return None

    return duplicated_schema


def search_and_replace_ref(schema: dict, target: str, replacement: str):
    for k, v in schema.items():
        if k == "$ref" and v == SCHEMA_REF_TEMPLATE.format(model=target):
            schema["$ref"] = SCHEMA_REF_TEMPLATE.format(model=replacement)
        if isinstance(v, dict):
            search_and_replace_ref(v, target, replacement)
    return schema


def Schema(parameter: Union[Parameter, Type[BaseModel]], components: Components):
    definitions = {}
    schema = {}
    if isclass(parameter) and issubclass(parameter, BaseModel):
        schema = parameter.schema(ref_template=SCHEMA_REF_TEMPLATE)
    elif isinstance(parameter, Parameter):
        annotation = (
            parameter.annotation if parameter.annotation is not parameter.empty else str
        )
        default = parameter.default if parameter.default is not parameter.empty else ...
        fields = {parameter.name: (annotation, default)}

        model = create_model("_", **fields).model_json_schema(
            ref_template=SCHEMA_REF_TEMPLATE
        )
        schema = model.get("properties", {}).get(parameter.name, {})
        definitions |= model.pop("$defs", {})
    schema = _clear_none_from_dict(schema)

    definitions.update(schema.pop("$defs", {}))
    if not definitions:
        return schema

    for referenced_schema_id, referenced_schema in definitions.items():
        if schema_has_been_registered(
            referenced_schema_id, referenced_schema, components
        ):
            continue
        if duplicated_schema := get_duplicated_schema(
            referenced_schema_id, referenced_schema, components
        ):
            logging.warning(
                "Model names for"
                f"\n{referenced_schema['key']} "
                "\n\tand"
                f"\n{duplicated_schema['key']} \n\t are duplicated."
                "You may want to consider renaming the models for clarity or explore if the models can be reused."
            )
            referenced_schema_key = referenced_schema["key"]
            schema = search_and_replace_ref(
                schema, referenced_schema_id, referenced_schema_key
            )
            referenced_schema_id = referenced_schema_key
        components.schema(referenced_schema_id, referenced_schema)

    return schema


def RequestParameter(
    parameter: Parameter,
    param_type,
    components: Components,
):
    return {
        "name": parameter.name,
        "in": param_type,
        "required": _is_required(parameter),
        "schema": Schema(parameter, components),
    }


# Operations helper methods
def Operations(api_spec, url_spec, components: Components):
    handler = url_spec.handler_class
    implemented_methods = get_implemented_http_methods(handler)
    return {
        method: Operation(api_spec, method, handler, components).schema()
        for method in implemented_methods
    }


class Operation:
    def _get_tags(self):
        tag = getattr(self.method, "_doc_tag", "untagged")
        self.spec.tag({"name": tag, "description": tag}, "handler")
        return [tag]

    def _get_summary(self):
        return getattr(
            self.method,
            "_doc_summary",
            f"{self.method.__name__.upper()}: {self.handler.handler_class_params.path}",
        )

    def _get_path_params(self):
        parameters = self.handler.handler_class_params.path_params[self.method.__name__]
        return [
            RequestParameter(parameter, "path", self.components)
            for parameter in parameters
        ]

    def _get_query_params(self):
        parameters = self.handler.handler_class_params.query_params[
            self.method.__name__
        ]

        return [
            RequestParameter(parameter, "query", self.components)
            for parameter in parameters
        ]

    def _get_operation_description(self):
        if not hasattr(self.method, "__doc__"):
            return {}
        if not self.method.__doc__:
            return {}
        doc = trim_docstring(self.method.__doc__)
        doc = re.sub(" +", " ", doc)
        return doc

    def __init__(self, spec, method, handler, components):
        self.spec = spec
        self.method = getattr(handler, method)
        self.handler = handler
        self.components = components

        operation = {
            "tags": self._get_tags(),
            "summary": self._get_summary(),
            "description": self._get_operation_description(),
            "parameters": [*self._get_path_params(), *self._get_query_params()],
            "requestBody": RequestBody(method, handler, components),
            "responses": Responses(method, handler, components),
        }
        self._schema = _clear_none_from_dict(operation)

    def schema(self):
        return self._schema


def RequestBody(method: str, handler, components):
    request_body = handler.handler_class_params.request_body[method]
    if not request_body:
        return None
    parameter = request_body
    schema = RequestBodySchema(parameter, components)
    return {"content": {"application/json": {"schema": schema}}}


def RequestBodySchema(parameter, components):
    return Schema(parameter, components)


def Responses(method, handler, components):
    responses = {
        200: SuccessResponse(method, handler, components),
        **_get_failure_responses(method, handler),
    }

    return _clear_none_from_dict(responses)


def SuccessResponse(method, handler, components):
    def get_success_response_description(response_model):
        description = ""
        if response_model and response_model.__doc__:
            description = trim_docstring(response_model.__doc__)
        return description

    response_model = handler.handler_class_params.response_models[method]
    response = {
        "description": get_success_response_description(response_model),
        "content": {"application/json": {"schema": Schema(response_model, components)}},
    }
    return _clear_none_from_dict(response)


def SuccessResponseModelSchema(response_model, components):
    schema = (
        response_model.schema(ref_template=SCHEMA_REF_TEMPLATE)
        if response_model
        else None
    )
    if not schema:
        return schema

    referenced_schemas = schema.pop("definitions", {})
    if not referenced_schemas:
        return schema

    for referenced_schema_id, referenced_schema in referenced_schemas.items():
        components.schema(referenced_schema_id, referenced_schema)

    return schema


def is_HTTPError_subclass(exception_class: Type[Exception]):
    if exception_class is HTTPError:
        return True

    return issubclass(exception_class, HTTPError)


def _get_failure_responses(method, handler) -> Dict[str, dict]:
    http_method = getattr(handler, method, None)
    exceptions = _retrieve_exceptions(http_method)
    return FailedResponses(exceptions)


def _retrieve_exceptions(http_method):
    error_codes_and_types = {}
    for exception_class, args, kwargs in get_exceptions(http_method):
        if not is_HTTPError_subclass(exception_class):
            continue

        exception_instance = exception_class(*args, **kwargs)
        status_code = exception_instance.status_code

        error_messages = error_codes_and_types.get(status_code, [])
        try:
            error_messages.append(str(exception_instance))
        except Exception:
            logging.warning(
                f"Failed to include exception for {http_method.__qualname__}"
            )

        error_codes_and_types[status_code] = error_messages
    return error_codes_and_types


def FailedResponses(exceptions):
    return {
        status_code: FailedResponse(error_types)
        for status_code, error_types in exceptions.items()
    }


def FailedResponse(error_types):
    return {
        "description": " | ".join(error_types),
    }
