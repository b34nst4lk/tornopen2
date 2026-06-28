from random import randint
from typing import Dict, NamedTuple, Type

import pytest
from tornado.web import Application, RequestHandler, url

from tornopen import HTTPError, documenter, validate_arguments


class OneErrorHandler(RequestHandler):
    @validate_arguments
    def get(self):
        raise HTTPError(400, error_type="generic_error", error_message="error 1")


class TwoErrorsWithSameErrorcodeHandler(RequestHandler):
    @validate_arguments
    def get(self):
        if randint(0, 1):
            raise HTTPError(400, error_type="generic_error", error_message="error 1")
        else:
            raise HTTPError(400, error_type="generic_error", error_message="error 2")


class TwoErrorsWithDifferentErrorcodeHandler(RequestHandler):
    @validate_arguments
    def get(self):
        if randint(0, 1):
            raise HTTPError(400, error_type="generic_error", error_message="error 1")
        else:
            raise HTTPError(403, error_type="generic_error", error_message="error 2")


class NotFoundError(HTTPError):
    def __init__(self, error_message: str):
        super().__init__(404, error_type="not_found", error_message=error_message)


class SimpleCustomErrorHandler(RequestHandler):
    @validate_arguments
    def get(self):
        raise NotFoundError("thing not found")


class RouteTestCase(NamedTuple):
    handler: Type[RequestHandler]
    expected: Dict[int, str]


class CustomErrorWithoutMessage(HTTPError):
    def __init__(self, status_code):
        self.status_code = status_code

    def __str__(self) -> str:
        return "custom error without message"


class CustomErrorWithoutMessageHandler(RequestHandler):
    @validate_arguments
    def get(self):
        raise CustomErrorWithoutMessage(420)


test_routes = [
    RouteTestCase(OneErrorHandler, {400: "error 1"}),
    RouteTestCase(TwoErrorsWithSameErrorcodeHandler, {400: "error 1 | error 2"}),
    RouteTestCase(
        TwoErrorsWithDifferentErrorcodeHandler, {400: "error 1", 403: "error 2"}
    ),
    RouteTestCase(SimpleCustomErrorHandler, {404: "thing not found"}),
    RouteTestCase(
        CustomErrorWithoutMessageHandler, {420: "custom error without message"}
    ),
]


# The following setup allows one pair route and handlers to be bounded in the
# Application instance at one time
@pytest.fixture(scope="module", params=test_routes)
def test_route(request):
    return request.param


@pytest.fixture
def app(test_route: RouteTestCase):
    route = url("/", test_route.handler)
    return documenter(Application([route]))


@pytest.mark.gen_test
def test_http_error_parsing(app, test_route: RouteTestCase):
    responses = app._documentation.categories["undocumented"]["paths"]["/"]["get"][
        "responses"
    ]

    for error_code, description in test_route.expected.items():
        assert responses[str(error_code)]["description"] == description
