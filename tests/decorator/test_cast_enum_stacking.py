from enum import Enum

import pytest
from tornado.web import RequestHandler

from tornopen import cast_enum_to_str, validate_arguments


class StackingEnum(Enum):
    value1 = "value1"
    value2 = "value2"


class CorrectOrderHandler(RequestHandler):
    @validate_arguments
    @cast_enum_to_str
    async def get(self, param: StackingEnum):
        assert isinstance(param, str)
        assert StackingEnum[param]
        self.set_status(200)
        self.write("success")


@pytest.mark.gen_test
async def test_validate_arguments_outer_cast_enum_inner(app, http_client, base_url):
    app.add_handlers(r".*", [("/", CorrectOrderHandler)])
    response = await http_client.fetch(
        f"{base_url}?param=value1", raise_error=False
    )
    assert response.code == 200


class WrongOrderHandler(RequestHandler):
    @cast_enum_to_str
    @validate_arguments
    async def get(self, param: StackingEnum):
        self.set_status(200)
        self.write("success")


@pytest.mark.xfail(
    reason=(
        "cast_enum_to_str must be stacked BELOW validate_arguments. When "
        "stacked above, the sync wrapper swallows the async return value and "
        "Tornado does not await the coroutine."
    ),
    strict=True,
)
@pytest.mark.gen_test
async def test_wrong_stacking_order_is_unsupported(app, http_client, base_url):
    app.add_handlers(r".*", [("/", WrongOrderHandler)])
    response = await http_client.fetch(
        f"{base_url}?param=value1", raise_error=False
    )
    # If this ever passes, the stacking order requirement has changed.
    assert response.code == 200
    # The handler body should not have run (param not cast, assertions skipped).
    assert response.body != b"success"