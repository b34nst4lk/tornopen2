import json
from typing import Tuple, Type

import pytest
from tornado.web import RequestHandler

from tornopen import (
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
