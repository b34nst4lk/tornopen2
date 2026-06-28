import pytest
import json

from tornado.web import RequestHandler

from tornopen import QueryParams, validate_arguments


class Pagination(QueryParams):
    item_limit: int = 20
    item_offset: int = 0


class QueryParamsRequestHandler(RequestHandler):
    @validate_arguments
    async def get(self, pagination: Pagination) -> Pagination:
        assert isinstance(pagination, QueryParams)
        assert isinstance(pagination, Pagination)
        return Pagination


@pytest.mark.gen_test
async def test_query_params_model(app, http_client, base_url):
    app.add_handlers(r".*", [("/", QueryParamsRequestHandler)])
    response = await http_client.fetch(
        f"{base_url}/?item_limit=10&item_offset=1", raise_error=False
    )

    assert response.code == 200
    assert json.loads(response.body) == {"item_limit": 10, "item_offset": 1}
