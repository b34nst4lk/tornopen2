"""
Note: Query parameters are required by default if they are not annotated as
Optional
"""

import pytest

from tests import HandlerTestCase, HandlerTestCases
from . import (
    BooleanHandler,
    EnumHandler,
    IntegerHandler,
    RequiredGenericListHandler,
    StringHandler,
    id_fn,
)

# Test cases
cases = HandlerTestCases()

cases.add_test_case(
    HandlerTestCase(
        name="Successful integer test cases",
        path="/",
        handler=IntegerHandler,
        expected_code=200,
        test_cases=[0, 1, -1, 123412351234, -123541234125123],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Fail integer test cases",
        path="/",
        handler=IntegerHandler,
        expected_code=400,
        test_cases=["1.12341253", "True", True, "false", False, "a12341", ""],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Successful str test cases",
        path="/",
        handler=StringHandler,
        expected_code=200,
        test_cases=["1.12341253", "True", True, "false", False, "a12341", None, ""],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Successful enum test cases",
        path="/",
        handler=EnumHandler,
        expected_code=200,
        test_cases=["value1", "value2"],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Failed enum test cases",
        path="/",
        handler=EnumHandler,
        expected_code=400,
        test_cases=[None, True, False, 1234, "!2341"],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Success boolean test cases",
        path="/",
        handler=BooleanHandler,
        expected_code=200,
        test_cases=[True, False, 1, 0, "true", "false", "t", "f"],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Failed boolean test cases",
        path="/",
        handler=BooleanHandler,
        expected_code=400,
        test_cases=[None, 1234, "!2341"],
    )
)
cases.add_test_case(
    HandlerTestCase(
        name="Success list query param test cases",
        path="/",
        handler=RequiredGenericListHandler,
        expected_code=200,
        test_cases=["1", "asd", "qweq,123412", ""],
    )
)


@pytest.mark.parametrize("binding, test_case, expected_code", cases, ids=id_fn)
@pytest.mark.gen_test
async def test_query_parameters(
    binding, test_case, expected_code, app, http_client, base_url
):
    app.add_handlers(r".*", [binding])
    url = f"{base_url}?param={test_case}"
    response = await http_client.fetch(url, raise_error=False)
    assert response.code == expected_code


@pytest.mark.parametrize("binding, test_case, expected_code", cases, ids=id_fn)
@pytest.mark.gen_test
async def test_required_query_parameters_not_provided(
    binding, test_case, expected_code, app, http_client, base_url
):
    app.add_handlers(r".*", [binding])
    # fetch without providing url
    response = await http_client.fetch(base_url, raise_error=False)
    assert response.code == 400
