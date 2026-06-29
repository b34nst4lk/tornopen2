import pytest
from tornado.web import Application, RequestHandler, url

from tornopen import (
    BaseModel,
    ResponseBody,
    documenter,
    validate_arguments,
)


class EvenSmallerModel(BaseModel):
    i: int


class SmallModel(BaseModel):
    e: EvenSmallerModel


class BigModel(ResponseBody):
    s: SmallModel


class NestedModelRequestHandler(RequestHandler):
    @validate_arguments
    async def get(self) -> BigModel:
        ...


@pytest.fixture
def routes():
    return [url("/", NestedModelRequestHandler)]


@pytest.fixture
def app(routes):
    return documenter(Application(routes))


@pytest.mark.gen_test
def test_nested_model_schema(app):
    ...
