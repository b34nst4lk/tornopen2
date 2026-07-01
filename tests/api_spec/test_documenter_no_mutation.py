from unittest.mock import patch

import pytest
from tornado.web import Application, RequestHandler, url

from tornopen import documenter, validate_arguments


class PlainHandler(RequestHandler):
    @validate_arguments
    async def get(self, name: str):
        self.write(f"hello {name}")


@pytest.fixture
def app():
    return Application([url(r"/hello/(?P<name>.*?)", PlainHandler)])


def test_documenter_does_not_set_doc_category_on_handler_class(app):
    assert "_doc_category" not in PlainHandler.__dict__
    documenter(app)
    assert "_doc_category" not in PlainHandler.__dict__


def test_documenter_cleans_handler_class_params_on_success(app):
    documenter(app)
    assert not hasattr(PlainHandler, "handler_class_params")


def test_documenter_cleans_handler_class_params_on_exception(app):
    from tornopen.api_spec import core as core_module

    with patch.object(
        core_module.TornOpenAPISpec, "path", side_effect=RuntimeError("boom")
    ):
        with pytest.raises(RuntimeError, match="boom"):
            documenter(app)
    assert not hasattr(PlainHandler, "handler_class_params")