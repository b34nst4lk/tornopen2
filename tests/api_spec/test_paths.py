from typing import NamedTuple

import pytest
from tornado.routing import URLSpec
from tornado.web import Application, RequestHandler, url

from tornopen import documenter, validate_arguments


class OnePathParamHandler(RequestHandler):
    @validate_arguments
    def get(self, path_param: str):
        ...


class TwoPathParamHandler(RequestHandler):
    @validate_arguments
    def get(self, path_param: str, path_param2: str):
        ...


class OnePathParamWithQueryParamHandler(RequestHandler):
    @validate_arguments
    def get(self, path_param: str, query_param: str):
        ...


class TwoPathParamWithQueryParamHandler(RequestHandler):
    @validate_arguments
    def get(self, path_param: str, path_param2: str, query_param: str):
        ...


class RouteTestCase(NamedTuple):
    url: URLSpec
    expected: str


test_routes = [
    RouteTestCase(url("/x/(?P<path_param>)", OnePathParamHandler), "/x/{path_param}"),
    RouteTestCase(
        url("/(?P<path_param>)", OnePathParamHandler),
        "/{path_param}",
    ),
    RouteTestCase(
        url("/y/(.*?)", OnePathParamHandler),
        "/y/{path_param}",
    ),
    RouteTestCase(
        url("/(.*?)", OnePathParamHandler),
        "/{path_param}",
    ),
    RouteTestCase(
        url("/x/(?P<path_param>)/(?P<path_param2>)", TwoPathParamHandler),
        "/x/{path_param}/{path_param2}",
    ),
    RouteTestCase(
        url("/(?P<path_param>)/(?P<path_param2>)", TwoPathParamHandler),
        "/{path_param}/{path_param2}",
    ),
    RouteTestCase(
        url("/y/(.*?)/(.*?)", TwoPathParamHandler),
        "/y/{path_param}/{path_param2}",
    ),
    RouteTestCase(
        url("/(.*?)/(.*?)", TwoPathParamHandler),
        "/{path_param}/{path_param2}",
    ),
    RouteTestCase(
        url("/x/(?P<path_param2>)/(?P<path_param>)", TwoPathParamHandler),
        "/x/{path_param2}/{path_param}",
    ),
    RouteTestCase(
        url("/(?P<path_param2>)/(?P<path_param>)", TwoPathParamHandler),
        "/{path_param2}/{path_param}",
    ),
    RouteTestCase(
        url("/x/(?P<path_param>)", OnePathParamWithQueryParamHandler),
        "/x/{path_param}",
    ),
    RouteTestCase(
        url("/(?P<path_param>)", OnePathParamWithQueryParamHandler),
        "/{path_param}",
    ),
    RouteTestCase(
        url("/y/(.*?)", OnePathParamWithQueryParamHandler),
        "/y/{path_param}",
    ),
    RouteTestCase(
        url("/(.*?)", OnePathParamWithQueryParamHandler),
        "/{path_param}",
    ),
    RouteTestCase(
        url(
            "/x/(?P<path_param>)/(?P<path_param2>)",
            TwoPathParamWithQueryParamHandler,
        ),
        "/x/{path_param}/{path_param2}",
    ),
    RouteTestCase(
        url(
            "/(?P<path_param>)/(?P<path_param2>)",
            TwoPathParamWithQueryParamHandler,
        ),
        "/{path_param}/{path_param2}",
    ),
    RouteTestCase(
        url("/y/(.*?)/(.*?)", TwoPathParamWithQueryParamHandler),
        "/y/{path_param}/{path_param2}",
    ),
    RouteTestCase(
        url("/(.*?)/(.*?)", TwoPathParamWithQueryParamHandler),
        "/{path_param}/{path_param2}",
    ),
    RouteTestCase(
        url("/x/(?P<path_param2>)/(?P<path_param>)", TwoPathParamWithQueryParamHandler),
        "/x/{path_param2}/{path_param}",
    ),
    RouteTestCase(
        url("/(?P<path_param2>)/(?P<path_param>)", TwoPathParamWithQueryParamHandler),
        "/{path_param2}/{path_param}",
    ),
]


# The following setup allows one pair route and handlers to be bounded in the
# Application instance at one time
@pytest.fixture(scope="module", params=test_routes)
def test_route(request):
    return request.param


@pytest.fixture
def app(test_route):
    route = test_route[0]
    return Application([route])


@pytest.mark.gen_test
def test_generated_path(app, test_route):
    app = documenter(app)
    docs = app._documentation.categories
    assert len(docs["undocumented"]["paths"]) == 1
    assert test_route[1] in docs["undocumented"]["paths"]
