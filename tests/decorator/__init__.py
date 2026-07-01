from enum import Enum
from typing import Optional

from tornado.routing import URLSpec
from tornado.web import RequestHandler

from tornopen import RequestBody, validate_arguments


# Test handlers for path params and required query params tests
class IntegerHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: int):
        assert isinstance(param, int)
        self.set_status(200)
        self.write("success")


class StringHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: str):
        assert isinstance(param, str)
        self.set_status(200)
        self.write("success")


class ExampleEnum(Enum):
    value1 = "value1"
    value2 = "value2"


class EnumHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: ExampleEnum):
        assert ExampleEnum(param)
        self.set_status(200)
        self.write("success")


class BooleanHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: bool):
        assert isinstance(param, bool)
        self.set_status(200)
        self.write("success")


class RequiredGenericListHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: list):
        assert isinstance(param, list)
        self.set_status(200)
        self.write("success")


# Test handlers for Optional query params
class OptionalIntegerHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: Optional[int] = None):
        assert isinstance(param, (int, type(None)))
        self.set_status(200)
        self.write("success")


class OptionalStringHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: Optional[str] = None):
        assert isinstance(param, (str, type(None)))
        self.set_status(200)
        self.write("success")


class OptionalEnumHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: Optional[ExampleEnum] = None):
        assert param is None or ExampleEnum(param)
        self.set_status(200)
        self.write("success")


class OptionalBooleanHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: Optional[bool] = None):
        assert isinstance(param, (bool, type(None)))
        self.set_status(200)
        self.write("success")


class OptionalGenericListHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: Optional[list] = None):
        assert isinstance(param, (list, type(None)))
        self.set_status(200)
        self.write("success")


class ComplexRequest(RequestBody):
    integer: int
    string: str
    boolean: bool


class ComplexRequestHandler(RequestHandler):
    @validate_arguments
    async def post(
        self,
        path_param: int,
        str_query: str,
        bool_query: bool,
        complex_request: ComplexRequest,
    ):
        assert isinstance(path_param, int)
        assert isinstance(str_query, str)
        assert isinstance(bool_query, bool)
        assert isinstance(complex_request, ComplexRequest)


# utils for formatting test results
def id_fn(val):
    if isinstance(val, URLSpec):
        return val.handler_class.__name__
