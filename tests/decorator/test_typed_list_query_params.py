import pytest
from tornado.web import RequestHandler

from tornopen import validate_arguments


class ListIntHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: list[int]):
        assert isinstance(param, list)
        assert all(isinstance(i, int) for i in param)
        self.set_status(200)
        self.write("success")


class OptionalListIntHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: list[int] | None = None):
        assert param is None or isinstance(param, list)
        self.set_status(200)
        self.write("success")


@pytest.mark.gen_test
async def test_typed_list_query_param_split(app, http_client, base_url):
    app.add_handlers(r".*", [("/", ListIntHandler)])
    response = await http_client.fetch(
        f"{base_url}?param=1,2,3", raise_error=False
    )
    assert response.code == 200


@pytest.mark.gen_test
async def test_typed_list_query_param_invalid_element(app, http_client, base_url):
    app.add_handlers(r".*", [("/", ListIntHandler)])
    response = await http_client.fetch(
        f"{base_url}?param=1,abc", raise_error=False
    )
    assert response.code == 400


@pytest.mark.gen_test
async def test_optional_typed_list_query_param_omitted(app, http_client, base_url):
    app.add_handlers(r".*", [("/", OptionalListIntHandler)])
    response = await http_client.fetch(base_url, raise_error=False)
    assert response.code == 200


@pytest.mark.gen_test
async def test_optional_typed_list_query_param_split(app, http_client, base_url):
    app.add_handlers(r".*", [("/", OptionalListIntHandler)])
    response = await http_client.fetch(
        f"{base_url}?param=1,2,3", raise_error=False
    )
    assert response.code == 200