import pytest
from tornado.web import HTTPError as TornadoHTTPError
from tornado.web import RequestHandler

from tornopen import HTTPError, validate_arguments
from tests import HandlerTestCase, HandlerTestCases


class CustomHTTPError(HTTPError):
    def __init__(self, status_code: int, *, error_message: str):
        self.status_code = status_code
        self.error_message = error_message

    def dict(self):
        return {"error_message": self.error_message}


class ErrorRequestHandler(RequestHandler):
    @validate_arguments
    async def get(self, error_type: str):
        match error_type:
            case "generic_error":
                raise HTTPError(
                    status_code=400,
                    error_type="generic_error",
                    error_message="This is my error message",
                )

            case "custom_http_error":
                raise CustomHTTPError(
                    400,
                    error_message="This is my error message",
                )
            case "value_error":
                raise ValueError("this is my error message")
            case "type_error":
                raise TypeError("this is my error message")
            case "tornado_error_400":
                raise TornadoHTTPError(400)
            case "tornado_error_500":
                raise TornadoHTTPError(500)


class DefaultErrorRequestHandler(RequestHandler):
    @validate_arguments
    async def get(self):
        raise HTTPError(
            status_code=400,
            error_type="generic_error",
            error_message="This is my error message",
        )


class CustomErrorRequestHandler(RequestHandler):
    @validate_arguments
    async def get(self):
        raise CustomHTTPError(403, error_message="This is my error message")


cases = HandlerTestCases()
cases.add_test_case(
    HandlerTestCase(
        name="Test HTTPErrors",
        path="/(?P<error_type>.*?)",
        handler=ErrorRequestHandler,
        expected_code=400,
        test_cases=["generic_error", "custom_http_error", "tornado_error_400"],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Test builtin errors",
        path="/(?P<error_type>.*?)",
        handler=ErrorRequestHandler,
        expected_code=500,
        test_cases=["value_error", "type_error", "tornado_error_500"],
    )
)


@pytest.mark.parametrize("binding,test_case,expected_code", cases)
@pytest.mark.gen_test
async def test_errors(binding, test_case, expected_code, app, http_client, base_url):
    app.add_handlers(r".*", [(binding)])

    response = await http_client.fetch(f"{base_url}/{test_case}", raise_error=False)
    assert response.code == expected_code
