import re
from inspect import Parameter, isclass, signature
from string import Formatter
from typing import Callable, Pattern, Type

from apispec.utils import trim_docstring
from tornado.routing import URLSpec
from tornado.web import RequestHandler

from ..model import RequestBody, ResponseBody
from .core import TornOpenAPISpec
from .plugin import TornOpenPlugin, get_implemented_http_methods

BRACKETS_PATTERN = re.compile(r"\((.*?)\)")


# Utils
def regex_to_url(regex: Pattern, method: Callable) -> str:
    has_keys = regex.groups
    is_keyword_regex = regex.groupindex
    cleaned_url = regex.pattern.replace("$", "")
    cleaned_url = cleaned_url.rstrip("/*") if cleaned_url != "/" else cleaned_url
    cleaned_url = re.sub(BRACKETS_PATTERN, "{}", cleaned_url)

    if not has_keys:
        return cleaned_url

    path_params = []
    if is_keyword_regex:
        path_params = [f"{{{key}}}" for key in regex.groupindex]
    else:
        sig = signature(method)
        path_params = [*sig.parameters.values()][1: regex.groups + 1]
        path_params = [f"{{{p.name}}}" for p in path_params]

    cleaned_url = cleaned_url.format(*path_params)
    return cleaned_url


def is_RequestBody_subclass(type_: Type):
    if not type_:
        return False
    if not isclass(type_):
        return False
    return issubclass(type_, RequestBody)


# / Utils


def parse_parameters(
    path: str, method: Callable
) -> tuple[list[Parameter], list[Parameter], Parameter | None, ResponseBody | None]:
    function_signature = signature(method)
    function_parameters = function_signature.parameters
    function_parameters = {k: v for k, v in function_parameters.items() if k != "self"}

    # filter param names
    path_param_names = [p[1] for p in list(Formatter().parse(path)) if p[1]]
    query_param_names = [
        p.name
        for p in function_parameters.values()
        if p.name not in path_param_names and not is_RequestBody_subclass(p.annotation)
    ]
    request_body_names = [
        p.name
        for p in function_parameters.values()
        if is_RequestBody_subclass(p.annotation)
    ]
    request_body_name = request_body_names[0] if request_body_names else None

    # group parameters
    path_parameters = [
        function_parameters[p] for p in path_param_names if p in function_parameters
    ]
    query_parameters = [function_parameters[p] for p in query_param_names]
    request_body = function_parameters[request_body_name] if request_body_name else None
    return_annotation = (
        function_signature.return_annotation
        if function_signature.return_annotation is not function_signature.empty
        else None
    )

    return (
        path_parameters,
        query_parameters,
        request_body,
        return_annotation,
    )


class HandlerParams:
    def __init__(self, regex: Pattern, handler: RequestHandler):
        implemented_methods = get_implemented_http_methods(handler)
        self.handler = handler
        self.path_params: dict[str, list] = {}
        self.query_params: dict[str, list] = {}
        self.request_body: dict = {}
        self.response_models: dict = {}

        for method_name in implemented_methods:
            method = getattr(handler, method_name)

            self.path = regex_to_url(regex, method)
            (
                path_params,
                query_params,
                request_body,
                return_annotation,
            ) = parse_parameters(self.path, method)

            self.path_params[method_name] = path_params
            self.query_params[method_name] = query_params
            self.request_body[method_name] = request_body
            self.response_models[method_name] = return_annotation


def create_api_spec(name: str, rules: list[URLSpec]):
    api_spec = TornOpenAPISpec(
        title=name,
        version="1.0.0",
        openapi_version="3.1.0",
        plugins=[TornOpenPlugin()],
    )
    for rule in rules:
        path = rule.regex
        handler = rule.handler_class
        handler.handler_class_params = HandlerParams(path, handler)
        try:
            api_spec.path(
                url_spec=rule,
                handler_class=handler,
                description=trim_docstring(handler.__doc__),
            )
        finally:
            del handler.handler_class_params

    enum_tags = []
    model_tags = []
    for name, schema in api_spec.components.schemas.items():
        if "enum" in schema:
            tag_name = f"enum.{name}"
            enum_tags.append(tag_name)
        else:
            tag_name = f"model.{name}"
            model_tags.append(tag_name)

        api_spec.tag(
            {
                "name": tag_name,
                "description": f'<SchemaDefinition schemaRef="#/components/schemas/{name}" />',
                "x-displayName": name,
            }
        )

    dict_spec = api_spec.to_dict()
    if api_spec._tags:
        x_tag_groups = []
        if api_spec.handler_tags:
            x_tag_groups.append(
                {"name": "Endpoints", "tags": list(api_spec.handler_tags)}
            )
        if enum_tags:
            x_tag_groups.append({"name": "Enum", "tags": enum_tags})
        if model_tags:
            x_tag_groups.append({"name": "Models", "tags": model_tags})
        dict_spec["x-tagGroups"] = x_tag_groups
    return dict_spec
