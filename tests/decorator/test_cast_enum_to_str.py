import pytest

from tests import HandlerTestCase, HandlerTestCases
from . import EnumToStrHandler, id_fn

# Test cases
cases = HandlerTestCases()
cases.add_test_case(
    HandlerTestCase(
        name="Successful Enum to String test cases",
        path="/",
        handler=EnumToStrHandler,
        expected_code=200,
        test_cases=["value1", "value2"],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Failed Enum to String test cases",
        path="/",
        handler=EnumToStrHandler,
        expected_code=400,
        test_cases=["alue1", "asdf", None, 1],
    )
)


@pytest.mark.parametrize("binding, test_case, expected_code", cases, ids=id_fn)
@pytest.mark.gen_test
async def test_cast_enum_to_str(
    binding, test_case, expected_code, app, http_client, base_url
):
    app.add_handlers(r".*", [binding])
    url = f"{base_url}?param={test_case}"
    response = await http_client.fetch(url, raise_error=False)
    assert response.code == expected_code


@pytest.mark.parametrize("binding, test_case, expected_code", cases, ids=id_fn)
@pytest.mark.gen_test
async def test_cast_enum_to_str_failed(
    binding, test_case, expected_code, app, http_client, base_url
):
    app.add_handlers(r".*", [binding])
    # fetch without providing url
    response = await http_client.fetch(
        f"{base_url}?param={test_case}", raise_error=False
    )
    assert response.code == expected_code
