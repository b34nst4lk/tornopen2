import json

import pytest
from tornado.web import RequestHandler

from tornopen import (
    RequestBody,
    UnsupportedMediaTypeError,
    ValidateArgumentsDecoratorFactory,
    validate_arguments,
)


class HelloRequest(RequestBody):
    name: str


class HelloHandler(RequestHandler):
    @validate_arguments
    async def post(self, body: HelloRequest):
        self.write(f"hello {body.name}")


@pytest.mark.gen_test
async def test_form_encoded_body_returns_415(app, http_client, base_url):
    app.add_handlers(r".*", [("/", HelloHandler)])
    response = await http_client.fetch(
        base_url,
        method="POST",
        body="name=alice",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        raise_error=False,
    )
    assert response.code == 415
    body = json.loads(response.body)
    assert body == {
        "error": {
            "type": "unsupported_media_type",
            "message": "Content-Type must be application/json",
        }
    }


@pytest.mark.gen_test
async def test_json_body_still_succeeds(app, http_client, base_url):
    app.add_handlers(r".*", [("/", HelloHandler)])
    response = await http_client.fetch(
        base_url,
        method="POST",
        body=json.dumps({"name": "alice"}),
        headers={"Content-Type": "application/json"},
        raise_error=False,
    )
    assert response.code == 200


@pytest.mark.gen_test
async def test_missing_content_type_with_body_returns_415(app, http_client, base_url):
    app.add_handlers(r".*", [("/", HelloHandler)])
    response = await http_client.fetch(
        base_url,
        method="POST",
        body=json.dumps({"name": "alice"}),
        headers={},
        raise_error=False,
    )
    assert response.code == 415


custom_factory = ValidateArgumentsDecoratorFactory()


@custom_factory.exception_handler(UnsupportedMediaTypeError)
def handle_unsupported_media_type(e: UnsupportedMediaTypeError):
    return 422, json.dumps({"custom": "media type rejected"})


class CustomHandler(RequestHandler):
    @custom_factory
    async def post(self, body: HelloRequest):
        self.write("ok")


@pytest.mark.gen_test
async def test_user_override_of_unsupported_media_type(app, http_client, base_url):
    app.add_handlers(r".*", [("/", CustomHandler)])
    response = await http_client.fetch(
        base_url,
        method="POST",
        body="name=alice",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        raise_error=False,
    )
    assert response.code == 422
    assert json.loads(response.body) == {"custom": "media type rejected"}


class RaiseDirectlyHandler(RequestHandler):
    @validate_arguments
    async def get(self):
        raise UnsupportedMediaTypeError(
            415,
            error_type="unsupported_media_type",
            error_message="raised directly",
        )


@pytest.mark.gen_test
async def test_raise_unsupported_media_type_directly(app, http_client, base_url):
    app.add_handlers(r".*", [("/", RaiseDirectlyHandler)])
    response = await http_client.fetch(base_url, raise_error=False)
    assert response.code == 415
    body = json.loads(response.body)
    assert body["error"]["message"] == "raised directly"