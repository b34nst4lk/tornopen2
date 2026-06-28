import json

import pytest
from tornado.web import RequestHandler

from tornopen import RequestBody, validate_arguments


class ComplexRequest(RequestBody):
    integer: int
    string: str
    boolean: bool


class ComplexResponse(RequestBody):
    integer: int
    string: str
    boolean: bool


class ComplexRequestHandler(RequestHandler):
    @validate_arguments
    async def post(
        self,
        path_param: int,
        str_query: str,
        bool_query: bool,
        complex_request: ComplexRequest,
    ) -> ComplexResponse:
        assert isinstance(path_param, int)
        assert isinstance(str_query, str)
        assert isinstance(bool_query, bool)
        assert isinstance(complex_request, ComplexRequest)
        return ComplexResponse(
            integer=complex_request.integer,
            string=complex_request.string,
            boolean=complex_request.boolean,
        )


@pytest.mark.gen_test
async def test_complex_handler(app, http_client, base_url):
    app.add_handlers(r".*", [("/(?P<path_param>.*?)", ComplexRequestHandler)])

    body = ComplexRequest(integer=12, string="sadge", boolean=True).model_dump_json()
    response = await http_client.fetch(
        f"{base_url}/123?str_query=awer&bool_query=true",
        method="POST",
        body=body,
        raise_error=False,
        headers={"Content-Type": "application/json"},
    )
    assert response.code == 200
    assert ComplexResponse(**json.loads(response.body))
