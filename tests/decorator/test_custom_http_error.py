import json

import pytest
from tornado.web import RequestHandler

from tornopen import HTTPError, validate_arguments


class CustomErrorWithoutMessage(HTTPError):
    """Subclass that skips the base __init__ (no error_type/error_message)."""

    def __init__(self, status_code: int):
        self.status_code = status_code

    def __str__(self) -> str:
        return "custom error without message"


class CustomErrorWithoutMessageHandler(RequestHandler):
    @validate_arguments
    async def get(self):
        raise CustomErrorWithoutMessage(420)


@pytest.mark.gen_test
async def test_custom_error_without_error_type_does_not_500(app, http_client, base_url):
    app.add_handlers(r".*", [("/", CustomErrorWithoutMessageHandler)])
    response = await http_client.fetch(base_url, raise_error=False)
    assert response.code == 420
    body = json.loads(response.body)
    # dict() should not raise; error_type defaults to None when absent
    assert body["error"]["type"] is None
    assert body["error"]["message"] == ""


class PartiallyInitializedError(HTTPError):
    """Only sets status_code and error_message, skips error_type."""

    def __init__(self, status_code: int, error_message: str):
        self.status_code = status_code
        self.error_message = error_message


class PartiallyInitializedHandler(RequestHandler):
    @validate_arguments
    async def get(self):
        raise PartiallyInitializedError(418, "i am a teapot")


@pytest.mark.gen_test
async def test_custom_error_partial_init(app, http_client, base_url):
    app.add_handlers(r".*", [("/", PartiallyInitializedHandler)])
    response = await http_client.fetch(base_url, raise_error=False)
    assert response.code == 418
    body = json.loads(response.body)
    assert body["error"]["type"] is None
    assert body["error"]["message"] == "i am a teapot"