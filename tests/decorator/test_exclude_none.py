import json

import pytest
from tornado.web import RequestHandler

from tornopen import (
    ResponseBody,
    ValidateArgumentsDecoratorFactory,
)


class OptionalFieldResponse(ResponseBody):
    name: str
    nickname: str | None = None


factory = ValidateArgumentsDecoratorFactory(exclude_none=True)


class ExcludeNoneHandler(RequestHandler):
    @factory
    async def get(self) -> OptionalFieldResponse:
        return OptionalFieldResponse(name="alice")


@pytest.mark.gen_test
async def test_exclude_none_factory_arg_omits_none_fields(app, http_client, base_url):
    app.add_handlers(r".*", [("/", ExcludeNoneHandler)])
    response = await http_client.fetch(base_url, raise_error=False)
    assert response.code == 200
    body = json.loads(response.body)
    assert body == {"name": "alice"}
    assert "nickname" not in body