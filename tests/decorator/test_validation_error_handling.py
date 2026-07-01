import json
from typing import Tuple, Type

import pytest
from tornado.web import RequestHandler

from tornopen import (
    RequestBody,
    RequestValidationError,
    ValidateArgumentsDecoratorFactory,
    validate_arguments,
)


class DefaultValidationErrorRequestHandler(RequestHandler):
    @validate_arguments
    async def get(self, query_param: int):
        pass


@pytest.mark.gen_test
async def test_default_validation_error(app, http_client, base_url):
    app.add_handlers(r".*", [("/", DefaultValidationErrorRequestHandler)])

    response = await http_client.fetch(f"{base_url}?query_param=abc", raise_error=False)
    assert response.code == 400
    assert json.loads(response.body) == {
        "error": {
            "type": "validation_error",
            "message": (
                "1 validation error for DefaultValidationErrorRequestHandler.get.request\n"
                "query_param\n"
                "  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='abc', input_type=str]\n"
                "    For further information visit https://errors.pydantic.dev/2.1/v/int_parsing"
            ),
        },
    }


custom_validate_arguments = ValidateArgumentsDecoratorFactory()


@custom_validate_arguments.exception_handler(RequestValidationError)
def handle_validation_exception(e: Type[RequestValidationError]) -> Tuple[int, str]:
    status_code = 402
    messages = [f"{error['loc']}" for error in e.errors()]
    return status_code, json.dumps("|".join(messages))


class CustomValidationErrorRequestHandler(RequestHandler):
    @custom_validate_arguments
    async def get(self, query_param: int):
        pass


@pytest.mark.gen_test
async def test_custom_validation_error(app, http_client, base_url):
    app.add_handlers(r".*", [("/", CustomValidationErrorRequestHandler)])

    response = await http_client.fetch(f"{base_url}?query_param=abc", raise_error=False)
    assert response.code == 402
    assert json.loads(response.body) == "('query_param',)"


int_status_factory = ValidateArgumentsDecoratorFactory()


@int_status_factory.exception_handler(RequestValidationError)
def handle_validation_exception_reads_status(e: RequestValidationError):
    # e.status_code must be an int (was "400" string before fix)
    assert isinstance(e.status_code, int)
    assert e.status_code == 400
    return e.status_code, json.dumps({"ok": True})


class IntStatusHandler(RequestHandler):
    @int_status_factory
    async def get(self, query_param: int):
        pass


@pytest.mark.gen_test
async def test_request_validation_error_status_code_is_int(app, http_client, base_url):
    app.add_handlers(r".*", [("/", IntStatusHandler)])
    response = await http_client.fetch(
        f"{base_url}?query_param=abc", raise_error=False
    )
    assert response.code == 400
    assert json.loads(response.body) == {"ok": True}


class IntStatusBody(RequestBody):
    value: int


class IntStatusBodyHandler(RequestHandler):
    @int_status_factory
    async def post(self, body: IntStatusBody):
        pass


@pytest.mark.gen_test
async def test_body_request_validation_error_status_code_is_int(
    app, http_client, base_url
):
    app.add_handlers(r".*", [("/", IntStatusBodyHandler)])
    response = await http_client.fetch(
        base_url,
        method="POST",
        body=json.dumps({"value": "not-an-int"}),
        headers={"Content-Type": "application/json"},
        raise_error=False,
    )
    assert response.code == 400
    assert json.loads(response.body) == {"ok": True}


@pytest.mark.gen_test
async def test_default_validation_error_sets_json_content_type(
    app, http_client, base_url
):
    app.add_handlers(r".*", [("/", DefaultValidationErrorRequestHandler)])
    response = await http_client.fetch(
        f"{base_url}?query_param=abc", raise_error=False
    )
    assert response.code == 400
    assert response.headers["Content-Type"].startswith("application/json")
