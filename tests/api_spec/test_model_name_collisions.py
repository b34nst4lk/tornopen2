import pytest
from tornado.web import Application, RequestHandler, url
from tornopen import RequestBody, documenter, validate_arguments
from . import namespace_1, namespace_2


class BigModel(RequestBody):
    field_1: namespace_1.Model
    field_2: namespace_2.Model


class ModelHandler(RequestHandler):
    @validate_arguments
    def post(self, model: namespace_1.Model):
        ...

    @validate_arguments
    def put(self, model: namespace_2.Model):
        ...


class BigModelHandler(RequestHandler):
    @validate_arguments
    def post(self, model: BigModel):
        ...

    @validate_arguments
    def put(self, model: BigModel):
        ...


class BigModel2Handler(RequestHandler):
    @validate_arguments
    def post(self, model: BigModel):
        ...

    @validate_arguments
    def put(self, model: BigModel):
        ...


@pytest.fixture
def app():
    return Application(
        [
            url("/a", ModelHandler),
            url("/b", BigModelHandler),
            url("/c", BigModel2Handler),
        ]
    )


@pytest.mark.gen_test
def test_name_collision(app):
    documenter(app)
