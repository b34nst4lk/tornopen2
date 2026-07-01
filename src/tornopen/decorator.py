"""
The `validate_arguments` decorator is adapted from the decorator by the same name
in the pydantic library. This decorator is currently still an experiment, and
is not official supported by pydantic until version 2.0.
"""

from enum import EnumType
from functools import wraps
from inspect import isclass, iscoroutinefunction, signature
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeAlias,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

try:
    import orjson as json
except ModuleNotFoundError:
    import json

from pydantic import ValidationError, create_model

# from pydantic.fields import ModelField
from tornado.httputil import HTTPServerRequest
from tornado.web import RequestHandler

import logging

from .http_error import HTTPError, RequestValidationError, UnsupportedMediaTypeError
from .model import BaseModel, QueryParams, RequestBody

if TYPE_CHECKING:
    from pydantic.typing import AnyCallable

    AnyCallableT = TypeVar("AnyCallableT", bound=AnyCallable)
    ConfigType = Union[None, Type[Any], Dict[str, Any]]


def _is_primitive(type_: Type):
    return (
        isinstance(type_, type)
        and type_ in (bool, str, int, float)
        or isinstance(type_, EnumType)
    )


def is_primitive(type_: Type):
    if _is_primitive(type_):
        return True
    if get_args(type_):
        return all(
            (is_primitive(t) or t is type(None)) and not is_collection(t)
            for t in get_args(type_)
        )

    return False


def _is_collection(type_: Type):
    return type_ in (list, set)


def is_collection(type_: Type):
    if _is_collection(type_):
        return True
    if get_origin(type_) in (list, set):
        return True
    if get_args(type_):
        return all(
            get_origin(t) in (list, set) or t in (list, set) or t is type(None)
            for t in get_args(type_)
        )
    return False


def retrieve_request_body(
    request: HTTPServerRequest,
) -> tuple[bytes | None, bool]:
    """Return (body, is_json).

    - JSON body: (raw bytes, True)
    - Non-JSON body present: (None, False) — caller raises 415
    - No body: (None, True) — caller lets pydantic raise 400 on missing field
    """
    content_type = request.headers.get("Content-Type", "")
    is_json = content_type.startswith("application/json")
    if is_json:
        return request.body, True
    if request.body:
        return None, False
    return None, True


def retrieve_query_arguments(request_handler: RequestHandler, fields) -> Dict[str, Any]:
    query_parameters = {}
    for name, field in fields.items():
        try:
            if is_collection(field):
                if (value := request_handler.get_query_argument(name)) is not None:
                    query_parameters[name] = value.split(",")
            elif is_primitive(field):
                query_parameters[name] = request_handler.get_query_argument(name)
        finally:
            continue

    return query_parameters


def is_wrapped_coroutine_function(func: Callable) -> bool:
    while hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    return iscoroutinefunction(func)


def _handle_http_error(e: HTTPError) -> Tuple[int, str]:
    logging.error(e, exc_info=True)
    return e.status_code, e.dict()


def _handle_pydantic_validation_error(e: ValidationError) -> Tuple[int, str]:
    logging.error(e, exc_info=True)
    status_code = 500
    error = json.dumps(
        {
            "error": {
                "type": "server_error",
                "message": "Internal Server Error",
            }
        }
    )
    return status_code, error


def _handle_request_validation_error(e: RequestValidationError) -> Tuple[int, str]:
    logging.error(e, exc_info=True)
    status_code = 400
    error = json.dumps(
        {
            "error": {
                "type": "validation_error",
                "message": str(e),
            }
        }
    )
    return status_code, error


E = TypeVar("E", bound=Exception)
ExceptionHandler: TypeAlias = Callable[[E], Tuple[int, str]]
ExceptionHandlers: TypeAlias = Dict[Type[E], ExceptionHandler]


class ValidateHTTPCallWrapper:
    """
    This wrapper splits the call to the HTTP method into the request validation
    and execution steps.
    """

    def __init__(self, function):
        self.raw_function = function
        self.__signature__ = signature(function)
        # Check if all parameters provided are valid, if not raise a TypeError
        # and complete stop initialization
        self.validate_parameters()

        self.url_params_validator = self.create_url_params_validator()
        (
            self.request_body_name,
            self.request_body_validator,
        ) = self.create_request_body_validator()

    def create_url_params_validator(self) -> BaseModel:
        attributes = {}
        for name, parameter in self.__signature__.parameters.items():
            if name == "self":
                continue
            if isinstance(parameter.annotation, type) and issubclass(parameter.annotation, RequestBody):
                continue
            if isinstance(parameter.annotation, type) and issubclass(parameter.annotation, QueryParams):
                continue

            attributes[name] = (
                parameter.annotation,
                ... if parameter.default is parameter.empty else parameter.default,
            )

        return create_model(
            f"{self.raw_function.__qualname__}.request",
            __base__=BaseModel,
            **attributes,
        )

    def create_request_body_validator(self):
        for name, parameter in self.__signature__.parameters.items():
            if name == "self":
                continue
            try:
                if issubclass(parameter.annotation, RequestBody):
                    return name, parameter.annotation
            except Exception:
                pass
        return None, None

    def validate_parameters(self) -> bool:
        for parameter in self.__signature__.parameters.values():
            if parameter.name == "self":
                continue
            if is_primitive(parameter.annotation):
                continue
            if is_collection(parameter.annotation):
                continue
            if issubclass(parameter.annotation, (RequestBody, QueryParams)):
                continue
            raise TypeError(f"{parameter.name} is not of a valid type")
        return True

    def validate_request(self, *args, **kwargs):
        try:
            request_body = (
                kwargs.pop(self.request_body_name) if self.request_body_name else None
            )
            parameters = {
                **self.url_params_validator(*args, **kwargs).model_dump(),
            }
            if request_body:
                parameters[self.request_body_name] = self.request_body_validator(
                    **request_body
                )
            return parameters
        except ValidationError as e:
            raise RequestValidationError(
                e,
                status_code=400,
                error_type="validation_error",
            ) from e

    def execute(self, *args, **kwargs):
        return self.raw_function(*args, **kwargs)


