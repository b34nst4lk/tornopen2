import pytest
from tornado.web import RequestHandler

from tornopen import Field, validate_arguments
from tests import HandlerTestCase, HandlerTestCases
from . import id_fn


class RangedIntegerHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: int = Field(1, le=10, ge=1)):
        ...


class MultipleOfIntegerHandler(RequestHandler):
    @validate_arguments
    async def get(self, param: int = Field(multiple_of=5)):
        ...


cases = HandlerTestCases()
cases.add_test_case(
    HandlerTestCase(
        name="Success ranged interger test cases",
        handler=RangedIntegerHandler,
        path="/",
        expected_code=200,
        test_cases=[
            1,
            5,
            10,
        ],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Failed ranged interger test cases",
        handler=RangedIntegerHandler,
        path="/",
        expected_code=400,
        test_cases=[-1, 200, "hello", 1.31, True],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Success multiple of interger test cases",
        handler=MultipleOfIntegerHandler,
        path="/",
        expected_code=200,
        test_cases=[-5, 5, 10],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Failed multiple of interger test cases",
        handler=MultipleOfIntegerHandler,
        path="/",
        expected_code=400,
        test_cases=[-1, 201, "hello", 1.31, True],
    )
)


@pytest.mark.parametrize("binding, test_case, expected_code", cases, ids=id_fn)
@pytest.mark.gen_test
async def test_field_validation(
    binding, test_case, expected_code, app, http_client, base_url
):
    app.add_handlers(r".*", [binding])

    response = await http_client.fetch(
        f"{base_url}?param={test_case}", raise_error=False
    )
    assert expected_code == response.code