class ValidateArgumentsDecoratorFactory:
    def __init__(self, exclude_none: bool = False):
        self.exception_handlers: ExceptionHandlers = {
            HTTPError: _handle_http_error,
            ValidationError: _handle_pydantic_validation_error,
            RequestValidationError: _handle_request_validation_error,
        }
        self.exclude_none = exclude_none

    def get_exception_handler(self, e: Exception) -> Optional[ExceptionHandler]:
        if (exception_type := type(e)) in self.exception_handlers:
            return self.exception_handlers[exception_type]

        for parent in exception_type.mro():
            if parent in self.exception_handlers:
                return self.exception_handlers[parent]
            if parent is Exception:
                return None
        return None

    def __call__(
        self,
        func: Optional["AnyCallableT"] = None,
        *,
        exclude_none: Optional[bool] = None,
    ) -> Any:
        """
        This replaces the validate_arguments decorator provided by Pydantic, and is
        meant specifically for decorating http methods defined in subclasses of
        `tornado.web.RequestHandler`

        ---

        Args:
            func: http method defined in subclass of `tornado.web.RequestHandler`
            exclude_none: per-decorator override; defaults to the factory's setting
        Returns:
            wrapped function that validates function parameters before the nested
            function is called
        """

        effective_exclude_none = (
            self.exclude_none if exclude_none is None else exclude_none
        )

        def validate(_func: "AnyCallable") -> "AnyCallable":
            wrapper = ValidateHTTPCallWrapper(_func)

            is_async = is_wrapped_coroutine_function(_func)

            @wraps(_func)
            async def wrapper_function(
                request_handler: RequestHandler, *path_args: list, **path_kwargs: dict
            ) -> Any:
                # Prepare function parameters
                request_handler_kwargs = {
                    **path_kwargs,
                    **retrieve_query_arguments(request_handler, _func.__annotations__),
                }

                # initialize default values
                status_code = 200
                payload = None

                # attempt to execute function
                try:
                    if wrapper.request_body_name:
                        body, is_json = retrieve_request_body(
                            request_handler.request
                        )
                        if not is_json:
                            raise UnsupportedMediaTypeError(
                                415,
                                error_type="unsupported_media_type",
                                error_message="Content-Type must be application/json",
                            )
                        request_handler_kwargs[wrapper.request_body_name] = (
                            json.loads(body) if body else {}
                        )
                    validated_arguments = wrapper.validate_request(
                        *path_args, **request_handler_kwargs
                    )
                except Exception as e:
                    handle_exception = self.get_exception_handler(e)
                    if not handle_exception:
                        raise e
                    status_code, payload = handle_exception(e)
                    request_handler.set_status(status_code)
                    if payload:
                        request_handler.set_header("Content-Type", "application/json")
                        request_handler.write(payload)
                    return

                try:
                    if is_async:
                        result = await wrapper.execute(
                            request_handler, **validated_arguments
                        )
                    else:
                        result = wrapper.execute(request_handler, **validated_arguments)
                    if result:
                        payload = result.model_dump_json(
                            exclude_none=effective_exclude_none,
                            exclude_unset=False,
                        )
                # handle exception from function execution
                except Exception as e:
                    handle_exception = self.get_exception_handler(e)
                    if not handle_exception:
                        raise e
                    status_code, payload = handle_exception(e)
                finally:
                    if status_code != 200:
                        request_handler.set_status(status_code)
                    if payload:
                        request_handler.set_header("Content-Type", "application/json")
                        request_handler.write(payload)

            return wrapper_function

        return validate(func) if func else validate

    def exception_handler(self, e: Type[Exception]):
        def decorator(func: Callable):
            self.exception_handlers[e] = func

        return decorator


def doc_category(category):
    def decorator(cls):
        if not isclass(cls):
            raise ValueError("doc_category is for decorating classes")
        setattr(cls, "_doc_category", category)
        return cls

    return decorator


def _doc_attribute(attribute_name):
    """
    This function creates functions from the attribute_name. The returned
    function can then be used as a decorator with attributes to set values to a
    decorated function
    """

    def _decorator(attribute):
        def decorator(func):
            setattr(func, f"_{attribute_name}", attribute)
            return func

        return decorator

    return _decorator


doc_tag = _doc_attribute("doc_tag")
doc_summary = _doc_attribute("doc_summary")

validate_arguments = ValidateArgumentsDecoratorFactory(exclude_none=False)
